"""define some utility functions"""
import os
import subprocess
import platform
import six
import wx
import wx.svg
from ..aui import aui

def MakeBitmap(red, green, blue, alpha=128, size=None, scale_factor=1):
    # Create the bitmap that we will stuff pixel values into using
    w, h = 16, 16
    if size is not None:
        w, h = size[0], size[1]
    w = int(round(w*scale_factor))
    h = int(round(h*scale_factor))
    # the raw bitmap access classes.
    bmp = wx.Bitmap(w, h, 32)
    bmp.SetScaleFactor(scale_factor)

    # Create an object that facilitates access to the bitmap's
    # pixel buffer
    pixelData = wx.AlphaPixelData(bmp)
    if not pixelData:
        raise RuntimeError("Failed to gain raw access to bitmap data.")

    # We have two ways to access each pixel, first we'll use an
    # iterator to set every pixel to the colour and alpha values
    # passed in.
    for pixel in pixelData:
        pixel.Set(red, green, blue, alpha)

    # Next we'll use the pixel accessor to set the border pixels
    # to be fully opaque
    pixels = pixelData.GetPixels()
    for x in six.moves.range(w):
        pixels.MoveTo(pixelData, x, 0)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
        pixels.MoveTo(pixelData, x, w - 1)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
    for y in six.moves.range(h):
        pixels.MoveTo(pixelData, 0, y)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
        pixels.MoveTo(pixelData, h - 1, y)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)

    return bmp


def PopupMenu(wnd, menu):
    # popup a menu, and return the selected command
    if not wnd or not menu:
        return wx.ID_NONE

    cc = aui.ToolbarCommandCapture()
    wnd.PushEventHandler(cc)

    wnd.PopupMenu(menu)

    command = cc.GetCommandId()
    wnd.PopEventHandler(True)
    return command


class FastLoadTreeCtrl(wx.TreeCtrl):
    """
    When a treectrl tries to load a large amount of items, it will be slow.
    This class will not load the children item until the parent is expanded (
    e.g., by a click).
    """
    def __init__(self,
                 parent,
                 getchildren=None,
                 style=wx.TR_DEFAULT_STYLE,
                 sort=True):
        wx.TreeCtrl.__init__(self, parent, style=style)
        self._get_children = getchildren
        assert self._get_children
        self._sort_children = sort
        self.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnTreeItemExpanding)

    def OnTreeItemExpanding(self, event):
        """expand the item with children"""
        item = event.GetItem()
        if not item.IsOk():
            return
        self.FillChildren(item)

    def FillChildren(self, item):
        """fill the node with children"""
        if not ((self.GetWindowStyle() & wx.TR_HIDE_ROOT)
                and item == self.GetRootItem()):
            child, _ = self.GetFirstChild(item)
            if not child.IsOk():
                return False
            if self.GetItemText(child) != "...":
                return False
        # delete the '...'
        self.DeleteChildren(item)
        children = self._get_children(item)
        for obj in children:
            # fill all the children
            child = self.AppendItem(item, obj['label'], obj['img'],
                                    obj['imgsel'], obj['data'])
            # add the place holder for children
            if obj['is_folder']:
                self.AppendItem(child, '...', -1, -1, None)
            clr = obj.get('color', None)
            if clr:
                self.SetItemTextColour(child, wx.Colour(100, 174, 100))
        if self._sort_children:
            self.SortChildren(item)
        return True

def svg_to_bitmap(svg, size=None, win=None):
    if size is None:
        if wx.Platform == '__WXMSW__':
            size = (24, 24)
        else:
            size = (16, 16)
    bmp = wx.svg.SVGimage.CreateFromBytes(str.encode(svg))
    bmp = bmp.ConvertToScaledBitmap(size, win)
    if win:
        bmp.SetScaleFactor(win.GetContentScaleFactor())
    return bmp


def open_file_with_default_app(filepath):
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(filepath)
    else:                                   # linux variants
        subprocess.call(('xdg-open', filepath))

def get_file_finder_name():

    if platform.system() == 'Darwin':       # macOS
        manager = 'Finder'
    elif platform.system() == 'Windows':    # Windows
        manager = 'Explorer'
    else:                         # linux variants
        manager = 'File Explorer'
    return manager

def show_file_in_finder(filepath):
    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', '-R', filepath))
    elif platform.system() == 'Windows':    # Windows
        subprocess.Popen( f'explorer /select,"{filepath}"' )
    else:                                   # linux variants
        subprocess.call(('nautilus', '-s', filepath))

def build_menu_from_list(items, menu=None):
    # for each item in items
    # {'type': ITEM_SEPARATOR}
    # {'type': ITEM_NORMAL, 'id': , 'label': , 'enable':}
    # {'type': ITEM_CHECK, 'id': , 'label': , 'enable':, 'check'}
    # {'type': ITEM_RADIO, 'id': , 'label': , 'enable':, 'check'}
    # {'type': ITEM_DROPDOWN, 'label':, 'items': []]
    if menu is None:
        menu = wx.Menu()
    for m in items:
        mtype = m.get('type', wx.ITEM_NORMAL)
        if mtype == wx.ITEM_SEPARATOR:
            item = menu.AppendSeparator()
        elif mtype == wx.ITEM_DROPDOWN:
            child = build_menu_from_list(m['items'])
            menu.AppendSubMenu(child, m['label'])
        elif mtype == wx.ITEM_NORMAL:
            item = menu.Append(m['id'], m['label'])
            item.Enable(m.get('enable', True))
        elif mtype == wx.ITEM_CHECK:
            item = menu.AppendCheckItem(m['id'], m['label'])
            item.Check(m.get('check', True))
            item.Enable(m.get('enable', True))
        elif mtype == wx.ITEM_RADIO:
            item = menu.AppendRadioItem(m['id'], m['label'])
            item.Check(m.get('check', True))
            item.Enable(m.get('enable', True))
    return menu


class _dict(dict):
    """dict like object that exposes keys as attributes"""
    def __getattr__(self, key):
        ret = self.get(key, None)
        if ret is None or key.startswith("__"):
            raise AttributeError()
        return ret
    def __setattr__(self, key, value):
        self[key] = value
    def __getstate__(self):
        return self
    def __setstate__(self, d):
        self.update(d)
    def update(self, d=None, **kwargs):
        """update and return self -- the missing dict feature in python"""
        if d:
            super().update(d)
        if kwargs:
            super().update(kwargs)
        return self

    def copy(self):
        return _dict(dict(self).copy())
