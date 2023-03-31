"""define some utility functions"""
import os
import subprocess
import platform
import six
import wx
from wx.lib.agw import aui
import wx.svg

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

def svg_to_bitmap(svg, width=16, height=16, win=None):
    bmp = wx.svg.SVGimage.CreateFromBytes(str.encode(svg))
    bmp = bmp.ConvertToScaledBitmap((width, height), win)
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
        subprocess.Popen( f"explorer '{filepath}'" )
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

def patch_aui_toolbar_art():

    def GetToolsPosition(self, dc, item, rect):
        """
        Returns the bitmap and text rectangles for a toolbar item.

        :param `dc`: a :class:`wx.DC` device context;
        :param `item`: an instance of :class:`AuiToolBarItem`;
        :param wx.Rect `rect`: the tool rectangle.
        """

        text_width = text_height = 0
        horizontal = self._orientation == aui.AUI_TBTOOL_HORIZONTAL
        text_bottom = self._text_orientation == aui.AUI_TBTOOL_TEXT_BOTTOM
        text_right = self._text_orientation == aui.AUI_TBTOOL_TEXT_RIGHT
        bmp_width = item.GetBitmap().GetLogicalWidth()
        bmp_height = item.GetBitmap().GetLogicalHeight()

        if self._agwFlags & aui.AUI_TB_TEXT:
            dc.SetFont(self._font)
            label_size = aui.GetLabelSize(dc, item.GetLabel(), not horizontal)
            text_height = label_size.GetHeight()
            text_width = label_size.GetWidth()

        bmp_x = bmp_y = text_x = text_y = 0

        if horizontal and text_bottom:
            bmp_x = rect.x + (rect.width//2) - (bmp_width//2)
            bmp_y = rect.y + 3
            text_x = rect.x + (rect.width//2) - (text_width//2)
            text_y = rect.y + ((bmp_y - rect.y) * 2) + bmp_height

        elif horizontal and text_right:
            bmp_x = rect.x + 3
            bmp_y = rect.y + (rect.height//2) - (bmp_height // 2)
            text_x = rect.x + ((bmp_x - rect.x) * 2) + bmp_width
            text_y = rect.y + (rect.height//2) - (text_height//2)

        elif not horizontal and text_bottom:
            bmp_x = rect.x + (rect.width // 2) - (bmp_width // 2)
            bmp_y = rect.y + 3
            text_x = rect.x + (rect.width // 2) - (text_width // 2)
            text_y = rect.y + ((bmp_y - rect.y) * 2) + bmp_height

        bmp_rect = wx.Rect(bmp_x, bmp_y, bmp_width, bmp_height)
        text_rect = wx.Rect(text_x, text_y, text_width, text_height)

        return bmp_rect, text_rect

    def GetToolSize(self, dc, wnd, item):
        """
        Returns the toolbar item size.

        :param `dc`: a :class:`wx.DC` device context;
        :param `wnd`: a :class:`wx.Window` derived window;
        :param `item`: an instance of :class:`AuiToolBarItem`.
        """

        if not item.GetBitmap().IsOk() and not self._agwFlags & aui.AUI_TB_TEXT:
            return wx.Size(16, 16)

        width = item.GetBitmap().GetLogicalWidth()
        height = item.GetBitmap().GetLogicalHeight()

        if self._agwFlags & aui.AUI_TB_TEXT:

            dc.SetFont(self._font)
            label_size = aui.GetLabelSize(dc, item.GetLabel(), self.GetOrientation() != aui.AUI_TBTOOL_HORIZONTAL)
            padding = 6

            if self._text_orientation == aui.AUI_TBTOOL_TEXT_BOTTOM:

                if self.GetOrientation() != aui.AUI_TBTOOL_HORIZONTAL:
                    height += 3   # space between top border and bitmap
                    height += 3   # space between bitmap and text
                    padding = 0

                height += label_size.GetHeight()

                if item.GetLabel() != "":
                    width = max(width, label_size.GetWidth()+padding)

            elif self._text_orientation == aui.AUI_TBTOOL_TEXT_RIGHT and item.GetLabel() != "":

                if self.GetOrientation() == aui.AUI_TBTOOL_HORIZONTAL:

                    width += 3  # space between left border and bitmap
                    width += 3  # space between bitmap and text
                    padding = 0

                width += label_size.GetWidth()
                height = max(height, label_size.GetHeight()+padding)

        # if the tool has a dropdown button, add it to the width
        if item.HasDropDown():
            if item.GetOrientation() == aui.AUI_TBTOOL_HORIZONTAL:
                width += aui.BUTTON_DROPDOWN_WIDTH+4
            else:
                height += aui.BUTTON_DROPDOWN_WIDTH+4

        return wx.Size(width, height)

    aui.AuiDefaultToolBarArt.GetToolSize = GetToolSize
    aui.AuiDefaultToolBarArt.GetToolsPosition = GetToolsPosition


class _dict(dict):
    """dict like object that exposes keys as attributes"""
    def __getattr__(self, key):
        ret = self.get(key)
        if not ret and key.startswith("__"):
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
