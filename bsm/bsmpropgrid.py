import wx
import json
from bsmprop import *
from _pymgr_helpers import Gcm

BSMGRID_CURSOR_RESIZE_HOR = 0
BSMGRID_CURSOR_RESIZE_VER = 1
BSMGRID_CURSOR_STD = 2

BSMGRID_NONE = 0
BSMGRID_RESIZE_SEP = 1
BSMGRID_RESIZE_BOT = 2

BSM_SCROLL_UNIT = 5

class bsmPropDropTarget(wx.PyDropTarget):
    def __init__(self, frame):
        wx.PyDropTarget.__init__(self)
        self.obj = wx.PyTextDataObject()
        self.SetDataObject(self.obj)
        self.frame = frame
    # override base class (pure) virtuals
    def OnEnter(self, x, y, d):
        return super(bsmPropDropTarget, self).OnDragOver(x, y, d)
    def OnLeave(self):
        pass
    def OnData(self, x, y, d):
        if not self.GetData():
            return wx.DragNone
        self.frame.OnDrop(x, y, self.obj.GetText())

        return d
    def OnDragOver(self, x, y, d):
        pt = wx.Point(x,y)
        rc = self.frame.GetClientRect()
        if (rc.Contains(pt)):
            (x,y) = self.frame.GetViewStart()
            if pt.y<15:
                self.frame.Scroll(-1,y-(15-pt.y)/3)
            if pt.y>rc.GetBottom()-15:
                self.frame.Scroll(-1,y-(rc.GetBottom()-15-pt.y)/3)
        return super(bsmPropDropTarget, self).OnDragOver(x, y, d)

class bsmPropGridBase(wx.ScrolledWindow):
    dragPropState = 0
    dragStartPt = wx.Point(0,0)
    dragProperty = None
    dragGrid = None
    def __init__(self, frame, num = None):
        wx.ScrolledWindow.__init__(self, frame, wx.ID_ANY, wx.DefaultPosition, 
                wx.DefaultSize)
        self.TitleWidth = 150
        self.PropSelected = None
        self.cursorMode = BSMGRID_CURSOR_STD
        self.ptMouseDown = wx.Point(0,0)
        self.PropUnderMouse = None
        self.resizeMode = BSMGRID_NONE
        #cursor
        self.resizeCursorHor = wx.StockCursor( wx.CURSOR_SIZEWE )
        self.resizeCursorVer = wx.StockCursor( wx.CURSOR_SIZENS )

        #set scroll paremeters
        self.SetScrollRate( BSM_SCROLL_UNIT, BSM_SCROLL_UNIT )
        self.SetVirtualSize(wx.Size(100,200))

        #drap target
        self.SetDropTarget(bsmPropDropTarget(self))
    
        self.PropList = []
        self.PropDict = {}
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnMouseUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnMouseRightClick)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnMouseDoubleClick)
        self.Bind(wx.EVT_MOTION, self.OnMouseMove)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        self.Bind(EVT_BSM_PROP_SELECTED, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CHANGING, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CHANGED, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_HIGHLIGHTED, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_RIGHT_CLICK, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_COLLAPSED, self.OnPropCollapsed, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_EXPANDED, self.OnPropExpanded, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DOUBLE_CLICK, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_INDENT, self.OnPropIndent, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_KEYDOWN, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_RESIZE, self.OnPropResize, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_REFRESH, self.OnPropRefresh, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DELETE, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DROP, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_BEGIN_DRAG, self.OnPropEventsHandler, id = wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CLICK_RADIO, self.OnPropEventsHandler, id = wx.ID_ANY)
       
        wx.py.dispatcher.connect(self.UpdateProp, signal='grid.updateprop')

    def UpdateProp(self, objs):
        for name, v in objs.iteritems():
            p = self.GetProperty(name)
            if isinstance(p, list): 
                for prop in p:
                    prop.SetValue(v)
            elif isinstance(p, bsmProperty):
                p.SetValue(v)

   #insert property
    def AppendProperty(self, name, label="", value="", update=True):
        return self.InsertProperty(name,label,value,-1, update)
    
    def _InsertProperty(self, prop, nIndex=-1, update = True):
        # add the prop window to the grid
        if not isinstance(prop, bsmProperty): return None

        if nIndex==-1 or nIndex>=self.GetPropCount():
            self.PropList.append(prop)
        else:
            self.PropList.insert(nIndex,prop)
        name = prop.GetName()
        if name in self.PropDict:
            self.PropDict[name].append(prop)
        else:
            self.PropDict[name] = [prop]
        
        if nIndex!=-1 and (not update):
            self.Check()
        self.UpdateGrid(update, update)
        wx.py.dispatcher.send(signal='prop.insert', prop = prop)
        return prop

    def InsertProperty(self, name, label="", value="", nIndex=-1, update = True):
        # add the prop window to the grid
        prop = bsmProperty(self,name,label,value)
        return self._InsertProperty(prop, nIndex, update)

    def CopyProperty(self, prop, nIndex = -1, update = True):
        if not isinstance(prop, bsmProperty): return None
        p = prop.duplicate()
        p.SetParent(self)
        return self._InsertProperty(p, nIndex, update)

    def InsertSeparator(self, name, nIndex   = -1, bUpdate = True):
        prop = self.InsertProperty(name,name,"",nIndex,bUpdate)
        if prop:
            # prop->SetEnable(False)
            prop.SetSeparator(True)
        return prop

    #remove property
    def RemoveProperty(self, prop, bUpdate = True):
        if isinstance(prop, str) or isinstance(prop, bsmProperty):
            nIndex =  self.FindProperty(prop)
        elif isinstance(prop, int):
            nIndex = prop
        else:
            return False
        if nIndex>=0 and nIndex<self.GetPropCount():
            prop  = self.PropList[nIndex]
            if prop == self.PropSelected:
                self.SelectProperty(-1)
            del self.PropList[nIndex]
            
            name = prop.GetName()
            idx = self.PropDict[name].index(prop)
            del self.PropDict[name][idx]
            if  self.PropDict[name] == []:
                del self.PropDict[name]

            if nIndex!=-1 and (not bUpdate):
                self.Check()
            if nIndex>=self.GetPropCount():
                nIndex = self.GetPropCount()-1
            self.SelectProperty(nIndex)

            self.UpdateGrid(bUpdate,bUpdate)
            return True
        return False

    def DeleteProperty(self, prop, bUpdate = True):
        if self.SendPropEvent(wxEVT_BSM_PROP_DELETE,prop):
            wx.py.dispatcher.send(signal='prop.delete', prop = prop)
            return self.RemoveProperty(prop,bUpdate)
        else:
            return False

    def FindProperty(self, prop):
        pPropWnd = self.GetProperty(prop)
        if not pPropWnd:
            return -1
        try:
            idx = self.PropList.index(pPropWnd)
            return idx
        except:
            pass
        return -1

    #get the property
    def GetProperty(self, prop):
        if isinstance(prop, bsmProperty):
            return prop
        elif isinstance(prop, str):
            p = self.PropDict.get(prop, [])
            if len(p) == 1: return p[0]
            elif p == []: return None
            else: return p
        elif isinstance(prop, int):
            index = prop
            if index>=0 and index < self.GetPropCount():
                return self.PropList[index]
            return None
        else:
            return None

    def GetPropertyIndex(self, prop):
        try:
            idx = self.PropList.index(prop)
            return idx
        except:
            pass
        return -1
    
    def GetPropCount(self):
        return len(self.PropList)
     
    #make the property visible
    def EnsureVisible(self, prop):
        pPropWnd = self.GetProperty(prop)
        if pPropWnd:
            rc = pPropWnd.GetClientRect()
            (rc.x, rc.y) = self.CalcScrolledPosition(rc.x, rc.y)
            (x, y) = self.GetViewStart()
            rcClient = self.GetClientRect()
            if (rcClient.GetTop()<rc.GetTop() and 
                    rcClient.GetBottom()>rc.GetBottom()):
                return
            if rcClient.GetTop()>rc.GetTop():
                y = y + ((rc.GetTop() - rcClient.GetTop())/BSM_SCROLL_UNIT)
                self.Scroll(-1,y)
            elif rcClient.GetBottom()<rc.GetBottom():
                y = y+ ((rc.GetBottom()-rcClient.GetBottom())/BSM_SCROLL_UNIT)
                self.Scroll(-1,y)

    # Select property
    def GetActivated(self):
        return self.FindProperty(self.PropSelected)

    def GetSelectedProperty(self):
        return self.PropSelected

    def SelectProperty(self, prop):
        pPropWnd = self.GetProperty(prop)
        if pPropWnd!=self.PropSelected:
            if self.PropSelected:
                self.PropSelected.SetActivated(False)
            self.PropSelected = pPropWnd
            if self.PropSelected:
                self.PropSelected.SetActivated(True)
            self.Refresh()
            return True
        return False

    def UpdateGrid(self, bRefresh, bAutosize):
        if bAutosize:
            self.AutoSize()
        if bRefresh:
            self.Refresh()

    def MoveProperty(self, prop, nStep):
        if isinstance(prop, bsmProperty):
            index = self.GetPropertyIndex(prop)
        elif isinstance(prop, int):
            index = prop
        else:
            return
        
        if nStep==0:
            return

        index2 = index + nStep
        if index2 < 0:
            index2 = 0
        if index2<self.GetPropCount():
            self.doMoveProperty(index,index2)
        else:
            self.doMoveProperty(index,-1)

    def MovePropertyDown(self, prop):
        self.MoveProperty(prop,2)

    def MovePropertyUp(self, prop):
        self.MoveProperty(prop,-1)
        
    #send the property event to the parent
    def SendPropEvent(self, event, prop=None):
        prop = self.GetProperty(prop)
        if isinstance(event, bsmPropertyEvent):
            evt = event
        elif isinstance(event, int):
            evt = bsmPropertyEvent(event)
            evt.SetProperty(prop)
        else:
            return False

        evt.SetId(self.GetId())
        eventObject = self.GetParent()
        evt.SetEventObject(eventObject)
        evtHandler = eventObject.GetEventHandler()

        evtHandler.ProcessEvent(evt)
        return not evt.IsRefused()

    #move the focus
    def NavigateProp(self, bDown):
        nActivated = self.GetActivated()
        while True:
            if bDown:
                nActivated = nActivated + 1
            else:
                nActivated = nActivated - 1

            if (nActivated < 0 or nActivated>=self.GetPropCount()):
                break

            wnd  = self.PropList[nActivated]
            if wnd.GetVisible():
                self.SelectProperty(nActivated)
                self.EnsureVisible(nActivated)
                break

    #move the property
    def doMoveProperty(self, index, index2):
        #the same position, ignore it
        if index==index2:
            return

        pProp = self.GetProperty(index)
        pPropList = []
        pPropList.append(pProp)
        if pProp.IsPropHasChildren() and (not pProp.IsPropExpand()):
            indent = pProp.GetIndent()
            for i in range (index+1, self.GetPropCount()):
                if (self.PropList[i].GetIndent()<=indent):
                    break
                pPropList.append(self.PropList[i])
       
        i = 0
        for p in pPropList:
            if index2==-1:
                self.PropList.append(p)
            else:
                #insert it before the propPrev
                self.PropList.insert(index2+i, p)
                i += 1

        if index2!=-1 and index>index2:
            index = index+ len(pPropList)

        for i in range(0, len(pPropList)):
            del self.PropList[index]

        self.UpdateGrid(True, True)
    
    #get the property under the mouse
    def PropHitTest(self, pt):
        for i in range(0, self.GetPropCount()):
            prop = self.PropList[i]
            if  not prop.GetVisible():
                continue
            if prop.GetClientRect().Contains(pt):
                return i
        return -1

    #layout the properties
    def AutoSize(self, bUpdate = True):
        rc = self.GetClientRect()
        (w, h) = (rc.width, 1)

        self.Check()
        for p in self.PropList:
            if p.GetVisible():
                sz= p.GetMinSize()
                w = max(w,sz.x)
                h = h + sz.y
        if bUpdate:
            self.SetVirtualSize(wx.Size(w,h))
        rc = self.GetClientRect()
        h = 1
        w = max(w,rc.width)
        for p in self.PropList:
            if p.GetVisible():
                hh = p.GetMinSize().y
                rc = wx.Rect(0,h,w,hh)
                p.SetClientRect(rc)
                h = h + hh
   
    def GetDrawRect(self):
        sz = self.GetClientSize()
        windowRect = wx.Rect(0,0,sz.x, sz.y)

        # We need to shift the client rectangle to take into account
        # scrolling, converting device to logical coordinates
        (windowRect.x, windowRect.y) = self.CalcUnscrolledPosition(windowRect.x, windowRect.y)

        return windowRect

    def Check(self):
        nParent = -1
        for i in range(0, self.GetPropCount()):
            pProp = self.PropList[i]
            while nParent !=-1:
                pProp2 = self.GetProperty(nParent)
                if pProp2.GetIndent() < pProp.GetIndent():
                    break

                nParent = pProp2.GetParentItem()
            pProp.SetParentItem(nParent)
            if nParent!=-1:
                pProp2 = self.GetProperty(nParent)
                assert(pProp2)
                pProp2.SetHasChildren(True, True)
            pProp.SetHasChildren(False, True)
            nParent = i
        bShow = True
        for i in range(0, self.GetPropCount()):
            pProp = self.PropList[i]
            nParent = pProp.GetParentItem()
            bShow = pProp.GetVisible()
            if nParent==-1 and ( not pProp.GetVisible()):
                bShow = True
            if nParent!=-1:
                pProp2 = self.GetProperty(nParent)
                assert(pProp2)
                bShow = pProp2.IsPropExpand()
                if pProp2.GetVisible()==False:
                    bShow = False
            pProp.SetVisible(bShow)

    #bsm event handling function   
    def OnPropCollapsed(self, evt):
        self.SendPropEvent(evt.GetEventType(),evt.GetProperty())
        self.UpdateGrid(True, True)

    def OnPropExpanded(self, evt):
         self.SendPropEvent(evt.GetEventType(),evt.GetProperty())
         self.UpdateGrid(True,True)

    def OnPropIndent(self, evt):
        self.UpdateGrid(True, True)

    def OnPropResize(self, evt):
        self.UpdateGrid(True,True)

    def  OnPropRefresh(self, evt):
        pProp = evt.GetProperty()
        if pProp == None:
            return
        rc= pProp.GetClientRect()
        (rc.x, rc.y) = self.CalcScrolledPosition(rc.x, rc.y)

        self.RefreshRect(rc,False)

    def OnPropEventsHandler(self, evt):
       pass

    def OnPropTextEnter(self, evt):
        assert (self.PropSelected)
        if self.PropSelected:
            self.PropSelected.OnTextEnter()

    #wxWidgets event handling function
    def OnKeyDown(self, evt):
        pProp  = self.PropSelected
        bSkip = True
        if pProp:
            index = self.GetActivated()
            keycode = evt.GetKeyCode()
            nIndent = pProp.GetIndent()
            if keycode == wx.WXK_LEFT:
                if evt.CmdDown():
                    pProp.SetIndent(nIndent-1)
                else:
                    pProp.SetExpand(False)
                bSkip = False
            elif keycode == wx.WXK_UP:
                if evt.CmdDown():
                    self.MovePropertyUp(index)
                else:
                    self.NavigateProp(False)
                bSkip = False
            elif keycode == wx.WXK_RIGHT:
                if evt.CmdDown():
                    pProp.SetIndent(nIndent+1)
                else:
                    pProp.SetExpand(True)
            elif keycode == wx.WXK_DOWN:
                if evt.CmdDown():    
                    self.MovePropertyDown(index)
                else:
                    self.NavigateProp(True)
                bSkip = False
            elif keycode == wx.WXK_DELETE:
                self.RemoveProperty(self.GetSelectedProperty())
        if bSkip:
            evt.Skip()

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        self.DoPrepareDC(dc)

        rc = self.GetDrawRect()
        #draw background
        crBg  = self.GetBackgroundColour()
        if not crBg.Ok():
            crBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)
        pen = wx.Pen(wx.BLACK,1,wx.TRANSPARENT)
        dc.SetPen(pen)
        brush = wx.Brush(crBg)
        dc.SetBrush(brush)
        dc.DrawRectangle(rc.x, rc.y, rc.width, rc.height)
        
        # draw the top edge
        dc.SetPen( wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.GetLeft(),rc.GetTop(),rc.GetRight(),rc.GetTop())

        for p in self.PropList:
            if p.GetVisible():
                #p.DrawItem(dc)
                rcItem = p.GetClientRect()
                upd = wx.RegionIterator(self.GetUpdateRegion())
                while upd.HaveRects():
                    updRect = upd.GetRect()
                    (updRect.x, updRect.y) = self.CalcUnscrolledPosition(updRect.x, updRect.y)
                    #draw all the properties
                    if rc.Intersects(rcItem):
                        p.SetNameWidth(self.TitleWidth)
                        p.DrawItem(dc)
                        break
                    upd.Next()
    
    def OnSize(self, evt):
        #rearrange the size of properties
        self.AutoSize(False)
        self.Refresh()
        evt.Skip()

    def OnEraseBackground(self, evt):
        #intentionally leave empty to remove the screen flash
        pass
    
    def OnMouseDown(self, evt):
        pt2 = self.CalcUnscrolledPosition(evt.GetPosition())
        index  = self.PropHitTest(pt2)
        if index!=-1:
            prop = self.GetProperty(index)
            if prop:
                #pass the event to the property
                ht =   prop.PropHitTest(pt2)
                self.resizeMode = BSMGRID_NONE
                #drag the spllitter
                if ht == bsmProperty.PROP_HIT_SPLITTER:
                    self.resizeMode = BSMGRID_RESIZE_SEP
                elif ht == bsmProperty.PROP_HIT_EDGE_BOTTOM:
                    self.resizeMode = BSMGRID_RESIZE_BOT
                elif ht == bsmProperty.PROP_HIT_EDGE_TOP:
                    if index>0:
                        index = index-1
                        self.resizeMode = BSMGRID_RESIZE_BOT
        self.ptMouseDown = pt2
        self.SelectProperty(index)
        if index!=-1:
            pProp = self.GetProperty(index)
            assert (pProp==self.PropSelected)
            ht = pProp.OnMouseDown(pt2)
            if ht == bsmProperty.PROP_HIT_TITLE:
                #start drag&drop
                bsmPropGrid.dragStartPt = self.ClientToScreen(pt2)
                bsmPropGrid.dragProperty = pProp
                bsmPropGrid.dragPropState = 1
            else:
                self.PropUnderMouse = pProp
                self.CaptureMouse()
        evt.Skip()

    def OnMouseUp(self, evt ):
        pt2 = self.CalcUnscrolledPosition(evt.GetPosition())
        if self.PropUnderMouse:
            #pass the event to the property
            self.PropUnderMouse.OnMouseUp(pt2)
            self.PropUnderMouse = None

        if self.GetCapture()==self:
            self.ReleaseMouse()

        self.ptMouseDown = wx.Point(0,0)
        self.resizeMode  = BSMGRID_NONE

        bsmPropGrid.dragProperty  = None
        bsmPropGrid.dragPropState = 0
        bsmPropGrid.dragStartPt   = wx.Point(0,0)

        evt.Skip()

    def OnMouseDoubleClick(self, evt):
        pt2 = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt2)
        if index!=-1:
            #pass the event to the property
            prop = self.GetProperty(index)
            prop.OnMouseDoubleClick(pt2)
    
        evt.Skip()

    def OnMouseMove(self,  evt):
        pt2 = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt2)
        prop = None
        if index!=-1:
            prop = self.GetProperty(index)
        if prop:
            prop.OnMouseMove(pt2)
        #drag & drop
        if evt.LeftIsDown() and bsmPropGrid.dragProperty and bsmPropGrid.dragPropState==1:
            pt  = self.ClientToScreen(pt2)
            if ((bsmPropGrid.dragStartPt.x-pt.x)*(bsmPropGrid.dragStartPt.x-pt.x)+
                    (bsmPropGrid.dragStartPt.y-pt.y)*(bsmPropGrid.dragStartPt.y-pt.y)>10):
                if True:#self.SendPropEvent(wxEVT_BSM_PROP_BEGIN_DRAG, self.sm_pDragProperty):
                    bsmPropGrid.dragPropState = 2
                    bsmPropGrid.dragGrid = self
                    # start drag operation
                    propData = wx.PyTextDataObject(bsmPropGrid.dragProperty.GetName())
                    source = wx.DropSource(bsmPropGrid.dragGrid)
                    source.SetData(propData)

                    rtn = source.DoDragDrop(True)
                    if rtn == wx.DragError:
                        wx.LogError("An error occurred during drag \
                                       and drop operation")
                    elif rtn == wx.DragNone:
                        pass
                    elif rtn == wx.DragCopy:
                        pass
                    elif rtn == wx.DragMove:
                        pass
                    elif rtn == wx.DragCancel:
                        pass
                    bsmPropGrid.dragPropState = 0
                    bsmPropGrid.dragGrid = None
        if (evt.LeftIsDown() and self.PropUnderMouse):
            if self.resizeMode == BSMGRID_RESIZE_SEP:
                self.TitleWidth = min(max(evt.GetX()-6,50),max(self.PropUnderMouse.GetSize().x-50,50))
                self.Refresh(False)
            elif self.resizeMode == BSMGRID_RESIZE_BOT:
                sz = self.PropUnderMouse.GetMinSize()
                sz2 = wx.Size(sz.x, sz.y)
                sz.y += (pt2.y- self.ptMouseDown.y)
                sz.y = max(sz.y,25)
                if sz.y!=sz2.y:
                    self.ptMouseDown.Set(pt2.x, pt2.y)
                    self.PropUnderMouse.SetMinSize(sz)
            else:
                self.PropUnderMouse.OnMouseMove(pt2)
        else:
            if not evt.IsButton():
                strToolTip = ""
                cursorMode = self.cursorMode
                cursorMode = BSMGRID_CURSOR_STD

                if prop:
                    #pass the event to the property
                    ht =   prop.PropHitTest(pt2)

                    #drag the spllitter
                    if ht == bsmProperty.PROP_HIT_SPLITTER:
                        cursorMode = BSMGRID_CURSOR_RESIZE_HOR
                    elif ht == bsmProperty.PROP_HIT_EDGE_BOTTOM:
                        cursorMode = BSMGRID_CURSOR_RESIZE_VER
                    elif ht == bsmProperty.PROP_HIT_EDGE_TOP:
                        if index>0:
                            cursorMode = BSMGRID_CURSOR_RESIZE_VER
                        else:
                            cursorMode = BSMGRID_CURSOR_STD
                    else:
                        cursorMode = BSMGRID_CURSOR_STD
                    #if prop.GetShowLabelTips() and ht == bsmProperty.PROP_HIT_TITLE:
                    if ht == bsmProperty.PROP_HIT_TITLE:
                        strToolTip = prop.GetName()
                    elif prop.GetShowValueTips() and ht == bsmProperty.PROP_HIT_VALUE:
                        strToolTip = prop.GetValue()
                    elif ht == bsmProperty.PROP_HIT_EXPAND:
                        strToolTip = prop.GetName()
                #set the tooltips
                if self.GetToolTipString() != strToolTip:
                    self.SetToolTipString(strToolTip)
                #set the cursor
                if cursorMode!=self.cursorMode:
                    self.cursorMode = cursorMode
                    if cursorMode == BSMGRID_CURSOR_RESIZE_HOR:
                        self.SetCursor(self.resizeCursorHor)
                    elif cursorMode == BSMGRID_CURSOR_RESIZE_VER:
                        self.SetCursor(self.resizeCursorVer)
                    else:
                        self.SetCursor(wx.NullCursor)
        evt.Skip()

    def OnMouseLeave(self, evt):
        #reset the mouse
        self.SetCursor( wx.NullCursor)
        evt.Skip()

    def OnMouseRightClick(self, evt):
        pt2 = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt2)
        #set the active property
        self.SelectProperty(index)
        if index!=-1:
            #pass the event to the property
            prop = self.GetProperty(index)
            prop.OnMouseRightClick(pt2)

    #drag&drop
    def OnDrop(self, x, y, strName):
        pt = wx.Point(x, y)
        pt = self.CalcUnscrolledPosition(pt)
        index2  = self.PropHitTest(pt)
        pProp = self.GetProperty(index2)
        #Insert a register? Let the parent to determine what to do
        if bsmPropGrid.dragProperty == None:
            wx.py.dispatcher.send(signal='prop.drop', index=index2, prop = strName, grid = self)
            return
        if strName != bsmPropGrid.dragProperty.GetName():
            return
        index = bsmPropGrid.dragGrid.FindProperty(bsmPropGrid.dragProperty)
        if index == -1:
            return

        if bsmPropGrid.dragGrid != self: #copy the registers
            indent = bsmPropGrid.dragProperty.GetIndent()
            #if index2 != -1:
            #    index2 = index2 + 1
            self.CopyProperty(bsmPropGrid.dragProperty, index2)
            for i in range(index+1, bsmPropGrid.dragGrid.GetPropCount()):
                pPropTemp = bsmPropGrid.dragGrid.GetProperty(i)
                if pPropTemp.GetIndent()<=indent:
                    break
                if index2 != -1:
                    index2 = index2 + 1
                self.CopyProperty(pPropTemp,index2)
        else:
            if pProp==bsmPropGrid.dragProperty:
                return
            self.doMoveProperty(index,index2)
        self.UpdateGrid(True, True)

class bsmPropGrid(bsmPropGridBase):
    GCM = Gcm()
    ID_PROP_GRID_ADD_SEP = wx.NewId()
    ID_PROP_GRID_READ_ONLY = wx.NewId()
    ID_PROP_BREAKPOINT = wx.NewId()
    ID_PROP_BREAKPOINT_CLEAR = wx.NewId()
    ID_PROP_GRID_INDENT_INS = wx.NewId()
    ID_PROP_GRID_INDENT_DES = wx.NewId()
    ID_PROP_GRID_MOVE_UP = wx.NewId()
    ID_PROP_GRID_MOVE_DOWN = wx.NewId()
    ID_PROP_GRID_DELETE = wx.NewId()
    ID_PROP_GRID_PROP = wx.NewId()

    def __init__(self, parent, num=None):
        bsmPropGridBase.__init__(self, parent)

        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_ADD_SEP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_PROP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_INDENT_INS)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_INDENT_DES)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_MOVE_UP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_MOVE_DOWN)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_READ_ONLY)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_GRID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_BREAKPOINT)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id = self.ID_PROP_BREAKPOINT_CLEAR)
        # if num is not defined or is occupied, generate a new one 
        if num is None or num in bsmPropGrid.get_nums():
            num = bsmPropGrid.GCM.get_next_num()
        self.num = num
        bsmPropGrid.GCM.set_active(self)
    def __del__(self):
        bsmPropGrid.GCM.destroy_mgr(self)
    
    @classmethod
    def get_instances(cls):
        for inst in cls.GCM.get_all_managers():
            if inst is not None:
                yield inst
    def OnPropEventsHandler(self, evt):
        if not self.SendPropEvent(evt):
            return
        prop = evt.GetProperty();
        eid = evt.GetEventType()
        if eid == wxEVT_BSM_PROP_RIGHT_CLICK:
            menu = wx.Menu()
            menu.Append(self.ID_PROP_GRID_ADD_SEP, "&Add separator");
            menu.AppendCheckItem(self.ID_PROP_GRID_READ_ONLY, "&Read only");
            bEnable = True
            menu.Enable(self.ID_PROP_GRID_READ_ONLY,bEnable);
            menu.Check(self.ID_PROP_GRID_READ_ONLY,prop.GetReadOnly());
            menu.AppendSeparator();
            menu.Append(self.ID_PROP_BREAKPOINT, "Breakpoint Condition");
            menu.Enable(self.ID_PROP_BREAKPOINT,prop.IsPropRadioChecked());
            menu.Append(self.ID_PROP_BREAKPOINT_CLEAR, "Clear all Breakpoints");
            #menu.Enable(self.ID_PROP_BREAKPOINT_CLEAR,m_bCheckBreakPoint);
            menu.AppendSeparator();
            menu.Append(self.ID_PROP_GRID_INDENT_INS, "Increase Indent\tCtrl-Right");
            menu.Append(self.ID_PROP_GRID_INDENT_DES, "Decrease Indent\tCtrl-Left");
            menu.AppendSeparator();
            menu.Append(self.ID_PROP_GRID_MOVE_UP, "Move up\tCtrl-Up");
            menu.Append(self.ID_PROP_GRID_MOVE_DOWN, "Move down\tCtrl-Down");
            menu.AppendSeparator();
            menu.Append(self.ID_PROP_GRID_DELETE, "&Delete");
            menu.AppendSeparator();
            menu.Append(self.ID_PROP_GRID_PROP, "&Properities");
            
            self.PopupMenu(menu)
            menu.Destroy()
        elif eid == wxEVT_BSM_PROP_CLICK_RADIO:
            if prop.IsPropRadioChecked():
                wx.py.dispatcher.send(signal='prop.bp_add', prop=prop)
            else:
                wx.py.dispatcher.send(signal='prop.bp_del', prop=prop)
        elif eid == wxEVT_BSM_PROP_CHANGED:
            wx.py.dispatcher.send(signal='prop.changed', prop=prop)

    def OnProcessCommand(self, evt):
        eid = evt.GetId()
        prop = self.GetSelectedProperty()
        if not prop: return
        if eid == self.ID_PROP_GRID_DELETE:
            self.DeleteProperty(prop);
        elif eid == self.ID_PROP_GRID_READ_ONLY:
            prop.SetReadOnly(not prop.GetReadOnly());
        elif eid == self.ID_PROP_GRID_PROP:
            dlg = dlgSettings(self, prop)
            dlg.ShowModal()
        elif eid == self.ID_PROP_GRID_INDENT_INS:
            prop.SetIndent(prop.GetIndent()+1);
        elif eid == self.ID_PROP_GRID_INDENT_DES:
            prop.SetIndent(prop.GetIndent()-1);
        elif eid == self.ID_PROP_GRID_MOVE_UP:
            self.MoveProperty(prop,-1);
        elif eid == self.ID_PROP_GRID_MOVE_DOWN:
            self.MoveProperty(prop,2);
        elif eid == self.ID_PROP_GRID_ADD_SEP:
            self.InsertSeparator("", self.GetActivated());
        elif eid == self.ID_PROP_BREAKPOINT:
            condition = prop.GetBPCondition()
            dlg = BreakpointSettingsDlg(self, condition[0], condition[1])
            if dlg.ShowModal() == wx.ID_OK:
                # clear the previous bp condition
                if prop.IsPropRadioChecked():
                    wx.py.dispatcher.send(signal='prop.bp_del', prop=prop)
                prop.SetBPCondition(dlg.GetCondition())
                # set the bp condition
                if prop.IsPropRadioChecked():
                    wx.py.dispatcher.send(signal='prop.bp_add', prop=prop)
        elif eid == self.ID_PROP_BREAKPOINT_CLEAR:
            self.ClearBreakpoints()
    
    def clearBreakePoints(self):
        for prop in self.PropList:
            if prop and prop.IsPropRadioChecked():
                prop.SetRadioChecked(False)
        m_bCheckBreakPoint = false;
    def triggerBreakPoint(self, name, cond, hitcount):
        for prop in self.PropList:
            if name == prop.GetName():
                if (cond, hitcount) == prop.GetBPCondition():
                    self.EnsureVisible(prop)
                    self.SelectProperty(prop)
                    return True
 
class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition = '', hitcount = ''):
        wx.Dialog.__init__ ( self, parent, id = wx.ID_ANY, title = u"Breakpoint Condition", pos = wx.DefaultPosition, size = wx.Size( 431,289 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )
        
        self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
        
        szAll = wx.BoxSizer( wx.VERTICAL )
        
        self.stInfo = wx.StaticText( self, wx.ID_ANY, u"At the end of each delta cycle, the expression is evaluated and the breakpoint is hit only if the expression is true or the register value has changed", wx.DefaultPosition, wx.DefaultSize, 0 )
        self.stInfo.Wrap( -1 )
        szAll.Add( self.stInfo, 1, wx.ALL, 15 )
        
        szCnd = wx.BoxSizer( wx.HORIZONTAL )
        
        
        szCnd.AddSpacer( ( 20, 0), 0, wx.EXPAND, 5 )
        
        szCond = wx.BoxSizer( wx.VERTICAL )
        
        self.rbChanged = wx.RadioButton( self, wx.ID_ANY, u"Has changed", wx.DefaultPosition, wx.DefaultSize, wx.RB_GROUP )
        szCond.Add( self.rbChanged, 5, wx.ALL|wx.EXPAND, 5 )
        
        self.rbCond = wx.RadioButton( self, wx.ID_ANY, u"Is true (value: $; for example, $==10)", wx.DefaultPosition, wx.DefaultSize, 0 )
        szCond.Add( self.rbCond, 0, wx.ALL|wx.EXPAND, 5 )
        
        self.tcCond = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        szCond.Add( self.tcCond, 0, wx.ALL|wx.EXPAND, 5 )
        
        self.cbHitCount = wx.CheckBox( self, wx.ID_ANY, u"Hit count (hit count: #; for example, #>10", wx.DefaultPosition, wx.DefaultSize, 0 )
        szCond.Add( self.cbHitCount, 0, wx.ALL, 5 )
        
        self.tcHitCount = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
        szCond.Add( self.tcHitCount, 0, wx.ALL|wx.EXPAND, 5 )
        
        
        szCnd.Add( szCond, 1, wx.EXPAND, 5 )
        
        
        szAll.Add( szCnd, 1, wx.EXPAND, 5 )
        
        self.stLine = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
        szAll.Add( self.stLine, 0, wx.EXPAND |wx.ALL, 5 )
        
        szConfirm = wx.BoxSizer( wx.HORIZONTAL )
        
        self.btnOK = wx.Button( self, wx.ID_OK, u"OK", wx.DefaultPosition, wx.DefaultSize, 0 )
        szConfirm.Add( self.btnOK, 0, wx.ALL, 5 )
        
        self.btnCancel = wx.Button( self, wx.ID_CANCEL, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
        szConfirm.Add( self.btnCancel, 0, wx.ALL, 5 )
        
        
        szAll.Add( szConfirm, 0, wx.ALIGN_RIGHT, 5 )
        
        
        self.SetSizer( szAll )
        self.Layout()
        
        # initialize the controls
        self.condition = condition
        self.hitcount = hitcount
        self.SetSizer( szAll )
        self.Layout()
        if self.condition == '':
            self.rbChanged.SetValue(True)
            self.tcCond.Disable()
        else:
            self.rbChanged.SetValue(False)
        self.tcCond.SetValue(self.condition)
        if self.hitcount == '':
            self.cbHitCount.SetValue(False)
            self.tcHitCount.Disable()
        else:
            self.cbHitCount.SetValue(True)
        self.tcHitCount.SetValue(self.hitcount) 
        # Connect Events
        self.rbChanged.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.rbCond.Bind(wx.EVT_RADIOBUTTON, self.OnRadioButton)
        self.cbHitCount.Bind(wx.EVT_CHECKBOX, self.OnRadioButton)
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOK)
    
    def __del__( self ):
        pass
    
    # Virtual event handlers, overide them in your derived class
    def OnRadioButton( self, event ):
        if self.rbChanged.GetValue():
            self.tcCond.Disable()
        else:
            self.tcCond.Enable()
        if self.cbHitCount.GetValue():
            self.tcHitCount.Enable()
        else:
            self.tcHitCount.Disable()
        event.Skip()
    def OnBtnOK( self, event ):
        # set condition to empty string to indicate the breakpoint will be
        # trigged when the value is changed
        if self.rbChanged.GetValue():
            self.condition = ''
        else:
            self.condition = self.tcCond.GetValue()
        if self.cbHitCount.GetValue():
            self.hitcount = self.tcHitCount.GetValue()
        else:
            self.hitcount = ""
        event.Skip()

    def GetCondition(self):
        return (self.condition, self.hitcount)

class dlgSettings(wx.Dialog):
    
    def __init__( self, parent, prop):
        wx.Dialog.__init__ (self, parent, id = wx.ID_ANY, title = u"Settings...", pos = wx.DefaultPosition, size = wx.Size( 402,494 ), style = wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )
        
        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        
        sz = wx.BoxSizer(wx.VERTICAL)
        
        self.propgrid = bsmPropGridBase(self)
        self.prop = prop
        if prop.GetSeparator():
            self.items = (('label', 'label', bsmProperty.PROP_CTRL_EDIT),
                ('indent', 'indent', bsmProperty.PROP_CTRL_SPIN),
                ('italic', 'italic', bsmProperty.PROP_CTRL_CHECK))
        else:
            self.items = (('name', 'name', bsmProperty.PROP_CTRL_EDIT),
                ('label', 'label', bsmProperty.PROP_CTRL_EDIT),
                ('value', 'value', bsmProperty.PROP_CTRL_EDIT),
                ('description', 'description', bsmProperty.PROP_CTRL_EDIT),
                ('valueMax', 'valueMax', bsmProperty.PROP_CTRL_SPIN),
                ('valueMin', 'valueMin', bsmProperty.PROP_CTRL_SPIN),
                ('indent', 'indent', bsmProperty.PROP_CTRL_SPIN),
                ('showRadio', 'showRadio', bsmProperty.PROP_CTRL_CHECK),
                ('enable', 'enable', bsmProperty.PROP_CTRL_CHECK),
                ('italic', 'italic', bsmProperty.PROP_CTRL_CHECK),
                ('readOnly', 'readOnly', bsmProperty.PROP_CTRL_CHECK),
                ('ctrlType', 'ctrlType', bsmProperty.PROP_CTRL_COMBO),
                ('choiceList','choiceList', bsmProperty.PROP_CTRL_EDIT),
                ('valueList', 'valueList', bsmProperty.PROP_CTRL_EDIT),
                ('textColor', 'crText', bsmProperty.PROP_CTRO_COLOR),
                ('textColorSel', 'crTextSel', bsmProperty.PROP_CTRO_COLOR),
                ('textColorDisable', 'crTextDisable', bsmProperty.PROP_CTRO_COLOR),
                ('bgColor', 'crBg', bsmProperty.PROP_CTRO_COLOR),
                ('bgColorSel', 'crBgSel', bsmProperty.PROP_CTRO_COLOR),
                ('bgColorDisable', 'crBgDisable', bsmProperty.PROP_CTRO_COLOR),
                ('showLabelTips', 'showLabelTips', bsmProperty.PROP_CTRL_CHECK),
                ('showValueTips', 'showValueTips', bsmProperty.PROP_CTRL_CHECK))
        p = self.propgrid 
        for (name, label, ctrl) in self.items:
            pp = p.InsertProperty(name, label, '')
            if prop:
                v = getattr(prop, name)
            else:
                v = ""
            if name in ['choiceList', 'valueList']:
                pp.SetValue('; '.join(v))
            elif ctrl == bsmProperty.PROP_CTRL_CHECK:
                pp.SetValue(str(v+0))
                pp.SetDescription(str(v))
            elif ctrl == bsmProperty.PROP_CTRO_COLOR:
                pp.SetValue(v)
                pp.SetBGColor(v,v,v)
                t = wx.Colour()
                t.SetFromString(v)
                t.SetRGB(t.GetRGB()^0xffffff)
                t = t.GetAsString(wx.C2S_HTML_SYNTAX)
                pp.SetTextColor(t,t,t)
            else:
                pp.SetValue(str(v))
            pp.SetShowRadio(False)
            pp.SetControlStyle(ctrl)

        sz.Add( self.propgrid, 1, wx.EXPAND |wx.ALL, 1)
        
        self.stcline = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        sz.Add(self.stcline, 0, wx.EXPAND |wx.ALL, 5)
        
        sz2 = wx.BoxSizer(wx.HORIZONTAL)
        
        self.btnOK = wx.Button(self, wx.ID_OK, u"&Ok", wx.DefaultPosition, wx.DefaultSize, 0)
        sz2.Add( self.btnOK, 0, wx.ALL, 5)
        
        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"&Cancel", wx.DefaultPosition, wx.DefaultSize, 0)
        sz2.Add(self.btnCancel, 0, wx.ALL, 5)
        
        sz.Add(sz2, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5)
        
        self.SetSizer(sz)
        self.Layout()
            
        # Connect Events
        self.btnOK.Bind( wx.EVT_BUTTON, self.OnBtnOk )
        self.btnCancel.Bind( wx.EVT_BUTTON, self.OnBtnCancel )
    
    
    def OnBtnOk( self, event ):
        for (name, label, ctrl) in self.items:
            v = self.propgrid.GetProperty(name)
            if name in ['choiceList', 'valueList']:
                setattr(self.prop, name, v.GetValue().split(';'))
            elif ctrl == bsmProperty.PROP_CTRL_CHECK:
                setattr(self.prop, name, bool(int(v.GetValue())))
            else:
                setattr(self.prop, name, type(getattr(self.prop, name))(v.GetValue()))
        event.Skip()
    
    def OnBtnCancel( self, event ):
        event.Skip()
