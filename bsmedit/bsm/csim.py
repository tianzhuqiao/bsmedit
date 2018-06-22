import sys, os
import cparser, cparser.caching, cparser.cwrapper
import ctypes
import six

#CParserFunc = cparser.caching.parse
# If we don't want to use caching:
CParserFunc = cparser.parse

def init_dll(dll, header):
    dll = ctypes.cdll.LoadLibrary(dll)
    parsedState = CParserFunc(header)

    wrapper = cparser.cwrapper.CWrapper()
    wrapper.register(parsedState, dll)
    return wrapper.wrapped

def callback(proto, fun):
    SIM_CALLBACK = ctypes.CFUNCTYPE(proto.restype, *proto.argtypes)
    return SIM_CALLBACK(fun)

class SStructWrapper(ctypes.Structure):
    def __init__(self, obj, *args, **kwargs):
        ctypes.Structure.__init__(self, *args, **kwargs)
        self._object = obj

    def SetObjectProp(self, item, value):
        if isinstance(item, six.string_types):
            if hasattr(self._object, item):
                v = getattr(self._object, item)
                if isinstance(v, ctypes.Array) and \
                   isinstance(v, ctypes.ARRAY(ctypes.c_byte, len(v))):
                    setattr(self._object, item,
                            (ctypes.c_byte*len(v))(*bytearray(str(value))))
                else:
                    setattr(self._object, item, value)
                return True
        return False

    def __getattr__(self, item):
        return self[item]

    def __setattr__(self, item, val):
        if hasattr(self, '_object'):
            if self.SetObjectProp(item, val):
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
        return self.SetObjectProp(item, val)
