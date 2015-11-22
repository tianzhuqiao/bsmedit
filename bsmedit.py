import wx
import os, sys
from main.main import bsmMainFrame
assertMode = wx.PYAPP_ASSERT_DIALOG
class RunApp(wx.App):
    def __init__(self):
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        wx.Log_SetActiveTarget(wx.LogStderr())

        self.SetAssertMode(assertMode)

        frame = bsmMainFrame(None)
        
        frame.Show(True)
        #frame.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        self.SetTopWindow(frame)
        self.frame = frame
        return True

    def OnExitApp(self, evt):
        self.frame.Close(True)

    def OnCloseFrame(self, evt):
        pass

def main(argv):
    app = RunApp()
    app.MainLoop()

if __name__ == '__main__':
    main(sys.argv)

