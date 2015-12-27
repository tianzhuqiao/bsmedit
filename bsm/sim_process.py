import Queue
import ctypes
import traceback
import numpy as np
from bsm.sim_engine import *
# the class to handle the breakpoint condition
# one breakpoint may trigger on multiple conditions,
# and each condition may trigger on multiple hit-counts.
class BpCond(object):
    def __init__(self, condition, hitcount):
        # single condition
        self.condition = condition
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
        trigger = False
        # if the condition is empty string, trigger if the value has changed
        if self.condition == '':
            trigger = (val != valp)
        else:
            # replace the '$' with the current value, then evaluate it
            cond = self.condition.replace('$', str(val))
            try:
                trigger = eval(cond)
            except:
                pass

        if trigger:
            self.hitsofar += 1
            for hc in self.hitcountset:
                # if the hitcount is empty string, always trigger
                if hc == '':
                    return (hc, self.hitsofar)
                # replace the '#' with the hitsofar
                hce = hc.replace('#', str(self.hitsofar))
                try:
                    bk = eval(hce)
                    if bk is True:
                        return (hc, self.hitsofar)
                except:
                    pass
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
                return
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
    def add(self, objs, objectsdict):
        resp = {}
        for name, cond, hitcount in objs:
            resp[name] = False
            if name not in objectsdict.keys():
                continue
            if name in self.data.keys():
                self.data[name].add_cond(cond, hitcount)
            else:
                self.data[name] = Breakpoint(name)
                self.data[name].add_cond(cond, hitcount)
            resp[name] = True
        return resp

    def delete(self, objs, objectsdict):
        resp = {}
        for name, cond, hitcount in objs:
            resp[name] = False
            if name not in objectsdict.keys():
                continue
            if name not in self.data.keys():
                continue
            self.data[name].del_cond(cond, hitcount)
            if len(self.data[name]) <= 0:
                del self.data[name]
            resp[name] = False
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
            objs = [o for o in objs if o in objsdict.keys()]
        for obj in objs:
            self.data[obj] = self.data.get(obj, 0) + 1
            resp[obj] = True
        self.update_monitor(objsdict)
        return resp
    def delete(self, objs, objsdict):
        resp = {o:False for o in objs}
        if objsdict:
            objs = [o for o in objs if o in objsdict.keys()]
        for obj in objs:
            if obj in self.data.keys():
                resp[obj] = True
                self.data[obj] -= 1
                if self.data[obj] <= 0:
                    del self.data[obj]
        self.update_monitor(objsdict)
        return resp
    def update_monitor(self, objsdict=None):
        if objsdict:
            self.monitor = [objsdict[k] for k in self.data.keys() if k in objsdict.keys()]
        else:
            self.monitor = self.data.keys()
    def get_monitor(self):
        return self.monitor

class ProcessCommand(object):
    def __init__(self, qCmd, qResp):
        self.simengine = None
        self.monitor = MonitorList()
        self.breakpoint = BpList()
        self.bp_values_prev = {}
        self.tfile = {}
        self.tbuf = {}
        self.qCmd = qCmd
        self.qResp = qResp
        self.running = False
        self.simStep = 20
        self.simUnitStep = BSM_NS
        self.simTotal = -1
        self.simUnitTotal = BSM_NS
        self.simTotalSec = -1

    def __del__(self):
        if self.simengine:
            self.simengine.ctx_stop()

    def is_valid_obj(self, name):
        return name in self.simengine.sim_objects

    def response(self, res):
        self.qResp.put(res)

    def load(self, filename):
        self.simengine = SimEngine(filename)
        if self.simengine.valid:
            print self.simengine.ctx.version
            print self.simengine.ctx.copyright
            self.simengine.ctx_set_callback(self.check_bp)
            objs = {}
            for name, obj in self.simengine.sim_objects.iteritems():
                objs[obj.name] = {'name':obj.name, 'basename':obj.basename,
                                  'kind':obj.kind, 'value':obj.value,
                                  'writable':obj.writable, 'readable':obj.readable,
                                  'numeric':obj.numeric, 'parent':obj.parent,
                                  'nkind':obj.nkind, 'register':obj.register}
            resp = [{'resp':'timestamp', 'value':self.simengine.ctx_time_str()}]
            resp.append({'resp':'load', 'value':objs})
        else:
            resp = [{'resp': 'ack', 'value': False}]
        return resp

    def check_bp(self, n):
        bps = self.breakpoint.get_bp()
        if len(bps) <= 0: return 0
        objs = bps.keys()
        values = self.read(objs)
        for name, bp in bps.iteritems():
            t = bp.triggered(values[name], self.bp_values_prev[name])
            if t is not None:
                self.response([{'resp': 'triggered', 'value': [name, t[0], t[1], t[2]]}])
                self.running = False
                self.bp_values_prev.update(values)
                return 1
        self.bp_values_prev.update(values)
        return 0

    def step(self, running):
        simStep = self.simStep
        simUnit = self.simUnitStep
        if self.simTotalSec > 0:
            t = self.simTotalSec - self.simengine.ctx_time()
            if t > 0:
                scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
                simStep = min(simStep, int(t*scale[simUnit]+0.5))
        if simStep <= 0:
            self.running = False
            self.response([{'resp': 'ack', 'value': True}])
            return
        self.running = running
        self.simengine.ctx_start(simStep, simUnit)
        resp = [{'resp':'timestamp', 'value':self.simengine.ctx_time_str()}]
        if self.monitor:
            objs = {}
            for obj in self.monitor.get_monitor():
                objs[obj.name] = unicode(self.simengine.ctx_read(obj), errors='replace')
            resp.append({'resp':'monitor', 'value':objs})
        if self.tbuf:
            bufs = {}
            for name, buf in self.tbuf.iteritems():
                self.simengine.ctx_read_trace_buf(buf['trace'])
                bufs[name] = buf['data']
            resp.append({'resp':'readbuf', 'value':bufs})
        return resp

    def set_parameter(self, param):
        self.simUnitStep = param.get('unitStep', self.simUnitStep)
        self.simStep = param.get('step', self.simStep)
        self.simTotal = param.get('total', self.simTotal)
        self.simUnitTotal = param.get('unitTotal', self.simUnitTotal)
        if self.simTotal > 0:
            scale = [1e15, 1e12, 1e9, 1e6, 1e3, 1e0]
            self.simTotalSec = self.simTotal/scale[self.simUnitTotal]
        else:
            self.simTotalSec = -1
        self.response([{'resp': 'ack', 'value': True}])

    def read(self, objects):
        objs = {}
        for obj in objects:
            if not self.is_valid_obj(obj):
                continue
            val = self.simengine.ctx_read(self.simengine.sim_objects[obj])
            objs[obj] = unicode(val, errors='replace')
        return objs

    def write(self, objects):
        resp = {}
        for name, value in objects.iteritems():
            resp[name] = False
            if name not in self.simengine.sim_objects:
                continue
            if not self.is_valid_obj(name):
                continue
            resp[name] = True
            self.simengine.ctx_write(self.simengine.sim_objects[name], value)
        return resp

    def time_stamp(self, second):
        if self.simengine is None:
            self.response([{'resp': 'ack', 'value': False}])
        if second:
            return self.simengine.ctx_time()
        else:
            return self.simengine.ctx_time_str()

    def trace_file(self, name, ntype, valid, trigger):
        if not self.is_valid_obj(name):
            return [{'resp': 'ack', 'value': False}]
        if valid and not self.is_valid_obj(valid):
            return [{'resp': 'ack', 'value': False}]
        if valid:
            valid = self.simengine.sim_objects[name]

        trace = SimTraceFile()
        trace.name = name
        trace.type = ntype
        if self.simengine.ctx_add_trace_file(trace):
            self.simengine.ctx_trace_file(trace, self.simengine.sim_objects[name], valid, trigger)
            self.tfile[name] = trace
            return [{'resp': 'ack', 'value': True}]

        return [{'resp': 'ack', 'value': False}]

    def trace_buf(self, name, size, valid=None, trigger=BSM_BOTHEDGE):
        if not self.is_valid_obj(name):
            return [{'resp': 'ack', 'value': False}]

        if valid and not self.is_valid_obj(valid):
            return [{'resp': 'ack', 'value': False}]
        if valid:
            valid = self.simengine.sim_objects[valid]

        if name in self.tbuf.keys():
            trace = self.tbuf[name]['trace']
            if trace.size != size:
                data = np.zeros((size))
                trace.size = size
                self.simengine.ctx_resize_trace_buf(trace, self.simengine.sim_objects[name])
                trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
                self.tbuf[name]['data'] = data
        else:
            trace = SimTraceBuf()
            trace.name = name
            trace.size = size
            data = np.zeros((size))
            trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            if self.simengine.ctx_add_trace_buf(trace):
                self.simengine.ctx_trace_buf(trace, self.simengine.sim_objects[name],
                                             valid, trigger)
                self.tbuf[name] = {'trace':trace, 'data':data}
        return [{'resp': 'ack', 'value': True}]

    def readbuf(self, objects):
        resp = {}
        for obj in objects:
            if obj not in self.tbuf.keys():
                self.trace_buf(obj, 256)
            if obj in self.tbuf.keys():
                self.simengine.ctx_read_trace_buf(self.tbuf[obj]['trace'])
                resp[obj] = self.tbuf[obj]['data']
        return resp

    def process(self):
        # if in running mode, send the step command automatically
        if self.running and self.qCmd.empty():
            tremain = self.simTotalSec - self.simengine.ctx_time()
            if (self.simTotalSec <= 0) or (tremain > 0):
                self.qCmd.put([{'cmd':'step', 'arguments':{'running': True, 'silent':True}}])
            else:
                self.running = False
        try:
            while True:
                for cmd in self.qCmd.get_nowait():
                    command = cmd.get('cmd', "")
                    args = cmd.get('arguments', {})
                    if command == 'exit':
                        return False
                    if not args.get('silent', True):
                        print cmd
                    if not command and not args:
                        print "unknown command"
                        self.response([{'resp': 'ack', 'value': False}])
                        continue

                    resp = [{'resp': command, 'value': False}]

                    if command == 'load':
                        resp = self.load(args.get('filename', None))

                    elif command == 'step':
                        resp = self.step(args.get('running', False))

                    elif command == 'pause':
                        self.running = False
                        resp[0]['value'] = True

                    elif command == 'monitor_add':
                        objs = self.monitor.add(args['objects'], self.simengine.sim_objects)
                        resp[0]['value'] = objs

                    elif command == 'monitor_del':
                        objs = self.monitor.delete(args['objects'], self.simengine.sim_objects)
                        resp[0]['value'] = objs

                    elif command == 'breakpoint_add':
                        objs = self.breakpoint.add(args['objects'], self.simengine.sim_objects)
                        bps = self.breakpoint.get_bp()
                        # update the current breakpoint values before they are
                        # checked next time
                        self.bp_values_prev = self.read(bps.keys())
                        resp[0]['value'] = objs

                    elif command == 'breakpoint_del':
                        self.breakpoint.delete(args['objects'], self.simengine.sim_objects)
                        resp[0]['value'] = True

                    elif command == 'set_parameter':
                        resp = self.set_parameter(args)

                    elif command == 'get_parameter':
                        resp[0]['value'] = {
                            'unitStep': self.simUnitStep,
                            'step': self.simStep,
                            'total': self.simTotal,
                            'unitTotal': self.simUnitTotal}

                    elif command in ['read', 'readbuf']:
                        objs = args.get('objects', None)
                        if objs and isinstance(objs, list) and hasattr(self, command):
                            resp[0]['value'] = getattr(self, command)(objs)
                        else:
                            resp = [{'resp': 'ack', 'value': False}]

                    elif command in ['write']:
                        objs = args.get('objects', None)
                        if objs and isinstance(objs, dict) and hasattr(self, command):
                            resp[0]['value'] = getattr(self, command)(objs)
                        else:
                            resp = [{'resp': 'ack', 'value': False}]
                    elif command == 'timestamp':
                        t = self.time_stamp(args.get('format', '') == 'second')
                        resp[0]['value'] = t

                    elif command == 'tracefile':
                        resp = self.trace_file(args['name'], args['type'],
                                               args['valid'], args['trigger'])

                    elif command == 'tracebuf':
                        resp = self.trace_buf(args['name'], args['size'],
                                              args['valid'], args['trigger'])

                    else:
                        print 'Unknown command: ', cmd

                    if resp:
                        self.response(resp)
        except Queue.Empty:
            pass
        except:
            traceback.print_exc(file=sys.stdout)
            self.response([{'resp': 'ack', 'value': False}])
        return True

    def exit(self):
        if self.simengine:
            self.simengine.ctx_stop()

class SimLogger(object):
    def __init__(self, qResp):
        self.qResp = qResp
    def write(self, buf):
        self.qResp.put([{'resp':'writeOut', 'value':buf}])

    def flush(self):
        pass

def sim_process(qResp, qCmd):
    log = SimLogger(qResp)
    stdout = sys.stdout
    stderr = sys.stderr
    sys.stdout = log
    sys.stderr = log
    proc = ProcessCommand(qCmd, qResp)
    while proc.process():
        pass
    sys.stdout = stdout
    sys.stderr = stderr
