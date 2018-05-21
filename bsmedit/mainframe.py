"""Subclass of mainFrame, which is generated by wxFormBuilder."""

import os
import sys
import imp
import importlib
import json
import six
import wx
import wx.lib.agw.aui as aui
import wx.py
import wx.py.dispatcher as dp
from .frameplus import FramePlus
from .mainframexpm import bsmedit_xpm, header_xpm
from .version import *
from . import c2p

class FileDropTarget(wx.FileDropTarget):
    def __init__(self):
        wx.FileDropTarget.__init__(self)

    def OnDropFiles(self, x, y, filenames):
        for fname in filenames:
            wx.CallAfter(dp.send, signal='frame.file_drop', filename=fname)
        return True

class MainFrame(FramePlus):

    ID_VM_RENAME = wx.NewId()
    ID_CONTACT = wx.NewId()
    def __init__(self, parent):
        FramePlus.__init__(self, parent, title='bsmedit',
                           size=wx.Size(800, 600),
                           style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.InitMenu()
        self._mgr.SetAGWFlags(self._mgr.GetAGWFlags()
                              | aui.AUI_MGR_ALLOW_ACTIVE_PANE
                              | aui.AUI_MGR_SMOOTH_DOCKING
                              | aui.AUI_MGR_USE_NATIVE_MINIFRAMES
                              | aui.AUI_MGR_LIVE_RESIZE)
        # set mainframe icon
        icon = c2p.EmptyIcon()
        icon.CopyFromBitmap(c2p.BitmapFromXPM(bsmedit_xpm))
        self.SetIcon(icon)

        # status bar
        self.statusbar = wx.StatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.statusbar_width = [-1]
        self.statusbar.SetStatusWidths(self.statusbar_width)

        # persistent configuration
        self.config = wx.FileConfig('bsmedit', style=wx.CONFIG_USE_LOCAL_FILE)

        # recent file list
        self.filehistory = wx.FileHistory(8)
        self.config.SetPath('/FileHistory')
        self.filehistory.Load(self.config)
        self.filehistory.UseMenu(self.menuRecentFiles)
        self.filehistory.AddFilesToMenu()
        self.Bind(wx.EVT_MENU_RANGE, self.OnMenuFileHistory, id=wx.ID_FILE1,
                  id2=wx.ID_FILE9)

        self.closing = False

        # Create & Link the Drop Target Object to main window
        self.SetDropTarget(FileDropTarget())

        self.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.OnPaneActivated)
        dp.connect(self.SetPanelTitle, 'frame.set_panel_title')
        dp.connect(self.ShowStatusText, 'frame.show_status_text')
        dp.connect(self.AddFileHistory, 'frame.add_file_history')
        dp.connect(self.SetConfig, 'frame.set_config')
        dp.connect(self.GetConfig, 'frame.get_config')

        sys.path.append('.')

        self.addon = {}
        try:
            # check if the __init__ module defines all the modules to be loaded
            mod = importlib.import_module('bsmedit.bsm.__init__')
            bsmpackages = mod.auto_load_module
        except ImportError:
            bsmpackages = self._package_contents('bsm')
        for pkg in bsmpackages:
            mod = importlib.import_module('bsmedit.bsm.%s' % pkg)
            if hasattr(mod, 'bsm_initialize'):
                mod.bsm_initialize(self)
                self.addon[pkg] = True


        # used to change the name of a pane in a notebook;
        # TODO change the pane name when it does not belong to a notebook
        self.activePaneWindow = None

        # initialization done, broadcasting the message so plugins can do some
        # after initialization processing.
        dp.send('frame.initialized')

        # load the perspective
        perspective = self.GetConfig('mainframe', 'perspective')
        if perspective:
            self._mgr.LoadPerspective(perspective)

        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.OnPaneMenu)
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPaneClose)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_VM_RENAME)

    def InitMenu(self):
        """initialize the menubar"""
        menubar = wx.MenuBar(0)
        menuFile = wx.Menu()
        menuNew = wx.Menu()
        menuFile.AppendSubMenu(menuNew, "New")

        menuOpen = wx.Menu()
        menuFile.AppendSubMenu(menuOpen, "Open")

        menuFile.AppendSeparator()

        self.menuRecentFiles = wx.Menu()
        menuFile.AppendSubMenu(self.menuRecentFiles, "Recent Files")

        menuFile.AppendSeparator()
        menuFile.Append(wx.ID_CLOSE, "&Quit")

        menubar.Append(menuFile, "&File")

        # add the common Edit menus to menubar; otherwise, the context-menu
        # from bsmshell or editor may not work (e.g., Mac)
        menuEdit = wx.Menu()
        menuEdit.Append(wx.ID_UNDO, "&Undo")
        menuEdit.Append(wx.ID_REDO, "&Redo")
        menuEdit.AppendSeparator()
        menuEdit.Append(wx.ID_CUT, "&Cut")
        menuEdit.Append(wx.ID_COPY, "&Copy")
        menuEdit.Append(wx.ID_PASTE, "&Paste")
        menuEdit.Append(wx.ID_CLEAR, "&Clear")
        menuEdit.AppendSeparator()
        menuEdit.Append(wx.ID_SELECTALL, "&Select All")

        menubar.Append(menuEdit, "&Edit")

        menuView = wx.Menu()
        menuToolbar = wx.Menu()
        menuView.AppendSubMenu(menuToolbar, "&Toolbars")
        menuView.AppendSeparator()
        menuPanes = wx.Menu()
        menuView.AppendSubMenu(menuPanes, "Panels")

        menubar.Append(menuView, "&View")

        menuTool = wx.Menu()
        menubar.Append(menuTool, "&Tools")
        menuHelp = wx.Menu()
        menuHelp.Append(wx.ID_HOME, "&Home")
        menuHelp.Append(self.ID_CONTACT, "&Contact")
        menuHelp.AppendSeparator()
        menuHelp.Append(wx.ID_ABOUT, "&About")
        menubar.Append(menuHelp, "&Help")

        self.SetMenuBar(menubar)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.OnFileQuit, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnHelpHome, id=wx.ID_HOME)
        self.Bind(wx.EVT_MENU, self.OnHelpContact, id=self.ID_CONTACT)
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=wx.ID_ABOUT)

    def AddFileHistory(self, filename):
        """add the file to recent file list"""
        self.config.SetPath('/FileHistory')
        self.filehistory.AddFileToHistory(filename)
        self.filehistory.Save(self.config)
        self.config.Flush()

    def SetConfig(self, group, **kwargs):
        if not group.startswith('/'):
            group = '/'+group
        for key, value in six.iteritems(kwargs):
            if key in ['signal', 'sender']:
                # reserved key for dp.send
                continue
            if not isinstance(value, str):
                # add sign to indicate that the value needs to be deserialize
                value = '__bsm__'+json.dumps(value)
            self.config.SetPath(group)
            self.config.Write(key, value)

    def GetConfig(self, group, key):
        if not group.startswith('/'):
            group = '/'+group
        if self.config.HasGroup(group):
            self.config.SetPath(group)
            if self.config.HasEntry(key):
                value = self.config.Read(key)
                if value.startswith('__bsm__'):
                    value = json.loads(value[7:])
                return value
        return None

    def OnPaneClose(self, evt):
        # check if the window should be destroyed
        # auiPaneInfo.IsDestroyOnClose() can not be used since if the pane is
        # added to a notebook, IsDestroyOnClose() always returns False
        def PaneClosingVeto(pane):
            force = self.closing
            if hasattr(pane, 'bsm_destroyonclose'):
                force = pane.bsm_destroyonclose
            return not force
        # close the notebook
        if evt.pane.IsNotebookControl():
            nb = evt.pane.window
            for idx in range(nb.GetPageCount()-1, -1, -1):
                wnd = nb.GetPage(idx)
                page = self._mgr.GetPane(wnd)

                if page.IsOk() and PaneClosingVeto(wnd):
                    nb.RemovePage(idx)
                    page.Dock()
                    page.Hide()
                    page.window.Reparent(self)
                    page.window.notebook_id = -1
                    page.Top()
            return
        # close a page or a panel
        wnd = evt.pane.window
        if PaneClosingVeto(wnd):
            evt.Veto()
            if evt.pane.IsNotebookPage():
                nb = self._mgr.GetNotebooks()
                notebook = nb[evt.pane.notebook_id]
                idx = notebook.GetPageIndex(wnd)
                notebook.RemovePage(idx)
                evt.pane.Dock()
                evt.pane.Hide()
                evt.pane.window.Reparent(self)
                evt.pane.window.notebook = notebook
                evt.pane.Top()
                self._mgr.Update()
            self._mgr.ShowPane(wnd, False)
            self._mgr.Update()

    def OnPaneMenu(self, evt):
        # get the index inside the current tab control
        idx = evt.GetSelection()
        tabctrl = evt.GetEventObject()
        tabctrl.SetSelection(idx)
        page = tabctrl.GetPage(idx)
        self.activePaneWindow = page
        menu = wx.Menu()
        menu.Append(self.ID_VM_RENAME, "&Rename")
        self.PopupMenu(menu)

    def OnProcessCommand(self, evt):
        nid = evt.GetId()
        if nid == self.ID_VM_RENAME:
            if not self.activePaneWindow:
                return

            pane = self._mgr.GetPane(self.activePaneWindow)
            if not pane:
                return
            name = pane.caption
            name = wx.GetTextFromUser("Type in the name:", "Input Name",
                                      name, self)
            if name != pane.caption:
                pane.Caption(name)
                pane.window.SetLabel(name)
                self._mgr.Update()

            self.activePaneWindow = None

    def OnClose(self, event):
        """close the main program"""
        self.closing = True
        self.SetConfig('mainframe', perspective=self._mgr.SavePerspective())
        dp.send('frame.exit')
        self.config.Flush()
        super(MainFrame, self).OnClose(event)

    def ShowStatusText(self, text, index=0, width=-1):
        """set the status text"""
        if index >= len(self.statusbar_width):
            exd = [0]*(index+1-len(self.statusbar_width))
            self.statusbar_width.extend(exd)
            self.statusbar.SetFieldsCount(index+1)
        if self.statusbar_width[index] < width:
            self.statusbar_width[index] = width
            self.statusbar.SetStatusWidths(self.statusbar_width)
        self.statusbar.SetStatusText(text, index)

    def _package_contents(self, package_name):
        """return a list of the modules"""
        MOD_EXT = ('.py')
        mod = imp.find_module('bsmedit')
        (f, pathname, _) = imp.find_module(package_name, [mod[1]])
        if f:
            raise ImportError('Not a package: %r', package_name)

        # Use a set because some may be both source and compiled.
        return set([os.path.splitext(module)[0] for module in
                    os.listdir(pathname)
                    if module.endswith(MOD_EXT) and not module.startswith('_')])

    def OnPaneActivated(self, event):
        """notify the window managers that the panel is activated"""
        pane = event.GetPane()
        if isinstance(pane, aui.auibook.AuiNotebook):
            window = pane.GetCurrentPage()
        else:
            window = pane
        dp.send('frame.activate_panel', pane=window)

    def SetPanelTitle(self, pane, title):
        """set the panel title"""
        if pane:
            info = self._mgr.GetPane(pane)
            if info and info.IsOk() and info.caption != title:
                info.Caption(title)
                self._mgr.RefreshPaneCaption(pane)

    # Handlers for mainFrame events.
    def OnFileQuit(self, event):
        """close the program"""
        self.Close(True)

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
        webbrowser.open("mail:tianzhu.qiao@feiyilin.com")
        wx.EndBusyCursor()

    def OnHelpAbout(self, event):
        """show about dialog"""
        dlg = AboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def OnMenuFileHistory(self, event):
        """open the recent file"""
        fileNum = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        self.filehistory.AddFileToHistory(path)
        dp.send('frame.file_drop', filename=path)

class AboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title="About bsmedit",
                           style=wx.DEFAULT_DIALOG_STYLE)

        szAll = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        self.panel.SetBackgroundColour(wx.WHITE)

        szPanel = wx.BoxSizer(wx.VERTICAL)

        self.header = wx.StaticBitmap(self.panel)
        self.header.SetBitmap(c2p.BitmapFromXPM(header_xpm))
        szPanel.Add(self.header, 0, wx.EXPAND, 0)

        caption = 'bsmedit %s'%BSM_VERSION
        self.stCaption = wx.StaticText(self.panel, wx.ID_ANY, caption)
        self.stCaption.SetFont(wx.Font(16, 74, 90, 92, False, "Arial"))

        szPanel.Add(self.stCaption, 0, wx.ALL|wx.EXPAND, 5)

        strCopyright = '(c) 2018 Tianzhu Qiao. All rights reserved.'

        self.stCopyright = wx.StaticText(self.panel, wx.ID_ANY, strCopyright)
        self.stCopyright.SetMaxSize((240, -1))
        self.stCopyright.SetFont(wx.Font(8, 74, 90, 90, False, "Arial"))
        szPanel.Add(self.stCopyright, 0, wx.ALL|wx.EXPAND, 5)

        build = wx.GetOsDescription() + '; wxWidgets ' + wx.version()
        self.stBuild = wx.StaticText(self.panel, wx.ID_ANY, build)
        self.stBuild.SetMaxSize((240, -1))
        self.stBuild.Wrap(240)
        self.stBuild.SetFont(wx.Font(8, 74, 90, 90, False, "Arial"))
        szPanel.Add(self.stBuild, 0, wx.ALL|wx.EXPAND, 5)

        stLine = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        szPanel.Add(stLine, 1, wx.EXPAND|wx.ALL, 0)

        self.panel.SetSizer(szPanel)
        self.panel.Layout()
        szPanel.Fit(self.panel)

        szAll.Add(self.panel, 1, wx.EXPAND|wx.ALL, 0)

        szConfirm = wx.BoxSizer(wx.VERTICAL)
        self.btnOk = wx.Button(self, wx.ID_OK, u"Ok")
        szConfirm.Add(self.btnOk, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        szAll.Add(szConfirm, 0, wx.EXPAND, 5)

        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)
