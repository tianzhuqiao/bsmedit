import sys, os
import traceback
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

class SimEngine(object):

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
            pass

    def __getattr__(self, item):
        # so we can call simulation functions 'directly'
        if 'ctx' in item:
            return getattr(self.csim, item)
        return None

    def is_valid(self):
        return self.valid

    def get_objects(self):
        if not self.is_valid():
            return {}
        return self.sim_objects

    def check_object(self, obj):
        if not obj or (not isinstance(obj, csim.SStructWrapper)):
            return

        kinds = {'sc_signal':SC_OBJ_SIGNAL, 'sc_in': SC_OBJ_INPUT,
                 'sc_out':SC_OBJ_OUTPUT, 'sc_in_out': SC_OBJ_INOUT,
                 'sc_clock':SC_OBJ_CLOCK, 'xsc_property': SC_OBJ_XSC_PROP,
                 'sc_module':SC_OBJ_MODULE, 'xsc_array': SC_OBJ_XSC_ARRAY}
        kind = kinds.get(obj.kind, SC_OBJ_UNKNOWN)
        if kind == SC_OBJ_XSC_PROP and '[' in obj.name and ']' in obj['name']:
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
        if obj and obj.is_type(self.csim.sim_object):
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
                val = ctypes.cast(obj.value.sValue, ctypes.c_char_p).value
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
        return ctypes.cast(buf, ctypes.c_char_p).value

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

class ProcessCommand(object):
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
        if self.simengine and self.simengine.is_valid():
            self.simengine.ctx_stop()

    def response(self, resp):
        self.qresp.put(resp)

    def load(self, filename):
        self.simengine = SimEngine(filename)
        if self.simengine.is_valid():
            print(self.simengine.ctx['version'])
            print(self.simengine.ctx['copyright'])
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

    def check_bp(self, n):
        """check the breakpoints"""
        bps = self.breakpoint.get_bp()
        if len(bps) <= 0:
            return 0
        objs = list(bps.keys())
        values = self.read(objs)
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

    def step(self, running):
        """run simulation by one step"""
        if not self.simengine or not self.simengine.is_valid():
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

    def set_parameter(self, param):
        """set the parameters"""
        self.sim_unit_step = param.get('unitStep', self.sim_unit_step)
        self.sim_step = param.get('step', self.sim_step)
        self.sim_total = param.get('total', self.sim_total)
        self.sim_unit_total = param.get('unitTotal', self.sim_unit_total)
        more = param.get('more', False)
        if self.sim_total > 0:
            scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
            self.sim_total_sec = self.sim_total/scale[self.sim_unit_total]
            if more:
                self.sim_total_sec += self.time_stamp(True)
        else:
            self.sim_total_sec = -1
        return True

    def read(self, objects):
        """read the register value"""
        if not self.simengine or not self.simengine.is_valid():
            return {}
        if not objects:
            # empty list, read all the monitored objects
            objects = self.monitor.get_monitor()
        values = {}
        for obj in objects:
            values[obj] = self.simengine.ctx_read(obj)
        return values

    def write(self, objects):
        """write the register value"""
        if not self.simengine or not self.simengine.is_valid():
            return {}
        resp = {}
        for name, value in six.iteritems(objects):
            resp[name] = self.simengine.ctx_write(name, value)
        return resp

    def time_stamp(self, insecond):
        """return the current simulation time stamp in string"""
        if not self.simengine or not self.simengine.is_valid():
            return 0.0
        if insecond:
            #in second
            return self.simengine.ctx_time()
        return self.simengine.ctx_time_str()

    def trace_file(self, args):
        """dump the file"""
        if not self.simengine or not self.simengine.is_valid():
            return False
        name = args.get('name', None)
        ntype = args.get('ntype', BSM_TRACE_SIMPLE)
        valid = args.get('valid', None)
        trigger = args.get('trigger', BSM_BOTHEDGE)
        obj = self.simengine.find_object(name)
        if obj is None:
            return False
        if valid:
            valid = self.simengine.find_object(valid)
            if valid is None:
                return False
            valid = valid()

        trace = csim.SStructWrapper(self.simengine.csim.sim_trace_file())
        trace.name = name
        trace.type = ntype
        if self.simengine.ctx_create_trace_file(trace()):
            self.simengine.ctx_trace_file(trace(), obj(), valid, trigger)
            self.tfile[name] = trace
            self.tfile_raw[name] = [ntype, valid, trigger]
            return True

        return False

    def trace_buf(self, args):
        """trace the buffer"""
        if not self.simengine or not self.simengine.is_valid():
            return False
        name = args.get('name', None)
        size = args.get('size', 256)
        valid = args.get('valid', None)
        trigger = args.get('trigger', BSM_BOTHEDGE)
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


    def read_buf(self, objects):
        if not self.simengine or not self.simengine.is_valid():
            return {}
        if objects == []:
            # no object defined, return all the traced buffers
            objects = list(self.tbuf.keys())
        resp = {}
        for name in objects:
            obj = self.simengine.find_object(name)
            if obj is None:
                continue

            if name not in self.tbuf:
                # if not traced yet, trace it now with default settings
                self.trace_buf({'name':name})

            self.simengine.ctx_read_trace_buf(self.tbuf[name]['trace']())
            resp[name] = self.tbuf[name]['data']
        return resp

    def process(self):
        while True:
            running = self.running
            if self.running:
                if not self.simengine or not self.simengine.is_valid():
                    self.running = False
                else:
                    remain = self.sim_total_sec - self.simengine.ctx_time()
                    if not ((self.sim_total_sec <= 0) or (remain > 0)):
                        # pause simulation when reach the simulation time
                        self.running = False
            try:
                if self.running:
                    self.step(self.running)
                if self.running:
                    # In running mode, return immediately so that the simulation
                    # can be triggered as soon as possible
                    cmd = self.qcmd.get_nowait()
                else:
                    cmd = self.qcmd.get()
                if not cmd:
                    continue
                engine = self.simengine
                sim_objects = {}
                if engine:
                    sim_objects = engine.sim_objects

                command = cmd.get('cmd', '')
                args = cmd.get('arguments', {})

                # the response sends back the original command and one more
                # field, i.e., 'value'
                resp = cmd
                resp['value'] = False
                if not command and not args:
                    print("unknown command: ")
                    self.response(resp)
                    continue

                if command == 'exit':
                    return False

                if not args.get('silent', True):
                    print(cmd)

                if command == 'load':
                    resp['value'] = self.load(args.get('filename', None))
                elif command == 'step':
                    resp['value'] = self.step(args.get('running', False))
                    args['running'] = self.running
                elif command == 'pause':
                    self.running = False
                    resp['value'] = True
                elif command == 'monitor_signal':
                    objs = self.monitor.add(args['objects'], sim_objects)
                    resp['value'] = objs
                elif command == 'unmonitor_signal':
                    objs = self.monitor.delete(args['objects'], sim_objects)
                    resp['value'] = objs
                elif command == 'get_monitored_signal':
                    resp['value'] = self.monitor.get_monitor()
                elif command == 'add_breakpoint':
                    objs = self.breakpoint.add(args['objects'], sim_objects)
                    bps = self.breakpoint.get_bp()
                    # update the current breakpoint values before they are
                    # checked next time
                    self.bp_values_prev = self.read(list(bps.keys()))
                    resp['value'] = objs
                elif command == 'del_breakpoint':
                    objs = self.breakpoint.delete(args['objects'], sim_objects)
                    resp['value'] = objs
                elif command == 'get_breakpoint':
                    resp['value'] = self.breakpoint.data_raw
                elif command == 'set_parameter':
                    resp['value'] = self.set_parameter(args)
                elif command == 'get_parameter':
                    resp['value'] = {'unitStep': self.sim_unit_step,
                                     'step': self.sim_step,
                                     'total': self.sim_total,
                                     'unitTotal': self.sim_unit_total}
                elif command in ['read', 'read_buf']:
                    objs = args.get('objects', None)
                    resp['value'] = getattr(self, command)(objs)
                elif command in ['write']:
                    objs = args.get('objects', None)
                    if objs and isinstance(objs, dict):
                        resp['value'] = getattr(self, command)(objs)
                    else:
                        resp['value'] = False
                elif command == 'time_stamp':
                    t = self.time_stamp(args.get('format', '') == 'second')
                    resp['value'] = t
                elif command == 'trace_file':
                    resp['value'] = self.trace_file(args)
                elif command == 'get_trace_file':
                    resp['value'] = self.tfile_raw
                elif command == 'trace_buf':
                    resp['value'] = self.trace_buf(args)
                elif command == 'get_trace_buf':
                    resp['value'] = {b:self.tbuf[b]['raw'] for b in self.tbuf}
                elif command == 'get_status':
                    resp['value'] = {'running': self.running,
                                     'valid': engine and engine.valid}
                else:
                    print('Unknown command: ' + cmd)
                if resp:
                    self.response(resp)
                if self.running != running:
                    valid = engine and engine.valid
                    self.response({'cmd':'get_status',
                                   'value':{'running':self.running, 'valid':valid}})
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
    proc = ProcessCommand(qcmd, qresp)
    # infinite loop
    proc.process()
    sys.stdout = stdout
    sys.stderr = stderr
