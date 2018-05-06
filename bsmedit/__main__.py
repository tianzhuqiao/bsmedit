#!python2
import wx
import os, sys
from bsmedit.mainframe import MainFrame
import bsmedit.c2p as c2p
assertMode = c2p.APP_ASSERT_DIALOG
class RunApp(wx.App):
    def __init__(self):
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        wx.Log.SetActiveTarget(wx.LogStderr())

        self.SetAssertMode(assertMode)

        frame = MainFrame(None)
        frame.Show(True)
        self.SetTopWindow(frame)
        self.frame = frame
        return True

def main():
    app = RunApp()
    app.MainLoop()

if __name__ == '__main__':
    main()

