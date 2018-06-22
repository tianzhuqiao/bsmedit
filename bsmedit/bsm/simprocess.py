import six
import six.moves.queue as Queue
import ctypes
import traceback
import numpy as np
from .simengine import *

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
    def __init__(self, qCmd, qResp):
        self.simengine = None
        self.monitor = MonitorList()
        self.breakpoint = BpList()
        self.bp_values_prev = {}
        self.tfile = {}
        self.tfile_raw = {}
        self.tbuf = {}
        self.tbuf_raw = {}
        self.qCmd = qCmd
        self.qResp = qResp
        self.running = False
        self.simStep = 20
        self.simUnitStep = BSM_NS
        self.simTotal = -1
        self.simUnitTotal = BSM_NS
        self.simTotalSec = -1

    def __del__(self):
        if self.simengine and self.simengine.is_valid():
            self.simengine.ctx_stop()

    def IsValidObj(self, name):
        if self.simengine and self.simengine.is_valid():
            return name and name in six.iterkeys(self.simengine.sim_objects)
        return False

    def response(self, resp):
        self.qResp.put(resp)

    def load(self, filename):
        self.simengine = SimEngine(filename)
        if self.simengine.is_valid():
            print(self.simengine.ctx['version'])
            print(self.simengine.ctx['copyright'])
            self.simengine.ctx_set_callback(self.check_bp)
            objs = {}
            for name, obj in six.iteritems(self.simengine.sim_objects):
                objs[obj.name] = {'name':obj.name, 'basename':obj.basename,
                                  'kind':obj.kind, 'value':"",
                                  'writable':obj.writable,
                                  'readable':obj.readable,
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
        simStep = self.simStep
        simUnit = self.simUnitStep
        if self.simTotalSec > 0:
            # not run infinitely
            t = self.simTotalSec - self.simengine.ctx_time()
            if t > 0:
                scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
                simStep = min(simStep, int(t*scale[simUnit]+0.5))
            else:
                # finished, no need to run
                self.running = False
                return False
        self.running = (running and (simStep == self.simStep))
        self.simengine.ctx_start(simStep, simUnit)

        return True

    def set_parameter(self, param):
        """set the parameters"""
        self.simUnitStep = param.get('unitStep', self.simUnitStep)
        self.simStep = param.get('step', self.simStep)
        self.simTotal = param.get('total', self.simTotal)
        self.simUnitTotal = param.get('unitTotal', self.simUnitTotal)
        more = param.get('more', False)
        if self.simTotal > 0:
            scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
            self.simTotalSec = self.simTotal/scale[self.simUnitTotal]
            if more:
                self.simTotalSec += self.time_stamp(True)
        else:
            self.simTotalSec = -1
        return True

    def read(self, objects):
        """read the register value"""
        if not self.simengine or not self.simengine.is_valid():
            return {}
        if objects == []:
            objects = self.monitor.get_monitor()
        objs = {}
        for obj in objects:
            if not self.IsValidObj(obj):
                continue
            val = self.simengine.ctx_read(self.simengine.sim_objects[obj])
            objs[obj] = val
        return objs

    def write(self, objects):
        """write the register value"""
        if not self.simengine or not self.simengine.is_valid():
            return {}
        resp = {}
        for name, value in six.iteritems(objects):
            resp[name] = False
            if name not in self.simengine.sim_objects:
                continue
            if not self.IsValidObj(name):
                continue
            resp[name] = True
            self.simengine.ctx_write(self.simengine.sim_objects[name], value)
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
        if not self.IsValidObj(name):
            return False
        if valid and not self.IsValidObj(valid):
            return False
        if valid:
            valid = self.simengine.sim_objects[name]

        trace = SimTraceFile()
        trace.name = name
        trace.type = ntype
        if self.simengine.ctx_create_trace_file(trace):
            self.simengine.ctx_trace_file(trace, self.simengine.sim_objects[name], valid, trigger)
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
        if not self.IsValidObj(name):
            return False

        if valid and not self.IsValidObj(valid):
            return False
        if valid:
            valid = self.simengine.sim_objects[valid]

        if name in six.iterkeys(self.tbuf):
            # remove the existing trace
            trace = self.tbuf[name]['trace']
            self.simengine.ctx_remove_trace_buf(trace)
            del self.tbuf[name]
            del self.tbuf_raw[name]

        trace = SimTraceBuf()
        trace.name = name
        trace.size = size
        data = np.zeros((size))
        trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        if self.simengine.ctx_create_trace_buf(trace):
            self.simengine.ctx_trace_buf(trace, self.simengine.sim_objects[name],
                                         valid, trigger)
            self.tbuf[name] = {'trace':trace, 'data':data}
            self.tbuf_raw[name] = [size, valid, trigger]
        return True

    def read_buf(self, objects):
        if not self.simengine or not self.simengine.is_valid():
            return {}
        if objects == []:
            # no object defined, return all the traced buffers
            objects = list(self.tbuf.keys())
        resp = {}
        for obj in objects:
            if obj not in six.iterkeys(self.tbuf):
                # if not traced yet, trace it now
                self.trace_buf({'name':obj})

            self.simengine.ctx_read_trace_buf(self.tbuf[obj]['trace'])
            resp[obj] = self.tbuf[obj]['data']
        return resp

    def process(self):
        while True:
            running = self.running
            if self.running:
                if not self.simengine or not self.simengine.is_valid():
                    self.running = False
                else:
                    tremain = self.simTotalSec - self.simengine.ctx_time()
                    if not ((self.simTotalSec <= 0) or (tremain > 0)):
                        self.running = False
            try:
                if self.running:
                    self.step(self.running)
                if self.running:
                    # In running mode, return immediately so that the simulation
                    # can be triggered as soon as possible
                    cmd = self.qCmd.get_nowait()
                else:
                    cmd = self.qCmd.get()
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
                    resp['value'] = {'unitStep': self.simUnitStep,
                                     'step': self.simStep,
                                     'total': self.simTotal,
                                     'unitTotal': self.simUnitTotal}
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
                    resp['value'] = self.tbuf_raw
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
                traceback.print_exc(file=sys.stdout)
class SimLogger(object):
    def __init__(self, qResp):
        self.qResp = qResp
    def write(self, buf):
        self.qResp.put({'cmd':'write_out', 'important':True, 'value':buf})

    def flush(self):
        pass

def sim_process(qResp, qCmd):
    log = SimLogger(qResp)
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = log
    sys.stderr = log
    proc = ProcessCommand(qCmd, qResp)
    # infinite loop
    proc.process()
    sys.stdout = stdout
    sys.stderr = stderr
