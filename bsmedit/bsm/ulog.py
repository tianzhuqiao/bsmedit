import os
import json
import traceback
import wx
import wx.py.dispatcher as dp
import pyulog
import pandas as pd
from ..aui import aui
from ..auibarpopup import AuiToolBarPopupArt
from . import graph
from .bsmxpm import open_xpm
from .pymgr_helpers import Gcm
from .utility import FastLoadTreeCtrl, PopupMenu, _dict
from .utility import svg_to_bitmap
from .. import to_byte
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
                    dataset.remove('dt')
                    dataset += [c]
                    if any(pattern in s for s in dataset):
                        temp.append(c)
                children = temp
        else:
            parent = self.GetItemText(item)
            if parent in self.data:
                children = list(self.data[parent].columns)
                children.remove('timestamp')
                children.remove('dt')
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

    def Load(self, filename):
        """load the ulog file"""
        u = pyulog.ULog(filename)
        data = _dict()
        for d in u.data_list:
            df = pd.DataFrame(d.data)
            df['dt'] = (df.timestamp - df.timestamp[0])/1e6 # to second
            data[d.name] = df
        self.data = data
        self.filename = filename
        self.FillTree()

        dp.send('frame.add_file_history', filename=filename)

    def FillTree(self, pattern=None):
        """fill the ulog objects tree"""
        #clear the tree control
        self.DeleteAllItems()
        if not self.data:
            return
        self.pattern = pattern
        # add the root item
        item = self.AddRoot("bsmedit")
        # fill the top level item
        self.FillChildren(item)

class ULogPanel(wx.Panel):
    Gcu = Gcm()
    ID_ULOG_OPEN = wx.NewId()
    ID_ULOG_EXPORT = wx.NewId()

    def __init__(self, parent, filename=None):
        wx.Panel.__init__(self, parent)

        self.toolbarart = AuiToolBarPopupArt(self)
        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        open_bmp = wx.Bitmap(to_byte(open_xpm))
        self.tb.AddTool(self.ID_ULOG_OPEN, "Open", open_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Open ulog file")

        self.tb.SetArtProvider(self.toolbarart)
        self.tb.Realize()
        self.tree = ULogTree(self)
        self.tb2 = aui.AuiToolBar(self)
        self.search = AutocompleteTextCtrl(self.tb2)
        self.search.SetHint('searching ...')
        item = self.tb2.AddControl(self.search)
        item.SetProportion(1)
        self.tb2.SetMargins(right=15)
        self.tb2.Realize()

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(self.tree, 1, wx.EXPAND)
        self.box.Add(self.tb2, 0, wx.EXPAND, 5)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnProcessCommand)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCmdUI)
        self.tree.Bind(wx.EVT_TREE_ITEM_MENU, self.OnTreeItemMenu)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated)
        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)

        # load the ulog
        if filename is not None:
            self.tree.Load(filename)

        self.num = self.Gcu.get_next_num()
        self.Gcu.set_active(self)

    def OnDoSearch(self, evt):
        #self.SaveConfig()
        pattern = self.search.GetValue()
        self.tree.FillTree(pattern)
        self.search.SetFocus()

    def Destroy(self):
        """
        Destroy the ulog properly before close the pane.
        """
        self.Gcu.destroy(self.num)
        super().Destroy()

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        menu = wx.Menu()
        menu.Append(self.ID_ULOG_EXPORT, "&Export to shell")
        cmd = PopupMenu(self, menu)
        text = self.tree.GetItemText(item)
        path = text
        if not self.tree.ItemHasChildren(item):
            parent = self.tree.GetItemParent(item)
            if parent.IsOk():
                path = f'{self.tree.GetItemText(parent)}.{path}'
        if cmd == self.ID_ULOG_EXPORT:
            dp.send(signal='shell.run',
                command=f'{text}=ulog.get().{path}',
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
        x = dataset['dt']
        y = dataset[dataname]

        # plot
        mgr = graph.plt.get_current_fig_manager()
        if not isinstance(mgr, graph.MatplotPanel) and hasattr(mgr, 'frame'):
            mgr = mgr.frame
        mgr.figure.gca().plot(x, y, label=f'{datasetname}.{dataname}')
        mgr.figure.gca().legend()
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
                self.tree.Load(filename=filename)
                (_, title) = os.path.split(filename)
                dp.send('frame.set_panel_title', pane=self, title=title)
            dlg.Destroy()

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()


class ULog:
    frame = None
    ID_ULOG_NEW = wx.NOT_FOUND

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
        manager = ULogPanel.Gcu.get_manager(num)
        if manager is None:
            manager = ULogPanel(cls.frame, filename)
            (_, filename) = os.path.split(filename)
            title = filename
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target="History")
            return manager
        # activate the manager
        elif manager and activate:
            dp.send(signal='frame.show_panel', panel=manager)

        return manager

    @classmethod
    def get(cls, num=None, filename=None):
        manager = None
        if num is not None:
            manager = ULogPanel.Gcu.get_manager(num)
        if manager is None:
            for m in ULogPanel.Gcu.get_all_managers():
                (_, name) = os.path.split(m.tree.filename)
                if filename in (m.tree.filename, name):
                    manager = m
                    break
        if num is None and filename is None:
            manager = ULogPanel.Gcu.get_active()
        return manager.tree.data

def bsm_initialize(frame, **kwargs):
    ULog.initialize(frame)
