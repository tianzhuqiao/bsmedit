import wx

if 'phoenix' in wx.version():
    bsm_is_phoenix = True
    import wx.html
    BitmapFromXPMData = wx.Bitmap
    HtmlListBox = wx.html.HtmlListBox
    ArtProvider_GetBitmap = wx.ArtProvider.GetBitmap
    EmptyIcon = wx.Icon
    EmptyBitmap = wx.Bitmap
    EVT_COMMAND_FIND = wx.EVT_FIND
    EVT_COMMAND_FIND_NEXT = wx.EVT_FIND_NEXT
    EVT_COMMAND_FIND_REPLACE = wx.EVT_FIND_REPLACE
    EVT_COMMAND_FIND_REPLACE_ALL = wx.EVT_FIND_REPLACE_ALL
    EVT_COMMAND_FIND_CLOSE = wx.EVT_FIND_CLOSE
    SystemSettings_GetColour= wx.SystemSettings.GetColour
    NamedColour = wx.Colour
    StockCursor = wx.Cursor
    PyDropTarget = wx.DropTarget
    PyTextDataObject = wx.TextDataObject
    APP_ASSERT_DIALOG = wx.APP_ASSERT_DIALOG
    FD_OPEN = wx.FD_OPEN
    FD_FILE_MUST_EXIST = wx.FD_FILE_MUST_EXIST
else:
    bsm_is_phoenix = False
    BitmapFromXPMData = wx.BitmapFromXPMData
    HtmlListBox = wx.HtmlListBox
    ArtProvider_GetBitmap = wx.ArtProvider_GetBitmap
    EmptyIcon = wx.EmptyIcon
    EmptyBitmap = wx.EmptyBitmap
    EVT_COMMAND_FIND = wx.EVT_COMMAND_FIND
    EVT_COMMAND_FIND_NEXT = wx.EVT_COMMAND_FIND_NEXT
    EVT_COMMAND_FIND_REPLACE = wx.EVT_COMMAND_FIND_REPLACE
    EVT_COMMAND_FIND_REPLACE_ALL = wx.EVT_COMMAND_FIND_REPLACE_ALL
    EVT_COMMAND_FIND_CLOSE = wx.EVT_COMMAND_FIND_CLOSE
    SystemSettings_GetColour= wx.SystemSettings_GetColour
    NamedColour = wx.NamedColour
    StockCursor = wx.StockCursor
    PyDropTarget = wx.PyDropTarget
    PyTextDataObject = wx.PyTextDataObject
    APP_ASSERT_DIALOG = wx.PYAPP_ASSERT_DIALOG
    FD_OPEN = wx.OPEN
    FD_FILE_MUST_EXIST = wx.FILE_MUST_EXIST

def SetClippingRect(dc, rc):
    if bsm_is_phoenix:
        dc.SetClippingRegion(rc)
    else:
        dc.SetClippingRect(rc)

def BitmapFromXPM(xpm):
    xpm_b = [x.encode('utf-8') for x in xpm]
    return BitmapFromXPMData(xpm_b)

def tbAddTool(tb, *args, **kwargs):
    if bsm_is_phoenix:
        tb.AddTool(*args, **kwargs)
    else:
        tb.AddLabelTool(*args, **kwargs)

def tbAddCheckTool(tb, *args, **kwargs):
    if bsm_is_phoenix:
        tb.AddCheckTool(*args, **kwargs)
    else:
        tb.AddCheckLabelTool(*args, **kwargs)

def treeGetData(tree, *args, **kwargs):
    if bsm_is_phoenix:
        return tree.GetItemData(*args, **kwargs)
    else:
        data = tree.GetPyData(*args, **kwargs)

def treeAppendItem(tree, parent, label, img, selimg, data):
    if not bsm_is_phoenix:
        data = wx.TreeItemData(data)
    return tree.AppendItem(parent, label, img, selimg, data)

def menuAppend(menu, item):
    if not bsm_is_phoenix:
        return menu.AppendItem(item)
    else:
        return menu.Append(item)
