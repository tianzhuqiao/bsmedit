import sys, os
from ..cparser import cparser, cwrapper
import ctypes
import six

#CParserFunc = cparser.caching.parse
# If we don't want to use caching:
CParserFunc = cparser.parse

def init_dll(dll, header):
    dll = ctypes.cdll.LoadLibrary(dll)
    parsedState = CParserFunc(header)

    wrapper = cwrapper.CWrapper()
    wrapper.register(parsedState, dll)
    return wrapper.wrapped

def callback(proto, fun):
    SIM_CALLBACK = ctypes.CFUNCTYPE(proto.restype, *proto.argtypes)
    return SIM_CALLBACK(fun)

class SStructWrapper(ctypes.Structure):
    def __init__(self, obj, *args, **kwargs):
        ctypes.Structure.__init__(self, *args, **kwargs)
        self._object = obj

    def __call__(self):
        return self._object

    def is_type(self, obj_type):
        return isinstance(self._object, obj_type)

    def set_object(self, item, value):
        if isinstance(item, six.string_types):
            if hasattr(self._object, item):
                v = getattr(self._object, item)
                if isinstance(v, ctypes.Array) and \
                   isinstance(v, ctypes.ARRAY(ctypes.c_byte, len(v))):
                    setattr(self._object, item,
                            (ctypes.c_byte*len(v))(*bytearray(str(value).encode())))
                else:
                    setattr(self._object, item, value)
                return True
        return False

    def __getattr__(self, item):
        if item == '_object':
            raise AttributeError()
        if hasattr(self._object, item):
            v = getattr(self._object, item)
            if isinstance(v, ctypes.Array) and \
               isinstance(v, ctypes.ARRAY(ctypes.c_byte, len(v))):
                return ctypes.cast(v, ctypes.c_char_p).value.decode()
            return v
        raise AttributeError()

    def __setattr__(self, item, val):
        if hasattr(self, '_object'):
            if self.set_object(item, val):
               return
        super(ctypes.Structure, self).__setattr__(item, val)

    def __getitem__(self, item):
        if isinstance(item, six.string_types):
            if hasattr(self._object, item):
                v = getattr(self._object, item)
                if isinstance(v, ctypes.Array) and \
                   isinstance(v, ctypes.ARRAY(ctypes.c_byte, len(v))):
                    return ctypes.cast(v, ctypes.c_char_p).value
                return v
        return None

    def __setitem__(self, item, val):
        return self.set_object(item, val)
