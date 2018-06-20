import sys, os
import traceback
from ctypes import Structure, POINTER, c_byte, create_string_buffer, cdll
import ctypes
import six
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

class SStructWrapper(Structure):
    def __init__(self, object, *args, **kwargs):
        Structure.__init__(self, *args, **kwargs)
        self.object = object

    def SetObjectProp(self, item, value):
        if isinstance(item, six.string_types):
            if hasattr(self.object, item):
                v = getattr(self.object, item)
                if isinstance(v, ctypes.ARRAY(c_byte, len(v))):
                    setattr(self.object, item, (ctypes.c_byte*len(v))(*bytearray(value)))
                else:
                    setattr(self.object, item, value)
                return True
        return False

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, item, val):
        if hasattr(self, 'object'):
            if self.SetObjectProp(item, val):
               return
        super(Structure, self).__setattr__(item, val)

    def __getitem__(self, item):
        if isinstance(item, six.string_types):
            if hasattr(self.object, item):
                v = getattr(self.object, item)
                if isinstance(v, ctypes.Array) and \
                   isinstance(v, ctypes.ARRAY(c_byte, len(v))):
                    return ctypes.cast(v, ctypes.c_char_p).value
                return v
        return None

    def __setitem__(self, item, val):
        return self.SetObjectProp(item, val)

class SimEngine(object):
    def __init__(self, dll, frame=None):
        self.frame = frame
        self.dll = ""
        self.ctx_callback = None
        self.valid = False
        folder = os.path.dirname(os.path.realpath(__file__))
        self.csim = csim.init_dll(dll, os.path.join(folder, 'bsm.h'))
        ctx = self.csim.sim_context()
        self.csim.bsm_sim_top(ctx)
        self.ctx = SStructWrapper(ctx)

        obj = self.csim.sim_object()
        rtn = self.csim.ctx_first_object(obj)
        self.sim_objects = {}
        while rtn:
            wobj = SStructWrapper(obj)
            self.check_object(wobj)
            if obj.readable:
                self.csim.ctx_read(obj)
            self.sim_objects[wobj.name] = wobj
            obj = self.csim.sim_object()
            rtn = self.csim.ctx_next_object(obj)
        self.valid = True

    def __del__(self):
        pass

    def __getattr__(self, item):
        if 'ctx' in item:
            return getattr(self.csim, item)

    def load(self, dll):
        return True

    def is_valid(self):
        return self.valid

    def get_objects(self):
        if not self.is_valid():
            return {}
        return self.sim_objects

    def check_object(self, obj):
        assert obj
        if not obj or (not isinstance(obj, SStructWrapper)):
            return
        kindstr = obj['kind']
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
            if obj.name.find("[") != -1 and  obj['name'].find("]") != -1:
                kind = SC_OBJ_XSC_ARRAY_ITEM
        elif kindstr == "sc_module":
            kind = SC_OBJ_MODULE
        elif kindstr == "xsc_array":
            kind = SC_OBJ_XSC_ARRAY
        obj.nkind = kind
        obj.register = (kind in (SC_OBJ_SIGNAL, SC_OBJ_INPUT,
                                    SC_OBJ_OUTPUT, SC_OBJ_INOUT, SC_OBJ_CLOCK,
                                    SC_OBJ_XSC_PROP, SC_OBJ_XSC_ARRAY_ITEM))
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
        if isinstance(obj, six.string_types):
            obj = self.sim_objects.get(obj, None)
        if not obj or (not isinstance(obj, SStructWrapper)):
            return ""
        obj = obj.object
        if not obj.readable:
            return ""
        if self.csim.ctx_read(obj):
            if obj.value.type == BSM_DATA_STRING:
                return ctypes.cast(obj.value.sValue, ctypes.c_char_p).value
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
        if isinstance(obj, six.string_types):
            obj = self.sim_objects.get(obj, None)
        if not obj or (not isinstance(obj, SStructWrapper)):
            return False

        obj = obj.object

        if not obj.writable:
            return ""

        if self.ctx_read(obj):
            if obj.value.type == BSM_DATA_STRING:
                obj.value.sValue =  (c_byte*len(v))(*bytearray(value))
            elif obj.value.type == BSM_DATA_FLOAT:
                obj.value.fValue = float(value)
            elif obj.value.type == BSM_DATA_INT:
                obj.value.iValue = int(value)
            elif obj.value.type == BSM_DATA_UINT:
                obj.value.uValue = int(value)
        return self.csim.ctx_write(obj)

    def ctx_time_str(self):
        if not self.is_valid():
            return ""
        buf = create_string_buffer(256)
        self.csim.ctx_time_str(ctypes.cast(buf, ctypes.POINTER(c_byte)))
        return ctypes.cast(buf, ctypes.c_char_p).value

    def ctx_set_callback(self, fun):
        # the callback fun should take an integer arguments and return an
        # integer argument. Return 1 from the callback function will pause
        # the simulation
        if not self.is_valid():
            return False
        self.ctx_callback = csim.callback(self.csim.bsm_callback(), fun)
        self.csim.ctx_set_callback(self.ctx_callback)

