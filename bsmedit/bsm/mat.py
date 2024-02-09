import os
import sys
import traceback
import wx
import wx.py.dispatcher as dp
from scipy import io
from .pymgr_helpers import Gcm
from .fileviewbase import TreeCtrlNoTimeStamp, ListCtrlBase, PanelNotebookBase, FileViewBase

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


class MatTree(TreeCtrlNoTimeStamp):
    pass


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

    @classmethod
    def GetFileType(cls):
        return "mat files (*.mat)|*.mat|All files (*.*)|*.*"

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
