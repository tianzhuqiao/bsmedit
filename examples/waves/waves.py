import os
import ctypes
import wx
import wx.py.dispatcher as dp
import numpy as np
import bsmedit.bsm.csim as csim
from glsurface import SurfaceBase
class Wave(object):
    def __init__(self):
        folder = os.path.dirname(os.path.realpath(__file__))
        self.sim = csim.init_dll(os.path.join(folder, 'libwaves.so'),
                                 os.path.join(folder, 'waves.h'))
        self.f = self.sim.wave_frame()
        self.sim.get_frame(self.f)
        self.f.max_frame_len = self.f.rows*self.f.cols
        self.frame = np.zeros((1, self.f.max_frame_len)).astype(np.float32)
        self.f.frame = self.frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float))

    def get_frame(self):
        self.sim.get_frame(self.f)
        return np.reshape(self.frame, (self.f.rows, self.f.cols)).astype(np.float)

class Surface(SurfaceBase):
    def __init__(self, *args, **kwargs):
        SurfaceBase.__init__(self, *args, **kwargs)

    def Initialize(self):
        super(Surface, self).Initialize()
        self.SetShowStepSurface(False)
        self.SetShowMode(mesh=True)
        self.rotate_matrix = np.array([[ 0.9625753 , -0.21669953,  0.16275978],
                                       [ 0.26339024,  0.88946027, -0.3734787 ],
                                       [-0.06383575,  0.40237066,  0.91324866]],
                                      dtype=np.float32)

class SurfacePanel(wx.Panel):
    frame = None
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        self.sim = Wave()
        data = self.sim.get_frame()
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.canvas = Surface(self, {'z':data})
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)
        self.Layout()

    @classmethod
    def initialize(cls, frame):
        if cls.frame:
            return
        cls.frame = frame
        if not frame:
            return
        # history panel
        panel = cls(frame)
        dp.send(signal='frame.add_panel', panel=panel, title="wave",
                target="History", showhidemenu='View:Panels:wave')

def bsm_initialize(frame):
    SurfacePanel.initialize(frame)
