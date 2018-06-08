#!python2
import wx
import os, sys
import click
from bsmedit.mainframe import MainFrame
import bsmedit.c2p as c2p
assertMode = c2p.APP_ASSERT_DIALOG
class RunApp(wx.App):
    def __init__(self, ext_module):
        self.ext_module = ext_module
        wx.App.__init__(self, redirect=False)

    def OnInit(self):
        wx.Log.SetActiveTarget(wx.LogStderr())

        self.SetAssertMode(assertMode)

        frame = MainFrame(None, ext_module=self.ext_module)
        frame.Show(True)
        self.SetTopWindow(frame)
        self.frame = frame
        return True

@click.command()
@click.option('--ext-module', '-e', multiple=True, help="load external module")
def main(ext_module):
    app = RunApp(ext_module)
    app.MainLoop()

if __name__ == '__main__':
    main()

