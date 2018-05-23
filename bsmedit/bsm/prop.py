import six
import wx
from ._propxpm import radio_xpm, tree_xpm
from .. import c2p

wxEVT_BSM_PROP_SELECTED = wx.NewEventType()
EVT_BSM_PROP_SELECTED = wx.PyEventBinder(wxEVT_BSM_PROP_SELECTED, 1)
wxEVT_BSM_PROP_CHANGING = wx.NewEventType()
EVT_BSM_PROP_CHANGING = wx.PyEventBinder(wxEVT_BSM_PROP_CHANGING, 1)
wxEVT_BSM_PROP_CHANGED = wx.NewEventType()
EVT_BSM_PROP_CHANGED = wx.PyEventBinder(wxEVT_BSM_PROP_CHANGED, 1)
wxEVT_BSM_PROP_HIGHLIGHTED = wx.NewEventType()
EVT_BSM_PROP_HIGHLIGHTED = wx.PyEventBinder(wxEVT_BSM_PROP_HIGHLIGHTED, 1)
wxEVT_BSM_PROP_RIGHT_CLICK = wx.NewEventType()
EVT_BSM_PROP_RIGHT_CLICK = wx.PyEventBinder(wxEVT_BSM_PROP_RIGHT_CLICK, 1)

wxEVT_BSM_PROP_COLLAPSED = wx.NewEventType()
EVT_BSM_PROP_COLLAPSED = wx.PyEventBinder(wxEVT_BSM_PROP_COLLAPSED, 1)
wxEVT_BSM_PROP_EXPANDED = wx.NewEventType()
EVT_BSM_PROP_EXPANDED = wx.PyEventBinder(wxEVT_BSM_PROP_EXPANDED, 1)
wxEVT_BSM_PROP_DOUBLE_CLICK = wx.NewEventType()
EVT_BSM_PROP_DOUBLE_CLICK = wx.PyEventBinder(wxEVT_BSM_PROP_DOUBLE_CLICK, 1)
wxEVT_BSM_PROP_INDENT = wx.NewEventType()
EVT_BSM_PROP_INDENT = wx.PyEventBinder(wxEVT_BSM_PROP_INDENT, 1)
wxEVT_BSM_PROP_KEYDOWN = wx.NewEventType()
EVT_BSM_PROP_KEYDOWN = wx.PyEventBinder(wxEVT_BSM_PROP_KEYDOWN, 1)
wxEVT_BSM_PROP_RESIZE = wx.NewEventType()
EVT_BSM_PROP_RESIZE = wx.PyEventBinder(wxEVT_BSM_PROP_RESIZE, 1)
wxEVT_BSM_PROP_REFRESH = wx.NewEventType()
EVT_BSM_PROP_REFRESH = wx.PyEventBinder(wxEVT_BSM_PROP_REFRESH, 1)
wxEVT_BSM_PROP_DELETE = wx.NewEventType()
EVT_BSM_PROP_DELETE = wx.PyEventBinder(wxEVT_BSM_PROP_DELETE, 1)
wxEVT_BSM_PROP_DROP = wx.NewEventType()
EVT_BSM_PROP_DROP = wx.PyEventBinder(wxEVT_BSM_PROP_DROP, 1)
wxEVT_BSM_PROP_BEGIN_DRAG = wx.NewEventType()
EVT_BSM_PROP_BEGIN_DRAG = wx.PyEventBinder(wxEVT_BSM_PROP_BEGIN_DRAG, 1)
wxEVT_BSM_PROP_CLICK_RADIO = wx.NewEventType()
EVT_BSM_PROP_CLICK_RADIO = wx.PyEventBinder(wxEVT_BSM_PROP_CLICK_RADIO, 1)

PROP_CTRL_DEFAULT = 0
PROP_CTRL_NONE = 1
PROP_CTRL_EDIT = 2
PROP_CTRL_COMBO = 3
PROP_CTRL_FILE_SEL = 4
PROP_CTRL_FOLDER_SEL = 5
PROP_CTRL_SLIDER = 6
PROP_CTRL_SPIN = 7
PROP_CTRL_CHECK = 8
PROP_CTRL_RADIO = 9
PROP_CTRL_COLOR = 10
PROP_CTRL_NUM = 11

class bsmProperty(object):
    PROP_HIT_NONE = 0
    PROP_HIT_EXPAND = 1
    PROP_HIT_RADIO = 2
    PROP_HIT_TITLE = 3
    PROP_HIT_SPLITTER = 4
    PROP_HIT_VALUE = 5
    PROP_HIT_EDGE_BOTTOM = 6
    PROP_HIT_EDGE_TOP = 7

    IDC_BSM_PROP_CONTROL = wx.NewId()

    VALIDATE_NONE = 0
    VALIDATE_DEC = 1
    VALIDATE_HEX = 2
    VALIDATE_OCT = 3
    VALIDATE_BIN = 4
    MARGIN_X = 2


    imgRadio = None
    imgExpColp = None
    def __init__(self, parent, name, label, value):
        self.parent = parent
        self.name = name
        self.label = label
        self.labelTip = ''
        self.value = value
        self.valueTip = ''
        self.description = ""
        self.valueMax = 100
        self.valueMin = 0
        self.radioWidth = 15
        self.titleWidth = 80
        self.indent = 0
        self.showRadio = True
        self.bpCondition = ('', '')
        self.radioChecked = False
        self.radioFocused = False
        self.activated = False
        self.enable = True
        self.italic = False
        self.hasChildren = False
        self.expanded = True
        self.visible = True
        self.readOnly = False
        self.ctrlType = PROP_CTRL_EDIT
        self.controlWin = None
        self.parentProp = -1
        self.choiceList = []
        self.valueList = []
        self.SetGripperColor()
        self.SetTextColor(silent=True)
        self.SetBGColor(silent=True)
        self.minimumSize = wx.Size(200, 25)
        self.defaultSize = wx.Size(200, 25)
        self.clientRect = wx.Rect(0, 0, 0, 0)
        self.gripperRect = wx.Rect(0, 0, 0, 0)
        self.expanderRect = wx.Rect(0, 0, 0, 0)
        self.radioRect = wx.Rect(0, 0, 0, 0)
        self.splitterRect = wx.Rect(0, 0, 0, 0)
        self.titleRect = wx.Rect(0, 0, 0, 0)
        self.titleRectColumn = wx.Rect(0, 0, 0, 0)
        self.valueRect = wx.Rect(0, 0, 0, 0)
        self.showLabelTips = True
        self.showValueTips = True
        self.separator = False
        #self.m_validate = wx.FILTER_NONE
        #self.m_nValidateType(VALIDATE_NONE)
        if type(self).imgRadio is None or type(self).imgExpColp is None:
            type(self).imgRadio = wx.ImageList(16, 16, True, 4)
            type(self).imgExpColp = wx.ImageList(12, 12, True, 2)
            type(self).imgRadio.Add(c2p.BitmapFromXPM(radio_xpm))
            type(self).imgExpColp.Add(c2p.BitmapFromXPM(tree_xpm))

    def duplicate(self):
        """
        copy the object

        copy.deepcopy does not work since the object contains pointer to wx
        objects
        """
        p = bsmProperty(self.parent, self.name, self.label, self.value)
        p.labelTip = self.labelTip
        p.valueTip = self.valueTip
        p.description = self.description
        p.valueMax = self.valueMax
        p.valueMin = self.valueMin
        p.radioWidth = self.radioWidth
        p.titleWidth = self.titleWidth
        p.indent = self.indent
        p.showRadio = self.showRadio
        p.bpCondition = self.bpCondition
        p.radioChecked = self.radioChecked
        p.radioFocused = self.radioFocused
        p.activated = self.activated
        p.enable = self.enable
        p.italic = self.italic
        p.hasChildren = self.hasChildren
        p.expanded = self.expanded
        p.visible = self.visible
        p.readOnly = self.readOnly
        p.ctrlType = self.ctrlType
        p.parentProp = self.parentProp
        p.choiceList = self.choiceList[:]
        p.valueList = self.valueList[:]
        p.SetGripperColor(self.gripperColor)
        p.SetTextColor(self.textColor, self.textColorSel, self.textColorDisable, True)
        p.SetBGColor(self.bgColor, self.bgColorSel, self.bgColorDisable, True)
        p.showLabelTips = self.showLabelTips
        p.showValueTips = self.showValueTips
        p.separator = self.separator
        return p

    def SetParent(self, parent):
        """set the parent window"""
        self.parent = parent

    def GetParent(self):
        """return the parent window"""
        return self.parent

    def SetSeparator(self, sep, silent=False):
        """set the property to be a separator"""
        if self.separator == sep:
            return
        self.separator = sep
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def GetSeparator(self):
        """return true if the property is a separator"""
        return self.separator

    def SetBPCondition(self, cond):
        """set the breakpoint condition"""
        checked = self.GetRadioChecked()
        if checked:
            # delete the current breakpoint
            self.SetRadioChecked(False)
            self.bpCondition = cond
            # add the breakpoint again
            self.SetRadioChecked(True)
        else:
            self.bpCondition = cond

    def GetBPCondition(self):
        """return the breakpoint condition"""
        return self.bpCondition

    def SetControlStyle(self, style):
        """set the control type
        style: default | none | editbox | combobox | file_sel_button |
               folder_sel_button | slider | spin | checkbox | radiobox |
               color
        """
        self.UpdatePropValue()
        self.DestroyControl()
        str_style = {'default':PROP_CTRL_DEFAULT, 'none': PROP_CTRL_NONE,
                     'editbox': PROP_CTRL_EDIT, 'combobox':PROP_CTRL_COMBO,
                     'file_sel_button':PROP_CTRL_FILE_SEL,
                     'folder_sel_button': PROP_CTRL_FOLDER_SEL,
                     'slider': PROP_CTRL_SLIDER, 'spin': PROP_CTRL_SPIN,
                     'checkbox': PROP_CTRL_CHECK, 'radiobox': PROP_CTRL_RADIO,
                     'color': PROP_CTRL_COLOR}
        if isinstance(style, six.string_types):
            style = str_style.get(style, None)
        if not isinstance(style, int):
            return False
        if style < PROP_CTRL_DEFAULT or style >= PROP_CTRL_NUM:
            return False
        if style != PROP_CTRL_DEFAULT:
            self.ctrlType = style
        return True

    def SetChoice(self, choice, value=None):
        """set the choices list
        Example:
            # dict parameter
            SetChoice({'1':1, '0':0, 'Z':'Z', 'X':'X'})
            # two lists
            SetChoice(['1', '0', 'Z', 'X'], [1, 0, 'Z', 'X'])
            # one list
            SetChoice([256, 512, 1024])
        """
        # dict, split the key and value
        if value is None and isinstance(choice, dict):
            value = list(choice.values())
            choice = list(choice.keys())
        # both choice and value are valid, but with different length
        if not choice or (value and len(choice) != len(value)):
            return
        # choice is always 'str'
        self.choiceList = [str(item) for item in choice]
        # value is not valid, use the choice instead
        if not value:
            self.valueList = choice
        else:
            self.valueList = value

    def SetEnable(self, enable, silent=False):
        """enable/disable the property"""
        if self.enable == enable:
            return
        self.enable = enable
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetName(self, name, silent=False):
        """set the name"""
        if self.name == name:
            return
        self.name = name
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetLabel(self, label, silent=False):
        """set the label"""
        if self.label == label:
            return
        self.label = label
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetLabelTip(self, tip):
        """set the label tip"""
        self.labelTip = tip

    def SetDescription(self, description, silent=False):
        """set the description"""
        if self.description == description:
            return
        self.description = description
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetItalicText(self, italic, silent=False):
        """turn on/of the italic text"""
        if self.italic == italic:
            return
        self.italic = italic
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetVisible(self, visible, silent=False):
        """
        show/hide the property

        The property may be hidden if its parent is in collapsed mode.
        """
        if self.visible == visible:
            return
        self.visible = visible
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetParentProp(self, prop):
        """set the parent property"""
        if prop == self:
            return
        self.parentProp = prop

    def SetRange(self, minVal, maxVal):
        """
        set the min/max values

        It is only used in spin and slider controls.
        """
        self.valueMax = float(maxVal)
        self.valueMin = float(minVal)

    def SetShowRadio(self, show, silent=True):
        """show/hide radio button"""
        self.showRadio = show
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def GetCtrlStyle(self):
        """return the control type"""
        return self.ctrlType

    def GetChoice(self):
        """return the choices list"""
        return (self.choiceList, self.valueList)

    def GetChoiceString(self, delims):
        """return the choices list in string"""
        return (delims.join(self.choiceList), delims.join(self.valueList))

    def IsEnabled(self):
        """return true if the property is enabled"""
        return self.enable

    def GetName(self):
        """get the name"""
        return self.name

    def GetLabel(self):
        """get the label"""
        return self.label

    def GetLabelTip(self):
        """get the label tip"""
        if self.labelTip:
            return self.labelTip
        return self.GetName()

    def GetValue(self):
        """get the value"""
        return self.value

    def GetValueTip(self):
        """get the valuetip"""
        if self.valueTip:
            return self.valueTip
        return self.value

    def GetDescription(self):
        """get the description"""
        return self.description

    def GetIndent(self):
        """get the indent"""
        return self.indent

    def IsExpanded(self):
        """return true if the expand/collapse button is expanded"""
        return self.expanded

    def HasChildren(self):
        """return true if the property has children"""
        return self.hasChildren

    def IsRadioChecked(self):
        """return true if the radio button is checked"""
        return self.radioChecked

    def IsItalicText(self):
        "return true if the italic is used for drawing"
        return self.italic

    def GetControlStyle(self):
        """get the control type"""
        return self.ctrlType

    def GetActivated(self):
        """return true if the property is activated"""
        return self.activated

    def GetVisible(self):
        """return true if the property is visible"""
        return self.visible

    def GetParentProp(self):
        """return the parent property"""
        return self.parentProp

    def GetRange(self):
        """return the value range"""
        return (self.valueMin, self.valueMax)

    def GetReadOnly(self):
        """return true if the property is readonly"""
        return self.readOnly

    def GetRadioChecked(self):
        """return true if the radio button is checked"""
        return self.radioChecked

    def GetRadioFocused(self):
        """return whether the radio is drawn in focused mode"""
        return self.radioFocused

    def GetShowRadio(self):
        """return whether the radio icon is shown"""
        return self.showRadio

    def GetGripperColor(self):
        return self.gripperColor

    def GetTextColor(self):
        """get the text colors"""
        return (self.textColor, self.textColorSel, self.textColorDisable)

    def GetBGColor(self):
        """get the background colors"""
        return (self.bgColor, self.bgColorSel, self.bgColorDisable)

    def SetTitleWidth(self, width):
        """set the title width"""
        self.titleWidth = width

    def GetTitleWidth(self):
        """return the width"""
        return self.titleWidth

    def Refresh(self):
        """notify the parent to redraw the property"""
        self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def DrawItem(self, dc):
        """draw the property"""
        if not self.GetVisible():
            return

        dc.SetBackgroundMode(wx.TRANSPARENT)
        if self.enable:
            dc.SetTextForeground(wx.BLACK)
        else:
            dc.SetTextForeground(wx.LIGHT_GREY)

        rc = self.GetClientRect()
        self.PrepareDrawRect()

        # draw background
        crBg = self.GetParent().GetBackgroundColour()
        pen = wx.Pen(wx.BLACK, 1, wx.TRANSPARENT)
        dc.SetPen(pen)
        brush = wx.Brush(crBg)
        dc.SetBrush(brush)
        dc.DrawRectangle(rc.x, rc.y, rc.width, rc.height)
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.left, rc.bottom, rc.right, rc.bottom)
        dc.DrawLine(rc.left, rc.top, rc.left, rc.bottom)
        dc.DrawLine(rc.right-1, rc.top, rc.right-1, rc.bottom)
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)))
        dc.DrawLine(rc.left, rc.top, rc.right, rc.top)
        dc.DrawLine(rc.left+1, rc.top, rc.left+1, rc.bottom)
        dc.DrawLine(rc.right, rc.top, rc.right, rc.bottom)

        # draw select rectangle
        if self.activated:
            pen.SetColour(wx.BLACK)
            pen.SetStyle(wx.DOT)

            dc.SetPen(pen)
            brush.SetStyle(wx.TRANSPARENT)
            dc.SetBrush(brush)
            dc.DrawRectangle(rc.x, rc.y, rc.width, rc.height)

        c2p.SetClippingRect(dc, self.titleRectColumn)

        if self.HasChildren():
            if type(self).imgExpColp.GetImageCount() == 2:
                (imagex, imagey) = type(self).imgExpColp.GetSize(0)
                x = self.expanderRect.x+(self.expanderRect.width-imagex)/2
                y = self.expanderRect.y+(self.expanderRect.height-imagey)/2+1
                idx = 0
                if not self.expanded:
                    idx = 1
                type(self).imgExpColp.Draw(idx, dc, x, y, wx.IMAGELIST_DRAW_TRANSPARENT)

        # draw gripper
        if self.gripperColor:
            pen.SetColour(self.gripperColor)#(178,34,34))
            pen.SetStyle(wx.TRANSPARENT)

            dc.SetPen(pen)
            brush.SetColour(self.gripperColor)#(178,34,34))
            brush.SetStyle(wx.SOLID)
            dc.SetBrush(brush)
            rcSim = self.gripperRect
            dc.DrawRectangle(rcSim.x, rcSim.y+1, 3, rcSim.height-1)

        # draw title
        if self.italic:
            dc.SetFont(wx.ITALIC_FONT)
        else:
            dc.SetFont(wx.NORMAL_FONT)

        (w, h) = dc.GetTextExtent(self.label)

        dc.DrawText(self.label, self.titleRect.GetX(), self.titleRect.top+
                    (self.titleRect.height - h)/2)
        self.showLabelTips = (self.titleRect.x+w) > self.titleRectColumn.right
        dc.DestroyClippingRegion()

        # separator does not have radio button, splitter bar and value sections
        if self.GetSeparator():
            return

        # draw radio button
        if self.GetShowRadio():
            state = 0
            if not self.IsEnabled():
                state = 1
            elif self.IsRadioChecked():
                state = 2
                if self.GetRadioFocused():
                    state = 3
            else:
                self.SetRadioFocused(False)

            if type(self).imgRadio.GetImageCount() == 4:
                (imagex, imagey) = type(self).imgRadio.GetSize(0)
                x = self.radioRect.x+(self.radioRect.width-imagex)/2
                y = self.radioRect.y+(self.radioRect.height-imagey)/2+1
                type(self).imgRadio.Draw(state, dc, x, y,
                                         wx.IMAGELIST_DRAW_TRANSPARENT)

        # draw splitter
        rcSplitter = self.splitterRect
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.left, rc.top, rc.left, rc.bottom)
        dc.DrawLine(rcSplitter.left, rcSplitter.top, rcSplitter.left, rcSplitter.bottom)
        dc.DrawLine(rcSplitter.right-1, rcSplitter.top, rcSplitter.right-1, rcSplitter.bottom)
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)))
        dc.DrawLine(rc.left+1, rc.top, rc.left+1, rc.bottom)
        dc.DrawLine(rcSplitter.left+1, rcSplitter.top, rcSplitter.left+1, rcSplitter.bottom)
        dc.DrawLine(rcSplitter.right, rcSplitter.top, rcSplitter.right, rcSplitter.bottom)

        # draw value
        self.showValueTips = False
        if self.controlWin is None:
            crbg = self.bgColor
            crtxt = wx.BLACK
            if not self.enable or self.GetReadOnly():
                crtxt = self.textColorDisable
                crbg = self.bgColorDisable
            elif self.activated:
                crtxt = self.textColorSel
                crbg = self.bgColorSel
            else:
                crtxt = self.textColor
                crbg = self.bgColor

            dc.SetPen(wx.Pen(crtxt, 1, wx.TRANSPARENT))
            dc.SetBrush(wx.Brush(crbg))

            dc.DrawRectangle(self.valueRect.x, self.valueRect.y,
                             self.valueRect.width, self.valueRect.height)

            dc.SetTextForeground(crtxt)

            value = str(self.GetValue())
            if self.description != "":
                value += " (" + self.description + ")"
            (w, h) = dc.GetTextExtent(value)
            c2p.SetClippingRect(dc, self.valueRect)
            dc.DrawText(value, self.valueRect.GetX() + 1,
                        self.valueRect.top + (self.valueRect.height - h)/2)
            self.showValueTips = self.valueRect.width < w
            dc.DestroyClippingRegion()

    def PrepareDrawRect(self):
        """calculate the rect for each section"""
        MARGIN_X = type(self).MARGIN_X
        rc = self.GetClientRect()
        self.gripperRect = wx.Rect(*rc)
        self.gripperRect.x = self.gripperRect.x + MARGIN_X+self.indent*20
        self.gripperRect.SetWidth(6)

        self.expanderRect = wx.Rect(*rc)
        self.expanderRect.x = self.gripperRect.right + MARGIN_X
        self.expanderRect.SetWidth(self.radioWidth)

        self.radioRect = wx.Rect(*rc)
        self.radioRect.x = self.expanderRect.right + MARGIN_X
        self.radioRect.SetWidth(self.radioWidth)

        self.titleRect = wx.Rect(*rc)
        self.titleRect.SetLeft(self.radioRect.right + MARGIN_X*2)

        self.titleRect.SetWidth(self.titleWidth)

        self.splitterRect = wx.Rect(*rc)
        self.splitterRect.SetLeft(self.titleWidth + MARGIN_X)
        self.splitterRect.SetWidth(8)

        self.titleRectColumn = wx.Rect(*rc)
        self.titleRectColumn.SetLeft(self.gripperRect.left)
        self.titleRectColumn.SetRight(self.titleWidth)

        self.valueRect = wx.Rect(*rc)
        self.valueRect.SetX(self.splitterRect.right)
        self.valueRect.SetWidth(rc.right-self.splitterRect.right)
        self.valueRect.Deflate(1, 1)

    def HitTest(self, pt):
        """find the mouse position relative to the property"""
        # bottom edge
        rc = wx.Rect(*self.clientRect)
        rc.SetTop(rc.bottom-2)
        if rc.Contains(pt):
            return self.PROP_HIT_EDGE_BOTTOM
        # top edge
        rc = wx.Rect(*self.clientRect)
        rc.SetBottom(rc.top+2)
        if rc.Contains(pt):
            return self.PROP_HIT_EDGE_TOP

        if self.titleRectColumn.Contains(pt):
            if self.expanderRect.Contains(pt):
                # expand/collapse icon
                return self.PROP_HIT_EXPAND
            elif self.radioRect.Contains(pt):
                # radio icon
                return self.PROP_HIT_RADIO
            elif self.titleRect.Contains(pt):
                # elsewhere on the title
                return self.PROP_HIT_TITLE
        elif self.splitterRect.Contains(pt):
            # gripper
            return self.PROP_HIT_SPLITTER
        elif self.valueRect.Contains(pt):
            # value
            return self.PROP_HIT_VALUE
        return self.PROP_HIT_NONE

    def OnMouseDown(self, pt):
        ht = self.HitTest(pt)
        # click on the expand buttons? expand it?
        if self.HasChildren() and ht == self.PROP_HIT_EXPAND:
            self.SetExpand(not self.expanded)
        elif ht == self.PROP_HIT_SPLITTER or ht == self.PROP_HIT_NONE:
            self.UpdatePropValue()
            self.DestroyControl()
        elif not self.GetReadOnly() and ht == self.PROP_HIT_VALUE:
            # show the control when in PROP_DISP_NORMAL mode
            self.CreateControl()
        return ht

    def OnMouseUp(self, pt):
        ht = self.HitTest(pt)
        if self.IsEnabled():
            # click on the radio buttons? change the state
            if self.GetShowRadio() and ht == self.PROP_HIT_RADIO:
                checked = self.IsRadioChecked()
                self.SetRadioChecked(not checked)
        return ht

    def OnMouseDoubleClick(self, pt):
        ht = self.HitTest(pt)
        if self.IsEnabled():
            if not self.GetReadOnly():
                # show the control when in PROP_DISP_NORMAL mode
                if ht == self.PROP_HIT_VALUE:
                    self.CreateControl()
            if ht == self.PROP_HIT_EXPAND:
                self.SetExpand(not self.expanded)
            self.SendPropEvent(wxEVT_BSM_PROP_DOUBLE_CLICK)
        return ht

    def OnMouseRightClick(self, pt):
        ht = self.HitTest(pt)
        if self.IsEnabled():
            #destory the control when the mouse moves out
            if ht == self.PROP_HIT_NONE:
                self.UpdatePropValue()
                self.DestroyControl()
            self.SendPropEvent(wxEVT_BSM_PROP_RIGHT_CLICK)
        return ht

    def OnMouseMove(self, pt):
        ht = self.HitTest(pt)
        return ht

    def OnTextEnter(self):
        self.UpdatePropValue()
        self.DestroyControl()
        self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)
    #control maintained by this property
    def CreateControl(self):
        """create the control"""
        if self.controlWin != None or self.GetSeparator():
            return
        sizeCtrl = wx.Size(0, 0)
        self.PreparePropValidator()
        ctrlType = self.ctrlType
        if ctrlType == PROP_CTRL_EDIT:
            txt = wx.TextCtrl(self.parent, self.IDC_BSM_PROP_CONTROL,
                              self.GetValue(), self.valueRect.GetTopLeft(),
                              wx.DefaultSize, wx.TE_PROCESS_ENTER)
            self.controlWin = txt
            sizeCtrl = self.controlWin.GetSize()
        elif ctrlType == PROP_CTRL_COMBO:
            combo = wx.ComboBox(self.parent, wx.ID_ANY, self.GetValue(),
                                self.valueRect.GetTopLeft(), wx.DefaultSize,
                                self.choiceList, wx.TE_PROCESS_ENTER)
            self.controlWin = combo
            sizeCtrl = self.controlWin.GetSize()
        elif ctrlType == [PROP_CTRL_FILE_SEL, PROP_CTRL_FOLDER_SEL]:
            #m_control = new BSMPropEditBtn(m_parent,IDC_BSM_PROP_CONTROL,GetValue())
            #sizeCtrl = m_control->GetSize()
            pass
        elif ctrlType == PROP_CTRL_SLIDER:
            nmax = int(self.valueMax)
            nmin = int(self.valueMin)
            val = int(self.value)

            rcSlider = wx.Rect(*self.valueRect)
            slider = wx.Slider(self.parent, wx.ID_ANY, val, nmin, nmax,
                               rcSlider.GetTopLeft(), wx.DefaultSize,
                               wx.SL_LABELS | wx.SL_AUTOTICKS |
                               wx.SL_HORIZONTAL | wx.SL_TOP)
            self.controlWin = slider
            sizeCtrl = self.controlWin.GetSize()
        elif ctrlType == PROP_CTRL_SPIN:
            nmax = int(self.valueMax)
            nmin = int(self.valueMin)
            val = int(self.value)
            spin = wx.SpinCtrl(self.parent, wx.ID_ANY, "%d"%val,
                               self.valueRect.GetTopLeft(), wx.DefaultSize,
                               wx.SP_ARROW_KEYS, nmin, nmax, val)
            self.controlWin = spin
            sizeCtrl = self.controlWin.GetSize()

        elif ctrlType == PROP_CTRL_CHECK:
            val = int(self.value)
            control = wx.CheckBox(self.parent, wx.ID_ANY, "",
                                  self.valueRect.GetTopLeft(), wx.DefaultSize)
            control.SetValue(val != 0)
            self.controlWin = control
            sizeCtrl = self.controlWin.GetSize()
        elif ctrlType == PROP_CTRL_RADIO:
            radio = wx.RadioBox(self.parent, wx.ID_ANY, "",
                                self.valueRect.GetTopLeft(), wx.DefaultSize,
                                self.choiceList, 5, wx.RA_SPECIFY_COLS)
            try:
                i = self.valueList.index(self.value)
                radio.SetSelection(i)
            except ValueError:
                pass
            self.controlWin = radio
            sizeCtrl = self.controlWin.GetSize()
        elif ctrlType == PROP_CTRL_COLOR:
            color = wx.ColourPickerCtrl(self.parent, wx.ID_ANY, wx.BLACK,
                                        style=wx.CLRP_DEFAULT_STYLE |
                                        wx.CLRP_SHOW_LABEL)
            try:
                color.SetColour(self.value)
            except ValueError:
                pass
            self.controlWin = color
            sizeCtrl = self.controlWin.GetSize()
        if self.controlWin:
            size = sizeCtrl
            sz = self.GetSize()
            self.defaultSize = wx.Size(*self.minimumSize)
            size.x = max(sz.x, self.valueRect.GetX()+size.x+2)
            size.y = max(sz.y, size.y+2)
            if size != sz:
                self.SetMinSize(size)
            self.LayoutControl()
            self.controlWin.SetFocus()
            self.controlWin.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)

    def OnKillFocus(self, evt):
        # destroy the control if it loses focus. Wait until the event has been
        # processed; otherwise, it may crash.
        wx.CallAfter(self.DestroyControl)
        evt.Skip()

    def LayoutControl(self):
        """re-positioning the control"""
        if self.controlWin is None:
            return
        (x, y) = self.parent.GetViewStart()
        rc = wx.Rect(*self.valueRect)
        rc.Offset(wx.Point(-x*5, -y*5))
        if self.ctrlType in [PROP_CTRL_EDIT, PROP_CTRL_COMBO, PROP_CTRL_SPIN,
                             PROP_CTRL_CHECK, PROP_CTRL_RADIO, PROP_CTRL_SLIDER,
                             PROP_CTRL_FILE_SEL, PROP_CTRL_FOLDER_SEL,
                             PROP_CTRL_COLOR]:
            self.controlWin.SetSize(rc.GetSize())
            self.controlWin.Move(rc.GetTopLeft())

    def DestroyControl(self):
        """destroy the value setting control"""
        if self.controlWin:
            self.controlWin.Show(False)
            self.controlWin.Destroy()
            self.controlWin = None
            sz = self.GetSize()
            size = wx.Size(*self.defaultSize)
            if size != sz:
                self.SetMinSize(size)
            return True
        return False

    def PreparePropValidator(self):
        pass

    def UpdatePropValue(self):
        """update the value"""
        if self.controlWin is None:
            return False

        value = self.value
        description = self.description
        self.value = ""
        self.description = ""
        ctrlType = self.ctrlType
        if ctrlType == PROP_CTRL_EDIT:
            self.value = self.controlWin.GetValue()
        elif ctrlType in [PROP_CTRL_FILE_SEL, PROP_CTRL_FOLDER_SEL]:
            self.value = self.controlWin.GetLabel()
        elif ctrlType == PROP_CTRL_COMBO:
            comb = self.controlWin
            self.value = comb.GetValue()
            try:
                sel = self.choiceList.index(self.value)
                assert sel >= 0 and sel < len(self.valueList)
                self.value = self.valueList[sel]
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        elif ctrlType == PROP_CTRL_SLIDER:
            slider = self.controlWin
            self.value = ("%d"%slider.GetValue())
        elif ctrlType == PROP_CTRL_SPIN:
            spin = self.controlWin
            self.value = ("%d"%spin.GetValue())
        elif ctrlType == PROP_CTRL_CHECK:
            check = self.controlWin
            self.value = ("%d"%check.GetValue())
            if check.GetValue():
                self.description = "true"
            else:
                self.description = "false"
        elif ctrlType == PROP_CTRL_RADIO:
            radio = self.controlWin
            sel = radio.GetSelection()
            assert sel >= 0 and sel < len(self.valueList)
            self.value = self.valueList[sel]
            self.description = self.choiceList[sel]
        elif ctrlType == PROP_CTRL_COLOR:
            clr = self.controlWin.GetColour()
            self.value = clr.GetAsString(wx.C2S_HTML_SYNTAX)
            self.SetBGColor(self.value, self.value, self.value)
            clr.SetRGB(clr.GetRGB()^0xffffff)
            t = clr.GetAsString(wx.C2S_HTML_SYNTAX)
            self.SetTextColor(t, t, t)

        if self.SendPropEvent(wxEVT_BSM_PROP_CHANGING):
            self.SendPropEvent(wxEVT_BSM_PROP_CHANGED)
            return True
        else:
            #the parent rejects the operation, restore the original value
            self.SetDescription(description)
            self.SetValue(value)
            return False

    def UpdateDescription(self):
        """update the description"""
        self.description = ""
        ctrlType = self.ctrlType
        if ctrlType == PROP_CTRL_EDIT:
            pass
        elif ctrlType in [PROP_CTRL_FILE_SEL, PROP_CTRL_FOLDER_SEL]:
            pass
        elif ctrlType == PROP_CTRL_COMBO:
            try:
                sel = self.valueList.index(self.value)
                assert sel >= 0 and sel < len(self.choiceList)
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        elif ctrlType == PROP_CTRL_SLIDER:
            pass
        elif ctrlType == PROP_CTRL_SPIN:
            pass
        elif ctrlType == PROP_CTRL_CHECK:
            value = int(self.value)
            if value == 0:
                self.description = "false"
            elif value == 1:
                self.description = "true"
        elif ctrlType == PROP_CTRL_RADIO:
            try:
                sel = self.valueList.index(self.value)
                assert sel >= 0  and sel < len(self.choiceList)
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        return True

    def SendPropEvent(self, event):
        """ send property grid event to parent"""
        eventObject = self.GetParent()
        evt = bsmPropertyEvent(event)
        evt.SetProperty(self)
        evt.SetEventObject(eventObject)
        evtHandler = eventObject.GetEventHandler()

        if evtHandler.ProcessEvent(evt):
            return not evt.IsRefused()
        return False

    def SetClientRect(self, rcClient):
        """set the client rect"""
        if self.clientRect != rcClient:
            self.clientRect = wx.Rect(*rcClient)
            self.PrepareDrawRect()
            self.LayoutControl()

    def SetMinSize(self, size, silent=False):
        """set the min size"""
        if self.minimumSize != size:
            self.minimumSize = wx.Size(*size)
            if not silent:
                self.SendPropEvent(wxEVT_BSM_PROP_RESIZE)

    def GetClientRect(self):
        """return the client rect"""
        return wx.Rect(*self.clientRect)

    def GetSize(self):
        """return the current size"""
        return self.clientRect.GetSize()

    def GetMinSize(self):
        """return the min size"""
        return wx.Size(*self.minimumSize)

    def SetValue(self, value, silent=False):
        """set the value"""
        if self.value != str(value):
            self.DestroyControl()
            self.value = str(value)
            self.UpdateDescription()
            if not silent and self.GetVisible():
                self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)
            return True
        return False

    def SetValueTip(self, tip):
        """set the value tip"""
        self.valueTip = tip

    def SetIndent(self, indent, silent=False):
        """set the indent to a positive integer"""
        if indent < 0:
            indent = 0
        if indent == self.indent:
            return
        self.indent = indent
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_INDENT)

    def SetExpand(self, expand, silent=False):
        """expand/collapse the children"""
        if not self.HasChildren():
            return
        if expand == self.expanded:
            return
        self.expanded = expand
        if silent:
            return
        if self.expanded:
            evt = wxEVT_BSM_PROP_EXPANDED
        else:
            evt = wxEVT_BSM_PROP_COLLAPSED
        if not silent:
            self.SendPropEvent(evt)

    def SetHasChildren(self, haschildren, silent=False):
        """Indicate that the property has children"""
        if haschildren == self.hasChildren:
            return
        self.hasChildren = haschildren
        if silent:
            return
        if self.expanded:
            evt = wxEVT_BSM_PROP_EXPANDED
        else:
            evt = wxEVT_BSM_PROP_COLLAPSED
        self.SendPropEvent(evt)

    def SetActivated(self, activated):
        """activate the property"""
        if activated == self.activated:
            return
        self.activated = activated
        if not activated:
            # destroy the control if the property is inactivated
            self.OnTextEnter()
        else:
            self.SendPropEvent(wxEVT_BSM_PROP_SELECTED)

    def SetReadOnly(self, readonly, silent=False):
        """set the property to readonly"""
        if readonly != self.GetReadOnly():
            self.readOnly = readonly
            if not silent and self.GetVisible():
                self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetRadioFocused(self, focus, silent=False):
        """focus/unfocus the radio button"""
        if focus != self.GetRadioFocused():
            self.radioFocused = focus
            if not silent and self.GetVisible():
                self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetRadioChecked(self, check, silent=False):
        """check/uncheck the radio button"""
        if check != self.IsRadioChecked():
            self.radioChecked = check
            if not self.SendPropEvent(wxEVT_BSM_PROP_CLICK_RADIO):
                self.radioChecked = not check
            if not silent and self.GetVisible():
                self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetGripperColor(self, clr=None):
        self.gripperColor = clr

    def SetTextColor(self, crText=None, crTextSel=None, crTextDisable=None,
                     silent=False):
        """
        set the text colors

        All values are string. If the value is None, the color will reset to
        default.
        """
        self.textColor = crText
        if not self.textColor:
            self.textColor = wx.BLACK.GetAsString(wx.C2S_HTML_SYNTAX)
        self.textColorSel = crTextSel
        if not self.textColorSel:
            self.textColorSel = wx.WHITE.GetAsString(wx.C2S_HTML_SYNTAX)
        self.textColorDisable = crTextDisable
        if not self.textColorDisable:
            self.textColorDisable = wx.LIGHT_GREY.GetAsString(wx.C2S_HTML_SYNTAX)
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetBGColor(self, crBg=None, crBgSel=None, crBgDisable=None,
                   silent=False):
        """
        set the background colors

        All values are string. If the value is None, the color will reset to
        default.
        """
        self.bgColor = crBg
        if not self.bgColor:
            self.bgColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW).GetAsString(wx.C2S_HTML_SYNTAX)
        self.bgColorSel = crBgSel
        if not self.bgColorSel:
            self.bgColorSel = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUHILIGHT).GetAsString(wx.C2S_HTML_SYNTAX)
        self.bgColorDisable = crBgDisable
        if not self.bgColorDisable:
            self.bgColorDisable = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE).GetAsString(wx.C2S_HTML_SYNTAX)
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def GetShowLabelTips(self):
        """return whether label tooltip is allowed"""
        return self.showLabelTips

    def GetShowValueTips(self):
        """return whether value tooltip is allowed"""
        return self.showValueTips

class bsmPropertyEvent(wx.PyCommandEvent):
    def __init__(self, commandType, id=0):
        wx.PyCommandEvent.__init__(self, commandType, id)
        self.prop = None
        self.refused = False

    def GetProperty(self):
        """return the attached bsmProperty"""
        return self.prop

    def SetProperty(self, prop):
        """attach the bsmProperty instance"""
        if isinstance(prop, bsmProperty):
            self.prop = prop

    def Refused(self, refused):
        """refuse the event"""
        self.refused = refused

    def IsRefused(self):
        """return whether the event is refused"""
        return self.refused

