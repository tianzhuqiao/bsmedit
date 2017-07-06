from ctypes import Structure, c_char, c_double, c_int, c_voidp, c_bool, POINTER, c_ulonglong, c_longlong
from ctypes import create_string_buffer, cdll, CFUNCTYPE
import traceback
import sys

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
class SimObjValue(Structure):
    _fields_ = [('sValue', c_char*256),
                ('fValue', c_double),
                ('uValue', c_ulonglong),
                ('iValue', c_longlong),
                ('type', c_int)]
class SimObj(Structure):
    _fields_ = [('name', c_char*256),
                ('basename', c_char*256),
                ('kind', c_char*256),
                ('value', SimObjValue),
                ('writable', c_bool),
                ('readable', c_bool),
                ('numeric', c_bool),
                ('obj', c_voidp),
                ('parent', c_char*256),
                ('nkind', c_int),
                ('register', c_bool)]

class SimTraceFile(Structure):
    _fields_ = [('name', c_char*256),
                ('type', c_int),
                ('obj', c_voidp)]

class SimTraceBuf(Structure):
    _fields_ = [('name', c_char*256),
                ('buffer', POINTER(c_double)),
                ('size', c_int),
                ('obj', c_voidp),
                ('buf', c_voidp)]

class SimContext(Structure):
    _fields_ = [('version', c_char*256),
                ('copyright', c_char*256),
               ]
#


class SimEngine(object):
    DOUBLE = c_double
    PDOUBLE = POINTER(DOUBLE)
    PPDOUBLE = POINTER(PDOUBLE)
    INT = c_int
    SIM_CALLBACK = CFUNCTYPE(c_int, c_int)
    def __init__(self, dll, frame=None):
        self.frame = frame
        self.dll = ""
        self.ctx_callback = None
        self.valid = False
        self.load(dll)

    def __del__(self):
        pass

    def load(self, dll):
        self.dll = dll
        self.valid = False
        PTFILE = POINTER(SimTraceFile)
        PTOBJ = POINTER(SimObj)
        PTBUF = POINTER(SimTraceBuf)
        interfaces = [['start', '', (c_double, c_int), None],
                      ['stop', '', None, None],
                      ['time', '', None, c_double],
                      ['time_str', '_helper', (c_char*255, ), c_bool],
                      ['create_trace_file', '', (PTFILE,), c_bool],
                      ['stop_trace_file', '', (PTFILE,), c_bool],
                      ['trace_file', '', (PTFILE, PTOBJ, PTOBJ, c_int), c_bool],
                      ['create_trace_buf', '', (PTBUF,), c_bool],
                      ['stop_trace_buf', '', (PTBUF,), c_bool],
                      ['trace_buf', '', (PTBUF, PTOBJ, PTOBJ, c_int), c_bool],
                      ['read_trace_buf', '', (PTBUF,), c_bool],
                      ['resize_trace_buf', '', (PTBUF,), c_bool],
                      ['set_callback', '_helper', (self.SIM_CALLBACK, ), None],
                      ['read', '_helper', (PTOBJ,), c_bool],
                      ['write', '_helper', (PTOBJ,), c_bool],
                     ]
        try:
            self.cdll = cdll.LoadLibrary(str(dll))
            # create the simulation
            sim_top = self.interface("bsm_sim_top", None, POINTER(SimContext))
            self.ctx = sim_top().contents

            # load all the interfaces
            for inf in interfaces:
                ninf = 'ctx_'+inf[0]
                nmethod = ninf + inf[1]
                setattr(self, nmethod, self.interface(ninf, inf[2], inf[3]))

            # load all the objects
            first_object = self.interface("ctx_first_object", (PTOBJ,), c_bool)
            next_object = self.interface("ctx_next_object", (PTOBJ,), c_bool)
            obj = SimObj()
            rtn = first_object(obj)
            self.sim_objects = {}
            while rtn:
                self.check_object(obj)
                if obj.readable:
                    self.ctx_read(obj)
                self.sim_objects[obj.name] = obj
                obj = SimObj()
                rtn = next_object(obj)
        except:
            traceback.print_exc(file=sys.stdout)
            return False
        self.valid = True
        return True

    def is_valid(self):
        return self.valid

    def get_objects(self):
        if not self.is_valid():
            return {}
        return self.sim_objects

    def check_object(self, obj):
        assert obj
        if not obj or (not isinstance(obj, SimObj)):
            return
        kindstr = obj.kind
        kind = SC_OBJ_UNKNOWN
        if kindstr == "sc_signal":
            kind = SC_OBJ_SIGNAL
        elif kindstr == "sc_in":
            kind = SC_OBJ_INPUT
        elif kindstr == "sc_out":
            kind = SC_OBJ_OUTPUT
        elif kindstr == "sc_in_out":
            kind = SC_OBJ_INOUT
        elif kindstr == "sc_clock":
            kind = SC_OBJ_CLOCK
        elif kindstr == "xsc_property":
            kind = SC_OBJ_XSC_PROP
            if obj.name.find("[") != -1 and  obj.name.find("]") != -1:
                kind = SC_OBJ_XSC_ARRAY_ITEM
        elif kindstr == "sc_module":
            kind = SC_OBJ_MODULE
        elif kindstr == "xsc_array":
            kind = SC_OBJ_XSC_ARRAY

        obj.nkind = kind
        obj.register = (kind in [SC_OBJ_SIGNAL, SC_OBJ_INPUT,
                                 SC_OBJ_OUTPUT, SC_OBJ_INOUT, SC_OBJ_CLOCK,
                                 SC_OBJ_XSC_PROP, SC_OBJ_XSC_ARRAY_ITEM])
        name = obj.name
        idx = name.rfind('.')
        if kind == SC_OBJ_XSC_ARRAY_ITEM:
            idx = name.rfind('[')
        obj.parent = ""
        if idx != -1:
            name = name[0:idx]
            obj.parent = name

    def ctx_read(self, obj):
        if not self.is_valid():
            return ""
        if not obj or (not isinstance(obj, SimObj)):
            return ""
        if not obj.readable:
            return ""
        if self.ctx_read_helper(obj):
            if obj.value.type == BSM_DATA_STRING:
                return unicode(obj.value.sValue, errors='replace')
            elif obj.value.type == BSM_DATA_FLOAT:
                return obj.value.fValue
            elif obj.value.type == BSM_DATA_INT:
                return obj.value.iValue
            elif obj.value.type == BSM_DATA_UINT:
                return obj.value.uValue
        return ""

    def ctx_write(self, obj, value):
        if not self.is_valid():
            return False
        if not obj or (not isinstance(obj, SimObj)):
            return False
        if not obj.writable:
            return ""
        if self.ctx_read_helper(obj):
            if obj.value.type == BSM_DATA_STRING:
                obj.value.sValue = str(value)
            elif obj.value.type == BSM_DATA_FLOAT:
                obj.value.fValue = float(value)
            elif obj.value.type == BSM_DATA_INT:
                obj.value.iValue = int(value)
            elif obj.value.type == BSM_DATA_UINT:
                obj.value.uValue = int(value)
        return self.ctx_write_helper(obj)

    def ctx_time_str(self):
        if not self.is_valid():
            return ""
        buf = create_string_buffer(255)
        self.ctx_time_str_helper(buf)
        return buf.value

    def ctx_set_callback(self, fun):
        # the callback fun should take an integer arguments and return an
        # integer argument. Return 1 from the callback function will pause
        # the simulation
        if not self.is_valid():
            return False
        self.ctx_callback = self.SIM_CALLBACK(fun)
        self.ctx_set_callback_helper(self.ctx_callback)

    def interface(self, fun, arg=None, res=None):
        fun = getattr(self.cdll, fun)
        fun.argtypes = arg
        fun.restype = res
        return fun
