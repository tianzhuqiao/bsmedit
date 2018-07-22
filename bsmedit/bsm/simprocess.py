import sys, os
import traceback
import inspect
import re
import ctypes
import six.moves.queue as Queue
import six
import numpy as np
from . import csim

SC_OBJ_UNKNOWN = 0
SC_OBJ_SIGNAL = 1
SC_OBJ_INPUT = 2
SC_OBJ_OUTPUT = 3
SC_OBJ_INOUT = 4
SC_OBJ_CLOCK = 5
SC_OBJ_XSC_PROP = 6
SC_OBJ_XSC_ARRAY_ITEM = 7
SC_OBJ_MODULE = 8
SC_OBJ_XSC_ARRAY = 9

BSM_FS = 0
BSM_PS = 1
BSM_NS = 2
BSM_US = 3
BSM_MS = 4
BSM_SEC = 5

BSM_POSEDGE = 0
BSM_NEGEDGE = 1
BSM_BOTHEDGE = 2
BSM_NONEEDGE = 3

BSM_TRACE_VCD = 0
BSM_TRACE_SIMPLE = 1

BSM_DATA_STRING = 0
BSM_DATA_FLOAT = 1
BSM_DATA_INT = 2
BSM_DATA_UINT = 3

class SimSysC(object):
    """class to load the systemc simulation"""
    def __init__(self, dll):
        self.ctx_callback = None
        self.valid = False
        try:
            folder = os.path.dirname(os.path.realpath(__file__))
            self.csim = csim.init_dll(dll, os.path.join(folder, 'bsm.h'))

            # create simulation
            ctx = self.csim.sim_context()
            self.csim.bsm_sim_top(ctx)
            self.ctx = csim.SStructWrapper(ctx)

            # load all objects
            obj = self.csim.sim_object()
            rtn = self.csim.ctx_first_object(obj)
            self.sim_objects = {}
            while rtn:
                wobj = csim.SStructWrapper(obj)
                self.check_object(wobj)
                if obj.readable:
                    self.csim.ctx_read(obj)
                self.sim_objects[wobj.name] = wobj
                obj = self.csim.sim_object()
                rtn = self.csim.ctx_next_object(obj)
            self.valid = True
        except:
            traceback.print_exc(file=sys.stdout)

    def __getattr__(self, item):
        # so we can call simulation functions 'directly'
        if item == 'csim':
            raise AttributeError()
        if 'ctx' in item:
            return getattr(self.csim, item)
        raise AttributeError()

    def is_valid(self):
        return self.valid

    def get_objects(self):
        if not self.is_valid():
            return {}
        return self.sim_objects

    def check_object(self, obj):
        if not obj or (not isinstance(obj, csim.SStructWrapper)):
            return

        kinds = {'sc_signal':SC_OBJ_SIGNAL, 'sc_in':SC_OBJ_INPUT,
                 'sc_out':SC_OBJ_OUTPUT, 'sc_in_out':SC_OBJ_INOUT,
                 'sc_clock':SC_OBJ_CLOCK, 'xsc_property':SC_OBJ_XSC_PROP,
                 'sc_module':SC_OBJ_MODULE, 'xsc_array':SC_OBJ_XSC_ARRAY}
        kind = kinds.get(obj.kind, SC_OBJ_UNKNOWN)
        if kind == SC_OBJ_XSC_PROP and '[' in obj.name and ']' in obj.name:
            kind = SC_OBJ_XSC_ARRAY_ITEM
        obj.nkind = kind
        obj.register = (kind in (SC_OBJ_SIGNAL, SC_OBJ_INPUT, SC_OBJ_OUTPUT,
                                 SC_OBJ_INOUT, SC_OBJ_CLOCK, SC_OBJ_XSC_PROP,
                                 SC_OBJ_XSC_ARRAY_ITEM))

        # retrieve the parent module from name
        name = obj.name
        idx = name.rfind('.')
        if kind == SC_OBJ_XSC_ARRAY_ITEM:
            idx = name.rfind('[')
        obj.parent = ""
        if idx != -1:
            obj.parent = name[0:idx]

    def find_object(self, obj):
        if not self.is_valid():
            return None
        if isinstance(obj, six.string_types):
            obj = self.sim_objects.get(obj, None)
        if obj and isinstance(obj, csim.SStructWrapper) and \
           obj.is_type(self.csim.sim_object):
            return obj
        return None

    def ctx_read(self, obj):
        obj = self.find_object(obj)
        if obj is None:
            return ""

        obj = obj()
        if not obj.readable:
            return ""

        val = ''
        if self.csim.ctx_read(obj):
            if obj.value.type == BSM_DATA_STRING:
                val = ctypes.cast(obj.value.sValue, ctypes.c_char_p).value.decode()
            elif obj.value.type == BSM_DATA_FLOAT:
                val = obj.value.fValue
            elif obj.value.type == BSM_DATA_INT:
                val = obj.value.iValue
            elif obj.value.type == BSM_DATA_UINT:
                val = obj.value.uValue
        return val

    def ctx_write(self, obj, value):
        obj = self.find_object(obj)
        if obj is None:
            return False

        obj = obj()

        if not obj.writable:
            return False

        if obj.value.type == BSM_DATA_STRING:
            obj.value.sValue = (ctypes.c_byte*len(obj.value.sValue))(*bytearray(value))
        elif obj.value.type == BSM_DATA_FLOAT:
            obj.value.fValue = float(value)
        elif obj.value.type == BSM_DATA_INT:
            obj.value.iValue = int(value)
        elif obj.value.type == BSM_DATA_UINT:
            obj.value.uValue = int(value)
        else:
            return False

        return self.csim.ctx_write(obj)

    def ctx_time_str(self):
        if not self.is_valid():
            return ""
        buf = ctypes.create_string_buffer(256)
        self.csim.ctx_time_str(ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        return ctypes.cast(buf, ctypes.c_char_p).value.decode()

    def ctx_set_callback(self, fun):
        # the callback fun should take an integer arguments and return an
        # integer argument. Return 1 from the callback function will pause
        # the simulation
        if not self.is_valid():
            return False
        self.ctx_callback = csim.callback(self.csim.bsm_callback(), fun)
        self.csim.ctx_set_callback(self.ctx_callback)
        return True

class BpCond(object):
    """
    The class to handle the breakpoint condition. One breakpoint may trigger on
    multiple conditions, and each condition may trigger on multiple hit-counts.
    """
    def __init__(self, condition, hitcount):
        # single condition
        self.condition = condition
        self.valid = True
        # multiple hitcounts on multiple conditions
        # since they trigger on the same condition, it only needs to evaluate
        # the condition once
        self.hitcount = []
        if isinstance(hitcount, list):
            self.hitcount = hitcount
        else:
            self.hitcount = [hitcount]
        # generate the hitcount set to remove the duplicated hitcounts, so
        # they are not evaluated multiple times
        self.hitcountset = set(self.hitcount)
        # the number of the breakpoint condition being triggered since it is set
        self.hitsofar = 0

    def add_hitcount(self, hitcount):
        # append the hitcount
        self.hitcount.append(hitcount)
        # regenerate the set
        self.hitcountset = set(self.hitcount)

    def del_hitcount(self, hitcount):
        idx = self.hitcount.index(hitcount)
        if idx == -1:
            return
        del self.hitcount[idx]
        self.hitcountset = set(self.hitcount)

    def triggered(self, val, valp):
        # invalid condition, no need to check
        if not self.valid:
            return None
        try:
            trigger = False
            # if the condition is empty, trigger if the value has changed
            if not self.condition:
                trigger = (val != valp)
            else:
                # replace the '$' with the current value, then evaluate it
                cond = self.condition.replace('$', str(val))
                trigger = eval(cond)

            if trigger:
                self.hitsofar += 1
                for hc in self.hitcountset:
                    # if the hitcount is empty, always trigger
                    if not hc:
                        return (hc, self.hitsofar)
                    # replace the '#' with the hitsofar
                    hce = hc.replace('#', str(self.hitsofar))
                    bk = eval(hce)
                    if bk is True:
                        return (hc, self.hitsofar)
        except:
            traceback.print_exc(file=sys.stdout)
            self.valid = False
        return None

    def __len__(self):
        # return the hitcount length, it may be called to determine whether
        # the condition is empty and can be deleted.
        return len(self.hitcount)

class Breakpoint(object):
    def __init__(self, name):
        self.name = name
        # the BpCond list
        self.condition = []

    def add_cond(self, cond, hitcount):
        for cnd in self.condition:
            # add hitcount to the existing condition
            if cnd.condition == cond:
                cnd.add_hitcount(hitcount)
                return
        # create a new BpCond instance
        self.condition.append(BpCond(cond, hitcount))

    def del_cond(self, cond, hitcount):
        for cnd in self.condition:
            if cnd.condition == cond:
                cnd.del_hitcount(hitcount)
                if len(cnd) <= 0:
                    del self.condition[self.condition.index(cnd)]
                break

    def triggered(self, val, valp):
        for cnd in self.condition:
            trigger = cnd.triggered(val, valp)
            if trigger is not None:
                return (cnd.condition, trigger[0], trigger[1])
        return None

    def __len__(self):
        # it may be called to determine whether the bp is empty and can be
        # deleted
        return len(self.condition)

class BpList(object):
    def __init__(self):
        self.data = {}
        self.data_raw = []
    def add(self, objs, objectsdict):
        resp = {}
        for name, cond, hitcount in objs:
            resp[name] = False
            if name not in six.iterkeys(objectsdict):
                continue
            if name in six.iterkeys(self.data):
                self.data[name].add_cond(cond, hitcount)
            else:
                self.data[name] = Breakpoint(name)
                self.data[name].add_cond(cond, hitcount)
            resp[name] = True
            self.data_raw.append([name, cond, hitcount])
        return resp

    def delete(self, objs, objectsdict):
        resp = {}
        for name, cond, hitcount in objs:
            resp[name] = False
            if name not in six.iterkeys(objectsdict):
                continue
            if name not in six.iterkeys(self.data):
                continue
            self.data[name].del_cond(cond, hitcount)
            if len(self.data[name]) <= 0:
                del self.data[name]
            resp[name] = True
            idx = self.data_raw.index([name, cond, hitcount])
            del self.data_raw[idx]
        return resp

    def get_bp(self):
        return self.data

# the list of registers to be monitored
class MonitorList(object):
    def __init__(self):
        self.data = {}
        self.monitor = []
    def add(self, objs, objsdict):
        resp = {o:False for o in objs}
        if objsdict:
            objs = [o for o in objs if o in six.iterkeys(objsdict)]
        for obj in objs:
            self.data[obj] = self.data.get(obj, 0) + 1
            resp[obj] = True
        self.update_monitor(objsdict)
        return resp
    def delete(self, objs, objsdict):
        resp = {o:False for o in objs}
        if objsdict:
            objs = [o for o in objs if o in six.iterkeys(objsdict)]
        for obj in objs:
            if obj in six.iterkeys(self.data):
                resp[obj] = True
                self.data[obj] -= 1
                if self.data[obj] <= 0:
                    del self.data[obj]
        self.update_monitor(objsdict)
        return resp
    def update_monitor(self, objsdict=None):
        if objsdict:
            regs = list(objsdict.keys())
            self.monitor = [k for k in six.iterkeys(self.data) if k in regs]
        else:
            self.monitor = list(self.data.keys())
    def get_monitor(self):
        return self.monitor

class SimInterface(object):
    all_interfaces = {}
    def __init__(self):
        pass
    def __call__(self, fun):
        argspec = inspect.getargspec(fun)
        argspec = inspect.formatargspec(*argspec)
        temp = argspec.split(',')
        interf = {'args': '('+', '.join(temp[1:]).strip(),
                  'doc': fun.__doc__}
        SimInterface.all_interfaces[fun.__name__] = interf#'('+', '.join(temp[1:]).strip()
        return fun

class SimCommand(object):
    sim_units = {'fs':BSM_FS, 'ps':BSM_PS, 'ns':BSM_NS, 'us':BSM_US,
                 'ms':BSM_MS, 's':BSM_SEC}
    trigger_type = {'posneg': BSM_BOTHEDGE, 'pos': BSM_POSEDGE,
                    'neg': BSM_NEGEDGE, 'none': BSM_NONEEDGE,
                    BSM_BOTHEDGE:BSM_BOTHEDGE, BSM_POSEDGE:BSM_POSEDGE,
                    BSM_NEGEDGE:BSM_NEGEDGE, BSM_NONEEDGE:BSM_NONEEDGE}
    tfile_format = {'bsm': BSM_TRACE_SIMPLE, 'vcd': BSM_TRACE_VCD,
                    BSM_TRACE_SIMPLE: BSM_TRACE_SIMPLE,
                    BSM_TRACE_VCD:BSM_TRACE_VCD}
    def __init__(self, qcmd, qresp):
        self.simengine = None
        self.monitor = MonitorList()
        self.breakpoint = BpList()
        self.bp_values_prev = {}
        self.tfile = {}
        self.tfile_raw = {}
        self.tbuf = {}
        self.qcmd = qcmd
        self.qresp = qresp
        self.running = False
        self.sim_step = 20
        self.sim_unit_step = BSM_NS
        self.sim_total = -1 # -1 --> run forever
        self.sim_unit_total = BSM_NS
        self.sim_total_sec = -1

    def __del__(self):
        if self.is_valid():
            self.simengine.ctx_stop()

    def response(self, resp):
        self.qresp.put(resp)

    def check_bp(self, n):
        """check the breakpoints"""
        bps = self.breakpoint.get_bp()
        if len(bps) <= 0:
            return 0
        objs = list(bps.keys())
        values = self.read(objects=objs)
        for name, bp in six.iteritems(bps):
            t = bp.triggered(values[name], self.bp_values_prev[name])
            if t is not None:
                # set the important filed to be True, so the client will
                # never ignore the events
                resp = {'cmd': 'breakpoint_triggered', 'important': True,
                        'value': [name, t[0], t[1], t[2]]}
                self.response(resp)
                self.running = False
                self.bp_values_prev.update(values)
                return 1
        self.bp_values_prev.update(values)
        return 0

    @SimInterface()
    def is_valid(self, **kwargs):
        if self.simengine and self.simengine.is_valid():
            return True
        return False

    @SimInterface()
    def load(self, filename="", **kwargs):
        if not os.path.exists(filename):
            return None
        self.simengine = SimSysC(filename)
        if self.is_valid():
            print(self.simengine.ctx.version)
            print(self.simengine.ctx.copyright)
            self.simengine.ctx_set_callback(self.check_bp)
            objs = {}
            for name, obj in six.iteritems(self.simengine.sim_objects):
                objs[name] = {'name':obj.name, 'basename':obj.basename,
                              'kind':obj.kind, 'value':"",
                              'writable':obj.writable, 'readable':obj.readable,
                              'numeric':obj.numeric, 'parent':obj.parent,
                              'nkind':obj.nkind, 'register':obj.register}
            return objs
        return None

    @SimInterface()
    def step(self, running=False, **kwargs):
        """
        proceed the simulation with one step

        The step is set with set_parameter(). The GUI components will be updated
        after the running.

        The breakpoints are checked at each delta cycle.
        """
        if not self.is_valid():
            return False

        sim_step = self.sim_step
        sim_unit = self.sim_unit_step
        if self.sim_total_sec > 0:
            # not run infinitely
            t = self.sim_total_sec - self.simengine.ctx_time()
            if t > 0:
                # step should not exceed the remaining simulation time
                scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
                sim_step = min(sim_step, int(t*scale[sim_unit]+0.5))
            else:
                # finished, no need to run
                self.running = False
                return False
        self.running = (running and (sim_step == self.sim_step))
        self.simengine.ctx_start(sim_step, sim_unit)

        return True

    @SimInterface()
    def pause(self, **kwargs):
        """pause the simulation"""
        self.running = False
        return True

    def _parse_time(self, t):
        """
        parse the time in time+unit format

        For example,
            1) 1.5us will return (1.5, BSM_US)
            2) 100 will return (100, None), where unit is None (current one will
               be used)
        """
        pattern = r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?:\s)*(fs|ps|ns|us|ms|s|)"
        x = re.match(pattern, str(t))
        if x:
            if x.group(2):
                unit = self.sim_units.get(x.group(2), None)
                if unit is None:
                    raise ValueError("unknown time format: " + str(time))
                return float(x.group(1)), unit
            else:
                return float(x.group(1)), None
        return None, None

    @SimInterface()
    def set_parameter(self, step=None, total=None, more=False, **kwargs):
        """set the parameters"""
        step, step_unit = self._parse_time(step)
        total, total_unit = self._parse_time(total)
        if step_unit is not None:
            self.sim_unit_step = step_unit
        if step is not None:
            self.sim_step = step
        if total is not None:
            self.sim_total = total
        if total_unit is not None:
            self.sim_unit_total = total_unit
        if self.sim_total > 0:
            scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
            self.sim_total_sec = self.sim_total/scale[self.sim_unit_total]
            if more:
                self.sim_total_sec += self.time_stamp(format='second')
        else:
            self.sim_total_sec = -1
        return self.get_parameter()

    @SimInterface()
    def get_parameter(self, **kwargs):
        return {'step_unit':self.sim_unit_step, 'step': self.sim_step,
                'total':self.sim_total, 'total_unit':self.sim_unit_total}

    def _object_list(self, objs):
        """help function to generate object list"""
        if isinstance(objs, six.string_types):
            return [objs]
        elif isinstance(objs, (list, tuple)):
            return objs
        else:
            raise ValueError()

    @SimInterface()
    def read(self, objects=None, **kwargs):
        """
        get the values of the registers

        If objects only contains one register, its value will be returned if
        succeed; otherwise a dictionary is returned, where the keys are the
        items in objects.

        Example: read a single register
        >>> read('top.sig_bool', True)

        Example: read multiple registers from the same simulation
        >>> read(['top.sig_bool', 'top.sig_cos']
        """
        if not self.is_valid():
            return {}

        if not objects:
            # empty list, read all the monitored objects
            objects = self.monitor.get_monitor()
        else:
            objects = self._object_list(objects)

        values = {}
        for obj in objects:
            values[obj] = self.simengine.ctx_read(obj)
        return values

    @SimInterface()
    def write(self, objects=None, **kwargs):
        """
        write the value to the registers

        objs should be a dictionary where the keys are the register name.
        Due to the two-step mechanism in SystemC, the value will be updated
        after the next delta cycle. That is, if a read() is called after
        write(), it will return the previous value.

        Example:
        >>> a = read('top.sig_int', True)
        >>> write({'top.sig_int': 100}, True)
        >>> b = read('top.sig_int', True) # a == b
        >>> step()
        >>> c = read('top.sig_int', True)
        """
        if not self.is_valid():
            return False
        if not objects or not isinstance(objects, dict):
            return False
        resp = {}
        for name, value in six.iteritems(objects):
            resp[name] = self.simengine.ctx_write(name, value)
        return resp

    @SimInterface()
    def time_stamp(self, insecond=False, **kwargs):
        """return the current simulation time stamp in string"""
        if not self.is_valid():
            return 0.0
        if insecond:
            #in second
            return self.simengine.ctx_time()
        return self.simengine.ctx_time_str()

    @SimInterface()
    def trace_file(self, filename='', name='', fmt='bsm', valid=None,
                   trigger='posneg', **kwargs):
        """
        dump object values to a file

        filename:
            trace filename
        name:
            register name
        fmt:
            'bsm': only output the register value, one per line (Default)
            'vcd': output the SystemC VCD format data
        valid:
            the trigger signal. If it is none, the write-operation will be
            triggered by the register itself
        trigger:
            'posneg': trigger on both rising and falling edges
            'pos': trigger on rising edge
            'neg': trigger on falling edge
            'none': no triggering
        """
        if not self.is_valid():
            return False
        raw = [filename, name, fmt, valid, trigger]

        if not filename:
            filename = name
        if filename in self.tfile:
            return False

        obj = self.simengine.find_object(name)
        if obj is None:
            return False
        if valid:
            valid = self.simengine.find_object(valid)
            if valid is None:
                return False
            valid = valid()
        fmt = self.tfile_format.get(fmt, None)
        trigger = self.trigger_type.get(trigger, None)
        if fmt is None:
            raise ValueError("Not supported trace type: " + str(raw[0]))
        if trigger is None:
            raise ValueError("Not supported trigger type: " + str(raw[2]))
        trace = csim.SStructWrapper(self.simengine.csim.sim_trace_file())
        trace.name = filename
        trace.type = fmt
        if self.simengine.ctx_create_trace_file(trace()):
            self.simengine.ctx_trace_file(trace(), obj(), valid, trigger)
            self.tfile[filename] = {'trace': trace, 'raw':raw}
            return True

        return False

    @SimInterface()
    def close_trace_file(self, filename="", **kwargs):
        """stop dumping to a file"""
        if filename not in self.tfile:
            return False
        trace = self.tfile[filename]['trace']
        if self.simengine.ctx_close_trace_file(trace()):
            del self.tfile[filename]
            return True
        return False

    @SimInterface()
    def get_trace_files(self, **kwargs):
        """return all the trace files"""
        return {b:self.tfile[b]['raw'] for b in self.tfile}

    @SimInterface()
    def trace_buf(self, name='', size=256, valid=None, trigger="posneg",
                  **kwargs):
        """start dumping the register to a numpy array"""
        if not self.is_valid():
            return False
        # used to return the traced buffer list
        raw = [size, valid, trigger]
        obj = self.simengine.find_object(name)
        if obj is None:
            return False

        if valid:
            valid = self.simengine.find_object(valid)
            if valid is None:
                return False
            valid = valid()

        trigger = self.trigger_type.get(trigger, None)
        if trigger is None:
            raise ValueError("Not supported trigger type: " + str(raw[2]))

        if name in self.tbuf:
            # remove the existing trace
            trace = self.tbuf[name]['trace']
            self.simengine.ctx_close_trace_buf(trace())
            del self.tbuf[name]

        trace = csim.SStructWrapper(self.simengine.csim.sim_trace_buf())
        trace.name = name
        trace.size = size
        data = np.zeros((size))
        trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        if self.simengine.ctx_create_trace_buf(trace()):
            self.simengine.ctx_trace_buf(trace(), obj(), valid, trigger)
            self.tbuf[name] = {'trace':trace, 'data':data, 'raw':raw}
        return True

    @SimInterface()
    def close_trace_buf(self, name='', **kwargs):
        """stop dumping to a numpy array"""
        if not name in self.tbuf:
            return False

        trace = self.tbuf[name]['trace']
        if self.simengine.ctx_close_trace_buf(trace()):
            del self.tbuf[name]
            return True
        return False

    @SimInterface()
    def read_buf(self, objects=None, **kwargs):
        """
        read the traced buffer to an numpy array

        If the buffer is previous traced by calling trace_buf, the array with
        previous defined size will return; otherwise the trace_buf will be
        called with default arguments first.
        """
        if not self.is_valid():
            return {}
        if not objects:
            # no object defined, return all the traced buffers
            objects = list(self.tbuf.keys())
        else:
            objects = self._object_list(objects)

        resp = {}
        for name in objects:
            obj = self.simengine.find_object(name)
            if obj is None:
                continue

            if name not in self.tbuf:
                # if not traced yet, trace it now with default settings
                self.trace_buf(name=name)

            self.simengine.ctx_read_trace_buf(self.tbuf[name]['trace']())
            resp[name] = self.tbuf[name]['data']
        return resp


    @SimInterface()
    def get_trace_bufs(self, **kwargs):
        return {b:self.tbuf[b]['raw'] for b in self.tbuf}

    @SimInterface()
    def monitor_signal(self, objects=None, **kwargs):
        """
        monitor the register value

        At end of each step, the simulation process will report the value
        """
        if not self.is_valid() or not objects:
            return {}

        objects = self._object_list(objects)
        return self.monitor.add(objects, self.simengine.sim_objects)

    @SimInterface()
    def unmonitor_signal(self, objects=None, **kwargs):
        """stop monitoring the register"""
        if not self.is_valid() or not objects:
            return {}

        objects = self._object_list(objects)
        return self.monitor.delete(objects, self.simengine.get_objects())

    @SimInterface()
    def get_monitored_signals(self, **kwargs):
        """get the list of the monitored signals"""
        return self.monitor.get_monitor()

    @SimInterface()
    def get_status(self, **kwargs):
        return {'valid': self.is_valid(), 'running': self.running}

    @SimInterface()
    def add_breakpoint(self, name="", condition=None, hitcount=None, **kwargs):
        """
        add the breakpoint

        bp = (name, condition, hitcount) or name
        """
        if not self.is_valid():
            return {}
        if not self.simengine.find_object(name):
            raise ValueError("Invalid object %s"%name)
        objs = self.breakpoint.add([[name, condition, hitcount]],
                                   self.simengine.get_objects())
        bps = self.breakpoint.get_bp()
        # update the current breakpoint values before they are
        # checked next time
        self.bp_values_prev = self.read(objects=list(bps.keys()))
        return objs

    @SimInterface()
    def del_breakpoint(self, name="", condition=None, hitcount=None, **kwargs):
        """delete the breakpoint"""
        if not self.is_valid():
            return {}

        if not self.simengine.find_object(name):
            raise ValueError("Invalid object %s"%name)
        return self.breakpoint.delete([[name, condition, hitcount]],
                                      self.simengine.get_objects())

    @SimInterface()
    def get_breakpoints(self, **kwargs):
        """get all the breakpoints"""
        return self.breakpoint.data_raw

    @SimInterface()
    def get_interfaces(self, **kwargs):
        return SimInterface.all_interfaces

    def process(self):
        while True:
            running = self.running
            if self.running:
                if not self.is_valid():
                    self.running = False
                else:
                    remain = self.sim_total_sec - self.simengine.ctx_time()
                    if not ((self.sim_total_sec <= 0) or (remain > 0)):
                        # pause simulation when reach the simulation time
                        self.running = False
            try:
                if self.running:
                    self.step(running=self.running)
                if self.running:
                    # In running mode, return immediately so that the simulation
                    # can be triggered as soon as possible
                    cmd = self.qcmd.get_nowait()
                else:
                    cmd = self.qcmd.get()
                if not cmd:
                    continue

                command = cmd.get('cmd', '')
                args = cmd.get('arguments', {})

                # the response sends back the original command and one more
                # field, i.e., 'value'
                resp = cmd
                resp['value'] = False
                if not command and not args:
                    raise ValueError("unknown command: ", cmd)

                if command == 'exit':
                    return False

                if not args.get('silent', True):
                    print(cmd)

                if hasattr(self, command):
                    fun = getattr(self, command)
                    resp['value'] = fun(**args)
                else:
                    raise ValueError('unknown command: ', cmd)

                self.response(resp)
                if self.running != running:
                    # automatically report status change
                    self.response({'cmd':'get_status', 'value':self.get_status()})
            except Queue.Empty:
                pass
            except:
                if resp:
                    self.response(resp)
                traceback.print_exc(file=sys.stdout)

class SimLogger(object):
    def __init__(self, qresp):
        self.qresp = qresp

    def write(self, buf):
        self.qresp.put({'cmd':'write_out', 'important':True, 'value':buf})

    def flush(self):
        pass

def sim_process(qresp, qcmd):
    log = SimLogger(qresp)
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = log
    sys.stderr = log
    proc = SimCommand(qcmd, qresp)
    # infinite loop
    proc.process()
    sys.stdout = stdout
    sys.stderr = stderr
