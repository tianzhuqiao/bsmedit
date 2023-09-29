"""Subclass of mainFrame, which is generated by wxFormBuilder."""

import sys
import importlib
import traceback
import json
import datetime
import six
import six.moves
import wx
import wx.py
import wx.py.dispatcher as dp
import wx.adv
from .aui import aui
from .frameplus import FramePlus
from .mainframexpm import  bsmedit_svg
from . import __version__
from .bsm.utility import PopupMenu, svg_to_bitmap, build_menu_from_list
from .bsm import auto_load_module

class FileDropTarget(wx.FileDropTarget):
    def __init__(self):
        wx.FileDropTarget.__init__(self)

    def OnDropFiles(self, x, y, filenames):
        for fname in filenames:
            wx.CallAfter(dp.send, signal='frame.file_drop', filename=fname)
        return True

class TaskBarIcon(wx.adv.TaskBarIcon):
    TBMENU_RESTORE = wx.NewId()
    TBMENU_CLOSE = wx.NewId()
    TBMENU_CHANGE = wx.NewId()
    TBMENU_REMOVE = wx.NewId()

    def __init__(self, frame, icon):
        wx.adv.TaskBarIcon.__init__(self, iconType=wx.adv.TBI_DOCK)
        self.frame = frame

        # Set the image
        self.SetIcon(icon, "bsmedit")
        self.imgidx = 1

        # bind some events
        #self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=self.TBMENU_RESTORE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)


    def CreatePopupMenu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        menu = wx.Menu()
        menu.Append(self.TBMENU_RESTORE, "Restore bsmedit")
        menu.Append(self.TBMENU_CLOSE, "Close bsmedit")
        return menu


    def MakeIcon(self, img):
        """
        The various platforms have different requirements for the
        icon size...
        """
        if "wxMSW" in wx.PlatformInfo:
            img = img.Scale(16, 16)
        elif "wxGTK" in wx.PlatformInfo:
            img = img.Scale(22, 22)
        # wxMac can be any size upto 128x128, so leave the source img alone....
        icon = wx.Icon(img.ConvertToBitmap())
        return icon


    def OnTaskBarActivate(self, evt):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()


    def OnTaskBarClose(self, evt):
        wx.CallAfter(self.frame.Close)

class MultiDimensionalArrayEncoder(json.JSONEncoder):
    def encode(self, obj):
        def hint_tuples(item):
            if isinstance(item, tuple):
                return {'__tuple__': True, 'items': item}
            if isinstance(item, list):
                return [hint_tuples(e) for e in item]
            if isinstance(item, dict):
                return {key: hint_tuples(value) for key, value in item.items()}
            else:
                return item

        return super().encode(hint_tuples(obj))

def hinted_tuple_hook(obj):
    if '__tuple__' in obj:
        return tuple(obj['items'])
    else:
        return obj

class MainFrame(FramePlus):

    ID_VM_RENAME = wx.NewId()
    ID_CONTACT = wx.NewId()

    def __init__(self, parent, **kwargs):
        FramePlus.__init__(self,
                           parent,
                           title='bsmedit',
                           size=wx.Size(800, 600),
                           style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.InitMenu()
        self._mgr.SetAGWFlags(self._mgr.GetAGWFlags()
                              | aui.AUI_MGR_ALLOW_ACTIVE_PANE
                              | aui.AUI_MGR_SMOOTH_DOCKING
                              | aui.AUI_MGR_USE_NATIVE_MINIFRAMES
                              | aui.AUI_MGR_LIVE_RESIZE)
        # set mainframe icon
        icon = wx.Icon()
        icon.CopyFromBitmap(svg_to_bitmap(bsmedit_svg, 1024, 1024,win=self))
        self.SetIcon(icon)

        if 'wxMac' in wx.PlatformInfo:
            icon.CopyFromBitmap(svg_to_bitmap(bsmedit_svg, 1024, 1024, win=self))
            self.tbicon = TaskBarIcon(self, icon)

        # status bar
        self.statusbar = wx.StatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.statusbar_width = [-1]
        self.statusbar.SetStatusWidths(self.statusbar_width)

        # persistent configuration
        conf = kwargs.get('config', 'bsmedit')
        self.config = wx.FileConfig(conf, style=wx.CONFIG_USE_LOCAL_FILE)

        # recent file list
        self.filehistory = wx.FileHistory(8)
        self.config.SetPath('/FileHistory')
        self.filehistory.Load(self.config)
        self.filehistory.UseMenu(self.menuRecentFiles)
        self.filehistory.AddFilesToMenu()
        self.Bind(wx.EVT_MENU_RANGE,
                  self.OnMenuFileHistory,
                  id=wx.ID_FILE1,
                  id2=wx.ID_FILE9)

        self.closing = False

        # Create & Link the Drop Target Object to main window
        self.SetDropTarget(FileDropTarget())

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)
        self.Bind(aui.EVT_AUI_PANE_ACTIVATED, self.OnPaneActivated)
        dp.connect(self.SetPanelTitle, 'frame.set_panel_title')
        dp.connect(self.ShowStatusText, 'frame.show_status_text')
        dp.connect(self.AddFileHistory, 'frame.add_file_history')
        dp.connect(self.SetConfig, 'frame.set_config')
        dp.connect(self.GetConfig, 'frame.get_config')

        # append sys path
        sys.path.append('')
        for p in kwargs.get('path', []):
            sys.path.append(p)

        self.bsm_packages = auto_load_module
        self.addon = {}
        self.InitAddOn(kwargs.get('module', ()), debug=kwargs.get('debug', False))

        # initialization done, broadcasting the message so plugins can do some
        # after initialization processing.
        dp.send('frame.initialized')
        # load the perspective
        if not kwargs.get('ignore_perspective', False):
            self.LoadPerspective()

        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.OnPageRightDown)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

    def LoadPerspective(self):
        perspective = self.GetConfig('mainframe', 'perspective')
        if perspective and not wx.GetKeyState(wx.WXK_SHIFT):
            w = self.GetConfig('mainframe', 'frame_width')
            h = self.GetConfig('mainframe', 'frame_height')
            if w is not None and h is not None and w > 300 and h > 300:
                self.SetSize(w, h)
            self._mgr.LoadPerspective(perspective)
            self.UpdatePaneMenuLabel()

    def InitMenu(self):
        """initialize the menubar"""
        menubar = wx.MenuBar()
        self.SetMenuBar(menubar)

        self.AddMenu('&File:New', kind="Popup", autocreate=True)
        self.AddMenu('&File:Open', kind="Popup")
        self.AddMenu('&File:Sep', kind="Separator")
        self.AddMenu('&File:Recent Files', kind="Popup")
        self.menuRecentFiles = self.GetMenu(['File', 'Recent Files'])
        self.AddMenu('&File:Sep', kind="Separator")
        self.AddMenu('&File:&Quit', id=wx.ID_CLOSE)

        self.AddMenu('&View:Toolbars', kind="Popup", autocreate=True)
        self.AddMenu('&View:Sep', kind="Separator")
        self.AddMenu('&View:Panels', kind="Popup")

        self.AddMenu('&Tools', kind="Popup", autocreate=True)

        self.AddMenu('&Help:&Home', id=wx.ID_HOME, autocreate=True)
        self.ID_CONTACT = self.AddMenu('&Help:&Contact')
        self.AddMenu('&Help:Sep', kind="Separator")
        self.AddMenu('&Help:About', id=wx.ID_ABOUT)

        # Connect Events
        self.Bind(wx.EVT_MENU, self.OnFileQuit, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnHelpHome, id=wx.ID_HOME)
        self.Bind(wx.EVT_MENU, self.OnHelpContact, id=self.ID_CONTACT)
        self.Bind(wx.EVT_MENU, self.OnHelpAbout, id=wx.ID_ABOUT)

    def InitAddOn(self, modules, debug=False):
        if not modules:
            # load all modules
            modules = ["default"]

        for module in modules:
            module = module.split('+')
            options = {'debug': debug}
            if len(module) == 2:
                if all([c in 'htblr' for c in module[1]]):
                    if 'h' in module[1]:
                        options['active'] = False
                    if 't' in module[1]:
                        options['direction'] = 'Top'
                    if 'b' in module[1]:
                        options['direction'] = 'bottom'
                    if 'l' in module[1]:
                        options['direction'] = 'left'
                    if 'r' in module[1]:
                        options['direction'] = 'right'
                options['data'] = module[1]
            module = module[0]
            if module == 'default':
                module = self.bsm_packages
            else:
                module = [module]
            for pkg in module:
                if pkg in self.bsm_packages:
                    # module in bsm
                    pkg = 'bsmedit.bsm.%s' % pkg

                if pkg in self.addon:
                    # already loaded
                    continue
                self.addon[pkg] = False
                try:
                    mod = importlib.import_module(pkg)
                except ImportError:
                    traceback.print_exc(file=sys.stdout)
                else:
                    if hasattr(mod, 'bsm_initialize'):
                        mod.bsm_initialize(self, **options)
                        self.addon[pkg] = True
                    else:
                        print("Error: Invalid module: %s" % pkg)

    def AddFileHistory(self, filename):
        """add the file to recent file list"""
        self.config.SetPath('/FileHistory')
        self.filehistory.AddFileToHistory(filename)
        self.filehistory.Save(self.config)
        self.config.Flush()

    def SetConfig(self, group, **kwargs):
        if not group.startswith('/'):
            group = '/' + group
        for key, value in six.iteritems(kwargs):
            if key in ['signal', 'sender']:
                # reserved key for dp.send
                continue
            if not isinstance(value, str):
                # add sign to indicate that the value needs to be deserialize
                enc = MultiDimensionalArrayEncoder()
                value = '__bsm__' + enc.encode(value)
            self.config.SetPath(group)
            self.config.Write(key, value)

    def GetConfig(self, group, key=None):
        if not group.startswith('/'):
            group = '/' + group
        if self.config.HasGroup(group):
            self.config.SetPath(group)
            if key is None:
                rst = {}
                more, k, index = self.config.GetFirstEntry()
                while more:
                    value = self.config.Read(k)
                    if value.startswith('__bsm__'):
                        value = json.loads(value[7:], object_hook=hinted_tuple_hook)
                    rst[k] = value
                    more, k, index = self.config.GetNextEntry(index)
                return rst

            if self.config.HasEntry(key):
                value = self.config.Read(key)
                if value.startswith('__bsm__'):
                    value = json.loads(value[7:])
                return value
        return None

    def OnPageRightDown(self, evt):
        # get the index inside the current tab control
        idx = evt.GetSelection()
        tabctrl = evt.GetEventObject()
        tabctrl.SetSelection(idx)
        page = tabctrl.GetPage(idx)
        self.RenamePanel(page)

    def OnRightDown(self, evt):
        evt.Skip()

        part = self._mgr.HitTest(*evt.GetPosition())
        if not part or part.pane.IsNotebookControl():
            return

        self.RenamePanel(part.pane.window)

    def RenamePanel(self, panel):
        if not panel:
            return
        menu = wx.Menu()
        menu.Append(self.ID_VM_RENAME, "&Rename")
        pane_menu = None
        if panel in self.paneMenu:
            menu.AppendSeparator()
            pane_menu = self.paneMenu[panel]
            build_menu_from_list(pane_menu['menu'], menu)
        command = PopupMenu(self, menu)
        if command == self.ID_VM_RENAME:
            pane = self._mgr.GetPane(panel)
            if not pane:
                return
            name = pane.caption
            name = wx.GetTextFromUser("Type in the name:", "Input Name", name,
                                      self)
            # when user click 'cancel', name will be empty, ignore it.
            if name and name != pane.caption:
                self.SetPanelTitle(pane.window, name)
        elif command != 0 and pane_menu is not None:
            for m in pane_menu['menu']:
                if command == m.get('id', None):
                    dp.send(signal=pane_menu['rxsignal'], command=command, pane=panel)
                    break

    def UpdatePaneMenuLabel(self):
        # update the menu
        for (pid, panel) in six.iteritems(self.paneAddon):
            pathlist = panel['path'].split(':')
            menuitem = self.GetMenu(pathlist[:-1])
            if not menuitem:
                continue
            pane = self._mgr.GetPane(panel['panel'])
            item = menuitem.FindItemById(pid)
            if item and pane.caption != item.GetItemLabelText():
                item.SetItemLabel(pane.caption)

    def OnCloseWindow(self, evt):
        self.tbicon.Destroy()
        evt.Skip()

    def OnClose(self, event):
        """close the main program"""
        dp.send('frame.closing', event=event)
        if event.GetVeto():
            return
        self.closing = True
        dp.send('frame.exiting')
        sz = self.GetSize()
        self.SetConfig('mainframe', frame_width=sz[0], frame_height=sz[1])
        self.SetConfig('mainframe', perspective=self._mgr.SavePerspective())
        dp.send('frame.exit')
        self.config.Flush()
        super().OnClose(event)

    def ShowStatusText(self, text, index=0, width=-1):
        """set the status text"""
        if index >= len(self.statusbar_width):
            exd = [0] * (index + 1 - len(self.statusbar_width))
            self.statusbar_width.extend(exd)
            self.statusbar.SetFieldsCount(index + 1)
        if self.statusbar_width[index] < width:
            self.statusbar_width[index] = width
            self.statusbar.SetStatusWidths(self.statusbar_width)
        self.statusbar.SetStatusText(text, index)

    def OnActivate(self, event):
        if not self.closing:
            dp.send('frame.activate', activate=event.GetActive())
        event.Skip()

    def OnPaneActivated(self, event):
        """notify the window managers that the panel is activated"""
        if self.closing:
            return
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
                self.UpdatePaneMenuLabel()

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
        webbrowser.open("mail:tq@feiyilin.com")
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
        wx.Dialog.__init__(self,
                           parent,
                           title="About bsmedit",
                           style=wx.DEFAULT_DIALOG_STYLE)

        szAll = wx.BoxSizer(wx.VERTICAL)

        self.panel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        self.panel.SetBackgroundColour(wx.WHITE)

        szPanelAll = wx.BoxSizer(wx.HORIZONTAL)

        self.header = wx.StaticBitmap(self.panel)
        self.header.SetBitmap(svg_to_bitmap(bsmedit_svg, 128, 128,  win=self))
        szPanelAll.Add(self.header, 0, wx.EXPAND, 0)


        szPanel = wx.BoxSizer(wx.VERTICAL)
        szPanel.AddStretchSpacer(1)
        MAX_SIZE = 300
        caption = 'bsmedit %s' % (__version__)
        self.stCaption = wx.StaticText(self.panel, wx.ID_ANY, caption)
        self.stCaption.SetMaxSize((MAX_SIZE, -1))
        self.stCaption.Wrap(MAX_SIZE)
        self.stCaption.SetFont(wx.Font(16, 74, 90, 92, False, "Arial"))

        szPanel.Add(self.stCaption, 0, wx.ALL | wx.EXPAND, 5)

        strCopyright = f'(c) 2018-{datetime.datetime.now().year} Tianzhu Qiao. All rights reserved.'
        self.stCopyright = wx.StaticText(self.panel, wx.ID_ANY, strCopyright)
        self.stCopyright.SetMaxSize((MAX_SIZE, -1))
        self.stCopyright.Wrap(MAX_SIZE)
        self.stCopyright.SetFont(wx.Font(10, 74, 90, 90, False, "Arial"))
        szPanel.Add(self.stCopyright, 0, wx.ALL | wx.EXPAND, 5)

        build = wx.GetOsDescription() + '; wxWidgets ' + wx.version()
        self.stBuild = wx.StaticText(self.panel, wx.ID_ANY, build)
        self.stBuild.SetMaxSize((MAX_SIZE, -1))
        self.stBuild.Wrap(MAX_SIZE)
        self.stBuild.SetFont(wx.Font(10, 74, 90, 90, False, "Arial"))
        szPanel.Add(self.stBuild, 0, wx.ALL | wx.EXPAND, 5)

        stLine = wx.StaticLine(self.panel, style=wx.LI_HORIZONTAL)
        szPanel.Add(stLine, 0, wx.EXPAND | wx.ALL, 0)
        szPanel.AddStretchSpacer(1)

        szPanelAll.Add(szPanel, 1, wx.EXPAND | wx.ALL, 0)

        self.panel.SetSizer(szPanelAll)
        self.panel.Layout()
        szPanel.Fit(self.panel)

        szAll.Add(self.panel, 1, wx.EXPAND | wx.ALL, 0)

        btnsizer = wx.StdDialogButtonSizer()

        self.btnOK = wx.Button(self, wx.ID_OK)
        self.btnOK.SetDefault()
        btnsizer.AddButton(self.btnOK)
        btnsizer.Realize()

        szAll.Add(btnsizer, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)
