"""Subclass of mainFrame, which is generated by wxFormBuilder."""

import os
import imp
import importlib
from datetime import date
import wx
import wx.lib.agw.aui as aui
import wx.py.dispatcher as dispatcher
from frameplus import framePlus
from bsmshell import bsmShell, HistoryPanel, StackPanel
from bsmhelp import HelpPanel
from dirtreectrl import DirTreeCtrl, Directory
from debuggerxpm import *
from dirpanelxpm import *
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
        self.initMenu()

        self.SetMinSize((640, 480))
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

        # history panel
        self.panelHistory = HistoryPanel(self)
        self.addPanel(self.panelHistory, title="History",
                      showhidemenu='View:Panels:Command History')
        # help panel
        self.panelHelp = HelpPanel(self)
        self.addPanel(self.panelHelp, title="Help",
                      target=self.panelHistory,
                      showhidemenu='View:Panels:Command Help')
        # debug stack panel
        self.panelStack = StackPanel(self)
        self.addPanel(self.panelStack, title="Call Stack",
                      target=self.panelHistory,
                      showhidemenu='View:Panels:Call Stack')
        # directory panel
        self.panelDir = DirPanel(self)
        self.addPanel(self.panelDir, title="Browsing",
                      target=self.panelHistory,
                      showhidemenu='View:Panels:Browsing')

        self.tbDebug = None
        self.initDebugger()
        self._mgr.Update()

        self.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.OnPaneActivated)
        dispatcher.connect(receiver=self.runCommand, signal='frame.run')
        dispatcher.connect(receiver=self.setPanelTitle, signal='frame.set_panel_title')
        dispatcher.connect(receiver=self.setStatusText, signal='frame.set_status_text')
        dispatcher.connect(receiver=self.addFileHistory, signal='frame.add_file_history')
        self.Bind(wx.EVT_CLOSE, self._onClose)

        #try:
        self.addon = {}
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

    def initMenu(self):
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
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnFileQuit, id=menuQuit.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpHome, id=menuHome.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpContact, id=menuContact.GetId())
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=menuAbout.GetId())

    def addFileHistory(self, filename):
        """add the file to recent file list"""
        self.config.SetPath('/FileHistory')
        self.filehistory.AddFileToHistory(filename)
        self.filehistory.Save(self.config)
        self.config.Flush()

    def OnPaneClose(self, evt):
        # check if the window should be destroyed
        # auiPaneInfo.IsDestroyOnClose() can not be used since if the pane is
        # added to a notebook, IsDestroyOnClose() always returns False
        if not hasattr(evt.pane, 'bsm_destroyonclose'):
            return
        if not evt.pane.bsm_destroyonclose:
            evt.Veto()
            if evt.pane.IsNotebookPage():
                notebook = self._mgr._notebooks[evt.pane.notebook_id]
                idx = notebook.GetPageIndex(evt.pane.window)
                notebook.RemovePage(idx)
                evt.pane.Dock()
                evt.pane.Hide()
                evt.pane.window.Reparent(self._mgr._frame)
                evt.pane.window.notebook = notebook
                evt.pane.Top()
                self._mgr.Update()
            self._mgr.ShowPane(evt.pane.window, False)
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

    def _onClose(self, evt):
        # stop the debugger if it is on
        if self.panelShell.isDebuggerOn():
            dispatcher.send(signal='debugger.stop')
        dispatcher.send(signal='frame.save_config', config=self.config)
        dispatcher.send(signal='frame.exit')
        evt.Skip()

    def setStatusText(self, text, index=0, width=-1):
        """set the status text"""
        if index >= len(self.statusbar_width):
            self.statusbar_width.extend([0 for i in range(index+1-len(self.statusbar_width))])
            self.statusbar.SetFieldsCount(index+1)
        if self.statusbar_width[index] != width:
            self.statusbar_width[index] = width
            self.statusbar.SetStatusWidths(self.statusbar_width)
        self.statusbar.SetStatusText(text, index)

    def _package_contents(self, package_name):
        MODULE_EXTENSIONS = ('.py')
        (file, pathname, description) = imp.find_module(package_name)
        if file:
            raise ImportError('Not a package: %r', package_name)

        # Use a set because some may be both source and compiled.
        return set([os.path.splitext(module)[0] for module in
                    os.listdir(pathname)
                    if module.endswith(MODULE_EXTENSIONS) and
                       not module.startswith('_')])

    def runCommand(self, command, prompt=True, verbose=True, debug=False):
        """execute the command in shell"""
        # show the debug toolbar in debug mode
        if debug and not self.tbDebug.IsShown():
            self.showPanel(self.tbDebug)
        self.panelShell.runCommand(command, prompt, verbose, debug)

    def OnPaneActivated(self, event):
        """notify the window managers that the panel is activated"""
        pane = event.GetPane()
        if isinstance(pane, aui.auibook.AuiNotebook):
            window = pane.GetCurrentPage()
            if window:
                dispatcher.send(signal='frame.activate_panel', pane=window)
        else:
            dispatcher.send(signal='frame.activate_panel', pane=pane)

    def setPanelTitle(self, pane, title):
        """set the panel title"""
        if pane:
            info = self._mgr.GetPane(pane)
            if info and info.IsOk() and info.caption != title:
                info.Caption(title)
                self._mgr.RefreshPaneCaption(pane)

    # Handlers for mainFrame events.
    def OnClose(self, event):
        self.Destroy()

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

    def initDebugger(self):
        """initialized the debug toolbar"""
        if self.tbDebug:
            return

        self.addMenu('Tools:Debug', rxsignal='', kind='Popup')
        self.ID_DBG_RUN = self.addMenu('Tools:Debug:Run\tF5',
                                       rxsignal='debugger.resume',
                                       updatesignal='frame.updateui')
        self.ID_DBG_STOP = self.addMenu('Tools:Debug:Stop\tShift-F5',
                                        rxsignal='debugger.stop',
                                        updatesignal='frame.updateui')
        self.ID_DBG_STEP = self.addMenu('Tools:Debug:Step\tF10',
                                        rxsignal='debugger.step',
                                        updatesignal='frame.updateui')
        self.ID_DBG_STEP_INTO = self.addMenu('Tools:Debug:Step Into\tF11',
                                             rxsignal='debugger.step_into',
                                             updatesignal='frame.updateui')
        self.ID_DBG_STEP_OUT = self.addMenu('Tools:Debug:Step Out\tShift-F11',
                                            rxsignal='debugger.step_out',
                                            updatesignal='frame.updateui')

        self.tbDebug = aui.AuiToolBar(self, style=wx.TB_FLAT | wx.TB_HORIZONTAL)
        self.tbDebug.AddSimpleTool(self.ID_DBG_RUN, 'Run (F5)',
                                   wx.BitmapFromXPMData(arrow_xpm),
                                   'Run (F5)')
        self.tbDebug.AddSimpleTool(self.ID_DBG_STOP, 'Stop (Shift-F5)',
                                   wx.BitmapFromXPMData(control_stop_square_xpm),
                                   'Stop (Shift-F5)')
        self.tbDebug.AddSimpleTool(self.ID_DBG_STEP, 'Step (F10)',
                                   wx.BitmapFromXPMData(arrow_step_over_xpm),
                                   'Step (F10)')
        self.tbDebug.AddSimpleTool(self.ID_DBG_STEP_INTO, 'Step Into (F11)',
                                   wx.BitmapFromXPMData(arrow_step_xpm),
                                   'Step Into (F11)')
        self.tbDebug.AddSimpleTool(self.ID_DBG_STEP_OUT, 'Step Out (Shift-F11)',
                                   wx.BitmapFromXPMData(arrow_step_out_xpm),
                                   'Step Out (Shift-F11)')
        self.tbDebug.Realize()

        self.addPanel(self.tbDebug, 'Debugger', active=False,
                      paneInfo=aui.AuiPaneInfo().Name('debugger')
                      .Caption('Debugger').ToolbarPane().Top(),
                      showhidemenu='View:Toolbars:Debugger')
        dispatcher.connect(receiver=self.OnUpdateUI, signal='frame.updateui')
        dispatcher.connect(self.debug_paused, 'debugger.paused')
        dispatcher.connect(self.debug_ended, 'debugger.ended')
        self.SetExtraStyle(wx.WS_EX_PROCESS_UI_UPDATES)

    def debug_paused(self):
        """update the debug toolbar status"""
        resp = dispatcher.send(signal='debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        self.tbDebug.EnableTool(self.ID_DBG_RUN, status['paused'])
        self.tbDebug.EnableTool(self.ID_DBG_STOP, status['paused'])
        self.tbDebug.EnableTool(self.ID_DBG_STEP, status['paused'])
        self.tbDebug.EnableTool(self.ID_DBG_STEP_INTO, status['can_stepin'])
        self.tbDebug.EnableTool(self.ID_DBG_STEP_OUT, status['can_stepout'])
        self.tbDebug.Refresh(False)

    def debug_ended(self):
        self.tbDebug.EnableTool(self.ID_DBG_RUN, False)
        self.tbDebug.EnableTool(self.ID_DBG_STOP, False)
        self.tbDebug.EnableTool(self.ID_DBG_STEP, False)
        self.tbDebug.EnableTool(self.ID_DBG_STEP_INTO, False)
        self.tbDebug.EnableTool(self.ID_DBG_STEP_OUT, False)
        self.tbDebug.Refresh(False)
        self.showPanel(self.tbDebug, False)

    def OnUpdateUI(self, event):
        """update the debugger toolbar"""
        eid = event.GetId()
        resp = dispatcher.send(signal='debugger.get_status')
        paused = False
        stepin = False
        stepout = False
        if resp and resp[0][1]:
            status = resp[0][1]
            paused = status['paused']
            stepin = status['can_stepin']
            stepout = status['can_stepout']

        enable = False
        if eid == self.ID_DBG_RUN:
            enable = paused
        elif eid == self.ID_DBG_STOP:
            enable = paused
        elif eid == self.ID_DBG_STEP:
            enable = paused
        elif eid == self.ID_DBG_STEP_INTO:
            enable = paused and stepin
        elif eid == self.ID_DBG_STEP_OUT:
            enable = paused and stepout
        event.Enable(enable)

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

        today = date.today()
        copyright = '(c) 2008-%i %s'%(today.year, 'Tianzhu Qiao. All rights reserved.')

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
        szPanel.Add(stLine, 0, wx.EXPAND |wx.ALL, 0)

        self.panel.SetSizer(szPanel)
        self.panel.Layout()
        szPanel.Fit(self.panel)

        szAll.Add(self.panel, 1, wx.EXPAND |wx.ALL, 0)

        szConfirm = wx.BoxSizer(wx.VERTICAL)
        self.btnOk = wx.Button(self, wx.ID_OK, u"Ok")
        szConfirm.Add(self.btnOk, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        szAll.Add(szConfirm, 0, wx.EXPAND, 5)

        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)

class DirPanel(wx.Panel):

    ID_GOTO_PARENT = wx.NewId()
    ID_GOTO_HOME = wx.NewId()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.tb = wx.ToolBar(self, style=wx.TB_FLAT | wx.TB_HORIZONTAL)
        self.tb.AddLabelTool(
            self.ID_GOTO_PARENT,
            'Parent',
            wx.BitmapFromXPMData(arrow_090_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            'Parent folder',
            wx.EmptyString,
            )
        self.tb.AddLabelTool(
            self.ID_GOTO_HOME,
            'Home',
            wx.BitmapFromXPMData(home_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            'Current folder',
            wx.EmptyString,
            )
        self.tb.Realize()
        self.dirtree = DirTreeCtrl(self, style=wx.TR_DEFAULT_STYLE |
                                   wx.TR_HAS_VARIABLE_ROW_HEIGHT |
                                   wx.TR_HIDE_ROOT)
        self.dirtree.SetRootDir(os.getcwd())
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.dirtree, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnGotoHome, id=self.ID_GOTO_HOME)
        self.Bind(wx.EVT_TOOL, self.OnGotoParent,
                  id=self.ID_GOTO_PARENT)

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated,
                  self.dirtree)

    def OnItemActivated(self, event):
        currentItem = event.GetItem()
        filename = self.dirtree.GetItemText(currentItem)
        parentItem = self.dirtree.GetItemParent(currentItem)
        if isinstance(self.dirtree.GetPyData(parentItem), Directory):
            d = self.dirtree.GetPyData(parentItem)
            filepath = os.path.join(d.directory, filename)
        else:
            return
        if self.dirtree.ItemHasChildren(currentItem):
            self.dirtree.SetRootDir(filepath)
            return
        (path, fileExtension) = os.path.splitext(filename)
        if fileExtension == '.py':
            dispatcher.send(signal='bsm.editor.openfile', filename=filepath)
        else:
            os.system("start "+ filepath)

    def OnGotoHome(self, event):
        root = self.dirtree.GetRootItem()
        if root and isinstance(self.dirtree.GetPyData(root), Directory):
            d = self.dirtree.GetPyData(root)
            if d.directory == os.getcwd():
                return
        self.dirtree.SetRootDir(os.getcwd())

    def OnGotoParent(self, event):
        root = self.dirtree.GetRootItem()
        if root and isinstance(self.dirtree.GetPyData(root), Directory):
            d = self.dirtree.GetPyData(root)
            path = os.path.abspath(os.path.join(d.directory, os.path.pardir))
            if path == d.directory:
                return
            self.dirtree.SetRootDir(path)

