import wx
import copy
from bsmpropxpm import *

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

    PROP_CTRL_DEFAULT  = 0
    PROP_CTRL_NONE     = 1
    PROP_CTRL_EDIT     = 2
    PROP_CTRL_COMBO    = 3
    PROP_CTRL_FILE_SEL = 4
    PROP_CTRL_FOLDER_SEL = 5 
    PROP_CTRL_SLIDER = 6 
    PROP_CTRL_SPIN   = 7
    PROP_CTRL_CHECK  = 8
    PROP_CTRL_RADIO  = 9
    PROP_CTRO_COLOR = 10
    imgRadio = None
    imgExpColp = None
    def __init__(self, parent, name, label, value):
        self.parent = parent
        self.name = name
        self.label = label
        self.value = value
        self.description = ""
        self.valueMax = "100"
        self.valueMin = "0"
        self.radioWidth = 15
        self.nameWidth = 80
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
        self.ctrlType = type(self).PROP_CTRL_EDIT
        self.controlWin = None
        self.parentItem = -1
        self.choiceList = []
        self.valueList = []
        self.SetTextColor(silent = True)
        self.SetBGColor(silent = True)
        self.minimumSize = wx.Size(200,25)
        self.defaultSize = wx.Size(200,25)
        self.clientRect = wx.Rect(0,0,0,0)
        self.expanderRect = wx.Rect(0,0,0,0)
        self.radioRect = wx.Rect(0,0,0,0)
        self.splitterRect = wx.Rect(0,0,0,0)
        self.titleRect = wx.Rect(0,0,0,0)
        self.titleRectColumn = wx.Rect(0,0,0,0)
        self.valueRect = wx.Rect(0,0,0,0)
        self.showLabelTips = True
        self.showValueTips = True
        self.separator = False
        #self.m_validate = wx.FILTER_NONE
        #self.m_nValidateType(VALIDATE_NONE)
        if type(self).imgRadio is None or type(self).imgExpColp is None:
            type(self).imgRadio = wx.ImageList(16,16,True,4)
            type(self).imgExpColp = wx.ImageList(12,12,True,2)
            type(self).imgRadio.Add(wx.BitmapFromXPMData(radio_xpm))
            type(self).imgExpColp.Add(wx.BitmapFromXPMData(tree_xpm))
    
    def duplicate(self):
        # copy the object, copy.deepcopy does not work since the object 
        # contains pointer to wx objects
        p = bsmProperty(self.parent, self.name, self.label, self.value)
        p.description = self.description
        p.valueMax = self.valueMax
        p.valueMin = self.valueMin
        p.radioWidth = self.radioWidth
        p.nameWidth = self.nameWidth
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
        p.parentItem = self.parentItem
        p.choiceList = self.choiceList[:]
        p.valueList = self.valueList[:]
        p.SetTextColor(self.textColor, self.textColorSel, self.textColorDisable, True)
        p.SetBGColor(self.bgColor, self.bgColorSel, self.bgColorDisable, True)
        p.showLabelTips = self.showLabelTips
        p.showValueTips = self.showValueTips
        p.separator = self.separator
        return p
   
    def SetParent(self, parent):
        self.parent = parent
    
    def GetParent(self):
        return self.parent
    
    def SetSeparator(self, sep, silent = False):
        self.separator = sep
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def GetSeparator(self):
        return self.separator

    def SetBPCondition(self, cond):
        self.bpCondition = cond
    
    def GetBPCondition(self):
        return self.bpCondition
    
    def SetControlStyle(self, uStyle):
        if uStyle != type(self).PROP_CTRL_DEFAULT:
            self.ctrlType = uStyle
    
    def SetChoice(self, choice, value):
        self.valueList = []
        self.choiceList = []
        self.choiceList = choice
        if len(choice) == len(value):
            self.valueList = value
        else:
            self.valueList = choice

    def AddPropChoice(self, choice, value):
        self.valueList.append(value)
        self.choiceList.append(choice)
    
    def SetEnable(self, bEnable):
        self.enable = bEnable

    def SetName(self, name, silent=False):
        self.name = name
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetLabel(self, label, silent=False):
        self.label = label
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetDescription(self, description, silent=False):
        self.description = description
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetItalicText(self, bItalic, silent=False):
        self.italic = bItalic
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetVisible(self, bVisible, silent=False):
        self.visible = bVisible
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetParentItem(self, nParent):
        self.parentItem = nParent

    def SetRange(self, maxVal, minVal):
        self.valueMax = int(maxVal)
        self.valueMin = int(minVal)
    
    def SetShowRadio(self, bShow, silent=True):
        self.showRadio = bShow
        if not silent and self.GetVisible():
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)
    
    def GetCtrlStyle(self):
        return self.ctrlType

    def GetChoice(self):
        return (self.choiceList, self.valueList)

    def GetChoiceString(self, delims):
        return (delims.join(self.choiceList), delims.join(self.valueList))

    def IsPropEnable(self):
        return self.enable

    def GetName(self):
        return self.name

    def GetLabel(self):
        return self.label

    def GetValue(self):
        return self.value

    def GetDescription(self):
        return self.description

    def GetIndent(self):
        return self.indent

    def IsPropExpand(self):
        return self.expanded

    def IsPropHasChildren(self):
        return self.hasChildren

    def IsPropRadioChecked(self):
        return self.radioChecked

    def IsPropItalicText(self):
        return self.italic  
    def GetControlStyle(self):
        return self.ctrlType

    def GetActivated(self):
        return self.activated

    def GetVisible(self):
        return self.visible

    def GetParentItem(self):
        return self.parentItem

    def GetRange(self):
        return (self.valueMax, self.valueMin)
    
    def GetReadOnly(self):
        return self.readOnly

    def GetRadioFocused(self):
        return self.radioFocused

    def GetShowRadio(self):
        return self.showRadio
    
    def GetTextColor(self):
        return (self.textColor, self.textColorSel, self.textColorDisable)

    def GetBGColor(self):
        return (self.bgColor, self.bgColorSel, self.bgColorDisable)

    def SetNameWidth(self, width):
        self.nameWidth = width

    def GetNameWidth(self): 
        return self.nameWidth

    def DrawItem(self, dc):
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
        crBg  = self.GetParent().GetBackgroundColour()
        pen = wx.Pen(wx.BLACK, 1, wx.TRANSPARENT)
        dc.SetPen(pen)
        brush = wx.Brush(crBg)
        dc.SetBrush(brush)
        dc.DrawRectangle(rc.x,rc.y, rc.width, rc.height)
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.GetLeft(),rc.GetBottom(), rc.GetRight(),rc.GetBottom())
        dc.DrawLine(rc.GetLeft(),rc.GetTop(), rc.GetLeft(),rc.GetBottom())
        dc.DrawLine(rc.GetRight()-1,rc.GetTop(), rc.GetRight()-1,rc.GetBottom())
        dc.SetPen( wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)))
        dc.DrawLine(rc.GetLeft(),rc.GetTop(),rc.GetRight(),rc.GetTop())
        dc.DrawLine(rc.GetLeft()+1,rc.GetTop(), rc.GetLeft()+1,rc.GetBottom())
        dc.DrawLine(rc.GetRight(),rc.GetTop(), rc.GetRight(),rc.GetBottom())
        
        # draw select rectangle
        if self.activated:
            pen.SetColour(wx.BLACK)
            pen.SetStyle(wx.DOT)

            dc.SetPen(pen)
            brush.SetStyle(wx.TRANSPARENT)
            dc.SetBrush(brush)
            dc.DrawRectangle(rc.x, rc.y, rc.width, rc.height)
        

        dc.SetClippingRect(self.titleRectColumn)
        if self.IsPropHasChildren():        
            if type(self).imgExpColp.GetImageCount() == 2:
                (imagex, imagey) = type(self).imgExpColp.GetSize(0)
                x = self.expanderRect.x+(self.expanderRect.width-imagex)/2
                y = self.expanderRect.y+(self.expanderRect.height-imagey)/2+1
                idx = 0
                if not self.expanded:
                    idx = 1
                type(self).imgExpColp.Draw(idx, dc,x,y,wx.IMAGELIST_DRAW_TRANSPARENT)
        
        # draw title
        if self.italic:
            dc.SetFont(wx.ITALIC_FONT)
        else:
            dc.SetFont(wx.NORMAL_FONT)

        (w, h) = dc.GetTextExtent(self.label)

        dc.DrawText(self.label, self.titleRect.GetX(), self.titleRect.GetTop()+
            (self.titleRect.height - h)/2)
        self.showLabelTips = (self.titleRect.x+w)>self.titleRectColumn.GetRight()
        dc.DestroyClippingRegion()

        # separator does not have radio button, splitter bar and value sections
        if self.GetSeparator(): return
        
        # draw radio button
        if self.GetShowRadio():
            nRadioState = 0
            if not self.enable:
                nRadioState = 1
            elif self.IsPropRadioChecked():
                nRadioState = 2
                if self.GetRadioFocused():
                    nRadioState = 3
            else:
                self.SetRadioFocused(False)

            if type(self).imgRadio.GetImageCount()==4:
                (imagex, imagey) = type(self).imgRadio.GetSize(0)
                x = self.radioRect.x+(self.radioRect.width-imagex)/2
                y = self.radioRect.y+(self.radioRect.height-imagey)/2+1
                type(self).imgRadio.Draw(nRadioState,dc,x,y,wx.IMAGELIST_DRAW_TRANSPARENT)
        
        # draw splitter
        rcSplitter = self.splitterRect
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.GetLeft(),rc.GetTop(), rc.GetLeft(),rc.GetBottom())
        dc.DrawLine(rcSplitter.GetLeft(),rcSplitter.GetTop(), rcSplitter.GetLeft(),rcSplitter.GetBottom())
        dc.DrawLine(rcSplitter.GetRight()-1,rcSplitter.GetTop(), rcSplitter.GetRight()-1,rcSplitter.GetBottom())
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)))
        dc.DrawLine(rc.GetLeft()+1,rc.GetTop(), rc.GetLeft()+1,rc.GetBottom())
        dc.DrawLine(rcSplitter.GetLeft()+1,rcSplitter.GetTop(), rcSplitter.GetLeft()+1,rcSplitter.GetBottom())
        dc.DrawLine(rcSplitter.GetRight(),rcSplitter.GetTop(), rcSplitter.GetRight(),rcSplitter.GetBottom())

        # draw value
        self.showValueTips = False
        if self.controlWin==None:
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

            dc.SetPen(wx.Pen(crtxt,1,wx.TRANSPARENT ))
            dc.SetBrush(wx.Brush(crbg))

            dc.DrawRectangle(self.valueRect.x, self.valueRect.y, self.valueRect.width, self.valueRect.height)

            dc.SetTextForeground(crtxt)
           
            strValue = self.GetValue()
            if self.description != "":
                strValue = strValue + " (" + self.description + ")"
            (w, h) = dc.GetTextExtent(strValue)
            dc.SetClippingRect(self.valueRect)
            dc.DrawText(strValue, self.valueRect.GetX()+1,
                self.valueRect.GetTop()+(self.valueRect.height - h)/2)
            self.showValueTips = self.valueRect.width<w
            dc.DestroyClippingRegion()

    def PrepareDrawRect(self):
        MARGIN_X = type(self).MARGIN_X
        rc = self.GetClientRect()
        self.expanderRect = wx.Rect(*rc)
        self.expanderRect.x = self.expanderRect.x + MARGIN_X+self.indent*20
        self.expanderRect.SetWidth(self.radioWidth)

        self.radioRect = wx.Rect(*rc)
        self.radioRect.x = self.expanderRect.GetRight() + MARGIN_X
        self.radioRect.SetWidth(self.radioWidth)

        self.titleRect = wx.Rect(*rc)
        self.titleRect.SetLeft (self.radioRect.GetRight() + MARGIN_X)
        
        self.titleRect.SetWidth(self.nameWidth)

        self.splitterRect = wx.Rect(*rc)
        self.splitterRect.SetLeft(self.nameWidth + MARGIN_X)
        self.splitterRect.SetWidth(8)

        self.titleRectColumn = wx.Rect(*rc)
        self.titleRectColumn.SetLeft(self.expanderRect.GetLeft())
        self.titleRectColumn.SetRight(self.nameWidth)
        
        self.valueRect = wx.Rect(*rc)
        self.valueRect.SetX(self.splitterRect.GetRight())
        self.valueRect.SetWidth(rc.GetRight()-self.splitterRect.GetRight())
        self.valueRect.Deflate(1,1)
  
    # mouse actions, called by the parent grid
    def PropHitTest(self, pt):
        rc = wx.Rect(*self.clientRect)
        rc.SetTop(rc.GetBottom()-2)
        if rc.Contains(pt):
            return self.PROP_HIT_EDGE_BOTTOM
        rc = wx.Rect(*self.clientRect)
        rc.SetBottom(rc.GetTop()+2)
        if rc.Contains(pt):
            return self.PROP_HIT_EDGE_TOP

        if self.titleRectColumn.Contains(pt):
            if self.expanderRect.Contains(pt):
                return self.PROP_HIT_EXPAND
            elif self.radioRect.Contains(pt):
                return self.PROP_HIT_RADIO
            elif self.titleRect.Contains(pt):
                return self.PROP_HIT_TITLE
        elif self.splitterRect.Contains(pt):
            return self.PROP_HIT_SPLITTER
        elif self.valueRect.Contains(pt):
            return self.PROP_HIT_VALUE
        
        return self.PROP_HIT_NONE

    def OnMouseDown(self, pt):
        ht = self.PropHitTest(pt)
        # click on the expand buttons? expand it?
        if self.IsPropHasChildren() and ht == self.PROP_HIT_EXPAND:
            self.SetExpand(not self.expanded)
        elif ht == self.PROP_HIT_SPLITTER or ht == self.PROP_HIT_NONE:
            self.UpdatePropValue()
            self.DestroyControl()
        elif not self.GetReadOnly() and ht == self.PROP_HIT_VALUE:
            # show the control when in PROP_DISP_NORMAL mode
            self.CreateControl()
        return ht

    def OnMouseUp(self, pt ):
        ht = self.PropHitTest(pt)
        if self.IsPropEnable():
            # click on the radio buttons? change the state
            if self.GetShowRadio() and ht == self.PROP_HIT_RADIO:
                wasChecked = self.IsPropRadioChecked()
                self.SetRadioChecked(not wasChecked)
                if not self.SendPropEvent(wxEVT_BSM_PROP_CLICK_RADIO):
                    self.SetRadioChecked(wasChecked)
        return ht

    def OnMouseDoubleClick(self, pt):
        ht = self.PropHitTest(pt)
        if self.IsPropEnable():
            if not self.GetReadOnly():
                # show the control when in PROP_DISP_NORMAL mode
                if ht == self.PROP_HIT_VALUE:
                    self.CreateControl()
            if ht == self.PROP_HIT_EXPAND:
                self.SetExpand(not self.expanded)
            self.SendPropEvent(wxEVT_BSM_PROP_DOUBLE_CLICK)
        return ht

    def OnMouseRightClick(self, pt):
        ht = self.PropHitTest(pt)
        if self.IsPropEnable():
            #destory the control when the mouse moves out
            if ht == self.PROP_HIT_NONE:
                self.UpdatePropValue()
                self.DestroyControl()
            self.SendPropEvent(wxEVT_BSM_PROP_RIGHT_CLICK)
        return ht

    def OnMouseMove(self, pt):
        ht = self.PropHitTest(pt)
        return ht

    def OnTextEnter(self):
        self.UpdatePropValue()
        self.DestroyControl()
        return 1

    #control maintained by this property
    def CreateControl(self):
        assert self.controlWin==None
        if self.controlWin!=None or self.GetSeparator():
            return
        sizeCtrl = wx.Size(0,0)
        self.PreparePropValidator()
        uCtrlType = self.ctrlType
        if uCtrlType == type(self).PROP_CTRL_EDIT:
            self.controlWin = wx.TextCtrl(self.parent,self.IDC_BSM_PROP_CONTROL, 
                        self.GetValue(), self.valueRect.GetTopLeft(),
                        wx.DefaultSize,wx.TE_PROCESS_ENTER)
            sizeCtrl = self.controlWin.GetSize()
        elif uCtrlType == type(self).PROP_CTRL_COMBO:
            self.controlWin = wx.ComboBox(self.parent, wx.ID_ANY, 
                        self.GetValue(), self.valueRect.GetTopLeft(), 
                        wx.DefaultSize, self.choiceList,wx.TE_PROCESS_ENTER)
            sizeCtrl = self.controlWin.GetSize()
        elif uCtrlType == type(self).PROP_CTRL_FILE_SEL or \
             uCtrlType == type(self).PROP_CTRL_FOLDER_SEL:
            #m_control = new BSMPropEditBtn(m_parent,IDC_BSM_PROP_CONTROL,GetValue())
            #sizeCtrl = m_control->GetSize()
            pass
        elif uCtrlType == type(self).PROP_CTRL_SLIDER:
            nmax = int(self.valueMax)
            nmin = int(self.valueMin)
            val = int(self.value)
            
            rcSlider = wx.Rect(*self.valueRect)
            self.controlWin = wx.Slider(self.parent, wx.ID_ANY, val , 
                    nmin, nmax, rcSlider.GetTopLeft(), wx.DefaultSize,
                    wx.SL_LABELS|wx.SL_AUTOTICKS|wx.SL_HORIZONTAL|wx.SL_TOP)

            sizeCtrl = self.controlWin.GetSize()
        elif uCtrlType == type(self).PROP_CTRL_SPIN:
            nmax = int(self.valueMax)
            nmin = int(self.valueMin)
            val = int(self.value)
            self.controlWin = wx.SpinCtrl(self.parent, wx.ID_ANY, "%d"%val,
                    self.valueRect.GetTopLeft(), wx.DefaultSize,
                    wx.SP_ARROW_KEYS, nmin, nmax, val)
            sizeCtrl = self.controlWin.GetSize()
        
        elif uCtrlType == type(self).PROP_CTRL_CHECK:
            val = int(self.value)
            control = wx.CheckBox(self.parent, wx.ID_ANY, "",
                    self.valueRect.GetTopLeft(), wx.DefaultSize)
            control.SetValue(val!=0)
            self.controlWin = control
            sizeCtrl = self.controlWin.GetSize()
        elif uCtrlType == type(self).PROP_CTRL_RADIO:
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
        elif uCtrlType == type(self).PROP_CTRO_COLOR:
            color = wx.ColourPickerCtrl(self.parent, wx.ID_ANY, wx.BLACK, 
                    style = wx.CLRP_DEFAULT_STYLE|wx.CLRP_SHOW_LABEL)
            try:
                color.SetColour(self.value)
            except ValueError:
                pass
            self.controlWin = color
            sizeCtrl = self.controlWin.GetSize()
        if self.controlWin:
            size = sizeCtrl
            sz   = self.GetSize()
            self.defaultSize = wx.Size(*self.minimumSize)
            size.x = max(sz.x, self.valueRect.GetX()+size.x+2)
            size.y = max(sz.y,size.y+2)
            if size != sz:
                self.SetMinSize(size)
            self.LayoutControl()
            self.controlWin.SetFocus()

    def LayoutControl(self):
        if self.controlWin == None:
            return
        (x,y) = self.parent.GetViewStart()
        rc = wx.Rect(*self.valueRect)
        rc.Offset(wx.Point(-x*5,-y*5))
        if self.ctrlType in [type(self).PROP_CTRL_EDIT, type(self).PROP_CTRL_COMBO, type(self).PROP_CTRL_SPIN,
                                type(self).PROP_CTRL_CHECK, type(self).PROP_CTRL_RADIO, type(self).PROP_CTRL_SLIDER,
                                type(self).PROP_CTRL_FILE_SEL, type(self).PROP_CTRL_FOLDER_SEL, 
                                type(self).PROP_CTRO_COLOR]:
            self.controlWin.SetSize(rc.GetSize())
            self.controlWin.Move(rc.GetTopLeft())

    def DestroyControl(self):
        bRtn = False
        if self.controlWin:
            self.controlWin.Destroy()
            self.controlWin = None
            bRtn = True

            sz = self.GetSize()
            size = self.GetParent().GetClientSize()
            size.y = self.defaultSize.y
            size.x = self.defaultSize.x
            if size!=sz:
                self.SetMinSize(size)
        return bRtn

    def PreparePropValidator(self):
        pass

    def UpdatePropValue(self):
        if self.controlWin == None:
            return False
        
        bRtn = False
        strValue       = self.value
        strDescription = self.description
        self.value = ""
        self.description = ""
        uCtrlType = self.ctrlType
        if uCtrlType == type(self).PROP_CTRL_EDIT:
            self.value = self.controlWin.GetValue()
        elif uCtrlType == type(self).PROP_CTRL_FILE_SEL or \
            uCtrlType == type(self).PROP_CTRL_FOLDER_SEL:
            self.value = self.controlWin.GetLabel()
        elif uCtrlType == type(self).PROP_CTRL_COMBO:
            comb = self.controlWin
            self.value = comb.GetValue()
            try:
                sel = self.choiceList.index(self.value)
                assert (sel >= 0 and sel < len(self.valueList))
                self.value = self.valueList[sel]
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        elif uCtrlType == type(self).PROP_CTRL_SLIDER:
            slider = self.controlWin
            self.value = ("%d"%slider.GetValue())
        elif uCtrlType == type(self).PROP_CTRL_SPIN:
            spin = self.controlWin
            self.value = ("%d"%spin.GetValue())
        elif uCtrlType == type(self).PROP_CTRL_CHECK:
            check = self.controlWin
            self.value = ("%d"%check.GetValue())
            if check.GetValue():
                self.description = "true"
            else:
                 self.description = "false"
        elif uCtrlType == type(self).PROP_CTRL_RADIO:
            size = self.controlWin.GetMinSize()
            radio = self.controlWin
            sel = radio.GetSelection()
            assert (sel>=0 and sel< len(self.valueList))
            self.value = self.valueList[sel]
            self.description = self.choiceList[sel]
        elif uCtrlType == type(self).PROP_CTRO_COLOR:
            clr = self.controlWin.GetColour()
            self.value = clr.GetAsString(wx.C2S_HTML_SYNTAX)
            self.SetBGColor(self.value, self.value, self.value)
            clr.SetRGB(clr.GetRGB()^0xffffff)
            t = clr.GetAsString(wx.C2S_HTML_SYNTAX)
            self.SetTextColor(t, t, t)
        bRtn = True
        if self.SendPropEvent(wxEVT_BSM_PROP_CHANGING):
            self.SendPropEvent(wxEVT_BSM_PROP_CHANGED)
        else:
            self.value = strValue
            self.description = strDescription

        return bRtn

    def UpdateDescription(self):
        strDescription = self.description
        self.description = ""
        uCtrlType = self.ctrlType
        if uCtrlType == type(self).PROP_CTRL_EDIT:        
            pass
        elif uCtrlType == type(self).PROP_CTRL_FILE_SEL or \
             uCtrlType == type(self).PROP_CTRL_FOLDER_SEL:
            pass
        elif uCtrlType == type(self).PROP_CTRL_COMBO:
            try:
                sel = self.valueList.index(self.value)
                assert(sel>=0 and sel<len(self.choiceList))
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        elif uCtrlType == type(self).PROP_CTRL_SLIDER:
            pass
        elif uCtrlType == type(self).PROP_CTRL_SPIN:
            pass
        elif uCtrlType == type(self).PROP_CTRL_CHECK:
            value = int(self.value)
            if value == 0:
                self.description = "false"
            elif value == 1:
                self.description = "true"
        elif uCtrlType == type(self).PROP_CTRL_RADIO:
            try:
                sel = self.valueList.index(self.value)
                assert (sel>=0  and sel<len(self.choiceList))
                self.description = self.choiceList[sel]
            except ValueError:
                pass
        return True

    #send the event to the parent grid
    def SendPropEvent(self, eventType):
        # Send property grid event of specific type and with specific property
        eventObject = self.GetParent()
        evt = bsmPropertyEvent(eventType)
        evt.SetProperty(self)
        evt.SetEventObject(eventObject)
        evtHandler = eventObject.GetEventHandler()

        bRtn = evtHandler.ProcessEvent(evt)
        if bRtn:
            bRtn = not evt.IsRefused()
        return bRtn

    #the parent
    def GetParent(self):
        return self.parent

    #size 
    def SetClientRect(self, rcClient):
        if self.clientRect!=rcClient:
            self.clientRect = wx.Rect(*rcClient)
            self.PrepareDrawRect()
            self.LayoutControl()

    def SetMinSize(self, size, silent = False):
        if self.minimumSize!=size:
            self.minimumSize = wx.Size(*size)
            if not silent:
                self.SendPropEvent(wxEVT_BSM_PROP_RESIZE)
    
    def GetClientRect(self):
        return wx.Rect(*self.clientRect)
    
    def GetSize(self):
        return self.clientRect.GetSize()
    
    def GetMinSize(self):
        return wx.Size(*self.minimumSize)
    
    #overide setting functions
    def SetValue(self, value, silent = False):
        if self.value != value:
            self.value = value
            self.UpdateDescription()
            if not silent and self.GetVisible():
                self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)
            return True
        return False

    def SetIndent(self, nIndent, silent = False):
        if nIndent<0:
            nIndent=0
        if nIndent == self.indent:
            return
        if nIndent>=0:
            self.indent = nIndent
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_INDENT)

    def SetExpand(self, bExpand, silent = False):
        if bExpand == self.expanded:
            return
        self.expanded = bExpand
        if silent: return
        if self.expanded:
            evt = wxEVT_BSM_PROP_EXPANDED
        else:
            evt = wxEVT_BSM_PROP_COLLAPSED
        if not silent:
            self.SendPropEvent(evt)

    def SetHasChildren(self, bHasChildren, silent = False):
        if bHasChildren == self.hasChildren:
            return
        self.hasChildren = bHasChildren
        if silent: return
        if self.expanded:
            evt = wxEVT_BSM_PROP_EXPANDED
        else:
            evt = wxEVT_BSM_PROP_COLLAPSED
        self.SendPropEvent(evt)

    def SetActivated(self, bActivated):
        if bActivated == self.activated:
            return
        self.activated = bActivated
        if not bActivated:
            self.OnTextEnter()
        else:
            self.SendPropEvent(wxEVT_BSM_PROP_SELECTED)

    def SetReadOnly(self, bReadOnly, silent = False):
        if bReadOnly!=self.GetReadOnly():
            self.readOnly = bReadOnly
            if silent: return
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetRadioFocused(self, bFocus, silent = False):
        if bFocus!=self.GetRadioFocused():
            self.radioFocused = bFocus
            if silent: return
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetRadioChecked(self, bCheck, silent = False):
        if bCheck!=self.IsPropRadioChecked():
            self.radioChecked = bCheck
            if silent: return
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetTextColor(self, crText = None, crTextSel = None, 
                                         crTextDisable = None, silent = False):
        self.textColor = crText
        if not self.textColor:
            self.textColor = wx.BLACK.GetAsString(wx.C2S_HTML_SYNTAX)
        self.textColorSel = crTextSel
        if not self.textColorSel:
            self.textColorSel = wx.WHITE.GetAsString(wx.C2S_HTML_SYNTAX)
        self.textColorDisable = crTextDisable
        if not self.textColorDisable:
            self.textColorDisable = wx.LIGHT_GREY.GetAsString(wx.C2S_HTML_SYNTAX)
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)

    def SetBGColor(self, crBg = None, crBgSel = None, crBgDisable = None, 
                                                               silent = False):
        self.bgColor = crBg
        if not self.bgColor:
            self.bgColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW).GetAsString(wx.C2S_HTML_SYNTAX)
        self.bgColorSel = crBgSel
        if not self.bgColorSel:
            self.bgColorSel = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUHILIGHT).GetAsString(wx.C2S_HTML_SYNTAX)
        self.bgColorDisable = crBgDisable
        if not self.bgColorDisable:
            self.bgColorDisable = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE).GetAsString(wx.C2S_HTML_SYNTAX)
        if not silent:
            self.SendPropEvent(wxEVT_BSM_PROP_REFRESH)
    
    def GetShowLabelTips(self):
        return self.showLabelTips

    def GetShowValueTips(self):
        return self.showValueTips
   
    def GetContextMenu(self, menu, nIDStart, nIDEnd):
        return False

    def OnPropContextMenu(self, nID):
        return False

#properties event 
class bsmPropertyEvent(wx.PyCommandEvent):
    def __init__(self, commandType, id = 0):
        wx.PyCommandEvent.__init__(self, commandType, id)
        self.prop = None
        self.name = ""
        self.refused = False

    def GetProperty(self):
        return self.prop

    def GetPropertyName(self):
        return self.name

    def SetProperty(self, prop):
        if isinstance(prop, bsmProperty):
            self.prop = prop
        elif isinstance(prop, str):
            self.name = strReg

    def Refused(self, bRefused):
        self.refused = bRefused

    def IsRefused(self):
        return self.refused

