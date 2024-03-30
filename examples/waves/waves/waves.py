import os
import ctypes
import multiprocessing as mp
import six.moves.queue as Queue
import wx
import wx.py.dispatcher as dp
import wx.lib.agw.aui as aui
from ctypes import CFUNCTYPE, c_int
import numpy as np
import bsmedit.bsm.csim as csim
from bsmedit.glsurface import TrackingSurface
from .wavesxpm import run_xpm, pause_xpm, stop_xpm
from bsmedit import to_byte

class Wave(object):
    def __init__(self, qCmd, qResp):
        folder = os.path.dirname(os.path.realpath(__file__))
        self.sim = csim.init_dll(os.path.join(folder, '../libwaves.so'),
                                 os.path.join(folder, '../waves.h'))
        self.f = self.sim.wave_frame()
        self.f.callback = csim.callback(self.f.callback, self.new_frame_arrive)
        self.sim.get_frame(self.f)
        self.f.max_frame_len = self.f.rows*self.f.cols
        self.frame = np.zeros(self.f.max_frame_len).astype(np.float32)
        self.f.frame = self.frame.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
        self.qCmd = qCmd
        self.qResp = qResp
        self.status = 'pause'

    def get_frame(self):
        self.sim.get_frame(self.f)
        return np.reshape(self.frame, (self.f.rows, self.f.cols)).astype(np.float32)

    def new_frame_arrive(self, evt):
        try:
            cmd = self.qCmd.get_nowait()
            command = cmd.get('cmd', '')
            if command == 'run':
                self.status = 'run'
            elif command == 'pause':
                self.status = 'pause'
            elif command == 'stop':
                self.status = 'stop'
            self.qResp.put({'status':self.status})
        except Queue.Empty:
            pass
        if self.frame.size and self.status == 'run':
            frame = np.reshape(self.frame, (self.f.rows, self.f.cols)).astype(np.float32)
            self.qResp.put({"frame":frame})
        return self.status != 'stop'

    def run(self):
        self.sim.get_frames(self.f)

class Surface(TrackingSurface):
    def __init__(self, *args, **kwargs):
        TrackingSurface.__init__(self, *args, **kwargs)

    def Initialize(self):
        super(Surface, self).Initialize()
        self.SetShowStepSurface(False)
        self.SetShowMode(mesh=True)
        self.rotate_matrix = np.array([[ 0.9625753 , -0.21669953,  0.16275978],
                                       [ 0.26339024,  0.88946027, -0.3734787 ],
                                       [-0.06383575,  0.40237066,  0.91324866]],
                                      dtype=np.float32)

def SimProcess(qCmd, qResp):
    sim = Wave(qCmd, qResp)
    sim.run()

class SurfacePanel(wx.Panel):
    frame = None
    panel = None
    ID_RUN = wx.NewId()
    ID_PAUSE = wx.NewId()
    ID_STOP = wx.NewId()
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)
        #self.sim = Wave()
        data = np.zeros((30, 30))#self.sim.get_frame()
        sizer = wx.BoxSizer(wx.VERTICAL)
        tb = aui.AuiToolBar(self, -1, wx.DefaultPosition, wx.DefaultSize,
                            agwStyle=aui.AUI_TB_OVERFLOW|aui.AUI_TB_PLAIN_BACKGROUND)
        tb.SetToolBitmapSize(wx.Size(16, 16))
        tb.AddSimpleTool(self.ID_RUN, "Run", wx.Bitmap(to_byte(run_xpm)))
        tb.AddSimpleTool(self.ID_PAUSE, "Pause", wx.Bitmap(to_byte(pause_xpm)))
        tb.AddSimpleTool(self.ID_STOP, "Stop", wx.Bitmap(to_byte(stop_xpm)))
        tb.Realize()
        sizer.Add(tb, 0, wx.EXPAND, 0)

        self.canvas = Surface(self, {'z':data})
        self.canvas.SetRangeZ([-1., 1.])
        sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateTool)
        self.Bind(wx.EVT_TOOL, self.OnProcessTool)

        self.qCmd = mp.Queue()
        self.qResp = mp.Queue()
        self.process = mp.Process(target=SimProcess, args=(self.qCmd, self.qResp))
        self.process.start()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(3)

        self.status = 'pause'

    def stop(self):
        self.timer.Stop()
        if self.process and self.process.is_alive():
            self.qCmd.put({'cmd':'stop'})
            self.process.join()

    def OnUpdateTool(self, event):
        eid = event.GetId()
        if eid == self.ID_RUN:
            event.Enable(self.status != 'run')
        elif eid in [self.ID_PAUSE, self.ID_STOP]:
            event.Enable(self.status == 'run')
        else:
            event.Skip()

    def OnProcessTool(self, event):
        eid = event.GetId()
        if eid == self.ID_RUN:
            if not self.process or not self.process.is_alive():
                self.process = mp.Process(target=SimProcess, args=(self.qCmd, self.qResp))
                self.process.start()
            self.qCmd.put({"cmd":"run"})
        elif eid == self.ID_PAUSE:
            self.qCmd.put({"cmd":"pause"})
        elif eid == self.ID_STOP:
            self.qCmd.put({"cmd":"stop"})
        else:
            event.Skip()

    def OnTimer(self, event):
        if not self.qCmd or not self.qResp or not self.process:
            return
        try:
            data = self.qResp.get_nowait()
            self.status = data.get('status', self.status)
            frame = data.get('frame', None)
            if self.canvas.initialized and frame is not None:
                self.canvas.NewFrameArrive(frame, False)
        except Queue.Empty:
            pass

    @classmethod
    def initialize(cls, frame):
        if cls.frame:
            return
        cls.frame = frame
        if not frame:
            return
        dp.connect(cls.uninitialize, 'frame.exit')
        # waves panel
        cls.panel = cls(frame)
        dp.send(signal='frame.add_panel', panel=cls.panel, title="wave",
                showhidemenu='View:Panels:Wave')

    @classmethod
    def uninitialize(cls):
        if cls.panel:
            cls.panel.stop()

def bsm_initialize(frame, **kwargs):
    SurfacePanel.initialize(frame)
