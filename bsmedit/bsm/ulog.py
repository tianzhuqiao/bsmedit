import sys
import os
import traceback
import wx
import wx.py.dispatcher as dp
import pyulog
import pandas as pd
from .pymgr_helpers import Gcm
from .utility import get_variable_name
from .fileviewbase import ListCtrlBase, TreeCtrlBase, PanelNotebookBase, FileViewBase

def load_ulog(filename):
    try:
        ulg = pyulog.ULog(filename)
    except:
        traceback.print_exc(file=sys.stdout)
        return {}

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

class ULogTree(TreeCtrlBase):
    ID_ULOG_EXPORT = wx.NewIdRef()
    ID_ULOG_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()

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

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        self.UnselectAll()
        has_child = self.ItemHasChildren(item)
        menu = wx.Menu()
        menu.Append(self.ID_ULOG_EXPORT, "&Export to shell")
        if not has_child:
            menu.Append(self.ID_ULOG_EXPORT_WITH_TIMESTAMP, "E&xport to shell with timestamp")

        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
        path = self.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_ULOG_EXPORT, self.ID_ULOG_EXPORT_WITH_TIMESTAMP]:
            name = get_variable_name(path)
            command = f'{name}=ulog.get()["{path[0]}"]'
            if len(path) > 1:
                if cmd == self.ID_ULOG_EXPORT_WITH_TIMESTAMP:
                    command += f'.get(["timestamp", "{path[1]}"])'
                else:
                    command += f'.get(["{path[1]}"])'
            dp.send(signal='shell.run',
                command=command,
                prompt=False,
                verbose=False,
                history=True)
            dp.send(signal='shell.run',
                command=f'{name}',
                prompt=True,
                verbose=True,
                history=False)

    def GetItemPlotData(self, item):
        if self.ItemHasChildren(item):
            return None, None
        parent = self.GetItemParent(item)
        if not parent.IsOk():
            return None, None
        datasetname = self.GetItemText(parent)
        dataset = self.data[datasetname]
        dataname = self.GetItemText(item)
        x = dataset['timestamp']/1e6
        y = dataset[dataname]
        return x, y

    def GetItemDragData(self, item):
        path = self.GetItemPath(item)
        if len(path) == 1:
            data = self.data[path[0]]
        else:
            data = self.data[path[0]].loc[:, ['timestamp', path[1]]]
            data['timestamp'] /= 1e6
        return data

    def GetPlotXLabel(self):
        return "t(s)"

class MessageListCtrl(ListCtrlBase):

    def BuildColumns(self):
        super().BuildColumns()
        start = self.data_start_column
        self.InsertColumn(start, "Timestamp", width=120)
        self.InsertColumn(start+1, "Type", width=120)
        self.InsertColumn(start+2, "Message", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.data_shown.iloc[i].message
            if self.Search(m, text, flags):
                return i

        # not found
        return -1

    def ApplyPattern(self):
        if not self.pattern:
            self.data_shown = self.data
        else:
            self.data_shown = self.data.loc[self.data.level.str.contains(self.pattern, case=False) | self.data.message.str.contains(self.pattern, case=False)]

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        m = self.data_shown.iloc[item]
        if column == 0:
            return str(m.timestamp/1e6)
        if column == 1:
            return m.level
        if column == 2:
            return m.message
        return ""

class InfoListCtrl(ListCtrlBase):

    def BuildColumns(self):
        super().BuildColumns()
        start = self.data_start_column
        self.InsertColumn(start, "Key", width=120)
        self.InsertColumn(start+1, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.data_shown[i]
            if self.Search(m[0], text, flags) or self.Search(str(m[1]), text, flags):
                return i

        # not found
        return -1

    def Load(self, data):
        data = [[k, v] for k, v in data.items()]
        data = sorted(data, key=lambda x: x[0])
        super().Load(data)

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        return str(self.data_shown[item][column])

class ParamListCtrl(ListCtrlBase):

    def BuildColumns(self):
        super().BuildColumns()
        start = self.data_start_column
        self.InsertColumn(start, "Key", width=200)
        self.InsertColumn(start+1, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.data_shown[i]
            if self.Search(str(m[0]), text, flags) or self.Search(str(m[1]), text, flags):
                return i

        # not found
        return -1

    def ApplyPattern(self):
        if self.pattern:
            self.data_shown = [[k, v] for k, v in self.data.items() if self.pattern in str(k).lower() or self.pattern.lower() in str(v).lower()]
        else:
            self.data_shown = [[k, v] for k, v in self.data.items()]

        self.data_shown = sorted(self.data_shown, key=lambda x: x[0])

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        return str(self.data_shown[item][column])

class ChgParamListCtrl(ListCtrlBase):

    def BuildColumns(self):
        super().BuildColumns()
        start = self.data_start_column
        self.InsertColumn(start, "Timestamp", width=120)
        self.InsertColumn(start+1, "Key", width=200)
        self.InsertColumn(start+2, "Value", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.data_shown[i]
            if self.Search(str(m[1]), text, flags) or self.Search(str(m[2]), text, flags):
                return i

        # not found
        return -1

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        m = self.data_shown[item]
        if column == 0:
            return str(m[0]/1e6)
        return str(m[column])


class ULogPanel(PanelNotebookBase):
    Gcu = Gcm()

    def __init__(self, parent, filename=None):
        self.ulg = None
        PanelNotebookBase.__init__(self, parent, filename=filename)

        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchLog, self.search_log)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchParam, self.search_param)

        self.num = self.Gcu.get_next_num()
        self.Gcu.set_active(self)

    def init_pages(self):
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

        self.ulg = None

    def Load(self, filename, add_to_history=True):
        """load the ulog file"""
        u = load_ulog(filename)
        self.ulg = u
        self.filename = filename
        self.tree.Load(u['data'])
        self.logList.Load(u['log'])
        self.infoList.Load(u['info'])
        self.paramList.Load(u['param'])
        self.chgParamList.Load(u['changed_param'])
        super().Load(filename, add_to_history=add_to_history)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.Fill(pattern)
        self.search.SetFocus()

    def OnDoSearchLog(self, evt):
        pattern = self.search_log.GetValue()
        self.logList.Fill(pattern)

    def OnDoSearchParam(self, evt):
        pattern = self.search_param.GetValue()
        self.paramList.Fill(pattern)

    def Destroy(self):
        """
        Destroy the ulog properly before close the pane.
        """
        self.Gcu.destroy(self.num)
        super().Destroy()

    @classmethod
    def GetFileType(cls):
        return "ulog files (*.ulg;*.ulog)|*.ulg;*.ulog|All files (*.*)|*.*"

    @classmethod
    def get_all_managers(cls):
        return cls.Gcu.get_all_managers()

    @classmethod
    def get_active(cls):
        return cls.Gcu.get_active()

    @classmethod
    def set_active(cls, panel):
        cls.Gcu.set_active(panel)

    @classmethod
    def get_manager(cls, num):
        return cls.Gcu.get_manager(num)

class ULog(FileViewBase):
    name = 'ulog'
    panel_type = ULogPanel

    @classmethod
    def check_filename(cls, filename):
        if filename is None:
            return True

        _, ext = os.path.splitext(filename)
        return (ext.lower() in ['.ulog', '.ulg'])

    @classmethod
    def initialized(cls):
        # add ulog to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.ulog import ULog as ulog',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def get(cls, num=None, filename=None, data_only=True):
        manager = super().get(num, filename, data_only)
        ulg = None
        if manager:
            ulg = manager.ulg
        elif filename:
            try:
                ulg = load_ulog(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        if ulg:
            data = ulg
            if data_only and data:
                return data.get('data', None)
            return data
        return None

def bsm_initialize(frame, **kwargs):
    ULog.initialize(frame)
