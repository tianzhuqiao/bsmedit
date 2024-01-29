import os
import sys
import json
import traceback
from csv import Sniffer
import wx
import wx.py.dispatcher as dp
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from .pymgr_helpers import Gcm
from .utility import get_variable_name
from .utility import build_tree
from .fileviewbase import TreeCtrlBase, PanelNotebookBase, FileViewBase

def read_csv(filename):
    sep = ','
    with open(filename, encoding='utf-8') as fp:
        line = fp.readline()
        s = Sniffer()
        d = s.sniff(line)
        sep = d.delimiter
    csv = pd.read_csv(filename, sep=sep)
    d = {}
    for c in csv:
        d[c] = csv[c]
    return build_tree(build_tree(csv), '->')

class CsvTree(TreeCtrlBase):
    ID_CSV_SET_X = wx.NewIdRef()
    ID_CSV_EXPORT = wx.NewIdRef()
    ID_CSV_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()

    def __init__(self, *args, **kwargs):
        TreeCtrlBase.__init__(self, *args, **kwargs)
        self.x_path = None

    def GetItemPlotData(self, item):
        y = self.GetItemData(item)

        if not is_numeric_dtype(y):
            text = self.GetItemText(item)
            print(f"{text} is not numeric, ignore plotting!")
            return None, None

        if self.x_path is not None and self.GetItemPath(item) != self.x_path:
            x = self.GetItemDataFromPath(self.x_path)
        else:
            x = np.arange(0, len(y))
        return x, y

    def GetItemDragData(self, item):
        pass

    def OnTreeBeginDrag(self, event):
        if self.data.empty:
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
                mitem = menu.AppendCheckItem(self.ID_CSV_SET_X, "&Unset as x-axis data")
                mitem.Check(True)
                menu.AppendSeparator()
            elif is_numeric_dtype(value):
                menu.AppendCheckItem(self.ID_CSV_SET_X, "&Set as x-axis data")
                menu.AppendSeparator()

        menu.Append(self.ID_CSV_EXPORT, "&Export to shell")
        if self.x_path and (self.x_path != path or len(selections) > 1):
            menu.Append(self.ID_CSV_EXPORT_WITH_TIMESTAMP, "E&xport to shell with x")

        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
        path = self.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_CSV_EXPORT, self.ID_CSV_EXPORT_WITH_TIMESTAMP]:
            if len(selections) <= 1:
                name = get_variable_name(path)
            else:
                name = "_csv"
            x, y = self.GetItemPlotData(item)
            if cmd == self.ID_CSV_EXPORT_WITH_TIMESTAMP:
                data = x.to_frame()
            else:
                data = pd.DataFrame()
            for sel in selections:
                x, y = self.GetItemPlotData(sel)
                data[y.name] = y

            data.to_pickle('_csv.pickle')
            dp.send(signal='shell.run',
                command=f'{name}=pd.read_pickle("_csv.pickle")',
                prompt=False,
                verbose=False,
                history=False)
            dp.send('shell.run',
                    command=f'{name}',
                    prompt=True,
                    verbose=True,
                    history=False)
        elif cmd == self.ID_CSV_SET_X:
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

class CsvPanel(PanelNotebookBase):
    Gcc = Gcm()

    def __init__(self, parent, filename=None):
        PanelNotebookBase.__init__(self, parent, filename=filename)

        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.num = self.Gcc.get_next_num()
        self.Gcc.set_active(self)

    def init_pages(self):
        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(CsvTree)
        self.notebook.AddPage(panel, 'Data')

        # load the csv
        self.csv = None

    def Load(self, filename, add_to_history=True):
        """load the csv file"""
        u = read_csv(filename)
        self.csv = u
        self.filename = filename
        self.tree.Load(u)
        super().Load(filename, add_to_history=add_to_history)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.FillTree(pattern)
        item = self.tree.FindItemFromPath(self.tree.x_path)
        if item:
            self.tree.SetItemBold(item, True)
        self.search.SetFocus()

    def Destroy(self):
        """
        Destroy the csv properly before close the pane.
        """
        self.Gcc.destroy(self.num)
        super().Destroy()

    @classmethod
    def GetFileType(cls):
        return "csv files (*.csv)|*.csv|All files (*.*)|*.*"

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

class CSV(FileViewBase):
    name = 'csv'
    panel_type = CsvPanel

    @classmethod
    def check_filename(cls, filename):
        if filename is None:
            return True

        _, ext = os.path.splitext(filename)
        return (ext.lower() in ['.csv'])

    @classmethod
    def initialized(cls):
        # add csv to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.csvs import CSV',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def get(cls, num=None, filename=None, data_only=True):
        manager = cls._get_manager(num, filename)
        if num is None and filename is None and manager is None:
            manager = CsvPanel.Gcc.get_active()
        csv = None
        if manager:
            csv = manager.csv
        elif filename:
            try:
                csv = read_csv(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        return csv

def bsm_initialize(frame, **kwargs):
    CSV.initialize(frame)
