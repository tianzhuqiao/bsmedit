import Queue
from sim_engine import *
import numpy as np
import ctypes

# the class to handle the breakpoint condition
# one breakpoint may trigger on multiple conditions,
# and each condition may trigger on multiple hit-counts.
class bp_cond():
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
        if idx == -1: return
        del self.hitcount[idx]
        self.hitcountset = set(self.hitcount)

    def triggered(self, v, vp):
        trigger = False
        # if the condition is empty string, trigger if the value has changed
        if self.condition == '':
            trigger = (v != vp)
        else:
            # replace the '$' with the current value, then evaluate it
            cond = self.condition.replace('$', str(v))
            try:
                trigger = eval(cond)
            except:
                pass
        
        if trigger:
            self.hitsofar += 1
            for hc in self.hitcountset:
                # if the hitcount is empty string, always trigger
                if hc=='':
                    return (hc, self.hitsofar)
                # replace the '#' with the hitsofar
                hce = hc.replace('#', str(self.hitsofar))
                try:
                    bk = eval(hce)
                    if bk == True:
                        return (hc, self.hitsofar)
                except:
                    pass
        return None

    def __len__(self):
        # return the hitcount length, it may be called to determine whether 
        # the condition is empty and can be deleted.
        return len(self.hitcount)

class bp():
    def __init__(self, name):
        self.name = name
        # the bp_cond list
        self.condition = []

    def add_cond(self, cond, hitcount):
        for c in self.condition:
            # add hitcount to the existing condition
            if c.condition == cond:
                c.add_hitcount(hitcount)
                return
        # create a new bp_cond instance
        self.condition.append(bp_cond(cond, hitcount))

    def del_cond(self, cond, hitcount):
         for c in self.condition:
            if c.condition == cond:
                c.del_hitcount(hitcount)
                if len(c) <=0:
                    del self.condition[self.condition.index(c)]                    
                return
    def triggered(self, v, vp):
        for c in self.condition:
            t = c.triggered(v, vp)
            if t is not None:
                return (c.condition, t[0], t[1])
        return None

    def __len__(self):
        # it may be called to determine whether the bp is empty and can be 
        # deleted
        return len(self.condition)

class bp_list():
    def __init__(self):
        self.data = {}
    def add(self, objs):
        for name, cond, hitcount in objs:
            if name in self.data.keys():
                self.data[name].add_cond(cond, hitcount)
            else:
                self.data[name] = bp(name)
                self.data[name].add_cond(cond, hitcount)
    def delete(self, objs):
        for name, cond, hitcount in objs:
            if name not in self.data.keys():
                continue
            self.data[name].del_cond(cond, hitcount)
            if len(self.data[name])<=0:
                del self.data[name]
    def get_bp(self):
        return self.data

# the list of registers to be monitored
class monitor_list():
    def __init__(self):
        self.data = {}
        self.monitor = []
    def add(self, objs, objsdict = None):
        if objsdict:
            objs = [o for o in objs if o in objsdict.keys()]
        for obj in objs:
            self.data[obj] = self.data.get(obj, 0) + 1
        self.update_monitor(objsdict)
    def delete(self, objs, objsdict):
        if objsdict:
            objs = [o for o in objs if o in objsdict.keys()]
        for obj in objs:
            if obj in self.data.keys():
                self.data[obj] -= 1
                if self.data[obj] <=0:
                    del self.data[obj]
        self.update_monitor(objsdict)
    def update_monitor(self, objsdict = None):
        if objsdict:
            self.monitor = [objsdict[k] for k in self.data.keys() if k in objsdict.keys()]
        else:
            self.monitor = self.data.keys()
    def get_monitor(self):
        return self.monitor

class processCommand():
    def __init__(self, qCmd, qResp):
        self.simengine = None
        self.monitor = monitor_list()
        self.breakpoint = bp_list()
        self.traceFile = {}
        self.traceBuf = {}
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

    def Response(self, res):
        self.qResp.put(res)

    def load(self, filename):
        self.simengine = sim_engine(filename)
        if self.simengine.valid:
            print self.simengine.ctx.version
            print self.simengine.ctx.copyright
            self.simengine.ctx_set_callback(self.check_bp)
            objs = {}
            for name, obj in self.simengine.sim_objects.iteritems():
                objs[obj.name] = {'name':obj.name, 'basename':obj.basename,
                    'kind': obj.kind, 'value':obj.value,
                    'writable':obj.writable, 'readable': obj.readable,
                    'numeric':obj.numeric, 'parent':obj.parent,
                    'nkind': obj.nkind, 'register': obj.register}
            resp = [{'cmd':'timestamp', 'time':self.simengine.ctx_time_str()}]
            resp.append({'cmd':'objects','objects':objs})
        else:
            resp = [{'cmd': 'ack', 'value': False}]
        return resp
    def check_bp(self, n):
        bps = self.breakpoint.get_bp()
        if len(bps)<=0: return 0
        objs = bps.keys()
        values = self.read(objs)
        for name, bp in bps.iteritems():
            t = bp.triggered(values[name], self.bp_values_prev[name])
            if t is not None:
                self.Response([{'cmd': 'triggered', 'bp': [name, t[0], t[1], t[2]]}])
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
            if t>0:
                 scale = [1e15, 1e12,1e9, 1e6, 1e3,1e0]
                 simStep = min(simStep, int(t*scale[simUnit]+0.5))
        if simStep <= 0:
            self.running = False
            self.Response([{'cmd': 'ack', 'value': True}])
            return
        self.running = running
        self.simengine.ctx_start(simStep, simUnit)
        resp = [{'cmd':'timestamp', 'time':self.simengine.ctx_time_str()}]
        if self.monitor:
            objs = {}
            for obj in self.monitor.get_monitor():
                objs[obj.name] = unicode(self.simengine.ctx_read(obj), errors='replace')
            resp.append({'cmd':'monitor', 'objects':objs})
        if self.traceBuf:
            bufs = {}
            for name, buf in self.traceBuf.iteritems():
                self.simengine.ctx_read_trace_buf(buf['trace'])
                bufs[name] = buf['data']
            resp.append({'cmd':'readbuf', 'bufs':bufs})
        return resp
    def set_parameter(self, param):
        self.simUnitStep = param.get('unitStep', self.simUnitStep)
        self.simStep = param.get('step', self.simStep)
        self.simTotal = param.get('total', self.simTotal)
        self.simUnitTotal = param.get('unitTotal', self.simUnitTotal)
        if self.simTotal > 0:
            scale = [1e15, 1e12,1e9, 1e6, 1e3,1e0]
            self.simTotalSec  =self.simTotal/scale[self.simUnitTotal]
        else:
            self.simTotalSec = -1
        self.Response([{'cmd': 'ack', 'value': True}])

    def read(self, objects):
        objs = {}
        for obj in objects:
            if obj not in self.simengine.sim_objects: continue
            objs[obj] = unicode(self.simengine.ctx_read(self.simengine.sim_objects[obj]), errors='replace')
        return objs
    def write(self, objects):
        for name, value in objects.iteritems():
            if name not in self.simengine.sim_objects.keys(): continue
            self.simengine.ctx_write(self.simengine.sim_objects[name], value)
        return [{'cmd': 'ack', 'value': True}]
    def time_stamp(self, second):
        if self.simengine is None:
            self.Response([{'cmd': 'ack', 'value': False}])
        if cmd.get('format', '') == 'second':
            return self.simengine.ctx_time()
        else:
            return self.simengine.ctx_time_str()
    def trace_file(self, cmd):
        trace = simTraceFile()
        trace.name = cmd['name']
        trace.type = cmd['type']
        if self.simengine.ctx_add_trace_file(trace):
            self.simengine.ctx_trace_file(trace, self.simengine.sim_objects[cmd['name']])
            self.traceFile[cmd['name']] = trace
        return [{'cmd': 'ack', 'value': True}]
    def trace_buf(self, name, size):
        if name in self.traceBuf.keys():
            trace = self.traceBuf[name]['trace']
            if trace.size != size:
                data = np.zeros((size))
                trace.size = size
                self.simengine.ctx_resize_trace_buf(trace, self.simengine.sim_objects[name])
                trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
                self.traceBuf[name]['data'] = data
        else:
            trace = simTraceBuf()
            trace.name = name
            trace.size = size
            data = np.zeros((size))
            trace.buffer = data.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
            if self.simengine.ctx_add_trace_buf(trace):
                self.simengine.ctx_trace_buf(trace, self.simengine.sim_objects[name])
                self.traceBuf[name] = {'trace':trace, 'data':data}
        return [{'cmd': 'ack', 'value': True}]
    def read_buf(self, objects):
        resp = {}
        for obj in objects:
            if obj not in self.traceBuf.keys():
                self.trace_buf(obj, 256)
            if obj in self.traceBuf.keys():
                self.simengine.ctx_read_trace_buf(self.traceBuf[obj]['trace'])
                resp[obj] = self.traceBuf[obj]['data']
        return resp
    def process(self):
        # if in running mode, send the step command automatically
        if self.running and self.qCmd.empty():
            t = self.simTotalSec - self.simengine.ctx_time()
            if self.simTotalSec <=0 or t>0:
                self.qCmd.put([{'cmd':'step', 'running': True}])
            else:
                self.running = False
        try:
            while True:
                command = self.qCmd.get_nowait()
                #print command
                for cmd in command:
                    resp = None
                    if cmd['cmd'] == 'load':
                        resp = self.load(cmd['filename'])
                    elif cmd['cmd'] == 'step':
                        resp = self.step(cmd.get('running', False))
                    elif cmd['cmd'] == 'pause':
                       self.running = False
                       resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'monitor_add':
                        self.monitor.add(cmd['objects'], self.simengine.sim_objects)  
                        resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'monitor_del':
                        self.monitor.delete(cmd['objects'], self.simengine.sim_objects)
                        resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'breakpoint_add':
                        self.breakpoint.add(cmd['objects'])
                        bps = self.breakpoint.get_bp()
                        self.bp_values_prev = self.read(bps.keys())
                        resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'breakpoint_del':
                        self.breakpoint.delete(cmd['objects'])
                        resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'set_parameter':
                        self.set_parameter(cmd)      
                    elif cmd['cmd'] == 'get_parameter':
                        resp = [{'cmd': 'get_parameter', 'unitStep': self.simUnitStep, 'step': self.simStep, 'total': self.simTotal, 'unitTotal': self.simUnitTotal}]
                    elif cmd['cmd'] == 'read':
                        objs = self.read(cmd['objects']) 
                        resp = [{'cmd':'read', 'objects':objs}]
                    elif cmd['cmd'] == 'write':
                        resp = self.write(cmd['objects'])
                    elif cmd['cmd'] == 'timestamp':
                        t = self.time_stamp(cmd.get('format', '') == 'second')
                        resp = [{'cmd':'timestamp', 'time': t}]
                    elif cmd['cmd'] == 'tracefile':
                        resp = self.trace_file(cmd)
                    elif cmd['cmd'] == 'tracebuf':
                        self.trace_buf(cmd['name'], cmd['size'])
                        resp = [{'cmd': 'ack', 'value': True}]
                    elif cmd['cmd'] == 'readbuf':
                        bufs = self.read_buf(cmd['objects'])
                        resp = [{'cmd': 'readbuf', 'bufs': bufs}]
                    elif cmd['cmd'] == 'exit':
                        #self.Response([{'cmd': 'ack', 'value': True}])
                        return False;
                    if resp:
                        self.Response(resp)
        except Queue.Empty:
            pass
        return True

    def exit(self):
        if self.simengine:
            self.simengine.ctx_stop()

def sim_process(qResp, qCmd):
    proc = processCommand(qCmd, qResp)
    while proc.process():
        pass
    
