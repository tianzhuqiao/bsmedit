import datetime
import wx
import wx.py
import wx.py.dispatcher as dp
import wx.adv
import aui2 as aui
from bsmutility.frameplus import FramePlus, TaskBarIcon
from bsmutility.utility import svg_to_bitmap
from .mainframexpm import  bsmedit_svg
from . import __version__
from .bsm import auto_load_module, auto_load_module_external
from .version import PROJECT_NAME


class MainFrame(FramePlus):
    CONFIG_NAME = PROJECT_NAME
    options = {}

    def __init__(self, parent, **kwargs):
        self.options = kwargs
        super().__init__(parent,
                         title=PROJECT_NAME,
                         size=wx.Size(800, 600),
                         style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL,
                         **kwargs)

        agw_flags = (self._mgr.GetAGWFlags()
                              | aui.AUI_MGR_ALLOW_ACTIVE_PANE
                              | aui.AUI_MGR_USE_NATIVE_MINIFRAMES
                              | aui.AUI_MGR_LIVE_RESIZE)

        if wx.Platform != '__WXMSW__':
            agw_flags |= aui.AUI_MGR_SMOOTH_DOCKING

        self._mgr.SetAGWFlags(agw_flags)

        # set mainframe icon
        icon = wx.Icon()
        icon.CopyFromBitmap(svg_to_bitmap(bsmedit_svg, size=(1024, 1024), win=self))
        self.SetIcon(icon)

        if 'wxMac' in wx.PlatformInfo:
            icon.CopyFromBitmap(svg_to_bitmap(bsmedit_svg, size=(1024, 1024), win=self))
            self.tbicon = TaskBarIcon(self, icon, PROJECT_NAME)

        dp.send(signal='shell.run',
                command='import pandas as pd',
                prompt=False,
                verbose=False,
                history=False)
        dp.send(signal='shell.run',
                command='import pickle',
                prompt=False,
                verbose=False,
                history=False)

    def InitMenu(self):
        """initialize the menubar"""
        super().InitMenu()

        self.AddMenu('&Help:&Home', id=wx.ID_HOME, autocreate=True)
        id_contact = self.AddMenu('&Help:&Report problem')
        self.AddMenu('&Help:Sep', kind="Separator")
        self.AddMenu('&Help:About', id=wx.ID_ABOUT)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.OnHelpHome, id=wx.ID_HOME)
        self.Bind(wx.EVT_MENU, self.OnHelpContact, id=id_contact)
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=wx.ID_ABOUT)

    def GetDefaultAddonPackages(self):
        if self.options.get('external', False):
            return auto_load_module + auto_load_module_external
        return auto_load_module

    def GetAbsoluteAddonPath(self, pkg):
        if pkg in auto_load_module:
            # module in bsm
            return 'bsmedit.bsm.%s' % pkg
        return super().GetAbsoluteAddonPath(pkg)

    def OnCloseWindow(self, evt):
        self.tbicon.Destroy()
        evt.Skip()

    def OnHelpHome(self, event):
        """go to homepage"""
        wx.BeginBusyCursor()
        import webbrowser
        webbrowser.open("http://bsmedit.feiyilin.com")
        wx.EndBusyCursor()

    def OnHelpContact(self, event):
        """send email"""
        wx.BeginBusyCursor()
        import webbrowser
        webbrowser.open("https://github.com/tianzhuqiao/bsmedit/issues")
        wx.EndBusyCursor()

    def OnHelpAbout(self, event):
        """show about dialog"""
        dlg = AboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()


class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent,
                         title=f"About {PROJECT_NAME}",
                         style=wx.DEFAULT_DIALOG_STYLE)

        szAll = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        self.panel.SetBackgroundColour(wx.WHITE)

        szPanelAll = wx.BoxSizer(wx.HORIZONTAL)

        self.header = wx.StaticBitmap(self.panel)
        self.header.SetBitmap(svg_to_bitmap(bsmedit_svg, size=(128, 128), win=self))
        szPanelAll.Add(self.header, 0, wx.EXPAND, 0)


        szPanel = wx.BoxSizer(wx.VERTICAL)
        szPanel.AddStretchSpacer(1)
        MAX_SIZE = 300
        caption = f'{PROJECT_NAME} {__version__}'
        self.stCaption = wx.StaticText(self.panel, wx.ID_ANY, caption)
        self.stCaption.SetMaxSize((MAX_SIZE, -1))
        self.stCaption.Wrap(MAX_SIZE)
        self.stCaption.SetFont(wx.Font(pointSize=16, family=wx.FONTFAMILY_DEFAULT,
                                       style=wx.FONTSTYLE_NORMAL,
                                       weight=wx.FONTWEIGHT_NORMAL,
                                       underline=False))

        szPanel.Add(self.stCaption, 0, wx.ALL | wx.EXPAND, 5)

        strCopyright = f'(c) 2018-{datetime.datetime.now().year} Tianzhu Qiao.\n All rights reserved.'
        self.stCopyright = wx.StaticText(self.panel, wx.ID_ANY, strCopyright)
        self.stCopyright.SetMaxSize((MAX_SIZE, -1))
        self.stCopyright.Wrap(MAX_SIZE)
        self.stCopyright.SetFont(wx.Font(pointSize=10, family=wx.FONTFAMILY_DEFAULT,
                                         style=wx.FONTSTYLE_NORMAL,
                                         weight=wx.FONTWEIGHT_NORMAL,
                                         underline=False))
        szPanel.Add(self.stCopyright, 0, wx.ALL | wx.EXPAND, 5)

        build = wx.GetOsDescription() + '; wxWidgets ' + wx.version()
        self.stBuild = wx.StaticText(self.panel, wx.ID_ANY, build)
        self.stBuild.SetMaxSize((MAX_SIZE, -1))
        self.stBuild.Wrap(MAX_SIZE)
        self.stBuild.SetFont(wx.Font(pointSize=10, family=wx.FONTFAMILY_DEFAULT,
                                     style=wx.FONTSTYLE_NORMAL,
                                     weight=wx.FONTWEIGHT_NORMAL,
                                     underline=False))
        szPanel.Add(self.stBuild, 0, wx.ALL | wx.EXPAND, 5)

        stLine = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        szPanel.Add(stLine, 0, wx.EXPAND | wx.ALL, 10)
        szPanel.AddStretchSpacer(1)

        szPanelAll.Add(szPanel, 1, wx.EXPAND | wx.ALL, 5)

        self.panel.SetSizer(szPanelAll)
        self.panel.Layout()
        szPanel.Fit(self.panel)

        szAll.Add(self.panel, 1, wx.EXPAND | wx.ALL, 0)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.AddStretchSpacer()
        self.btnOK = wx.Button(self, wx.ID_OK)
        self.btnOK.SetDefault()
        btnsizer.Add(self.btnOK, 0, wx.EXPAND | wx.ALL, 5)
        szAll.Add(btnsizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)
