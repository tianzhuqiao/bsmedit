"""define some utility functions"""
import six
import wx
import wx.lib.agw.aui as aui
from .. import c2p

def MakeBitmap(red, green, blue, alpha=128):
    # Create the bitmap that we will stuff pixel values into using
    # the raw bitmap access classes.
    bmp = c2p.EmptyBitmap(16, 16, 32)

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
    for x in six.moves.range(16):
        pixels.MoveTo(pixelData, x, 0)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
        pixels.MoveTo(pixelData, x, 16-1)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
    for y in six.moves.range(16):
        pixels.MoveTo(pixelData, 0, y)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)
        pixels.MoveTo(pixelData, 16-1, y)
        pixels.Set(red, green, blue, wx.ALPHA_OPAQUE)

    return bmp

def PopupMenu(wnd, menu):
    if not wnd or not menu:
        return

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
    def __init__(self, parent, getchildren=None, style=wx.TR_DEFAULT_STYLE,
                 sort=True):
        wx.TreeCtrl.__init__(self, parent, style=style)
        self._get_children = getchildren
        assert(self._get_children)
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
        if not ((self.GetWindowStyle() & wx.TR_HIDE_ROOT) and item == self.GetRootItem()):
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
            child = c2p.treeAppendItem(self, item, obj['label'], obj['img'], obj['imgsel'],
                                       obj['data'])
            # add the place holder for children
            if obj['is_folder']:
                c2p.treeAppendItem(self, child, '...', -1, -1, None)
            clr = obj.get('color', None)
            if clr:
                self.SetItemTextColour(child, wx.Colour(100, 174, 100))
        if self._sort_children:
            self.SortChildren(item)
        return True
