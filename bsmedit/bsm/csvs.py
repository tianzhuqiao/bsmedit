import sys
import os
import json
import traceback
from csv import Sniffer
import wx
import wx.py.dispatcher as dp
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from ..aui import aui
from . import graph
from .bsmxpm import open_svg
from .pymgr_helpers import Gcm
from .utility import svg_to_bitmap, get_variable_name
from .utility import get_file_finder_name, show_file_in_finder, build_tree
from .autocomplete import AutocompleteTextCtrl
from .treectrlbase import TreeCtrlBase

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
    return build_tree(csv)

class CsvTree(TreeCtrlBase):
    ID_CSV_SET_X = wx.NewIdRef()
    ID_CSV_EXPORT = wx.NewIdRef()
    ID_CSV_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()

    def __init__(self, *args, **kwargs):
        TreeCtrlBase.__init__(self, *args, **kwargs)
        self.x_path = None

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

    def GetItemPlotData(self, item):
        y = self.GetItemData(item)

        if not is_numeric_dtype(y):
            text = self.GetItemText(item)
            print(f"{text} is not numeric, ignore plotting!")
            return None, None

        if self.x_path is not None:
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
        text = self.GetItemText(item)
        path = self.GetItemPath(item)
        value = self.GetItemData(item)
        menu = wx.Menu()
        if self.x_path and self.x_path == path:
            mitem = menu.AppendCheckItem(self.ID_CSV_SET_X, "&Unset as x-axis data")
            mitem.Check(True)
            menu.AppendSeparator()
        elif is_numeric_dtype(value):
            menu.AppendCheckItem(self.ID_CSV_SET_X, "&Set as x-axis data")
            menu.AppendSeparator()

        menu.Append(self.ID_CSV_EXPORT, "&Export to shell")
        if self.x_path and self.x_path != path:
            menu.Append(self.ID_CSV_EXPORT_WITH_TIMESTAMP, "E&xport to shell with x")

        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
        path = self.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_CSV_EXPORT, self.ID_CSV_EXPORT_WITH_TIMESTAMP]:
            name = get_variable_name(text)
            x, y = self.GetItemPlotData(item)
            if cmd == self.ID_CSV_EXPORT_WITH_TIMESTAMP:
                data = pd.concat((x, y), axis=1)
            else:
                data = y
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

class CsvPanel(wx.Panel):
    Gcc = Gcm()
    ID_CSV_OPEN = wx.NewIdRef()

    def __init__(self, parent, filename=None):
        wx.Panel.__init__(self, parent)

        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        open_bmp = wx.Bitmap(svg_to_bitmap(open_svg, win=self))
        self.tb.AddTool(self.ID_CSV_OPEN, "Open", open_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Open csv file")

        self.tb.Realize()

        self.notebook = aui.AuiNotebook(self, agwStyle=aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS | wx.NO_BORDER)

        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(CsvTree)
        self.notebook.AddPage(panel, 'Data')

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.notebook, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)
        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)

        # load the csv
        self.csv = None
        if filename is not None:
            self.Load(filename)

        self.num = self.Gcc.get_next_num()
        self.Gcc.set_active(self)

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
        """load the csv file"""
        u = read_csv(filename)
        self.csv = u
        self.filename = filename
        self.tree.Load(u)
        dp.send('frame.add_file_history', filename=filename)

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

    def OnProcessCommand(self, event):
        """process the menu command"""
        eid = event.GetId()
        if eid == self.ID_CSV_OPEN:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "csv files (*.csv)|*.csv|All files (*.*)|*.*"
            dlg = wx.FileDialog(self, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                self.Load(filename=filename)
                (_, title) = os.path.split(filename)
                dp.send('frame.set_panel_title', pane=self, title=title)
            dlg.Destroy()

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()


class CSV:
    frame = None
    ID_CSV_NEW = wx.NOT_FOUND
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
                       path='File:Open:CSV file',
                       rxsignal='bsm.csv')
        if resp:
            cls.ID_CSV_NEW = resp[0][1]

        dp.connect(cls._process_command, signal='bsm.csv')
        dp.connect(receiver=cls._frame_set_active,
                   signal='frame.activate_panel')
        dp.connect(receiver=cls._frame_uninitialize, signal='frame.exiting')
        dp.connect(receiver=cls._initialized, signal='frame.initialized')
        dp.connect(receiver=cls.open, signal='frame.file_drop')
        dp.connect(cls.PaneMenu, 'bsm.csv.pane_menu')

    @classmethod
    def _initialized(cls):
        # add csv to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.csvs import CSV',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def _frame_set_active(cls, pane):
        if pane and isinstance(pane, CsvPanel):
            if CsvPanel.Gcc.get_active() == pane:
                return
            CsvPanel.Gcc.set_active(pane)

    @classmethod
    def _frame_uninitialize(cls):
        for mgr in CsvPanel.Gcc.get_all_managers():
            dp.send('frame.delete_panel', panel=mgr)

        dp.send('frame.delete_menu', path="File:Open:csv", id=cls.ID_CSV_NEW)

    @classmethod
    def _process_command(cls, command):
        if command == cls.ID_CSV_NEW:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "csv files (*.csv)|*.csv|All files (*.*)|*.*"
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
        open an csv file

        If the csv has already been opened, return its handler; otherwise, create one.
        """
        if filename is not None:
            _, ext = os.path.splitext(filename)
            if not (ext.lower() in ['.csv']):
                return None

        manager = cls._get_manager(num, filename)
        if manager is None:
            manager = CsvPanel(cls.frame, filename)
            (_, filename) = os.path.split(filename)
            title = filename
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target="History",
                    pane_menu={'rxsignal': 'bsm.csv.pane_menu',
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
        if manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)
        return manager

    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, CsvPanel):
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
            mgrs =  CsvPanel.Gcc.get_all_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  CsvPanel.Gcc.get_all_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def _get_manager(cls, num=None, filename=None):
        manager = None
        if num is not None:
            manager = CsvPanel.Gcc.get_manager(num)
        if manager is None and isinstance(filename, str):
            abs_filename = os.path.abspath(filename)
            for m in CsvPanel.Gcc.get_all_managers():
                if abs_filename == os.path.abspath(m.filename):
                    manager = m
                    break
        return manager

    @classmethod
    def get(cls, num=None, filename=None):
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
