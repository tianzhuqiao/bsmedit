import os
import sys
import json
import traceback
import wx
import wx.py.dispatcher as dp
from scipy import io
import numpy as np
import pandas as pd
from .pymgr_helpers import Gcm
from .utility import get_variable_name, send_data_to_shell
from .fileviewbase import TreeCtrlBase, ListCtrlBase, PanelNotebookBase, FileViewBase

def process_record(d):
    if d.dtype.names is None:
        if len(d) == 1 and d.dtype.name == 'object':
            return process_record(d[0])
        return d
    data = {}
    for name in d.dtype.names:
        data[name] = process_record(d[name])
    return data

def load_mat(filename):
    data = {'info': {}, 'data': {}}
    raw = io.loadmat(filename)
    data['info']['version'] = raw['__version__']
    data['info']['header'] = raw['__header__']
    data['info']['globals'] = raw['__globals__']

    # data
    keys = [k for k in raw if not k.startswith('__')]
    for k in keys:
        data['data'][k] = process_record(raw[k])

    return data

class MatTree(TreeCtrlBase):
    ID_SET_X = wx.NewIdRef()
    ID_EXPORT = wx.NewIdRef()
    ID_EXPORT_WITH_X = wx.NewIdRef()
    ID_PLOT = wx.NewIdRef()

    def __init__(self, *args, **kwargs):
        TreeCtrlBase.__init__(self, *args, **kwargs)
        self.x_path = None

    def Load(self, data):
        self.x_path = None
        super().Load(data)

    def GetItemPlotData(self, item):
        y = self.GetItemData(item)

        x = None
        if self.x_path is not None and self.GetItemPath(item) != self.x_path:
            x = self.GetItemDataFromPath(self.x_path)
            if len(x) != len(y):
                name = self.GetItemText(item)
                print(f"'{name}' and '{self.x_path[-1]}' have different length, ignore x-axis data!")
                x = None
        if x is None:
            x = np.arange(0, len(y))
        return x, y

    def GetItemDragData(self, item):
        pass

    def OnTreeBeginDrag(self, event):
        if not self.data:
            return

        ids = self.GetSelections()
        objs = []
        df = pd.DataFrame()

        for item in ids:
            if item == self.GetRootItem() or self.ItemHasChildren(item):
                continue
            if not item.IsOk():
                break
            path = self.GetItemPath(item)
            if path == self.x_path:
                # ignore x-axis data
                continue
            df[path[-1]] = self.GetItemData(item)

        if df.empty:
            return

        x = np.arange(0, len(df))
        if self.x_path:
            x = self.GetItemDataFromPath(self.x_path)
        df.insert(loc=0, column='_x',  value=x)

        objs.append(['', df.to_json()])
        # need to explicitly allow drag
        # start drag operation
        data = wx.TextDataObject(json.dumps(objs))
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
        item = event.GetItem()
        if not item.IsOk():
            return
        if self.ItemHasChildren(item):
            return
        selections = self.GetSelections()
        if not selections:
            selections = [item]
        path = self.GetItemPath(item)
        value = self.GetItemData(item)
        menu = wx.Menu()
        if len(selections) <= 1:
            # single item selection
            if self.x_path and self.x_path == path:
                mitem = menu.AppendCheckItem(self.ID_SET_X, "Unset as x-axis data")
                mitem.Check(True)
                menu.AppendSeparator()
            else:
                menu.AppendCheckItem(self.ID_SET_X, "Set as x-axis data")
                menu.AppendSeparator()

        menu.Append(self.ID_EXPORT, "Export to shell")
        if self.x_path and (self.x_path != path or len(selections) > 1):
            menu.Append(self.ID_EXPORT_WITH_X, "Export to shell with x-axis data")

        menu.AppendSeparator()
        menu.Append(self.ID_PLOT, "Plot")

        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
        path = self.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_EXPORT, self.ID_EXPORT_WITH_X]:
            if len(selections) <= 1:
                name = get_variable_name(path)
            else:
                name = "_mat"
            x, y = self.GetItemPlotData(item)
            data = []
            if cmd == self.ID_EXPORT_WITH_X:
                data.append(['x', x])
            for sel in selections:
                y = self.GetItemData(sel)
                name = self.GetItemText(sel)
                data.append([name, y])
            data_size = [len(d[1]) for d in data]
            data_1d = [len(d[1].shape) <= 1 or sorted(d[1].shape)[-2] == 1  for d in data]
            if all(data_1d) and all(d == data_size[0] for d in data_size):
                df = pd.DataFrame()
                for name, val in data:
                    df[name] = val.flatten()
                data = df
            send_data_to_shell(name, data)
        elif cmd == self.ID_SET_X:
            if self.x_path:
                # clear the current x-axis data
                xitem = self.FindItemFromPath(self.x_path)
                if xitem is not None:
                    self.SetItemBold(xitem, False)
            if self.x_path != path:
                # select the new data as x-axis
                self.x_path = path
                self.SetItemBold(item, True)
            else:
                # clear the current x-axis
                self.x_path = None
        elif cmd in [self.ID_PLOT]:
            self.PlotItem(item)

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


class MatPanel(PanelNotebookBase):
    Gcc = Gcm()

    def __init__(self, parent, filename=None):
        PanelNotebookBase.__init__(self, parent, filename=filename)

        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.num = self.Gcc.get_next_num()
        self.Gcc.set_active(self)

    def init_pages(self):
        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(MatTree)
        self.notebook.AddPage(panel, 'Data')

        # info page
        self.infoList = InfoListCtrl(self.notebook)
        self.notebook.AddPage(self.infoList, 'Info')

        # load the mat
        self.mat = None

    def Load(self, filename, add_to_history=True):
        """load the mat file"""
        u = load_mat(filename)
        self.mat = u
        self.filename = filename
        self.tree.Load(u['data'])
        self.infoList.Load(u['info'])
        super().Load(filename, add_to_history=add_to_history)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.Fill(pattern)
        item = self.tree.FindItemFromPath(self.tree.x_path)
        if item:
            self.tree.SetItemBold(item, True)
        self.search.SetFocus()

    def Destroy(self):
        """
        Destroy the mat properly before close the pane.
        """
        self.Gcc.destroy(self.num)
        super().Destroy()

    @classmethod
    def GetFileType(cls):
        return "mat files (*.mat)|*.mat|All files (*.*)|*.*"

    @classmethod
    def get_all_managers(cls):
        return cls.Gcc.get_all_managers()

    @classmethod
    def get_active(cls):
        return cls.Gcc.get_active()

    @classmethod
    def set_active(cls, panel):
        cls.Gcc.set_active(panel)

    @classmethod
    def get_manager(cls, num):
        return cls.Gcc.get_manager(num)

class Mat(FileViewBase):
    name = 'mat'
    panel_type = MatPanel

    @classmethod
    def check_filename(cls, filename):
        if filename is None:
            return True

        _, ext = os.path.splitext(filename)
        return (ext.lower() in ['.mat'])

    @classmethod
    def initialized(cls):
        # add mat to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.mat import Mat',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def get(cls, num=None, filename=None, data_only=True):
        manager = super().get(num, filename, data_only)
        mat = None
        if manager:
            mat = manager.mat
        elif filename:
            try:
                mat = load_mat(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        return mat

def bsm_initialize(frame, **kwargs):
    Mat.initialize(frame)
