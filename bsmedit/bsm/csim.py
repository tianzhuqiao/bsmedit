import sys, os
import cparser, cparser.caching, cparser.cwrapper
from ctypes import *

#CParserFunc = cparser.caching.parse
# If we don't want to use caching:
CParserFunc = cparser.parse

def init_dll(dll, header):
    dll = cdll.LoadLibrary(dll)
    parsedState = CParserFunc(header)

    wrapper = cparser.cwrapper.CWrapper()
    wrapper.register(parsedState, dll)
    return wrapper.wrapped

def callback(proto, fun):
    SIM_CALLBACK = CFUNCTYPE(proto.restype, *proto.argtypes)
    return SIM_CALLBACK(fun)
