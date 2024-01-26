import json
import wx
import wx.py.dispatcher as dp
import numpy as np
from pandas.api.types import is_numeric_dtype, is_integer_dtype
from .utility import FastLoadTreeCtrl, _dict
from . import graph

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
        return None

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

    def OnTreeItemActivated(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        if self.ItemHasChildren(item):
            return
        path = self.GetItemPath(item)
        x, y = self.GetItemPlotData(item)
        if x is None or y is None or not is_numeric_dtype(y):
            print(f"{path[-1]} is not numeric, ignore plotting!")
            return
        self.plot(x, y, "/".join(path))

    def plot(self, x, y, label, step=False):
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
