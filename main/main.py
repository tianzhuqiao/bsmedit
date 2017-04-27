"""Subclass of mainFrame, which is generated by wxFormBuilder."""

import os
import imp
import importlib
import wx
import wx.lib.agw.aui as aui
import wx.py.dispatcher as dispatcher
from frameplus import framePlus
from bsmshell import bsmShell
from mainframexpm import about_xpm, bsmedit_xpm, header_xpm
from version import *

# Implementing mainFrame
intro = 'Welcome To BSMEdit 3\n' \
        'PyCrust %s - The Flakiest Python Shell' \
          % wx.py.version.VERSION

# Define File Drop Target class
class FileDropTarget(wx.FileDropTarget):
    def __init__(self):
        wx.FileDropTarget.__init__(self)

    def OnDropFiles(self, x, y, filenames):
        for fname in filenames:
            dispatcher.send(signal='bsm.editor.openfile', filename=fname)
        return True

class bsmMainFrame(framePlus):

    ID_VM_RENAME = wx.NewId()
    def __init__(self, parent):
        framePlus.__init__(self, parent, title=u"BSMEdit",
                           size=wx.Size(800, 600),
                           style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.InitMenu()
        self._mgr.SetAGWFlags(self._mgr.GetAGWFlags()
                              | aui.AUI_MGR_ALLOW_ACTIVE_PANE
                              | aui.AUI_MGR_SMOOTH_DOCKING
                              | aui.AUI_MGR_USE_NATIVE_MINIFRAMES
                              | aui.AUI_MGR_LIVE_RESIZE)
        # set mainframe icon
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(wx.BitmapFromXPMData(bsmedit_xpm))
        self.SetIcon(icon)
        # status bar
        self.statusbar = wx.StatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.statusbar_width = [-1]
        self.statusbar.SetStatusWidths(self.statusbar_width)

        # recent file list
        self.filehistory = wx.FileHistory(8)
        self.config = wx.FileConfig('bsmedit', style=wx.CONFIG_USE_LOCAL_FILE)
        self.config.SetPath('/FileHistory')
        self.filehistory.Load(self.config)
        self.filehistory.UseMenu(self.menuRecentFiles)
        self.filehistory.AddFilesToMenu()
        self.Bind(wx.EVT_MENU_RANGE, self.OnMenuFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        self.closing = False
        # shell panel
        ns = {}
        ns['wx'] = wx
        ns['app'] = wx.GetApp()
        ns['frame'] = self
        self.panelShell = bsmShell(self, 1, introText=intro, locals=ns)
        self._mgr.AddPane(self.panelShell,
                          aui.AuiPaneInfo().Name('shell').Caption('Console')
                          .CenterPane().CloseButton(False).Layer(1)
                          .Position(1).MinimizeButton(True).MaximizeButton(True))
        self._mgr.Update()

        self.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.OnPaneActivated)
        dispatcher.connect(receiver=self.SetPanelTitle, signal='frame.set_panel_title')
        dispatcher.connect(receiver=self.ShowStatusText, signal='frame.show_status_text')
        dispatcher.connect(receiver=self.AddFileHistory, signal='frame.add_file_history')

        #try:
        self.addon = {}
        try:
            # check if the __init__ module defines all the modules to be loaded
            mod = importlib.import_module('bsm.__init__')
            bsmpackages = mod.auto_load_module
        except ImportError:
            bsmpackages = self._package_contents('bsm')
        for pkg in bsmpackages:
            mod = importlib.import_module('bsm.%s' % pkg)
            if hasattr(mod, 'bsm_Initialize'):
                mod.bsm_Initialize(self)
                self.addon[pkg] = True
        #except:
        #    print 'Initializing addon failed'
        #    pass

        # Create a File Drop Target object
        dt = FileDropTarget()
        # Link the Drop Target Object to the Text Control
        self.SetDropTarget(dt)

        dispatcher.send(signal='frame.load_config', config=self.config)

        self.panelShell.SetFocus()

        self.activeTabCtrl = None
        self.activeTabCtrlIndex = -1

        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_UP, self.OnNoteBookTabRightUp)
        self.Bind(aui.EVT_AUI_PANE_CLOSE, self.OnPaneClose)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnPaneClose)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_VM_RENAME)

    def InitMenu(self):
        """initialize the menubar"""
        menubar = wx.MenuBar(0)
        menuFile = wx.Menu()
        menuNew = wx.Menu()
        menuFile.AppendSubMenu(menuNew, u"New")

        menuOpen = wx.Menu()
        menuFile.AppendSubMenu(menuOpen, u"Open")

        menuFile.AppendSeparator()

        self.menuRecentFiles = wx.Menu()
        menuFile.AppendSubMenu(self.menuRecentFiles, u"Recent Files")

        menuFile.AppendSeparator()

        menuQuit = wx.MenuItem(menuFile, wx.ID_CLOSE, u"&Quit",
                               wx.EmptyString, wx.ITEM_NORMAL)
        menuFile.AppendItem(menuQuit)

        menubar.Append(menuFile, u"&File")

        menuView = wx.Menu()
        menuToolbar = wx.Menu()
        menuView.AppendSubMenu(menuToolbar, u"&Toolbars")

        menuView.AppendSeparator()

        menuPanes = wx.Menu()
        menuView.AppendSubMenu(menuPanes, u"Panels")

        menubar.Append(menuView, u"&View")

        menuTool = wx.Menu()

        menubar.Append(menuTool, u"&Tools")

        menuHelp = wx.Menu()
        menuHome = wx.MenuItem(menuHelp, wx.ID_ANY, u"&Home", wx.EmptyString,
                               wx.ITEM_NORMAL)
        menuHelp.AppendItem(menuHome)

        menuContact = wx.MenuItem(menuHelp, wx.ID_ANY, u"&Contact",
                                  wx.EmptyString, wx.ITEM_NORMAL)
        menuHelp.AppendItem(menuContact)

        menuHelp.AppendSeparator()

        menuAbout = wx.MenuItem(menuHelp, wx.ID_ABOUT, u"&About",
                                wx.EmptyString, wx.ITEM_NORMAL)
        menuAbout.SetBitmap(wx.BitmapFromXPMData(about_xpm))
        menuHelp.AppendItem(menuAbout)

        menubar.Append(menuHelp, u"&Help")

        self.SetMenuBar(menubar)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.OnFileQuit, id=menuQuit.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpHome, id=menuHome.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpContact, id=menuContact.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=menuAbout.GetId())

    def AddFileHistory(self, filename):
        """add the file to recent file list"""
        self.config.SetPath('/FileHistory')
        self.filehistory.AddFileToHistory(filename)
        self.filehistory.Save(self.config)
        self.config.Flush()

    def OnPaneClose(self, evt):
        # check if the window should be destroyed
        # auiPaneInfo.IsDestroyOnClose() can not be used since if the pane is
        # added to a notebook, IsDestroyOnClose() always returns False
        def PaneClosingVeto(pane):
            force = self.closing
            if hasattr(pane, 'bsm_destroyonclose'):
                force = pane.bsm_destroyonclose
            resp = dispatcher.send('frame.closing_pane', pane = pane, force = force)
            if resp:
                status = resp[0][1]
                if isinstance(status, dict):
                    return dict.get('veto', False)
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

    def OnNoteBookTabRightUp(self, evt):
        idx = evt.GetSelection() # this is the index inside the current tab control
        tabctrl = evt.GetEventObject()
        tabctrl.SetSelection(idx)
        self.activeTabCtrl = tabctrl
        self.activeTabCtrlIndex = idx
        menu = wx.Menu()
        menu.Append(self.ID_VM_RENAME, "&Rename")
        self.PopupMenu(menu)

    def OnProcessCommand(self, evt):
        if not self.activeTabCtrl:
            return
        nid = evt.GetId()
        page = self.activeTabCtrl.GetPage(self.activeTabCtrlIndex)
        if nid == self.ID_VM_RENAME:
            pane = self._mgr.GetPane(page)
            name = pane.caption
            name = wx.GetTextFromUser("Type in the name:", "Input Name",
                                      name, self)
            if name:
                pane.Caption(name)
                page.SetLabel(name)
                self._mgr.Update()

        self.activeTabCtrl = None
        self.activeTabCtrlIndex = -1

    def OnClose(self, evt):
        """close the main program"""
        self.closing = True
        dispatcher.send(signal='frame.save_config', config=self.config)
        dispatcher.send(signal='frame.exit')
        super(bsmMainFrame, self).OnClose(evt)

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
        (file, pathname, description) = imp.find_module(package_name)
        if file:
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
        dispatcher.send(signal='frame.activate_panel', pane=window)

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
        dlg = bsmAboutDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def OnMenuFileHistory(self, event):
        """open the recent file"""
        fileNum = event.GetId() - wx.ID_FILE1
        path = self.filehistory.GetHistoryFile(fileNum)
        self.filehistory.AddFileToHistory(path)
        dispatcher.send(signal='bsm.editor.openfile', filename=path)

class bsmAboutDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=u"About", style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        szAll = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 255, 255))

        szPanel = wx.BoxSizer(wx.VERTICAL)

        szVersion = wx.BoxSizer(wx.VERTICAL)

        self.header = wx.StaticBitmap(self.panel)
        self.header.SetBitmap(wx.BitmapFromXPMData(header_xpm))
        szVersion.Add(self.header, 0, wx.ALL|wx.EXPAND, 0)
        caption = 'BSMEdit %s.%s'%(BSM_VERSION_MAJOR, BSM_VERSION_MIDDLE)
        self.stCaption = wx.StaticText(self.panel, wx.ID_ANY, caption)
        self.stCaption.Wrap(-1)
        self.stCaption.SetFont(wx.Font(28, 74, 90, 92, False, "Arial"))
        self.stCaption.SetForegroundColour(wx.Colour(255, 128, 64))

        szVersion.Add(self.stCaption, 0, wx.ALL, 5)

        version = ' Build %s' % (BSM_VERSION_MINOR)
        self.stVerion = wx.StaticText(self.panel, wx.ID_ANY, version)
        self.stVerion.Wrap(-1)
        self.stVerion.SetFont(wx.Font(8, 74, 90, 90, False, "Arial"))
        self.stVerion.SetForegroundColour(wx.Colour(120, 120, 120))

        szVersion.Add(self.stVerion, 0, wx.ALL, 5)

        copyright = '(c) 2008-2016 %s'%('Tianzhu Qiao. All rights reserved.')

        self.stCopyright = wx.StaticText(self.panel, wx.ID_ANY, copyright)
        self.stCopyright.Wrap(-1)
        self.stCopyright.SetFont(wx.Font(8, 74, 90, 90, False, "Arial"))

        szVersion.Add(self.stCopyright, 0, wx.ALL, 5)

        build = wx.GetOsDescription() + '; wxWidgets ' + wx.version()
        self.stBuild = wx.StaticText(self.panel, wx.ID_ANY, build)
        self.stBuild.Wrap(256 - 30)
        self.stBuild.SetFont(wx.Font(8, 74, 90, 90, False, "Arial"))

        szVersion.Add(self.stBuild, 0, wx.ALL|wx.EXPAND, 5)

        szPanel.Add(szVersion, 0, wx.EXPAND, 5)

        stLine = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        szPanel.Add(stLine, 0, wx.EXPAND|wx.ALL, 0)

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

