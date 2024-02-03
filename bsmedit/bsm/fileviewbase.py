import os
import json
import wx
import wx.py.dispatcher as dp
from wx.lib.mixins.listctrl import ListCtrlAutoWidthMixin
import numpy as np
from pandas.api.types import is_numeric_dtype
from ..aui import aui
from .bsmxpm import open_svg, refresh_svg
from .utility import FastLoadTreeCtrl, _dict
from .utility import svg_to_bitmap
from .utility import get_file_finder_name, show_file_in_finder
from .autocomplete import AutocompleteTextCtrl
from . import graph

class FindListCtrl(wx.ListCtrl):
    ID_FIND_REPLACE = wx.NewIdRef()
    ID_FIND_NEXT = wx.NewIdRef()
    ID_FIND_PREV = wx.NewIdRef()
    ID_COPY_NO_INDEX = wx.NewIdRef()
    def __init__(self, *args, **kwargs):
        wx.ListCtrl.__init__(self, *args, **kwargs)
        self.SetupFind()

        self.index_column = 0
        self.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self.OnRightClick)
        self.Bind(wx.EVT_TOOL, self.OnBtnCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_TOOL, self.OnBtnCopy, id=self.ID_COPY_NO_INDEX)

        accel = [
            (wx.ACCEL_CTRL, ord('F'), self.ID_FIND_REPLACE),
            (wx.ACCEL_SHIFT, wx.WXK_F3, self.ID_FIND_PREV),
            (wx.ACCEL_CTRL, ord('H'), self.ID_FIND_REPLACE),
            (wx.ACCEL_RAW_CTRL, ord('H'), self.ID_FIND_REPLACE),
            (wx.ACCEL_CTRL, ord('C'), wx.ID_COPY),
            (wx.ACCEL_CTRL | wx.ACCEL_SHIFT, ord('C'), self.ID_COPY_NO_INDEX),
        ]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)

    def OnRightClick(self, event):

        if self.GetSelectedItemCount() <= 0:
            return

        menu = wx.Menu()
        menu.Append(wx.ID_COPY, "&Copy \tCtrl+C")
        if 0 <= self.index_column < self.GetColumnCount():
            menu.Append(self.ID_COPY_NO_INDEX, "C&opy without index \tCtrl+Shift+C")
        self.PopupMenu(menu)

    def OnBtnCopy(self, event):
        cmd = event.GetId()
        columns = list(range(self.GetColumnCount()))
        if cmd == self.ID_COPY_NO_INDEX:
            columns.remove(self.index_column)
        if wx.TheClipboard.Open():
            item = self.GetFirstSelected()
            text = []
            while item != -1:
                tmp = []
                for c in columns:
                    tmp.append(self.GetItemText(item, c))
                text.append(" ".join(tmp))
                item = self.GetNextSelected(item)
            wx.TheClipboard.SetData(wx.TextDataObject("\n".join(text)))
            wx.TheClipboard.Close()

    def SetupFind(self):
        # find & replace dialog
        self.findDialog = None
        self.findStr = ""
        self.replaceStr = ""
        self.findFlags = 1
        self.stcFindFlags = 0
        self.findDialogStyle = 0 #wx.FR_REPLACEDIALOG
        self.wrapped = 0

        self.Bind(wx.EVT_TOOL, self.OnShowFindReplace, id=self.ID_FIND_REPLACE)
        self.Bind(wx.EVT_TOOL, self.OnFindNext, id=self.ID_FIND_NEXT)
        self.Bind(wx.EVT_TOOL, self.OnFindPrev, id=self.ID_FIND_PREV)

    def OnShowFindReplace(self, event):
        """Find and Replace dialog and action."""
        # find string
        findStr = ""#self.GetSelectedText()
        if findStr and self.findDialog:
            self.findDialog.Destroy()
            self.findDialog = None
        # dialog already open, if yes give focus
        if self.findDialog:
            self.findDialog.Show(1)
            self.findDialog.Raise()
            return
        if not findStr:
            findStr = self.findStr
        # find data
        data = wx.FindReplaceData(self.findFlags)
        data.SetFindString(findStr)
        data.SetReplaceString(self.replaceStr)
        # dialog
        title = 'Find'
        if self.findDialogStyle & wx.FR_REPLACEDIALOG:
            title = 'Find & Replace'

        self.findDialog = wx.FindReplaceDialog(
            self, data, title, self.findDialogStyle)
        # bind the event to the dialog, see the example in wxPython demo
        self.findDialog.Bind(wx.EVT_FIND, self.OnFind)
        self.findDialog.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.findDialog.Bind(wx.EVT_FIND_REPLACE, self.OnReplace)
        self.findDialog.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnReplaceAll)
        self.findDialog.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.findDialog.Show(1)
        self.findDialog.data = data  # save a reference to it...

    def message(self, text):
        """show the message on statusbar"""
        dp.send('frame.show_status_text', text=text)

    def FindText(self, start, end, text, flags=0):
        # not found
        return -1

    def doFind(self, strFind, forward=True):
        """search the string"""
        current = self.GetFirstSelected()
        if current == -1:
            current = 0
        position = -1
        if forward:
            if current < self.GetItemCount() - 1:
                position = self.FindText(current+1, self.GetItemCount()-1,
                                         strFind, self.findFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self.FindText(0, current, strFind, self.findFlags)
        else:
            if current > 0:
                position = self.FindText(current-1, 0, strFind, self.findFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self.FindText(self.GetItemCount()-1, current,
                                         strFind, self.findFlags)

        # not found the target, do not change the current position
        if position == -1:
            self.message("'%s' not found!" % strFind)
            position = current
            strFind = """"""
        #self.GotoPos(position)
        #self.SetSelection(position, position + len(strFind))
        while True:
            sel = self.GetFirstSelected()
            if sel == -1:
                break
            self.Select(sel, False)
        self.EnsureVisible(position)
        self.Select(position)
        return position

    def OnFind(self, event):
        """search the string"""
        self.findStr = event.GetFindString()
        self.findFlags = event.GetFlags()
        flags = 0
        #if wx.FR_WHOLEWORD & self.findFlags:
        #    flags |= stc.STC_FIND_WHOLEWORD
        #if wx.FR_MATCHCASE & self.findFlags:
        #    flags |= stc.STC_FIND_MATCHCASE
        #self.stcFindFlags = flags
        return self.doFind(self.findStr, wx.FR_DOWN & self.findFlags)

    def OnFindClose(self, event):
        """close find & replace dialog"""
        event.GetDialog().Destroy()

    def OnReplace(self, event):
        """replace"""
        # Next line avoid infinite loop
        findStr = event.GetFindString()
        self.replaceStr = event.GetReplaceString()

        source = self
        selection = source.GetSelectedText()
        if not event.GetFlags() & wx.FR_MATCHCASE:
            findStr = findStr.lower()
            selection = selection.lower()

        if selection == findStr:
            position = source.GetSelectionStart()
            source.ReplaceSelection(self.replaceStr)
            source.SetSelection(position, position + len(self.replaceStr))
        # jump to next instance
        position = self.OnFind(event)
        return position

    def OnReplaceAll(self, event):
        """replace all the instances"""
        source = self
        count = 0
        self.wrapped = 0
        position = start = source.GetCurrentPos()
        while position > -1 and (not self.wrapped or position < start):
            position = self.OnReplace(event)
            if position != -1:
                count += 1
            if self.wrapped >= 2:
                break
        self.GotoPos(start)
        if not count:
            self.message("'%s' not found!" % event.GetFindString())

    def OnFindNext(self, event):
        """go the previous instance of search string"""
        findStr = self.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr)

    def OnFindPrev(self, event):
        """go the previous instance of search string"""
        findStr = self.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr, False)

    def Search(self, src, pattern, flags):
        if not (wx.FR_MATCHCASE & flags):
            pattern = pattern.lower()
            src = src.lower()

        if wx.FR_WHOLEWORD & flags:
            return pattern in src.split()

        return pattern in src

class ListCtrlBase(FindListCtrl, ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        FindListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES|wx.LC_VIRTUAL)
        ListCtrlAutoWidthMixin.__init__(self)
        self.EnableAlternateRowColours()
        self.ExtendRulesAndAlternateColour()

        self.data_start_column = 0
        self.BuildColumns()

        self.data = None
        self.pattern = None
        self.data_shown = []

    def BuildColumns(self):
        self.InsertColumn(0, "#", width=60)
        self.data_start_column = 1

    def OnGetItemText(self, item, column):
        if self.data_start_column > 0 and column == 0:
            # index column
            return f"{item+1}"
        return ""

    def Load(self, data):
        self.data = data
        self.SetItemCount(0)
        if self.data is not None:
            self.Fill(self.pattern)

    def ApplyPattern(self):
        self.data_shown = self.data

    def Fill(self, pattern):
        self.pattern = pattern
        if isinstance(self.pattern, str):
            self.pattern = self.pattern.lower()
            self.pattern.strip()
        self.ApplyPattern()
        self.SetItemCount(len(self.data_shown))
        if self.GetItemCount():
            self.RefreshItems(0, len(self.data_shown)-1)

class TreeCtrlBase(FastLoadTreeCtrl):
    """the tree control to show the hierarchy of the objects in the vcd"""
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        style = style | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT |\
                wx.TR_MULTIPLE | wx.TR_LINES_AT_ROOT
        FastLoadTreeCtrl.__init__(self, parent, self.get_children, style=style)

        self.data = _dict()
        self.pattern = None
        self.expanded = {}

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        self.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)

    def GetItemDragData(self, item):
        path = self.GetItemPath(item)
        data = self.GetData(item)
        data = data.get(['timestamp', path[-1]]).copy()
        data.timestamp *= self.vcd.get('timescale', 1e-6) * 1e6
        return data

    def GetPlotXLabel(self):
        return ""

    def OnTreeBeginDrag(self, event):
        if not self.data:
            return

        ids = self.GetSelections()
        objs = []
        for item in ids:
            if item == self.GetRootItem() or self.ItemHasChildren(item):
                continue
            if not item.IsOk():
                break
            path = self.GetItemPath(item)
            data = self.GetItemDragData(item)
            objs.append(['/'.join(path[:-1]), data.to_json()])

        # need to explicitly allow drag
        # start drag operation
        data = wx.TextDataObject(json.dumps({'lines': objs, 'xlabel': self.GetPlotXLabel()}))
        source = wx.DropSource(self)
        source.SetData(data)
        rtn = source.DoDragDrop(True)
        if rtn == wx.DragError:
            wx.LogError("An error occurred during drag and drop operation")
        elif rtn == wx.DragNone:
            pass
        elif rtn == wx.DragCopy:
            pass
        elif rtn == wx.DragMove:
            pass
        elif rtn == wx.DragCancel:
            pass

    def OnTreeItemMenu(self, event):
        pass

    def GetItemPlotData(self, item):
        y = self.GetItemData(item)
        x = np.arange(0, len(y))
        return x, y

    def PlotItem(self, item, confirm=True):
        if self.ItemHasChildren(item):
            if confirm:
                text = self.GetItemText(item)
                msg = f"Do you want to plot all signals under '{text}'?"
                dlg = wx.MessageDialog(self, msg, 'bsmedit', wx.YES_NO)
                if dlg.ShowModal() != wx.ID_YES:
                    return

            child, cookie = self.GetFirstChild(item)
            while child.IsOk():
                self.PlotItem(child, confirm=False)
                child, cookie = self.GetNextChild(item, cookie)
        else:
            path = self.GetItemPath(item)
            x, y = self.GetItemPlotData(item)
            if x is not None and y is not None:
                self.plot(x, y, "/".join(path))

    def OnTreeItemActivated(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        self.PlotItem(item)

    def plot(self, x, y, label, step=False):
        if x is None or y is None or not is_numeric_dtype(y):
            print(f"{label} is not numeric, ignore plotting!")
            return

        # plot
        label = label.lstrip('_')
        mgr = graph.plt.get_current_fig_manager()
        if not isinstance(mgr, graph.MatplotPanel) and hasattr(mgr, 'frame'):
            mgr = mgr.frame
        if not mgr.IsShownOnScreen():
            dp.send('frame.show_panel', panel=mgr)
        ls, ms = None, None
        if mgr.figure.gca().lines:
            # match the line/marker style of the existing line
            line = mgr.figure.gca().lines[0]
            ls, ms = line.get_linestyle(), line.get_marker()
        if step:
            mgr.figure.gca().step(x, y, label=label, linestyle=ls, marker=ms)
        else:
            mgr.figure.gca().plot(x, y, label=label, linestyle=ls, marker=ms)

        mgr.figure.gca().legend()
        if ls is None:
            # 1st plot in axes
            mgr.figure.gca().grid(True)
            xlabel = self.GetPlotXLabel()
            if xlabel:
                mgr.figure.gca().set_xlabel(xlabel)
            if step:
                # hide the y-axis tick label
                mgr.figure.gca().get_yaxis().set_ticklabels([])

    def GetItemPath(self, item):
        if not item.IsOk():
            return []
        text = self.GetItemText(item)
        path = [text]
        parent = self.GetItemParent(item)

        while parent.IsOk() and parent != self.GetRootItem():
            path.insert(0, self.GetItemText(parent))
            parent = self.GetItemParent(parent)
        return path

    def GetItemData(self, item):
        if self.ItemHasChildren(item):
            return None

        path = self.GetItemPath(item)
        return self.GetItemDataFromPath(path)

    def GetItemDataFromPath(self, path):
        d = self.data
        for p in path:
            d = d[p]
        return d

    def _has_pattern(self, d):
        if not isinstance(d, dict):
            return False
        if any(self.pattern in k for k in d.keys()):
            return True
        for v in d.values():
            if self._has_pattern(v):
                return True
        return False

    def get_children(self, item):
        """ callback function to return the children of item """
        children = []
        pattern = self.pattern
        if item == self.GetRootItem():
            children = [[k, isinstance(v, dict)]  for k, v in self.data.items() if not pattern or pattern in k or self._has_pattern(v)]
        else:
            path = self.GetItemPath(item)
            d = self.data
            for p in path:
                d = d[p]
                children = [[k, isinstance(v, dict)]  for k, v in d.items() if not pattern or pattern in k or self._has_pattern(v)]

        if pattern:
            self.expanded = [c for c, _ in children if pattern not in c]
        if item == self.GetRootItem() and not self.expanded and children:
            self.expanded = [children[0][0]]

        children = [{'label': c, 'img':-1, 'imgsel':-1, 'data': None, 'is_folder': is_folder} for c, is_folder in children]
        return children

    def OnCompareItems(self, item1, item2):
        """compare the two items for sorting"""
        text1 = self.GetItemText(item1)
        text2 = self.GetItemText(item2)
        rtn = -2
        if text1 and text2:
            return text1.lower() > text2.lower()
        return rtn

    def Load(self, data):
        """load the dict data"""
        assert isinstance(data, dict)
        self.data = data
        self.Fill(self.pattern)

    def Fill(self, pattern=None):
        """fill the vcd  objects tree"""
        #clear the tree control
        self.expanded = {}
        self.DeleteAllItems()
        if not self.data:
            return
        self.pattern = pattern
        # add the root item
        item = self.AddRoot("bsmedit")
        # fill the top level item
        self.FillChildren(item)

        if not self.expanded:
            return
        # expand the child to show the items that match pattern
        child, cookie = self.GetFirstChild(item)
        while child.IsOk():
            name = self.GetItemText(child)
            if name in self.expanded:
                self.Expand(child)
            child, cookie = self.GetNextChild(item, cookie)

    def FindItemFromPath(self, path):
        if not path:
            return None
        item = self.GetRootItem()
        for p in path:
            child, cookie = self.GetFirstChild(item)
            while child.IsOk():
                name = self.GetItemText(child)
                if name == p:
                    item = child
                    break
                child, cookie = self.GetNextChild(item, cookie)
            else:
                return None
        return item


class PanelBase(wx.Panel):

    ID_OPEN = wx.NewIdRef()
    ID_REFRESH = wx.NewIdRef()
    def __init__(self, parent, filename=None):
        wx.Panel.__init__(self, parent)

        self.init()

        self.filename = None
        if filename is not None:
            self.Load(filename)

    def init(self):
        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)

    def GetFileName(self):
        filename = 'untitled'
        if self.filename:
            (_, filename) = os.path.split(self.filename)
        return filename

    def GetCaption(self):
        return self.GetFileName()

    def Load(self, filename, add_to_history=True):
        """load the file"""
        self.filename = filename
        # add the filename to history
        if add_to_history:
            dp.send('frame.add_file_history', filename=filename)
        title = self.GetCaption()
        dp.send('frame.set_panel_title', pane=self, title=title)

    @classmethod
    def GetFileType(cls):
        return "|All files (*.*)|*.*"

    @classmethod
    def get_all_managers(cls):
        return []

    @classmethod
    def get_active(cls):
        raise NotImplementedError

    @classmethod
    def set_active(cls, panel):
        raise NotImplementedError

    @classmethod
    def get_manager(cls, num):
        raise NotImplementedError

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        if eid == self.ID_OPEN:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = self.GetFileType()
            dlg = wx.FileDialog(self, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                self.Load(filename=filename)
                title = self.GetCaption()
                dp.send('frame.set_panel_title', pane=self, title=title)
            dlg.Destroy()
        elif eid == self.ID_REFRESH:
            if self.filename:
                self.Load(filename=self.filename)

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()
        if eid == self.ID_REFRESH:
            event.Enable(self.filename is not None)


class PanelNotebookBase(PanelBase):

    def init(self):
        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        open_bmp = svg_to_bitmap(open_svg, win=self)
        self.tb.AddTool(self.ID_OPEN, "Open", open_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Open file")
        self.tb.AddSeparator()
        refresh_bmp = svg_to_bitmap(refresh_svg, win=self)
        self.tb.AddTool(self.ID_REFRESH, "Refresh", refresh_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Refresh file")

        self.tb.Realize()

        self.notebook = aui.AuiNotebook(self, agwStyle=aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS | wx.NO_BORDER)

        self.init_pages()

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.notebook, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        super().init()

    def init_pages(self):
        return

    def CreatePageWithSearch(self, PageClass):
        panel = wx.Panel(self.notebook)
        search = AutocompleteTextCtrl(panel)
        search.SetHint('searching ...')
        ctrl = PageClass(panel)
        szAll = wx.BoxSizer(wx.VERTICAL)
        szAll.Add(search, 0, wx.EXPAND|wx.ALL, 2)
        szAll.Add(ctrl, 1, wx.EXPAND)
        szAll.Fit(panel)
        panel.SetSizer(szAll)
        return panel, search, ctrl


class FileViewBase:
    name = None
    panel_type = PanelBase
    frame = None
    target_pane = "History"

    ID_PANE_COPY_PATH = wx.NewIdRef()
    ID_PANE_COPY_PATH_REL = wx.NewIdRef()
    ID_PANE_SHOW_IN_FINDER = wx.NewIdRef()
    ID_PANE_SHOW_IN_BROWSING = wx.NewIdRef()
    ID_PANE_CLOSE = wx.NewIdRef()
    ID_PANE_CLOSE_OTHERS = wx.NewIdRef()
    ID_PANE_CLOSE_ALL = wx.NewIdRef()


    @classmethod
    def initialize(cls, frame, **kwargs):
        if cls.frame is not None:
            # already initialized
            return
        cls.frame = frame
        cls.IDS = {}
        cls.init_menu()

        dp.connect(cls.process_command, signal=f'bsm.{cls.name}')
        dp.connect(receiver=cls.set_active, signal='frame.activate_panel')
        dp.connect(receiver=cls.initialized, signal='frame.initialized')
        dp.connect(receiver=cls.uninitializing, signal='frame.exiting')
        dp.connect(receiver=cls.uninitialized, signal='frame.exit')
        dp.connect(receiver=cls.open, signal='frame.file_drop')
        dp.connect(cls.PaneMenu, f'bsm.{cls.name}.pane_menu')

    @classmethod
    def get_menu(cls):
        return [['open', f'File:Open:{cls.name} file']]

    @classmethod
    def init_menu(cls):
        assert cls.name is not None
        for key, menu in cls.get_menu():
            resp = dp.send(signal='frame.add_menu',
                           path=menu,
                            rxsignal=f'bsm.{cls.name}')
            if resp:
                cls.IDS[key] = resp[0][1]

    @classmethod
    def initialized(cls):
        # add interface to the shell
        pass

    @classmethod
    def set_active(cls, pane):
        if pane and isinstance(pane, cls.panel_type):
            if cls.panel_type.get_active() == pane:
                return
            cls.panel_type.set_active(pane)

    @classmethod
    def uninitializing(cls):
        # before save perspective
        for mgr in cls.panel_type.get_all_managers():
            dp.send('frame.delete_panel', panel=mgr)
        for key, menu in cls.get_menu():
            if key not in cls.IDS:
                continue
            dp.send('frame.delete_menu', path=menu, id=cls.IDS[key])

    @classmethod
    def uninitialized(cls):
        # after save perspective
        pass

    @classmethod
    def process_command(cls, command):
        if command == cls.IDS.get('open', None):
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = cls.panel_type.GetFileType()
            dlg = wx.FileDialog(cls.frame, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                cls.open(filename=filename, activate=True)
            dlg.Destroy()

    @classmethod
    def check_filename(cls, filename):
        raise NotImplementedError

    @classmethod
    def open(cls,
            filename=None,
            num=None,
            activate=True,
            add_to_history=True):
        """
        open an file

        If the file has already been opened, return its handler; otherwise, create it.
        """
        if not cls.check_filename(filename):
            return None

        manager = cls.get_manager(num, filename)
        if manager is None:
            manager = cls.panel_type(cls.frame)
            if filename:
                manager.Load(filename, add_to_history=add_to_history)
            title = manager.GetCaption()
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target=cls.target_pane,
                    pane_menu={'rxsignal': f'bsm.{cls.name}.pane_menu',
                           'menu': [
                               {'id':cls.ID_PANE_CLOSE, 'label':'Close'},
                               {'id':cls.ID_PANE_CLOSE_OTHERS, 'label':'Close Others'},
                               {'id':cls.ID_PANE_CLOSE_ALL, 'label':'Close All'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id':cls.ID_PANE_COPY_PATH, 'label':'Copy Path'},
                               {'id':cls.ID_PANE_COPY_PATH_REL, 'label':'Copy Relative Path'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id': cls.ID_PANE_SHOW_IN_FINDER, 'label':f'Reveal in  {get_file_finder_name()}'},
                               {'id': cls.ID_PANE_SHOW_IN_BROWSING, 'label':'Reveal in Browsing panel'},
                               ]} )
            return manager
        # activate the manager
        if manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)
        return manager

    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, cls.panel_type):
            return
        if command in [cls.ID_PANE_COPY_PATH, cls.ID_PANE_COPY_PATH_REL]:
            if wx.TheClipboard.Open():
                filepath = pane.filename
                if command == cls.ID_PANE_COPY_PATH_REL:
                    filepath = os.path.relpath(filepath, os.getcwd())
                wx.TheClipboard.SetData(wx.TextDataObject(filepath))
                wx.TheClipboard.Close()
        elif command == cls.ID_PANE_SHOW_IN_FINDER:
            show_file_in_finder(pane.filename)
        elif command == cls.ID_PANE_SHOW_IN_BROWSING:
            dp.send(signal='dirpanel.goto', filepath=pane.filename, show=True)
        elif command == cls.ID_PANE_CLOSE:
            dp.send(signal='frame.delete_panel', panel=pane)
        elif command == cls.ID_PANE_CLOSE_OTHERS:
            mgrs =  cls.panel_type.get_all_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  cls.panel_type.get_all_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def get_manager(cls, num=None, filename=None):
        manager = None
        if num is not None:
            manager = cls.panel_type.get_manager(num)
        if manager is None and isinstance(filename, str):
            abs_filename = os.path.abspath(filename).lower()
            for m in cls.panel_type.get_all_managers():
                if abs_filename == os.path.abspath(m.filename).lower():
                    manager = m
                    break
        return manager

    @classmethod
    def get(cls, num=None, filename=None, data_only=True):
        # return the content of a file
        manager = cls.get_manager(num, filename)
        if num is None and filename is None and manager is None:
            manager = cls.panel_type.get_active()
        return manager
