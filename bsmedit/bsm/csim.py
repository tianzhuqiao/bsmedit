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

