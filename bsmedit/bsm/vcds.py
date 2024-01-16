import sys
import os
import json
import traceback
import wx
import wx.py.dispatcher as dp
import pandas as pd
from pandas.api.types import is_numeric_dtype
from vcd.reader import TokenKind, tokenize
from ..aui import aui
from . import graph
from .bsmxpm import open_svg
from .pymgr_helpers import Gcm
from .utility import FastLoadTreeCtrl, PopupMenu, _dict, svg_to_bitmap
from .utility import get_file_finder_name, show_file_in_finder
from .autocomplete import AutocompleteTextCtrl
from .listctrl_base import ListCtrlBase
from ..pvcd.pvcd import load_vcd as load_vcd2

def load_vcd3(filename):
    vcd = load_vcd2(filename)
    if not vcd or not vcd['data']:
        return vcd
    if list(vcd['data'].keys()) == ['SystemC']:
        vcd['data'] = vcd['data']['SystemC']
    for k in list(vcd['data'].keys()):
        signal = k.split('.')
        if len(signal) > 1:
            d = vcd['data']
            for i in range(len(signal)-1):
                if not signal[i] in d:
                    d[signal[i]] = {}
                d = d[signal[i]]
            d[signal[-1]] = vcd['data'].pop(k)
            d[signal[-1]].rename(columns={d[signal[-1]].columns[-1]: signal[-1]}, inplace=True)
    return vcd

def load_vcd(filename):
    vcd = {'info':{}, 'data':{}, 'var': {}, 'comment': []}
    with open(filename, 'rb') as fp:
        time_units = {'fs': 1e-15, 'ps': 1e-12, 'ns': 1e-9, 'us': 1e-6, 'ms': 1e-3, 's': 1}
        tokens = tokenize(fp)
        token = next(tokens)
        t = 0
        while True:
            try:
                token = next(tokens)
            except StopIteration:
                break
            except:
                traceback.print_exc(file=sys.stdout)
                break
            if token.kind in [TokenKind.CHANGE_VECTOR, TokenKind.CHANGE_REAL,
                                TokenKind.CHANGE_SCALAR, TokenKind.CHANGE_STRING]:
                if not token.data.id_code in vcd['data']:
                    vcd['data'][token.data.id_code] = []
                vcd['data'][token.data.id_code] += [[t, token.data.value]]

            elif token.kind == TokenKind.CHANGE_TIME:
                t = token.data
            elif token.kind in [TokenKind.DATE, TokenKind.VERSION]:
                vcd['info'][token.kind.name] = token.data.strip()
            elif token.kind == TokenKind.TIMESCALE:
                vcd['info'][token.kind.name] = f'{token.data.magnitude.value} {token.data.unit.value}'
                vcd['timescale'] = token.data.magnitude.value * time_units[token.data.unit.value]
            elif token.kind == TokenKind.SCOPE:
                vcd['info'][token.kind.name] = f'{token.data.ident} {token.data.type_}'
            elif token.kind == TokenKind.VAR:
                vcd['var'][token.data.id_code] = {'reference': token.data.reference,
                                                  'bit': token.data.bit_index,
                                                  'type': token.data.type_.value,
                                                  'size': token.data.size}
            elif token.kind == TokenKind.COMMENT:
                vcd['comment'].append(token.data)



        for k in list(vcd['data'].keys()):
            signal = k
            if k in vcd['var']:
                signal = vcd['var'][k].get('reference', None) or k
                if signal != k:
                    if signal in vcd['data']:
                        num = len([dk for dk in vcd['data'].keys() if dk == signal])
                        print(f'Found duplicated signal {signal}')
                        signal  = f"{signal}-{num}"
                    vcd['data'][signal] = vcd['data'].pop(k)

            vcd['data'][signal] = pd.DataFrame.from_records(vcd['data'][signal], columns=['timestamp', signal])

        for k in list(vcd['data'].keys()):
            signal = k.split('.')
            if len(signal) > 1:
                d = vcd['data']
                for i in range(len(signal)-1):
                    if not signal[i] in d:
                        d[signal[i]] = {}
                    d = d[signal[i]]
                d[signal[-1]] = vcd['data'].pop(k)
                d[signal[-1]].rename(columns={k: signal[-1]}, inplace=True)
    return vcd


class VcdTree(FastLoadTreeCtrl):
    """the tree control to show the hierarchy of the objects in the vcd"""
    def __init__(self, parent, style=wx.TR_DEFAULT_STYLE):
        style = style | wx.TR_HAS_VARIABLE_ROW_HEIGHT | wx.TR_HIDE_ROOT |\
                wx.TR_MULTIPLE | wx.TR_LINES_AT_ROOT
        FastLoadTreeCtrl.__init__(self, parent, self.get_children, style=style)

        self.data = _dict()
        self.filename = ""
        self.pattern = None
        self.expanded = {}

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

    def GetData(self, item):
        if self.ItemHasChildren(item):
            return None

        path = self.GetItemPath(item)
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

    def Load(self, vcd):
        """load the vcd file"""
        data = _dict(vcd['data'])
        self.data = data
        self.FillTree(self.pattern)

    def FillTree(self, pattern=None):
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

class CommentListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.vcd = None
        self.InsertColumn(0, "#", width=60)
        self.InsertColumn(1, "Comment", width=wx.LIST_AUTOSIZE_USEHEADER)
        self.comment = []
        self.pattern = None

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.comment[i]
            if self.Search(m, text, flags):
                return i

        # not found
        return -1

    def Load(self, vcd):
        self.vcd = vcd
        self.SetItemCount(0)
        if self.vcd is not None:
            self.FillComment(self.pattern)

    def FillComment(self, pattern):
        self.pattern = pattern
        if isinstance(self.pattern, str):
            self.pattern = self.pattern.lower()
            self.pattern.strip()
        if not self.pattern:
            self.comment = self.vcd['comment']
        else:
            self.comment = [m for m in self.vcd['comment'] if self.pattern in m.lower() or self.pattern]

        self.SetItemCount(len(self.comment))
        if self.GetItemCount() > 0:
            self.RefreshItems(0, len(self.comment)-1)

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        m = self.comment[item]
        if column == 0:
            return m
        return ""

class InfoListCtrl(ListCtrlBase):
    def __init__(self, parent):
        ListCtrlBase.__init__(self, parent)
        self.vcd = None
        self.info = []
        self.pattern = None
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

    def Load(self, vcd):
        self.vcd = vcd
        self.SetItemCount(0)
        if self.vcd is not None:
            self.FillInfo(self.pattern)

    def FillInfo(self, pattern):
        self.pattern = pattern
        if isinstance(self.pattern, str):
            self.pattern = self.pattern.lower()
            self.pattern.strip()
        if self.pattern:
            self.info = [[k, v] for k, v in self.vcd['info'].items() if self.pattern in str(k).lower() or self.pattern.lower() in str(v).lower()]
        else:
            self.info = [[k, v] for k, v in self.vcd['info'].items()]

        self.info = sorted(self.info, key=lambda x: x[0])
        self.SetItemCount(len(self.info))
        if self.GetItemCount() > 0:
            self.RefreshItems(0, len(self.info)-1)

    def OnGetItemText(self, item, column):
        if column == 0:
            return f"{item+1}"
        column -= 1
        return str(self.info[item][column])

class VcdPanel(wx.Panel):
    Gcv = Gcm()
    ID_VCD_OPEN = wx.NewIdRef()
    ID_VCD_EXPORT = wx.NewIdRef()
    ID_VCD_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()

    def __init__(self, parent, filename=None):
        wx.Panel.__init__(self, parent)

        self.tb = aui.AuiToolBar(self, -1, agwStyle=aui.AUI_TB_OVERFLOW)
        self.tb.SetToolBitmapSize(wx.Size(16, 16))

        open_bmp = wx.Bitmap(svg_to_bitmap(open_svg, win=self))
        self.tb.AddTool(self.ID_VCD_OPEN, "Open", open_bmp,
                        wx.NullBitmap, wx.ITEM_NORMAL,
                        "Open vcd file")

        self.tb.Realize()

        agwStyle=aui.AUI_NB_TOP | aui.AUI_NB_TAB_SPLIT | aui.AUI_NB_SCROLL_BUTTONS | wx.NO_BORDER
        self.notebook = aui.AuiNotebook(self, agwStyle=agwStyle)

        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(VcdTree)
        self.notebook.AddPage(panel, 'Data')
        # info page
        panel_info, self.search_info, self.infoList = self.CreatePageWithSearch(InfoListCtrl)
        self.notebook.AddPage(panel_info, 'Info')
        # comment page
        panel_comment, self.search_comment, self.commentList = self.CreatePageWithSearch(CommentListCtrl)
        self.notebook.AddPage(panel_comment, 'Comment')

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
        self.Bind(wx.EVT_TEXT, self.OnDoSearchInfo, self.search_info)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchComment, self.search_comment)

        # load the vcd
        self.vcd = None
        if filename is not None:
            self.Load(filename)

        self.num = self.Gcv.get_next_num()
        self.Gcv.set_active(self)

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
        """load the vcd file"""
        u = load_vcd3(filename)
        self.vcd = u
        self.filename = filename
        self.tree.Load(u)
        self.infoList.Load(u)
        self.commentList.Load(u)
        dp.send('frame.add_file_history', filename=filename)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.FillTree(pattern)
        self.search.SetFocus()

    def OnDoSearchInfo(self, evt):
        pattern = self.search_info.GetValue()
        self.infoList.FillM(pattern)

    def OnDoSearchComment(self, evt):
        pattern = self.search_param.GetValue()
        self.commentList.FillComment(pattern)

    def Destroy(self):
        """
        Destroy the vcdg properly before close the pane.
        """
        self.Gcv.destroy(self.num)
        super().Destroy()

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        has_child = self.tree.ItemHasChildren(item)
        menu = wx.Menu()
        menu.Append(self.ID_VCD_EXPORT, "&Export to shell")
        if not has_child:
            menu.Append(self.ID_VCD_EXPORT_WITH_TIMESTAMP, "E&xport to shell with timestamp")

        cmd = PopupMenu(self, menu)
        text = self.tree.GetItemText(item)
        path = self.tree.GetItemPath(item)
        if not path:
            return
        if cmd in [self.ID_VCD_EXPORT, self.ID_VCD_EXPORT_WITH_TIMESTAMP]:
            name = text.replace('[', '').replace(']', '')
            command = f'{name}=VCD.get()'
            for p in path:
                command += f'["{p}"]'
            if cmd == self.ID_VCD_EXPORT_WITH_TIMESTAMP:
                command += f'.get(["timestamp", "{path[-1]}"])'
            elif not has_child:
                command += f'.get(["{path[-1]}"])'
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
        path = self.tree.GetItemPath(item)
        dataset = self.tree.GetData(item)
        x = dataset['timestamp']*self.vcd.get('timescale', 1e-6)*1e6
        y = dataset[path[-1]]
        if not is_numeric_dtype(y):
            print(f"{path[-1]} is not numeric, ignore plotting!")
            return

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
        mgr.figure.gca().plot(x, y, label="/".join(path),
                              linestyle=ls, marker=ms)
        mgr.figure.gca().legend()
        mgr.figure.gca().grid(True)
        mgr.figure.gca().set_xlabel('t(us)')

    def OnTreeBeginDrag(self, event):
        if not self.tree.data:
            return

        ids = self.tree.GetSelections()
        objs = []
        for item in ids:
            if item == self.tree.GetRootItem() or self.tree.ItemHasChildren(item):
                continue
            if not item.IsOk():
                break
            path = self.tree.GetItemPath(item)
            data = self.tree.GetData(item)
            data['timestamp'] *= self.vcd.get('timescale', 1e-6) * 1e6
            objs.append(['/'.join(path[:-1]), data.to_json()])

        # need to explicitly allow drag
        # start drag operation
        data = wx.TextDataObject(json.dumps({'lines': objs, 'xlabel': 't(us)'}))
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
        if eid == self.ID_VCD_OPEN:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "vcd files (*.vcd)|*.vcd|All files (*.*)|*.*"
            dlg = wx.FileDialog(self, "Choose a file", "", "", wildcard, style)
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()
                self.Load(filename=filename)
                (_, title) = os.path.split(filename)
                dp.send('frame.set_panel_title', pane=self, title=title)
            dlg.Destroy()

    def OnUpdateCmdUI(self, event):
        eid = event.GetId()


class VCD:
    frame = None
    ID_VCD_NEW = wx.NOT_FOUND
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
                       path='File:Open:vcd',
                       rxsignal='bsm.vcd')
        if resp:
            cls.ID_VCD_NEW = resp[0][1]

        dp.connect(cls._process_command, signal='bsm.vcd')
        dp.connect(receiver=cls._frame_set_active,
                   signal='frame.activate_panel')
        dp.connect(receiver=cls._frame_uninitialize, signal='frame.exiting')
        dp.connect(receiver=cls._initialized, signal='frame.initialized')
        dp.connect(receiver=cls.open, signal='frame.file_drop')
        dp.connect(cls.PaneMenu, 'bsm.vcd.pane_menu')

    @classmethod
    def _initialized(cls):
        # add vcd to the shell
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.vcds import VCD as VCD',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def _frame_set_active(cls, pane):
        if pane and isinstance(pane, VcdPanel):
            if VcdPanel.Gcv.get_active() == pane:
                return
            VcdPanel.Gcv.set_active(pane)

    @classmethod
    def _frame_uninitialize(cls):
        for mgr in VcdPanel.Gcv.get_all_managers():
            dp.send('frame.delete_panel', panel=mgr)

        dp.send('frame.delete_menu', path="View:vcd")
        dp.send('frame.delete_menu',
                path="File:New:vcd",
                id=cls.ID_VCD_NEW)

    @classmethod
    def _process_command(cls, command):
        if command == cls.ID_VCD_NEW:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            wildcard = "vcd files (*.vcd)|*.vcd|All files (*.*)|*.*"
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
        open an vcd file

        If the vcd has already been opened, return its handler; otherwise, create it.
        """
        if filename is not None:
            _, ext = os.path.splitext(filename)
            if not (ext.lower() in ['.vcd', '.bsm']):
                return None

        manager = cls._get_manager(num, filename)
        if manager is None:
            manager = VcdPanel(cls.frame, filename)
            (_, filename) = os.path.split(filename)
            title = filename
            dp.send(signal="frame.add_panel",
                    panel=manager,
                    title=title,
                    target="History",
                    pane_menu={'rxsignal': 'bsm.vcd.pane_menu',
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
        if not pane or not isinstance(pane, VcdPanel):
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
            mgrs =  VcdPanel.Gcv.get_all_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  VcdPanel.Gcv.get_all_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def _get_manager(cls, num=None, filename=None):
        manager = None
        if num is not None:
            manager = VcdPanel.Gcv.get_manager(num)
        if manager is None and isinstance(filename, str):
            abs_filename = os.path.abspath(filename)
            for m in VcdPanel.Gcv.get_all_managers():
                if abs_filename == os.path.abspath(m.filename):
                    manager = m
                    break
        return manager

    @classmethod
    def get(cls, num=None, filename=None, dataOnly=True):
        manager = cls._get_manager(num, filename)
        if num is None and filename is None and manager is None:
            manager = VcdPanel.Gcv.get_active()
        vcd = None
        if manager:
            vcd = manager.vcd
        elif filename:
            try:
                vcd = load_vcd3(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        if vcd:
            if dataOnly:
                return vcd['data']
        return vcd

def bsm_initialize(frame, **kwargs):
    VCD.initialize(frame)