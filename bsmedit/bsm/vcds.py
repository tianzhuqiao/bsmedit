import os
import sys
import re
import traceback
import wx
import wx.py.dispatcher as dp
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_integer_dtype
from vcd.reader import TokenKind, tokenize
from .pymgr_helpers import Gcm
from .utility import _dict, get_variable_name, send_data_to_shell
from .utility import build_tree
from .fileviewbase import ListCtrlBase, TreeCtrlBase, PanelNotebookBase, FileViewBase
from ..pvcd.pvcd import load_vcd as load_vcd2

def load_vcd3(filename):
    vcd = load_vcd2(filename)
    if not vcd or not vcd['data']:
        return vcd
    if list(vcd['data'].keys()) == ['SystemC']:
        vcd['data'] = vcd['data']['SystemC']
    vcd['data'] = build_tree(vcd['data'])
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
                        num = len([dk for dk in vcd['data'] if dk == signal])
                        print(f'Found duplicated signal "{signal}"')
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


def GetDataBit(value, bit):
    if not is_integer_dtype(value) or bit < 0:
        return None
    return value.map(lambda x: (x >> bit) & 1)

class VcdTree(TreeCtrlBase):
    ID_VCD_EXPORT = wx.NewIdRef()
    ID_VCD_EXPORT_WITH_TIMESTAMP = wx.NewIdRef()
    ID_VCD_EXPORT_RAW = wx.NewIdRef()
    ID_VCD_EXPORT_RAW_WITH_TIMESTAMP = wx.NewIdRef()
    ID_VCD_EXPORT_BITS = wx.NewIdRef()
    ID_VCD_EXPORT_BITS_WITH_TIMESTAMP = wx.NewIdRef()
    ID_VCD_PLOT = wx.NewIdRef()
    ID_VCD_PLOT_BITS = wx.NewIdRef()
    ID_VCD_PLOT_BITS_VERT = wx.NewIdRef()
    ID_VCD_TO_PYINT = wx.NewIdRef()
    ID_VCD_TO_INT8 = wx.NewIdRef()
    ID_VCD_TO_UINT8 = wx.NewIdRef()
    ID_VCD_TO_INT16 = wx.NewIdRef()
    ID_VCD_TO_UINT16 = wx.NewIdRef()
    ID_VCD_TO_INT32 = wx.NewIdRef()
    ID_VCD_TO_UINT32 = wx.NewIdRef()
    ID_VCD_TO_INT64 = wx.NewIdRef()
    ID_VCD_TO_UINT64 = wx.NewIdRef()
    ID_VCD_TO_FLOAT16 = wx.NewIdRef()
    ID_VCD_TO_FLOAT32 = wx.NewIdRef()
    ID_VCD_TO_FLOAT64 = wx.NewIdRef()
    ID_VCD_TO_FLOAT128 = wx.NewIdRef()

    def Load(self, data):
        """load the vcd file"""
        vcd = _dict(data)
        super().Load(vcd)

    def GetItemPlotData(self, item):
        path = self.GetItemPath(item)
        dataset = self.GetItemData(item)
        x = dataset['timestamp']*self.data.get('timescale', 1e-6)*1e6
        y = dataset[path[-1]]
        return x, y

    def GetItemDragData(self, item):
        path = self.GetItemPath(item)
        data = self.GetItemData(item)
        data = data.get(['timestamp', path[-1]]).copy()
        data.timestamp *= self.data.get('timescale', 1e-6) * 1e6
        return data

    def GetDataBits(self, value):
        if not is_integer_dtype(value):
            print(f"Can't retrieve bits from non-integer value")
            return None
        message = 'Type the index of bit to retrieve, separate by ",", e.g., "0,1,2"'
        dlg = wx.TextEntryDialog(self, message, value='')
        if dlg.ShowModal() == wx.ID_OK:
            idx = dlg.GetValue()
            idx = sorted([int(i) for i in re.findall(r'\d+', idx)])
            df = pd.DataFrame()
            for i in idx:
                df[f'bit{i}'] = GetDataBit(value, i)
            return df
        return None

    def OnTreeItemMenu(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        self.UnselectAll()
        path = self.GetItemPath(item)
        data = self.GetItemData(item)
        if data is None:
            return
        value = data[path[-1]]
        if len(value) == 0:
            return

        menu = wx.Menu()
        menu.Append(self.ID_VCD_EXPORT, "&Export to shell")
        menu.Append(self.ID_VCD_EXPORT_WITH_TIMESTAMP, "E&xport to shell with timestamp")
        export_menu = wx.Menu()
        export_menu.Append(self.ID_VCD_EXPORT_RAW, "Export raw value to shell")
        export_menu.Append(self.ID_VCD_EXPORT_RAW_WITH_TIMESTAMP, "Export raw value to shell with timestamp")
        if is_integer_dtype(value):
            export_menu.AppendSeparator()
            export_menu.Append(self.ID_VCD_EXPORT_BITS, "Export selected bits to shell")
            export_menu.Append(self.ID_VCD_EXPORT_BITS_WITH_TIMESTAMP, "Export selected bits to shell with timestamp")
        menu.AppendSubMenu(export_menu, 'More ...')
        if is_numeric_dtype(value):
            menu.AppendSeparator()
            menu.Append(self.ID_VCD_PLOT, "Plot")
            if is_integer_dtype(value):
                menu.Append(self.ID_VCD_PLOT_BITS, "Plot selected bits")
                menu.Append(self.ID_VCD_PLOT_BITS_VERT, "Plot selected bits vertically")

        menu.AppendSeparator()
        type_menu = wx.Menu()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_PYINT, "int in Python")
        mitem.Check(isinstance(value[0], int))
        type_menu.AppendSeparator()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_INT8, "int8")
        mitem.Check(value.dtype == np.int8)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_UINT8, "uint8")
        mitem.Check(value.dtype == np.uint8)
        type_menu.AppendSeparator()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_INT16, "int16")
        mitem.Check(value.dtype == np.int16)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_UINT16, "uint16")
        mitem.Check(value.dtype == np.uint16)
        type_menu.AppendSeparator()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_INT32, "int32")
        mitem.Check(value.dtype == np.int32)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_UINT32, "uint32")
        mitem.Check(value.dtype == np.uint32)
        type_menu.AppendSeparator()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_INT64, "int64")
        mitem.Check(value.dtype == np.int64)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_UINT64, "uint64")
        mitem.Check(value.dtype == np.uint64)
        type_menu.AppendSeparator()
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_FLOAT16, "float16")
        mitem.Check(value.dtype == np.float16)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_FLOAT32, "float32")
        mitem.Check(value.dtype == np.float32)
        mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_FLOAT64, "float64")
        mitem.Check(value.dtype == np.float64)
        if hasattr(np, 'float128'):
            mitem = type_menu.AppendCheckItem(self.ID_VCD_TO_FLOAT128, "float128")
            mitem.Check(value.dtype == np.float128)

        menu.AppendSubMenu(type_menu, 'As type')

        cmd = self.GetPopupMenuSelectionFromUser(menu)
        if cmd == wx.ID_NONE:
            return
        text = self.GetItemText(item)
        if not path:
            return

        def _as_type(nptype):
            try:
                value = data.raw.map(lambda x: int(x, 2))
                data[path[-1]] = value.astype(nptype)
                return
            except ValueError:
                pass
            except OverflowError:
                data[path[-1]] = value
            try:
                value = data.raw.astype(nptype)
                data[path[-1]] = value
                return
            except ValueError:
                pass
            try:
                value = data.raw.astype(np.float128)
                data[path[-1]] = value.astype(nptype)
                return
            except ValueError:
                pass
            print(f"Fail to convert to {nptype}")

        if cmd in [self.ID_VCD_EXPORT, self.ID_VCD_EXPORT_WITH_TIMESTAMP,
                   self.ID_VCD_EXPORT_RAW, self.ID_VCD_EXPORT_RAW_WITH_TIMESTAMP]:
            name = get_variable_name(path)
            command = f'{name}=VCD.get()'
            for p in path:
                command += f'["{p}"]'
            if cmd == self.ID_VCD_EXPORT_WITH_TIMESTAMP:
                command += f'.get(["timestamp", "{path[-1]}"])'
            elif cmd == self.ID_VCD_EXPORT_RAW_WITH_TIMESTAMP:
                command += '.get(["timestamp", "raw"])'
            elif cmd == self.ID_VCD_EXPORT_RAW:
                command += '.get(["raw"])'
            else:
                command += f'.get(["{path[-1]}"])'
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
        elif cmd in [self.ID_VCD_EXPORT_BITS, self.ID_VCD_EXPORT_BITS_WITH_TIMESTAMP]:
            df = self.GetDataBits(value)
            if df is not None:
                if cmd == self.ID_VCD_EXPORT_BITS_WITH_TIMESTAMP:
                    df.insert(loc=0, column='timestamp',  value=data['timestamp'])
                send_data_to_shell(name, df)

        elif cmd in [self.ID_VCD_PLOT, self.ID_VCD_PLOT_BITS, self.ID_VCD_PLOT_BITS_VERT]:
            x = data['timestamp']*self.data.get('timescale', 1e-6)*1e6
            if cmd == self.ID_VCD_PLOT:
                self.plot(x, value, '/'.join(path))
                return
            # plot bits
            df = self.GetDataBits(value)
            if df is not None:
                if cmd == self.ID_VCD_PLOT_BITS_VERT:
                    offsets = (np.arange(len(df.columns), 0, -1) - 1) * 1.2
                    df += offsets
                for bit in df:
                    self.plot(x, df[bit], '/'.join(path+[bit]), step=True)

        elif cmd == self.ID_VCD_TO_PYINT:
            try:
                value = data.raw.map(lambda x: int(x, 2))
                data[path[-1]] = value
                return
            except ValueError:
                pass
            try:
                value = data.raw.map(lambda x: int(x))
                data[path[-1]] = value
                return
            except ValueError:
                pass
            try:
                value = data.raw.map(lambda x: int(float(x)))
                data[path[-1]] = value
                return
            except ValueError:
                pass
            print(f'Fail to convert "{text}" to int')

        elif cmd == self.ID_VCD_TO_INT8:
            _as_type(np.int8)
        elif cmd == self.ID_VCD_TO_UINT8:
            _as_type(np.uint8)
        elif cmd == self.ID_VCD_TO_INT16:
            _as_type(np.int16)
        elif cmd == self.ID_VCD_TO_UINT16:
            _as_type(np.uint16)
        elif cmd == self.ID_VCD_TO_INT32:
            _as_type(np.int32)
        elif cmd == self.ID_VCD_TO_UINT32:
            _as_type(np.uint32)
        elif cmd == self.ID_VCD_TO_INT64:
            _as_type(np.int64)
        elif cmd == self.ID_VCD_TO_UINT64:
            _as_type(np.uint64)
        elif cmd == self.ID_VCD_TO_FLOAT16:
            _as_type(np.float16)
        elif cmd == self.ID_VCD_TO_FLOAT32:
            _as_type(np.float32)
        elif cmd == self.ID_VCD_TO_FLOAT64:
            _as_type(np.float64)
        elif cmd == self.ID_VCD_TO_FLOAT128:
            _as_type(np.float128)


class CommentListCtrl(ListCtrlBase):

    def BuildColumns(self):
        super().BuildColumns()
        start = self.data_start_column
        self.InsertColumn(start, "Comment", width=wx.LIST_AUTOSIZE_USEHEADER)

    def FindText(self, start, end, text, flags=0):
        direction = 1 if end > start else -1
        for i in range(start, end+direction, direction):
            m = self.data_shown[i]
            if self.Search(m, text, flags):
                return i

        # not found
        return -1

    def ApplyPattern(self):
        if not self.pattern:
            self.data_shown = self.data
        else:
            self.data_shown = [m for m in self.data if self.pattern in m.lower()]

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        m = self.data_shown[item]
        if column == 0:
            return m
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

    def ApplyPattern(self):
        if self.pattern:
            self.data_shown = [[k, v] for k, v in self.data.items() if self.pattern in str(k).lower() or self.pattern.lower() in str(v).lower()]
        else:
            self.data_shown = [[k, v] for k, v in self.data.items()]

    def OnGetItemText(self, item, column):
        if column < self.data_start_column:
            return super().OnGetItemText(item, column)
        column -= self.data_start_column
        return str(self.data_shown[item][column])

class VcdPanel(PanelNotebookBase):
    Gcv = Gcm()

    def __init__(self, parent, filename=None):
        PanelNotebookBase.__init__(self, parent, filename=filename)

        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchInfo, self.search_info)
        self.Bind(wx.EVT_TEXT, self.OnDoSearchComment, self.search_comment)

        self.num = self.Gcv.get_next_num()
        self.Gcv.set_active(self)

    def init_pages(self):
        # data page
        panel, self.search, self.tree = self.CreatePageWithSearch(VcdTree)
        self.notebook.AddPage(panel, 'Data')
        # info page
        panel_info, self.search_info, self.infoList = self.CreatePageWithSearch(InfoListCtrl)
        self.notebook.AddPage(panel_info, 'Info')
        # comment page
        panel_comment, self.search_comment, self.commentList = self.CreatePageWithSearch(CommentListCtrl)
        self.notebook.AddPage(panel_comment, 'Comment')

        self.vcd = None

    def Load(self, filename, add_to_history=True):
        """load the vcd file"""
        u = load_vcd3(filename)
        self.vcd = u
        self.filename = filename
        self.tree.Load(u['data'])
        self.infoList.Load(u['info'])
        self.commentList.Load(u['comment'])
        super().Load(filename, add_to_history=add_to_history)

    def OnDoSearch(self, evt):
        pattern = self.search.GetValue()
        self.tree.Fill(pattern)
        self.search.SetFocus()

    def OnDoSearchInfo(self, evt):
        pattern = self.search_info.GetValue()
        self.infoList.Fill(pattern)

    def OnDoSearchComment(self, evt):
        pattern = self.search_param.GetValue()
        self.commentList.Fill(pattern)

    def Destroy(self):
        """
        Destroy the vcdg properly before close the pane.
        """
        self.Gcv.destroy(self.num)
        super().Destroy()

    @classmethod
    def GetFileType(cls):
        return "vcd files (*.vcd)|*.vcd|All files (*.*)|*.*"

    @classmethod
    def get_all_managers(cls):
        return cls.Gcv.get_all_managers()

    @classmethod
    def get_active(cls):
        return cls.Gcv.get_active()

    @classmethod
    def set_active(cls, panel):
        cls.Gcv.set_active(panel)

    @classmethod
    def get_manager(cls, num):
        return cls.Gcv.get_manager(num)

class VCD(FileViewBase):
    name = 'vcd'
    panel_type = VcdPanel

    @classmethod
    def check_filename(cls, filename):
        if filename is None:
            return True

        _, ext = os.path.splitext(filename)
        return (ext.lower() in ['.vcd', '.bsm'])

    @classmethod
    def initialized(cls):
        # add pandas and vcd to the shell
        dp.send(signal='shell.run',
                command='import pandas as pd',
                prompt=False,
                verbose=False,
                history=False)
        dp.send(signal='shell.run',
                command='from bsmedit.bsm.vcds import VCD as VCD',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def get(cls, num=None, filename=None, data_only=True):
        manager = super().get(num, filename, data_only)
        vcd = None
        if manager:
            vcd = manager.vcd
        elif filename:
            try:
                vcd = load_vcd3(filename)
            except:
                traceback.print_exc(file=sys.stdout)
        if vcd:
            if data_only:
                return vcd['data']
        return vcd

def bsm_initialize(frame, **kwargs):
    VCD.initialize(frame)
