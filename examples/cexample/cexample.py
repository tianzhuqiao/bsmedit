import os
import ctypes
import numpy as np
import bsmedit.bsm.csim as csim
class cexample(object):
    def __init__(self):
        folder = os.path.dirname(os.path.realpath(__file__))
        self.sim = csim.init_dll(os.path.join(folder, 'libcexample.so'),
                                 os.path.join(folder, 'cexample.h'))
        self.f = self.sim.ce_frame()
        self.frame = np.zeros((1,100)).astype(np.int32)
        self.f.frame = self.frame.ctypes.data_as(ctypes.POINTER(ctypes.c_int))
        self.f.max_frame_len = self.frame.size

    def get_frame(self):
        self.sim.get_frame(self.f)
        return self.frame

