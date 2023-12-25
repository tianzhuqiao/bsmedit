import sys
import os
import json
import traceback
import wx
import wx.py.dispatcher as dp
import pyulog
import pandas as pd
from ..aui import aui
from . import graph
from .bsmxpm import open_svg
from .pymgr_helpers import Gcm
from .utility import FastLoadTreeCtrl, PopupMenu, _dict, svg_to_bitmap
from .utility import get_file_finder_name, show_file_in_finder
from .autocomplete import AutocompleteTextCtrl

class ULogTree(FastLoadTreeCtrl):
    """the tree control to show the hierarchy of the objects in the ulog"""
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        style = style | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT |\
                wx.TR_MULTIPLE | wx.TR_LINES_AT_ROOT
        FastLoadTreeCtrl.__init__(self, parent, self.get_children, style=style)

        self.data = _dict()
        self.filename = ""
        self.pattern = None
        self.expanded = {}

    def get_children(self, item):
        """ callback function to return the children of item """
        children = []
        is_folder = False
        pattern = self.pattern
        if item == self.GetRootItem():
            children = list(self.data.keys())
            is_folder = True
            if pattern:
                temp = []
                for c in children:
                    dataset = list(self.data[c].columns)
                    dataset.remove('timestamp')
                    if any(pattern in s for s in dataset):
                        self.expanded[c] = True
                        temp.append(c)
                    elif pattern in c:
                        temp.append(c)
                children = temp
        else:
            parent = self.GetItemText(item)
            if parent in self.data:
                children = list(self.data[parent].columns)
                children.remove('timestamp')
                if pattern and pattern not in parent:
                    children = [c for c in children if pattern in c]
        children = [{'label': c, 'img':-1, 'imgsel':-1, 'data': None, 'is_folder': is_folder} for c in children]
        return children

    def OnCompareItems(self, item1, item2):
        """compare the two items for sorting"""
        text1 = self.GetItemText(item1)
        text2 = self.GetItemText(item2)
        rtn = -2
        if text1 and text2:
            return text1.lower() > text2.lower()
        return rtn

    def Load(self, ulg):
        """load the ulog file"""
        data = _dict()
        for d in ulg.data_list:
            df = pd.DataFrame(d.data)
            data[d.name] = df
        self.data = data
        self.FillTree(self.pattern)

    def FillTree(self, pattern=None):
        """fill the ulog objects tree"""
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

class ListCtrlBase(FindListCtrl, wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin):
    def __init__(self, parent):
        FindListCtrl.__init__(self, parent, style=wx.LC_REPORT|wx.LC_HRULES|wx.LC_VRULES|wx.LC_VIRTUAL)
        wx.lib.mixins.listctrl.ListCtrlAutoWidthMixin.__init__(self)
        self.EnableAlternateRowColours()
        self.ExtendRulesAndAlternateColour()

class MessageListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.ulg = None
        self.InsertColumn(0, "#", width=60)
        self.InsertColumn(1, "Timestamp", width=120)
        self.InsertColumn(2, "Type", width=120)
        self.InsertColumn(3, "Message", width=wx.LIST_AUTOSIZE_USEHEADER)
        self.messages = []
        self.pattern = None

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.messages[i].message
            if self.Search(m, text, flags):
                return i

        # not found
        return -1

    def Load(self, ulg):
        self.ulg = ulg
        self.SetItemCount(0)
        if self.ulg is not None:
            self.FillMessage(self.pattern)

    def FillMessage(self, pattern):
        self.pattern = pattern
        if isinstance(self.pattern, str):
            self.pattern = self.pattern.lower()
            self.pattern.strip()
        if not self.pattern:
            self.messages = self.ulg.logged_messages
        else:
            self.messages = [m for m in self.ulg.logged_messages if self.pattern in m.message.lower() or self.pattern in m.log_level_str().lower()]

        self.SetItemCount(len(self.messages))
        self.RefreshItems(0, len(self.messages)-1)

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        m = self.messages[item]
        if column == 0:
            return str(m.timestamp/1e6)
        if column == 1:
            return m.log_level_str()
        if column == 2:
            return m.message
        return ""

class InfoListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.ulg = None
        self.info = []
        self.InsertColumn(0, "#", width=60)
        self.InsertColumn(1, "Key", width=120)
        self.InsertColumn(2, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.info[i]
            if self.Search(m[0], text, flags) or self.Search(str(m[1]), text, flags):
                return i

        # not found
        return -1

    def Load(self, ulg):
        self.ulg = ulg
        self.SetItemCount(0)
        if self.ulg is not None:
            self.info = [[k, v] for k, v in self.ulg.msg_info_dict.items()]
            self.info = sorted(self.info, key=lambda x: x[0])
            self.SetItemCount(len(self.info))

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        return str(self.info[item][column])

class ParamListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.ulg = None
        self.info = []
        self.InsertColumn(0, "#", width=60)
        self.InsertColumn(1, "Key", width=200)
        self.InsertColumn(2, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)
        self.pattern = None

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.info[i]
            if self.Search(str(m[0]), text, flags) or self.Search(str(m[1]), text, flags):
                return i

        # not found
        return -1

    def Load(self, ulg):
        self.ulg = ulg
        self.SetItemCount(0)
        if self.ulg is not None:
            self.FillParams(self.pattern)

    def FillParams(self, pattern):
        self.pattern = pattern
        if isinstance(self.pattern, str):
            self.pattern = self.pattern.lower()
            self.pattern.strip()
        if self.pattern:
            self.info = [[k, v] for k, v in self.ulg.initial_parameters.items() if self.pattern in str(k).lower() or self.pattern.lower() in str(v).lower()]
        else:
            self.info = [[k, v] for k, v in self.ulg.initial_parameters.items()]

        self.info = sorted(self.info, key=lambda x: x[0])
        self.SetItemCount(len(self.info))
        self.RefreshItems(0, len(self.info)-1)

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        return str(self.info[item][column])

class ChgParamListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.ulg = None
        self.InsertColumn(0, "#", width=60)
        self.InsertColumn(1, "Timestamp", width=120)
        self.InsertColumn(2, "Key", width=200)
        self.InsertColumn(3, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.ulg.changed_parameters[i]
            if self.Search(str(m[1]), text, flags) or self.Search(str(m[2]), text, flags):
                return i

        # not found
        return -1

    def Load(self, ulg):
        self.ulg = ulg
        self.SetItemCount(0)
        if self.ulg is not None:
            self.SetItemCount(len(self.ulg.changed_parameters))

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        m = self.ulg.changed_parameters[item]
        if column == 0:
            return str(m[0]/1e6)
        return str(m[column])


class ULogPanel(wx.Panel):
    Gcu = Gcm()
    ID_ULOG_OPEN = wx.NewIdRef()
    ID_ULOG_EXPORT = wx.NewIdRef()
    ID_ULOG_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()

    def __init__(self, parent, filename=None):
        wx.Panel.__init__(self, parent)

        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        open_bmp = wx.Bitmap(svg_to_bitmap(open_svg, win=self))
        self.tb.AddTool(self.ID_ULOG_OPEN, "Open", open_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Open ulog file")

        self.tb.Realize()

        self.notebook = aui.AuiNotebook(self, agwStyle=aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS | wx.NO_BORDER)

        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(ULogTree)
        self.notebook.AddPage(panel, 'Data')
        # log page
        panel_log, self.search_log, self.logList = self.CreatePageWithSearch(MessageListCtrl)
        self.notebook.AddPage(panel_log, 'Log')

        self.infoList = InfoListCtrl(self.notebook)
        self.notebook.AddPage(self.infoList, 'Info')

        panel_param, self.search_param, self.paramList = self.CreatePageWithSearch(ParamListCtrl)
        self.notebook.AddPage(panel_param, 'Param')

        self.chgParamList = ChgParamListCtrl(self.notebook)
        self.notebook.AddPage(self.chgParamList, 'Changed Param')

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.notebook, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)
        self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchLog, self.search_log)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchParam, self.search_param)

        # load the ulog
        self.ulg = None
        if filename is not None:
            self.Load(filename)

        self.num = self.Gcu.get_next_num()
        self.Gcu.set_active(self)

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

    def Load(self, filename):
        """load the ulog file"""
        u = pyulog.ULog(filename)
        self.ulg = u
        self.filename = filename
        self.tree.Load(u)
        self.logList.Load(u)
        self.infoList.Load(u)
        self.paramList.Load(u)
        self.chgParamList.Load(u)
        dp.send('frame.add_file_history', filename=filename)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.FillTree(pattern)
        self.search.SetFocus()

    def OnDoSearchLog(self, evt):
        pattern = self.search_log.GetValue()
        self.logList.FillMessage(pattern)

    def OnDoSearchParam(self, evt):
        pattern = self.search_param.GetValue()
        self.paramList.FillParams(pattern)

    def Destroy(self):
        """
        Destroy the ulog properly before close the pane.
        """
        self.Gcu.destroy(self.num)
        super().Destroy()

    def GetItemPath(self, item):
        if not item.IsOk():
            return []
        text = self.tree.GetItemText(item)
        path = [text]
        parent = self.tree.GetItemParent(item)
        if parent.IsOk() and parent != self.tree.GetRootItem():
            path.insert(0, self.tree.GetItemText(parent))
        return path

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        has_child = self.tree.ItemHasChildren(item)
        menu = wx.Menu()
        menu.Append(self.ID_ULOG_EXPORT, "&Export to shell")
        if not has_child:
            menu.Append(self.ID_ULOG_EXPORT_WITH_TIMESTAMP, "E&xport to shell with timestamp")

        cmd = PopupMenu(self, menu)
        text = self.tree.GetItemText(item)
        path = self.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_ULOG_EXPORT, self.ID_ULOG_EXPORT_WITH_TIMESTAMP]:
            name = text.replace('[', '').replace(']', '')
            command = f'{name}=ulog.get()["{path[0]}"]'
            if len(path) > 1:
                if cmd == self.ID_ULOG_EXPORT_WITH_TIMESTAMP:
                    command += f'.get(["timestamp", "{path[1]}"])'
                else:
                    command += f'.get(["{path[1]}"])'
            dp.send(signal='shell.run',
                command=command,
                prompt=True,
                verbose=True,
                history=True)

    def OnTreeItemActivated(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        if self.tree.ItemHasChildren(item):
            return
        parent = self.tree.GetItemParent(item)
        if not parent.IsOk():
            return
        datasetname = self.tree.GetItemText(parent)
        dataset = self.tree.data[datasetname]
        dataname = self.tree.GetItemText(item)
        x = dataset['timestamp']/1e6
        y = dataset[dataname]

        # plot
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
        mgr.figure.gca().plot(x, y, label="/".join([datasetname, dataname]),
                              linestyle=ls, marker=ms)
        mgr.figure.gca().legend()
        mgr.figure.gca().grid(True)
        mgr.figure.gca().set_xlabel('t(s)')

    def OnTreeBeginDrag(self, event):
        if not self.tree.data:
            return

        ids = self.tree.GetSelections()
        objs = []
        for item in ids:
            if item == self.tree.GetRootItem():
                continue
            if not item.IsOk():
                break
            path = self.GetItemPath(item)
            if len(path) == 1:
                data = self.tree.data[path[0]]
            else:
                data = self.tree.data[path[0]].loc[:, ['timestamp', path[1]]]
                data['timestamp'] /= 1e6
            objs.append([path[0], data.to_json()])
        # need to explicitly allow drag
        # start drag operation
        data = wx.TextDataObject(json.dumps(objs))
        source = wx.DropSource(self.tree)
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

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        if eid == self.ID_ULOG_OPEN:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "ulog files (*.ulg;*.ulog)|*.ulg;*.ulog|All files (*.*)|*.*"
            dlg = wx.FileDialog(self, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                self.Load(filename=filename)
                (_, title) = os.path.split(filename)
                dp.send('frame.set_panel_title', pane=self, title=title)
            dlg.Destroy()

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()


class ULog:
    frame = None
    ID_ULOG_NEW = wx.NOT_FOUND
    ID_PANE_COPY_PATH = wx.NewIdRef()
    ID_PANE_COPY_PATH_REL = wx.NewIdRef()
    ID_PANE_SHOW_IN_FINDER = wx.NewIdRef()
    ID_PANE_SHOW_IN_BROWSING = wx.NewIdRef()
    ID_PANE_CLOSE = wx.NewIdRef()
    ID_PANE_CLOSE_OTHERS = wx.NewIdRef()
    ID_PANE_CLOSE_ALL = wx.NewIdRef()


    @classmethod
    def initialize(cls, frame):
        if cls.frame is not None:
            # already initialized
            return
        cls.frame = frame

        resp = dp.send(signal='frame.add_menu',
                       path='File:Open:ulog',
                       rxsignal='bsm.ulog')
        if resp:
            cls.ID_ULOG_NEW = resp[0][1]

        dp.connect(cls._process_command, signal='bsm.ulog')
        dp.connect(receiver=cls._frame_set_active,
                   signal='frame.activate_panel')
        dp.connect(receiver=cls._frame_uninitialize, signal='frame.exiting')
        dp.connect(receiver=cls._initialized, signal='frame.initialized')
        dp.connect(receiver=cls.open, signal='frame.file_drop')
        dp.connect(cls.PaneMenu, 'bsm.ulog.pane_menu')

    @classmethod
    def _initialized(cls):
        # add ulog to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.ulog import ULog as ulog',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def _frame_set_active(cls, pane):
        if pane and isinstance(pane, ULogPanel):
            if ULogPanel.Gcu.get_active() == pane:
                return
            ULogPanel.Gcu.set_active(pane)

    @classmethod
    def _frame_uninitialize(cls):
        for mgr in ULogPanel.Gcu.get_all_managers():
            dp.send('frame.delete_panel', panel=mgr)

        dp.send('frame.delete_menu', path="View:ulog")
        dp.send('frame.delete_menu',
                path="File:New:ulog",
                id=cls.ID_ULOG_NEW)

    @classmethod
    def _process_command(cls, command):
        if command == cls.ID_ULOG_NEW:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "ulog files (*.ulg;*.ulog)|*.ulg;*.ulog|All files (*.*)|*.*"
            dlg = wx.FileDialog(cls.frame, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                cls.open(filename=filename)
            dlg.Destroy()

    @classmethod
    def open(cls,
            filename=None,
            num=None,
            activate=False):
        """
        open an ulog file

        If the ulog has already been opened, return its handler; otherwise, create it.
        """
        if filename is not None:
            _, ext = os.path.splitext(filename)
            if not (ext.lower() in ['.ulog', '.ulg']):
                return None

        manager = cls._get_manager(num, filename)
        if manager is None:
            manager = ULogPanel(cls.frame, filename)
            (_, filename) = os.path.split(filename)
            title = filename
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target="History",
                    pane_menu={'rxsignal': 'bsm.ulog.pane_menu',
                           'menu': [
                               {'id':cls.ID_PANE_CLOSE, 'label':'Close\tCtrl+W'},
                               {'id':cls.ID_PANE_CLOSE_OTHERS, 'label':'Close Others'},
                               {'id':cls.ID_PANE_CLOSE_ALL, 'label':'Close All'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id':cls.ID_PANE_COPY_PATH, 'label':'Copy Path\tAlt+Ctrl+C'},
                               {'id':cls.ID_PANE_COPY_PATH_REL, 'label':'Copy Relative Path\tAlt+Shift+Ctrl+C'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id': cls.ID_PANE_SHOW_IN_FINDER, 'label':f'Reveal in  {get_file_finder_name()}\tAlt+Ctrl+R'},
                               {'id': cls.ID_PANE_SHOW_IN_BROWSING, 'label':'Reveal in Browsing panel'},
                               ]} )
            return manager
        # activate the manager
        elif manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)
        return manager

    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, ULogPanel):
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
            mgrs =  ULogPanel.Gcu.get_all_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  ULogPanel.Gcu.get_all_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def _get_manager(cls, num=None, filename=None):
        manager = None
        if num is not None:
            manager = ULogPanel.Gcu.get_manager(num)
        if manager is None and isinstance(filename, str):
            abs_filename = os.path.abspath(filename)
            for m in ULogPanel.Gcu.get_all_managers():
                if abs_filename == os.path.abspath(m.filename):
                    manager = m
                    break
        return manager

    @classmethod
    def _load_ulog(cls, ulg):
        if not isinstance(ulg, pyulog.ULog):
            return None
        data = {}
        for d in ulg.data_list:
            df = pd.DataFrame(d.data)
            data[d.name] = df
        t = [m.timestamp for m in ulg.logged_messages]
        m = [m.message for m in ulg.logged_messages]
        l = [m.log_level_str() for m in ulg.logged_messages]
        log = pd.DataFrame.from_dict({'timestamp': t, 'level': l, "message": m})
        info = ulg.msg_info_dict
        param = ulg.initial_parameters
        changed_param = ulg.changed_parameters
        return {'data': data, 'log': log, 'info': info, 'param': param,
                'changed_param': changed_param}

    @classmethod
    def get(cls, num=None, filename=None, dataOnly=True):
        manager = cls._get_manager(num, filename)
        if num is None and filename is None and manager is None:
            manager = ULogPanel.Gcu.get_active()
        ulg = None
        if manager:
            ulg = manager.ulg
        elif filename:
            try:
                ulg = pyulog.ULog(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        if ulg:
            data = cls._load_ulog(ulg)
            if dataOnly and data:
                return data.get('data', None)
            return data
        return None

def bsm_initialize(frame, **kwargs):
    ULog.initialize(frame)
