import sys
import traceback
import six
import wx
import wx.py.dispatcher as dp
from .prop import *
from ._pymgr_helpers import Gcm
import bsmedit.c2p as c2p

class bsmPropDropTarget(c2p.PyDropTarget):
    def __init__(self, frame):
        c2p.PyDropTarget.__init__(self)
        self.obj = c2p.PyTextDataObject()
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
        pt = wx.Point(x, y)
        rc = self.frame.GetClientRect()
        if rc.Contains(pt):
            (x, y) = self.frame.GetViewStart()
            if pt.y < 15:
                self.frame.Scroll(-1, y-(15-pt.y)/3)
            if pt.y > rc.bottom-15:
                self.frame.Scroll(-1, y-(rc.bottom-15-pt.y)/3)
        return super(bsmPropDropTarget, self).OnDragOver(x, y, d)

class bsmPropGridBase(wx.ScrolledWindow):
    dragPropState = 0
    dragStartPt = wx.Point(0, 0)
    dragProperty = None
    dragGrid = None

    BSMGRID_NONE = 0
    BSMGRID_RESIZE_SEP = 1
    BSMGRID_RESIZE_BOT = 2

    BSM_SCROLL_UNIT = 5

    BSMGRID_CURSOR_RESIZE_HOR = 0
    BSMGRID_CURSOR_RESIZE_VER = 1
    BSMGRID_CURSOR_STD = 2
    def __init__(self, frame, num=None):
        wx.ScrolledWindow.__init__(self, frame)
        self.TitleWidth = 150
        self.PropSelected = None
        self.cursorMode = self.BSMGRID_CURSOR_STD
        self.ptMouseDown = wx.Point(0, 0)
        self.PropUnderMouse = None
        self.resizeMode = self.BSMGRID_NONE
        #cursor
        self.resizeCursorHor = c2p.StockCursor(wx.CURSOR_SIZEWE)
        self.resizeCursorVer = c2p.StockCursor(wx.CURSOR_SIZENS)

        #set scroll paremeters
        self.SetScrollRate(self.BSM_SCROLL_UNIT, self.BSM_SCROLL_UNIT)
        self.SetVirtualSize(wx.Size(100, 200))

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
        # calling CaptureMouse requires to implement EVT_MOUSE_CAPTURE_LOST
        self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, self.OnMouseCaptureLost)

        self.Bind(EVT_BSM_PROP_SELECTED, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CHANGING, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CHANGED, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_HIGHLIGHTED, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_RIGHT_CLICK, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_COLLAPSED, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_EXPANDED, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DOUBLE_CLICK, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_INDENT, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_KEYDOWN, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_RESIZE, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_REFRESH, self.OnPropRefresh, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DELETE, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_DROP, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_BEGIN_DRAG, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(EVT_BSM_PROP_CLICK_RADIO, self.OnPropEventsHandler, id=wx.ID_ANY)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnPropTextEnter, id=bsmProperty.IDC_BSM_PROP_CONTROL)
        dp.connect(self.UpdateProp, 'grid.updateprop')
        dp.connect(self.simLoad, 'sim.loaded')
        dp.connect(self.simUnload, 'sim.unloaded')

    def Destroy(self):
        dp.disconnect(self.UpdateProp, 'grid.updateprop')
        dp.disconnect(self.simLoad, 'sim.loaded')
        dp.disconnect(self.simUnload, 'sim.unloaded')
        super(bsmPropGridBase, self).Destroy()

    def simLoad(self, num):
        """try to reconnect the register when the simulation is loaded."""
        objs = []
        s = str(num) + '.'
        objs = [name for name in six.iterkeys(self.PropDict) if name.startswith(s)]
        if objs:
            resp = dp.send('sim.monitor_reg', objects=objs)
            if not resp:
                return
            status = resp[0][1]
            if status == False:
                return
            for obj in objs:
                if isinstance(status, dict) and not status.get(obj, False):
                    continue
                p = self.GetProperty(obj)
                if not p: continue
                if isinstance(p, bsmProperty):
                    p = [p]
                for prop in p:
                    prop.SetItalicText(False)
                    prop.SetReadOnly(False)
                    prop.SetEnable(True)

    def simUnload(self, num):
        s = str(num)+'.'
        for p in self.PropList:
            name = p.GetName()
            if not name.startswith(s):
                continue
            p.SetItalicText(True)
            p.SetReadOnly(True)
            p.SetEnable(False)

    def UpdateProp(self, objs):
        for name, v in six.iteritems(objs):
            p = self.GetProperty(name)
            if isinstance(p, list):
                for prop in p:
                    prop.SetValue(v)
            elif isinstance(p, bsmProperty):
                p.SetValue(v)

   #insert property
    def AppendProperty(self, name, label="", value="", update=True):
        return self.InsertProperty(name, label, value, -1, update)

    def _InsertProperty(self, prop, index=-1, update=True):
        # add the prop window to the grid
        if not isinstance(prop, bsmProperty):
            return None

        if index == -1 or index >= self.GetPropCount():
            self.PropList.append(prop)
        else:
            self.PropList.insert(index, prop)
        name = prop.GetName()
        if name in self.PropDict:
            self.PropDict[name].append(prop)
        else:
            self.PropDict[name] = [prop]

        if index != -1 and (not update):
            self.CheckProp()
        self.UpdateGrid(update, update)
        dp.send('prop.insert', prop=prop)
        return prop

    def InsertProperty(self, name, label="", value="", index=-1, update=True):
        # add the prop window to the grid
        prop = bsmProperty(self, name, label, str(value))
        return self._InsertProperty(prop, index, update)

    def CopyProperty(self, prop, index=-1, update=True):
        if not isinstance(prop, bsmProperty): return None
        p = prop.duplicate()
        p.SetParent(self)
        return self._InsertProperty(p, index, update)

    def InsertSeparator(self, name, index=-1, update=True):
        prop = self.InsertProperty(name, name, "", index, update)
        if prop:
            prop.SetSeparator(True)
        return prop

    #remove property
    def RemoveProperty(self, prop, update=True):
        if isinstance(prop, six.string_types) or isinstance(prop, bsmProperty):
            index = self.FindPropertyIndex(prop)
        elif isinstance(prop, int):
            index = prop
        else:
            return False
        if index >= 0 and index < self.GetPropCount():
            prop = self.PropList[index]
            if prop == self.PropSelected:
                self.SelectProperty(-1)
            del self.PropList[index]

            name = prop.GetName()
            idx = self.PropDict[name].index(prop)
            del self.PropDict[name][idx]
            if  not self.PropDict[name]:
                del self.PropDict[name]

            if index != -1 and (not update):
                self.CheckProp()
            if index >= self.GetPropCount():
                index = self.GetPropCount() - 1
            self.SelectProperty(index)

            self.UpdateGrid(update, update)
            return True
        return False

    def DeleteAllProperties(self, update=True):
        for i in range(len(self.PropList)-1, -1, -1):
            self.DeleteProperty(self.PropList[i], update)

    def DeleteProperty(self, prop, update=True):
        if self.SendPropEvent(wxEVT_BSM_PROP_DELETE, prop):
            dp.send('prop.delete', prop=prop)
            return self.RemoveProperty(prop, update)
        else:
            return False

    def FindPropertyIndex(self, prop):
        """return the index of prop, or -1 if not found"""
        p = self.GetProperty(prop)
        if not p:
            return -1
        try:
            idx = self.PropList.index(p)
            return idx
        except ValueError:
            traceback.print_exc(file=sys.stdout)
        return -1

    def GetProperty(self, prop):
        """return the bsmProperty instance"""
        if isinstance(prop, bsmProperty):
            # if prop is an bsmProperty instance, simply return
            return prop
        elif isinstance(prop, six.string_types):
            # search the prop name
            p = self.PropDict.get(prop, [])
            if not p:
                return None
            elif len(p) == 1:
                return p[0]
            return p
        elif isinstance(prop, int):
            # prop is the index
            index = prop
            if index >= 0 and index < self.GetPropCount():
                return self.PropList[index]
        return None

    def GetPropCount(self):
        """return the number of properties"""
        return len(self.PropList)

    def EnsureVisible(self, prop):
        """scroll the window to make sure prop is visible"""
        p = self.GetProperty(prop)
        if not p:
            return
        rc = p.GetClientRect()
        # translate to the scrolled position
        (rc.x, rc.y) = self.CalcScrolledPosition(rc.x, rc.y)
        (x, y) = self.GetViewStart()
        rcClient = self.GetClientRect()
        if rcClient.top < rc.top and rcClient.bottom > rc.bottom:
            # if the prop is visible, simply return
            return
        if rcClient.top > rc.top:
            # if the prop is on top of the client window
            y = y + ((rc.top - rcClient.top)/self.BSM_SCROLL_UNIT)
            self.Scroll(-1, y)
        elif rcClient.bottom < rc.bottom:
            # if the prop is under bottom of the client window
            y = y + ((rc.bottom-rcClient.bottom)/self.BSM_SCROLL_UNIT)
            self.Scroll(-1, y)

    def GetActivated(self):
        """get the index of the selected property"""
        return self.FindPropertyIndex(self.PropSelected)

    def GetSelectedProperty(self):
        """return the selected property"""
        return self.PropSelected

    def SelectProperty(self, prop):
        """set the active property"""
        p = self.GetProperty(prop)
        if p != self.PropSelected:
            if self.PropSelected:
                self.PropSelected.SetActivated(False)
            self.PropSelected = p
            if self.PropSelected:
                self.PropSelected.SetActivated(True)
            self.Refresh()
            return True
        return False

    def UpdateGrid(self, refresh, autosize):
        """update the grid"""
        if autosize:
            self.AutoSize()
        if refresh:
            self.Refresh()

    def MoveProperty(self, prop, step):
        """move the property"""
        index = self.FindPropertyIndex(prop)
        if index == -1:
            return

        if step == 0:
            # move zero step is no move at all
            return

        # calculate the new position
        index2 = index + step
        if index2 < 0:
            index2 = 0
        # move the prop, prop will be placed on top of index2
        if index2 < self.GetPropCount():
            self.doMoveProperty(index, index2)
        else:
            self.doMoveProperty(index, -1)

    def doMoveProperty(self, index, index2):
        """move the property"""
        # the same position, ignore it
        if index == index2:
            return

        prop = self.GetProperty(index)
        propList = [prop]
        if prop.HasChildren() and (not prop.IsExpanded()):
            # move all the children if they are not visible
            indent = prop.GetIndent()
            for i in six.moves.range(index+1, self.GetPropCount()):
                if self.PropList[i].GetIndent() <= indent:
                    break
                propList.append(self.PropList[i])

        i = 0
        for p in propList:
            if index2 == -1:
                self.PropList.append(p)
            else:
                #insert it before index2
                self.PropList.insert(index2+i, p)
                i += 1

        if index2 != -1 and index > index2:
            index = index + len(propList)

        # delete the original properties
        for i in six.moves.range(0, len(propList)):
            del self.PropList[index]

        self.UpdateGrid(True, True)

    def MovePropertyDown(self, prop):
        """move the property one step down"""
        # here step is 2 instead of 1 because the prop will be moved in front
        # of index + step. For example, prop is at position 5, to move it to
        # position 6:
        #    step 1) copy it in front of position 7 (position 7);
        #    step 2) remove the original prop at position 5
        #    step 3) the copy from step 1) will be at position 6 now
        self.MoveProperty(prop, 2)

    def MovePropertyUp(self, prop):
        """move the property one step up"""
        # here the step is -1. For example, prop is at position 5, to move it
        # to position 4, we can say move it in front of position 4. Delete the
        # original prop will not affect the position of the new copy.
        self.MoveProperty(prop, -1)

    def SendPropEvent(self, event, prop=None):
        """send the property event to the parent"""
        prop = self.GetProperty(prop)
        # prepare the event
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

    def NavigateProp(self, down):
        """change the selected property"""
        activated = self.GetActivated()
        # find the next visible property and activate it
        while True:
            if down:
                activated = activated + 1
            else:
                activated = activated - 1

            if activated < 0 or activated >= self.GetPropCount():
                break

            prop = self.PropList[activated]
            if prop.GetVisible():
                self.SelectProperty(activated)
                self.EnsureVisible(activated)
                break

    def PropHitTest(self, pt):
        """find the property under the mouse"""
        for i, prop in enumerate(self.PropList):
            prop = self.PropList[i]
            if  not prop.GetVisible():
                continue
            if prop.GetClientRect().Contains(pt):
                return i
        return -1

    def AutoSize(self, update=True):
        """layout the properties"""
        rc = self.GetClientRect()
        (w, h) = (rc.width, 1)

        self.CheckProp()
        # calculate the width and height
        for p in self.PropList:
            if p.GetVisible():
                sz = p.GetMinSize()
                w = max(w, sz.x)
                h = h + sz.y
        # need to update the virtual size?
        if update:
            self.SetVirtualSize(wx.Size(w, h))

        # set the property rect
        rc = self.GetClientRect()
        (w, h) = (max(w, rc.width), 1)
        for p in self.PropList:
            if p.GetVisible():
                hh = p.GetMinSize().y
                rc = wx.Rect(0, h, w, hh)
                p.SetClientRect(rc)
                h = h + hh

    def GetDrawRect(self):
        """return the drawing rect"""
        sz = self.GetClientSize()
        windowRect = wx.Rect(0, 0, sz.x, sz.y)

        # We need to shift the client rectangle to take into account
        # scrolling, converting device to logical coordinates
        (windowRect.x, windowRect.y) = self.CalcUnscrolledPosition(windowRect.x, windowRect.y)

        return windowRect

    def CheckProp(self):
        """update the property status"""
        parent = None
        for i, prop in enumerate(self.PropList):
            parent = self.GetProperty(i-1)
            # find the direct parent property
            while parent:
                if parent.GetIndent() < prop.GetIndent():
                    break
                parent = parent.GetParentProp()
            prop.SetParentProp(parent)
            if parent:
                # the parent has children now
                parent.SetHasChildren(True, True)
            # the current one does not have children yet; will be set by its
            # children
            prop.SetHasChildren(False, True)
        # show/hide the properties
        for prop in self.PropList:
            parent = prop.GetParentProp()
            if not parent:
                # always show prop without parent
                show = True
            else:
                # prop with parent depends on parent's status
                show = parent.IsExpanded() and parent.GetVisible()
            prop.SetVisible(show)

    def OnPropRefresh(self, evt):
        """refresh the property, for example, due to value changed"""
        self.SendPropEvent(evt.GetEventType(), evt.GetProperty())
        prop = evt.GetProperty()
        if prop is None:
            return
        rc = prop.GetClientRect()
        (rc.x, rc.y) = self.CalcScrolledPosition(rc.x, rc.y)
        self.RefreshRect(rc, True)

    def OnPropEventsHandler(self, evt):
        """process the property notification"""
        self.SendPropEvent(evt.GetEventType(), evt.GetProperty())
        if evt.GetEventType() in [wxEVT_BSM_PROP_COLLAPSED, wxEVT_BSM_PROP_EXPANDED,
                                  wxEVT_BSM_PROP_INDENT, wxEVT_BSM_PROP_RESIZE]:
            self.UpdateGrid(True, True)

    def OnPropTextEnter(self, evt):
        """send when the enter key is pressed in the property control window"""
        assert self.PropSelected
        if self.PropSelected:
            self.PropSelected.OnTextEnter()
            #self.UpdateGrid(True,True)

    def OnKeyDown(self, evt):
        """key down event"""
        prop = self.PropSelected
        skip = True
        if prop:
            skip = False
            index = self.GetActivated()
            keycode = evt.GetKeyCode()
            indent = prop.GetIndent()
            if keycode == wx.WXK_LEFT:
                if evt.CmdDown():
                    # Ctrl + Left decrease the indent
                    prop.SetIndent(indent-1)
                else:
                    # Left hide children
                    prop.SetExpand(False)
            elif keycode == wx.WXK_UP:
                if evt.CmdDown():
                    # Ctrl + Up move up
                    self.MovePropertyUp(index)
                else:
                    # Up select the above property
                    self.NavigateProp(False)
            elif keycode == wx.WXK_RIGHT:
                if evt.CmdDown():
                    # Ctrl + Right increase the indent
                    prop.SetIndent(indent+1)
                else:
                    # Right show children
                    prop.SetExpand(True)
            elif keycode == wx.WXK_DOWN:
                if evt.CmdDown():
                    # Ctrl + Down move the property down
                    self.MovePropertyDown(index)
                else:
                    # Down select the property below
                    self.NavigateProp(True)
            elif keycode == wx.WXK_DELETE:
                # delete the property
                self.RemoveProperty(self.GetSelectedProperty())
            else:
                skip = True
        if skip:
            evt.Skip()

    def OnPaint(self, event):
        """draw the property"""
        dc = wx.BufferedPaintDC(self)
        self.DoPrepareDC(dc)

        rc = self.GetDrawRect()
        #draw background
        crBg = self.GetBackgroundColour()
        if c2p.bsm_is_phoenix:
            if not crBg.IsOk():
                crBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)
            pen = wx.Pen(wx.BLACK, 1, wx.PENSTYLE_TRANSPARENT)
        else:
            if not crBg.Ok():
                crBg = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE)
            pen = wx.Pen(wx.BLACK, 1, wx.TRANSPARENT)
        dc.SetPen(pen)
        brush = wx.Brush(crBg)
        dc.SetBrush(brush)
        dc.DrawRectangle(rc.x, rc.y, rc.width, rc.height)

        # draw the top edge
        dc.SetPen(wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)))
        dc.DrawLine(rc.left, rc.top, rc.right, rc.top)

        # draw the properties
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
                        p.SetTitleWidth(self.TitleWidth)
                        p.DrawItem(dc)
                        break
                    upd.Next()

    def OnSize(self, evt):
        """resize the properties"""
        # rearrange the size of properties
        self.AutoSize(True)
        self.Refresh()
        evt.Skip()

    def OnEraseBackground(self, evt):
        """redraw the background"""
        #intentionally leave empty to remove the screen flash
        pass

    def OnMouseDown(self, evt):
        """right mouse down"""
        # find the property under mouse
        pt = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt)
        self.ptMouseDown = pt
        # activate the property under mouse
        self.SelectProperty(index)
        if index != -1:
            prop = self.GetProperty(index)
            assert prop and prop == self.PropSelected

            # pass the event to the property
            ht = prop.OnMouseDown(pt)
            self.PropUnderMouse = prop
            self.CaptureMouse()
            self.resizeMode = self.BSMGRID_NONE
            if ht == bsmProperty.PROP_HIT_SPLITTER:
                # drag the splitter
                self.resizeMode = self.BSMGRID_RESIZE_SEP
            elif ht == bsmProperty.PROP_HIT_EDGE_BOTTOM:
                # drag the bottom edge
                self.resizeMode = self.BSMGRID_RESIZE_BOT
            elif ht == bsmProperty.PROP_HIT_EDGE_TOP:
                # drag the bottom edge of the property above
                if index > 0:
                    index = index-1
                    self.PropUnderMouse = self.GetProperty(index)
                    self.resizeMode = self.BSMGRID_RESIZE_BOT
            elif ht == bsmProperty.PROP_HIT_TITLE:
                # start drag & drop
                bsmPropGrid.dragStartPt = self.ClientToScreen(pt)
                bsmPropGrid.dragProperty = prop
                bsmPropGrid.dragPropState = 1
        evt.Skip()

    def OnMouseUp(self, evt):
        """right mouse up"""
        if self.PropUnderMouse:
            pt = self.CalcUnscrolledPosition(evt.GetPosition())
            # pass the event to the property
            self.PropUnderMouse.OnMouseUp(pt)
            self.PropUnderMouse = None

        if self.GetCapture() == self:
            self.ReleaseMouse()

        # finish resizing
        self.ptMouseDown = wx.Point(0, 0)
        self.resizeMode = self.BSMGRID_NONE

        # finish drag & drop
        bsmPropGrid.dragProperty = None
        bsmPropGrid.dragPropState = 0
        bsmPropGrid.dragStartPt = wx.Point(0, 0)

        evt.Skip()

    def OnMouseDoubleClick(self, evt):
        """double click"""
        pt = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt)
        if index != -1:
            # pass the event to the property
            prop = self.GetProperty(index)
            prop.OnMouseDoubleClick(pt)

        evt.Skip()

    def OnMouseCaptureLost(self, evt):
        pass

    def OnMouseMove(self, evt):
        """mouse move"""
        pt = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt)
        prop = None
        if index != -1:
            # pass the event to the property
            prop = self.GetProperty(index)
            prop.OnMouseMove(pt)
        # drag & drop
        if evt.LeftIsDown() and bsmPropGrid.dragProperty and\
           bsmPropGrid.dragPropState == 1:
            pt = self.ClientToScreen(pt)
            start = bsmPropGrid.dragStartPt
            if (start.x-pt.x)**2+(start.y-pt.y)**2 > 10:
                if self.SendPropEvent(wxEVT_BSM_PROP_BEGIN_DRAG, self.dragProperty):
                    # the mouse is moved, so start drag & drop
                    bsmPropGrid.dragPropState = 2
                    bsmPropGrid.dragGrid = self
                    # start drag operation
                    propData = c2p.PyTextDataObject(bsmPropGrid.dragProperty.GetName())
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

        if evt.LeftIsDown() and self.PropUnderMouse:
            # resize the property
            if self.resizeMode == self.BSMGRID_RESIZE_SEP:
                # resize the title width for all properties
                self.TitleWidth = max(min(evt.GetX()-6, self.PropUnderMouse.GetSize().x-50), 50)
                self.Refresh(False)
            elif self.resizeMode == self.BSMGRID_RESIZE_BOT:
                # change the height for the property
                sz = self.PropUnderMouse.GetMinSize()
                sz2 = wx.Size(sz.x, sz.y)
                sz.y += (pt.y- self.ptMouseDown.y)
                sz.y = max(sz.y, 25)
                if sz.y != sz2.y:
                    self.ptMouseDown.x, self.ptMouseDown.y = pt.x, pt.y
                    self.PropUnderMouse.SetMinSize(sz)
            else:
                self.PropUnderMouse.OnMouseMove(pt)
        else:
            if not evt.IsButton():
                # no button is pressed, show the tooltip
                strToolTip = ""
                cursorMode = self.cursorMode
                cursorMode = self.BSMGRID_CURSOR_STD

                if prop:
                    #pass the event to the property
                    ht = prop.OnMouseMove(pt)

                    # change the cursor icon
                    if ht == bsmProperty.PROP_HIT_SPLITTER:
                        cursorMode = self.BSMGRID_CURSOR_RESIZE_HOR
                    elif ht == bsmProperty.PROP_HIT_EDGE_BOTTOM:
                        cursorMode = self.BSMGRID_CURSOR_RESIZE_VER
                    elif ht == bsmProperty.PROP_HIT_EDGE_TOP:
                        if index > 0:
                            cursorMode = self.BSMGRID_CURSOR_RESIZE_VER
                        else:
                            cursorMode = self.BSMGRID_CURSOR_STD
                    else:
                        cursorMode = self.BSMGRID_CURSOR_STD
                    #if prop.GetShowLabelTips() and ht == bsmProperty.PROP_HIT_TITLE:
                    if ht == bsmProperty.PROP_HIT_TITLE:
                        strToolTip = prop.GetLabelTip()
                    elif prop.GetShowValueTips() and ht == bsmProperty.PROP_HIT_VALUE:
                        strToolTip = prop.GetValueTip()
                    elif ht == bsmProperty.PROP_HIT_EXPAND:
                        strToolTip = prop.GetLabelTip()
                # set the tooltip
                if c2p.bsm_is_phoenix:
                    if self.GetToolTipText() != strToolTip:
                        self.SetToolTip(strToolTip)
                else:
                    if self.GetToolTipString() != strToolTip:
                        self.SetToolTipString(strToolTip)
                # set the cursor
                if cursorMode != self.cursorMode:
                    self.cursorMode = cursorMode
                    if cursorMode == self.BSMGRID_CURSOR_RESIZE_HOR:
                        self.SetCursor(self.resizeCursorHor)
                    elif cursorMode == self.BSMGRID_CURSOR_RESIZE_VER:
                        self.SetCursor(self.resizeCursorVer)
                    else:
                        self.SetCursor(wx.NullCursor)
        evt.Skip()

    def OnMouseLeave(self, evt):
        """mouse leaves the window"""
        self.SetCursor(wx.NullCursor)
        evt.Skip()

    def OnMouseRightClick(self, evt):
        """right click"""
        pt = self.CalcUnscrolledPosition(evt.GetPosition())
        index = self.PropHitTest(pt)
        # set the active property
        self.SelectProperty(index)
        if index != -1:
            # pass the event to the property
            prop = self.GetProperty(index)
            prop.OnMouseRightClick(pt)

    def OnDrop(self, x, y, name):
        """drop the property"""
        pt = wx.Point(x, y)
        pt = self.CalcUnscrolledPosition(pt)
        index2 = self.PropHitTest(pt)
        prop = self.GetProperty(index2)
        # insert a property? Let the parent to determine what to do
        if bsmPropGrid.dragProperty == None:
            dp.send('prop.drop', index=index2, prop=name, grid=self)
            return

        if name != bsmPropGrid.dragProperty.GetName():
            # something is wrong
            return

        index = bsmPropGrid.dragGrid.FindPropertyIndex(bsmPropGrid.dragProperty)
        if index == -1:
            # if not find the dragged property, do nothing
            return

        if bsmPropGrid.dragGrid != self:
            # drop the property from the other window, copy it
            indent = bsmPropGrid.dragProperty.GetIndent()
            self.CopyProperty(bsmPropGrid.dragProperty, index2)
            for i in six.moves.range(index+1, bsmPropGrid.dragGrid.GetPropCount()):
                # copy all its children
                child = bsmPropGrid.dragGrid.GetProperty(i)
                if child.GetIndent() <= indent:
                    break
                if index2 != -1:
                    index2 = index2 + 1
                self.CopyProperty(child, index2)
        else:
            # move the property if necessary
            if prop == bsmPropGrid.dragProperty:
                return
            self.doMoveProperty(index, index2)
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

        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_ADD_SEP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_PROP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_INDENT_INS)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_INDENT_DES)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_MOVE_UP)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_MOVE_DOWN)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_READ_ONLY)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_GRID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_BREAKPOINT)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=self.ID_PROP_BREAKPOINT_CLEAR)
        # if num is not defined or is occupied, generate a new one
        if num is None or num in bsmPropGrid.GCM.get_nums():
            num = bsmPropGrid.GCM.get_next_num()
        self.num = num
        bsmPropGrid.GCM.set_active(self)

    def Destroy(self):
        self.DeleteAllProperties()
        bsmPropGrid.GCM.destroy_mgr(self)
        super(bsmPropGrid, self).Destroy()

    def OnPropEventsHandler(self, evt):
        super(bsmPropGrid, self).OnPropEventsHandler(evt)
        # TODO disable the event processing if it is rejected by the parent
        prop = evt.GetProperty()
        eid = evt.GetEventType()
        if eid == wxEVT_BSM_PROP_RIGHT_CLICK:
            # show the context menu
            menu = wx.Menu()
            menu.Append(self.ID_PROP_GRID_ADD_SEP, "&Add separator")
            menu.AppendCheckItem(self.ID_PROP_GRID_READ_ONLY, "&Read only")
            bEnable = True
            menu.Enable(self.ID_PROP_GRID_READ_ONLY, bEnable)
            menu.Check(self.ID_PROP_GRID_READ_ONLY, prop.GetReadOnly())
            menu.AppendSeparator()
            menu.Append(self.ID_PROP_BREAKPOINT, "Breakpoint Condition")
            menu.Enable(self.ID_PROP_BREAKPOINT, prop.IsRadioChecked())
            menu.Append(self.ID_PROP_BREAKPOINT_CLEAR, "Clear all Breakpoints")
            menu.AppendSeparator()
            menu.Append(self.ID_PROP_GRID_INDENT_INS, "Increase Indent\tCtrl-Right")
            menu.Append(self.ID_PROP_GRID_INDENT_DES, "Decrease Indent\tCtrl-Left")
            menu.AppendSeparator()
            menu.Append(self.ID_PROP_GRID_MOVE_UP, "Move up\tCtrl-Up")
            menu.Append(self.ID_PROP_GRID_MOVE_DOWN, "Move down\tCtrl-Down")
            menu.AppendSeparator()
            menu.Append(self.ID_PROP_GRID_DELETE, "&Delete")
            menu.AppendSeparator()
            menu.Append(self.ID_PROP_GRID_PROP, "&Properties")

            self.PopupMenu(menu)
            menu.Destroy()
        elif eid == wxEVT_BSM_PROP_CLICK_RADIO:
            # turn on/off breakpoint
            if prop.IsRadioChecked():
                dp.send('prop.bp_add', prop=prop)
            else:
                dp.send('prop.bp_del', prop=prop)
        elif eid == wxEVT_BSM_PROP_CHANGED:
            # the value changed, notify the parent
            dp.send('prop.changed', prop=prop)

    def OnProcessCommand(self, evt):
        """process the context menu command"""
        eid = evt.GetId()
        prop = self.GetSelectedProperty()
        if not prop: return
        if eid == self.ID_PROP_GRID_DELETE:
            self.DeleteProperty(prop)
        elif eid == self.ID_PROP_GRID_READ_ONLY:
            prop.SetReadOnly(not prop.GetReadOnly())
        elif eid == self.ID_PROP_GRID_PROP:
            dlg = dlgSettings(self, prop)
            if dlg.ShowModal() == wx.ID_OK:
                prop.Refresh()
        elif eid == self.ID_PROP_GRID_INDENT_INS:
            prop.SetIndent(prop.GetIndent()+1)
        elif eid == self.ID_PROP_GRID_INDENT_DES:
            prop.SetIndent(prop.GetIndent()-1)
        elif eid == self.ID_PROP_GRID_MOVE_UP:
            self.MoveProperty(prop, -1)
        elif eid == self.ID_PROP_GRID_MOVE_DOWN:
            self.MoveProperty(prop, 2)
        elif eid == self.ID_PROP_GRID_ADD_SEP:
            self.InsertSeparator("", self.GetActivated())
        elif eid == self.ID_PROP_BREAKPOINT:
            condition = prop.GetBPCondition()
            dlg = BreakpointSettingsDlg(self, condition[0], condition[1])
            if dlg.ShowModal() == wx.ID_OK:
                prop.SetBPCondition(dlg.GetCondition())
        elif eid == self.ID_PROP_BREAKPOINT_CLEAR:
            self.clearBreakPoints()

    def clearBreakPoints(self):
        """clear all the breakpoints"""
        for prop in self.PropList:
            if prop and prop.IsRadioChecked():
                prop.SetRadioChecked(False)

    def triggerBreakPoint(self, name, cond, hitcount):
        """check whether the breakpoints are triggered"""
        for prop in self.PropList:
            if name == prop.GetName():
                if (cond, hitcount) == prop.GetBPCondition():
                    self.EnsureVisible(prop)
                    self.SelectProperty(prop)
                    return True

class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition='', hitcount=''):
        wx.Dialog.__init__(self, parent, title="Breakpoint Condition",
                           size=wx.Size(431, 289),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        szAll = wx.BoxSizer(wx.VERTICAL)
        label = ("At the end of each delta cycle, the expression is evaluated "
                 "and the breakpoint is hit only if the expression is true or "
                 "the register value has changed")
        self.stInfo = wx.StaticText(self, label=label)
        self.stInfo.Wrap(-1)
        szAll.Add(self.stInfo, 1, wx.ALL, 15)

        szCnd = wx.BoxSizer(wx.HORIZONTAL)

        szCnd.AddSpacer((20, 0), 0, wx.EXPAND, 5)

        szCond = wx.BoxSizer(wx.VERTICAL)

        self.rbChanged = wx.RadioButton(self, label="Has changed", style=wx.RB_GROUP)
        szCond.Add(self.rbChanged, 5, wx.ALL|wx.EXPAND, 5)

        label = "Is true (value: $; for example, $==10)"
        self.rbCond = wx.RadioButton(self, label=label)
        szCond.Add(self.rbCond, 0, wx.ALL|wx.EXPAND, 5)

        self.tcCond = wx.TextCtrl(self)
        szCond.Add(self.tcCond, 0, wx.ALL|wx.EXPAND, 5)

        label = "Hit count (hit count: #; for example, #>10"
        self.cbHitCount = wx.CheckBox(self, label=label)
        szCond.Add(self.cbHitCount, 0, wx.ALL, 5)

        self.tcHitCount = wx.TextCtrl(self)
        szCond.Add(self.tcHitCount, 0, wx.ALL|wx.EXPAND, 5)


        szCnd.Add(szCond, 1, wx.EXPAND, 5)


        szAll.Add(szCnd, 1, wx.EXPAND, 5)

        self.stLine = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.stLine, 0, wx.EXPAND |wx.ALL, 5)

        szConfirm = wx.BoxSizer(wx.HORIZONTAL)

        self.btnOK = wx.Button(self, wx.ID_OK, u"OK")
        szConfirm.Add(self.btnOK, 0, wx.ALL, 5)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"Cancel")
        szConfirm.Add(self.btnCancel, 0, wx.ALL, 5)

        szAll.Add(szConfirm, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szAll)
        self.Layout()

        # initialize the controls
        self.condition = condition
        self.hitcount = hitcount
        self.SetSizer(szAll)
        self.Layout()
        if self.condition == '':
            self.rbChanged.SetValue(True)
            self.tcCond.Disable()
        else:
            self.rbChanged.SetValue(False)
            self.rbCond.SetValue(True)
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

    def OnRadioButton(self, event):
        if self.rbChanged.GetValue():
            self.tcCond.Disable()
        else:
            self.tcCond.Enable()
        if self.cbHitCount.GetValue():
            self.tcHitCount.Enable()
        else:
            self.tcHitCount.Disable()
        event.Skip()
    def OnBtnOK(self, event):
        # set condition to empty string to indicate the breakpoint will be
        # triggered when the value is changed
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
    def __init__(self, parent, prop):
        wx.Dialog.__init__(self, parent, title=u"Settings...",
                           size=wx.Size(402, 494),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        sz = wx.BoxSizer(wx.VERTICAL)

        self.propgrid = bsmPropGridBase(self)
        self.prop = prop
        if prop.GetSeparator():
            self.items = (('label', 'Label', '', PROP_CTRL_EDIT),
                          ('indent', 'Indent level', '', PROP_CTRL_SPIN),
                          ('italic', 'Italic', '', PROP_CTRL_CHECK))
        else:
            self.items = (('name', 'Name', '', PROP_CTRL_EDIT),
                          ('label', 'Label', '', PROP_CTRL_EDIT),
                          ('value', 'Value', '', PROP_CTRL_EDIT),
                          ('description', 'Description', 'text shown next to the value', PROP_CTRL_EDIT),
                          ('valueMax', 'Max value', '', PROP_CTRL_SPIN),
                          ('valueMin', 'Min value', '', PROP_CTRL_SPIN),
                          ('indent', 'Indent level', '', PROP_CTRL_SPIN),
                          ('showRadio', 'Show breakpoint', '', PROP_CTRL_CHECK),
                          ('enable', 'Enable', '', PROP_CTRL_CHECK),
                          ('italic', 'Italic', '', PROP_CTRL_CHECK),
                          ('readOnly', 'Read only', '', PROP_CTRL_CHECK),
                          ('ctrlType', 'Control window type', '', PROP_CTRL_COMBO),
                          ('choiceList', 'Choice list', 'separate by ";"', PROP_CTRL_EDIT),
                          ('valueList', 'Value list', 'separate by ";"', PROP_CTRL_EDIT),
                          ('textColor', 'Normal text color', '', PROP_CTRL_COLOR),
                          ('textColorSel', 'Selected text color', '', PROP_CTRL_COLOR),
                          ('textColorDisable', 'Disable text color', '', PROP_CTRL_COLOR),
                          ('bgColor', 'Normal background color', '', PROP_CTRL_COLOR),
                          ('bgColorSel', 'Selected background color', '', PROP_CTRL_COLOR),
                          ('bgColorDisable', 'Disable background color', '', PROP_CTRL_COLOR))
                          #('showLabelTips', 'Show label tips', PROP_CTRL_CHECK),
                          #('showValueTips', 'Show value tips', PROP_CTRL_CHECK))
        p = self.propgrid
        for (name, label, tip, ctrl) in self.items:
            pp = p.InsertProperty(name, label, '')
            if prop:
                v = getattr(prop, name)
            else:
                v = ""
            pp.SetLabelTip(label)
            pp.SetValueTip(tip)
            if name == 'ctrlType':
                choice = ['default', 'none', 'editbox', 'combobox',
                          'select file button', 'select folder button',
                          'slider', 'spin', 'checkbox', 'radio button',
                          'colorpicker']
                value = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
                pp.SetChoice(choice, value)
            if name in ['choiceList', 'valueList']:
                pp.SetValue(';'.join(v))
            elif ctrl == PROP_CTRL_CHECK:
                pp.SetValue(str(v+0))
                pp.SetDescription(str(v))
            elif ctrl == PROP_CTRL_COLOR:
                pp.SetValue(v)
                pp.SetBGColor(v, v, v)
                t = wx.Colour(v)
                t.SetRGB(t.GetRGB()^0xffffff)
                t = t.GetAsString(wx.C2S_HTML_SYNTAX)
                pp.SetTextColor(t, t, t)
            elif ctrl in [PROP_CTRL_SPIN, PROP_CTRL_SLIDER]:
                pp.SetRange(2**31-1, -2**31)
                pp.SetValue(str(v))
            else:
                pp.SetValue(str(v))
            pp.SetShowRadio(False)
            pp.SetControlStyle(ctrl)

        sz.Add(self.propgrid, 1, wx.EXPAND | wx.ALL, 1)

        self.stcline = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        sz.Add(self.stcline, 0, wx.EXPAND | wx.ALL, 5)

        sz2 = wx.BoxSizer(wx.HORIZONTAL)

        self.btnOK = wx.Button(self, wx.ID_OK, u"&Ok")
        sz2.Add(self.btnOK, 0, wx.ALL, 5)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL, u"&Cancel")
        sz2.Add(self.btnCancel, 0, wx.ALL, 5)

        sz.Add(sz2, 0, wx.ALIGN_RIGHT|wx.RIGHT, 5)

        self.SetSizer(sz)
        self.Layout()

        # Connect Events
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOk)
        self.btnCancel.Bind(wx.EVT_BUTTON, self.OnBtnCancel)


    def OnBtnOk(self, event):
        if self.propgrid.PropSelected:
            self.propgrid.PropSelected.OnTextEnter()
        for (name, _, _, ctrl) in self.items:
            v = self.propgrid.GetProperty(name)
            if name in ['choiceList', 'valueList']:
                setattr(self.prop, name, v.GetValue().split(';'))
            elif ctrl == PROP_CTRL_CHECK:
                setattr(self.prop, name, bool(int(v.GetValue())))
            elif name == 'ctrlType':
                self.prop.SetControlStyle(int(v.GetValue()))
            else:
                setattr(self.prop, name, type(getattr(self.prop, name))(v.GetValue()))
        event.Skip()

    def OnBtnCancel(self, event):
        event.Skip()
