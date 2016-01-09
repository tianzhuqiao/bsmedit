import wx
import wx.lib.agw.aui as aui
import wx.py.dispatcher as dispatcher

class AuiFloatingFramePlus(aui.AuiFloatingFrame):
    def __init__(self, parent, owner_mgr, pane=None, id=wx.ID_ANY, title='',
                 style=wx.FRAME_TOOL_WINDOW | wx.FRAME_NO_TASKBAR |
                 wx.CLIP_CHILDREN):
        aui.AuiFloatingFrame.__init__(self, parent, owner_mgr, pane=pane,
                                      id=id, title=title, style=style)

class AuiManagerPlus(aui.AuiManager):
    def __init__(self, managed_window=None, agwFlags=None):
        aui.AuiManager.__init__(self, managed_window=managed_window,
                                agwFlags=agwFlags)

    def RefreshPaneCaption(self, window):
        if window is None:
            return
        pane = self.GetPane(window)
        if not pane.IsOk():
            return
        parent = window.GetParent()
        if parent is None:
            return
        if pane.IsNotebookPage() and isinstance(parent, aui.auibook.AuiNotebook):
            idx = parent.GetPageIndex(window)
            parent.SetPageText(idx, pane.caption)
            if idx == parent.GetSelection():
                for paneInfo in self.GetAllPanes():
                    if paneInfo.IsNotebookControl() \
                        and paneInfo.notebook_id == pane.notebook_id:
                        paneInfo.Caption(pane.caption)
                        self.RefreshCaptions()
                        break
        else:
            self.RefreshCaptions()
            parent.Update()

    def CreateFloatingFrame(self, parent, pane_info):
        """
        Creates a floating frame for the windows.

        :param Window `parent`: the floating frame parent;
        :param `pane_info`: the :class:`AuiPaneInfo` class with all the pane's information.
    ...."""

        return AuiFloatingFramePlus(parent, self, pane_info)

    # fix the bug: it seems that the paneInfo.rect is not update correctly, so
    # use the window true rect

    def PaneHitTest(self, panes, pt):
        """
        Similar to :meth:`HitTest`, but it checks in which :class:`AuiManager`
        rectangle the input point belongs to.

        :param `panes`: a list of :class:`AuiPaneInfo` instances;
        :param Point `pt`: the mouse position.
        """

        screenPt = self._frame.ClientToScreen(pt)
        for paneInfo in panes:
            rc = paneInfo.window.GetScreenRect()
            if paneInfo.IsDocked() and paneInfo.IsShown() \
                and rc.Contains(screenPt):
                if paneInfo.IsNotebookPage():
                    nb = self.GetNotebooks()
                    paneInfo = self.GetPane(nb[paneInfo.notebook_id])
                return paneInfo

        return aui.framemanager.NonePaneInfo

    # fix the bug: when drag the pane, call the Update() to update the
    # notebook, otherwise, the order of the notebookpage is wrong

    def OnLeftUp(self, event):
        """
        Handles the ``wx.EVT_LEFT_UP`` event for :class:`AuiManager`.

        :param `event`: a :class:`MouseEvent` to be processed.
        """

        update = False
        if self._action == aui.actionResize:
            update = False
        elif self._action == aui.actionClickButton:
            update = False
        elif self._action == aui.actionDragFloatingPane:
            update = True
        elif self._action == aui.actionDragToolbarPane:
            update = False
        elif self._action == aui.actionDragMovablePane:
            update = True
        super(AuiManagerPlus, self).OnLeftUp(event)
        if update:
            self.Update()

    def OnMotion_Resize(self, event):
        """
        Sub-handler for the :meth:`OnMotion` event.

        :param `event`: a :class:`MouseEvent` to be processed.
        """

        if aui.AuiManager_HasLiveResize(self):
            if self._currentDragItem != -1:
                self._action_part = self._uiparts[self._currentDragItem]
            else:
                self._currentDragItem = self._uiparts.index(self._action_part)

            if self._frame.HasCapture():
                self._frame.ReleaseMouse()

            self.DoEndResizeAction(event)
            self._frame.CaptureMouse()
            return

        if not self._action_part or not self._action_part.dock or\
           not self._action_part.orientation:
            return

        clientPt = event.GetPosition()
        screenPt = self._frame.ClientToScreen(clientPt)

        dock = self._action_part.dock
        pos = self._action_part.rect.GetPosition()

        if self._action_part.type == aui.AuiDockUIPart.typeDockSizer:
            minPix, maxPix = self.CalculateDockSizerLimits(dock)
        else:
            if not self._action_part.pane:
                return

            pane = self._action_part.pane
            minPix, maxPix = self.CalculatePaneSizerLimits(dock, pane)

        if self._action_part.orientation == wx.HORIZONTAL:
            pos.y = aui.Clip(clientPt.y - self._action_offset.y, minPix, maxPix)
        else:
            pos.x = aui.Clip(clientPt.x - self._action_offset.x, minPix, maxPix)
        hintrect = wx.RectPS(pos, self._action_part.rect.GetSize())

        if hintrect != self._action_rect:

            dc = wx.ClientDC(self._frame)
            aui.DrawResizeHint(dc, self._action_rect)
            aui.DrawResizeHint(dc, hintrect)
            self._action_rect = wx.Rect(*hintrect)

class framePlus(wx.Frame):
    PANE_NUM = 0
    def __init__(self, parent, id=wx.ID_ANY, title=u'BSMEdit',
                 pos=wx.DefaultPosition, size=wx.Size(800, 600),
                 style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL):
        wx.Frame.__init__(self, parent, id=id, title=title, pos=pos, size=size,
                          style=style)
        self._mgr = AuiManagerPlus()
        self._mgr.SetManagedWindow(self)
        self.menuaddon = {}
        self.paneaddon = {}
        dispatcher.connect(receiver=self.addMenu, signal='frame.add_menu')
        dispatcher.connect(receiver=self.delMenu, signal='frame.del_menu')
        dispatcher.connect(receiver=self.addPanel, signal='frame.add_panel')
        dispatcher.connect(receiver=self.closePanel, signal='frame.close_panel')
        dispatcher.connect(receiver=self.showPanel, signal='frame.show_panel')
        dispatcher.connect(receiver=self.TogglePanel, signal='frame.check_menu')
        dispatcher.connect(receiver=self.TogglePanelUI, signal='frame.update_menu')

    def getMenu(self, pathlist):
        """find the menu item"""
        # the top level menu
        menuidx = self.GetMenuBar().FindMenu(pathlist[0])
        if menuidx == wx.NOT_FOUND:
            return None

        menuitem = self.GetMenuBar().GetMenu(menuidx)
        if menuitem is None:
            return None
        for p in pathlist[1:]:
            for m in range(menuitem.GetMenuItemCount()):
                stritem = menuitem.FindItemByPosition(m).GetItemLabelText()
                stritem = stritem.split('\t')[0]
                if stritem == p:
                    menuitem = menuitem.FindItemByPosition(m).GetSubMenu()
                    break
        return menuitem

    def addMenu(self, path, rxsignal, updatesignal=None, kind='Normal'):
        """
        add the item to menubar

        Support menu kind: 'Separator', 'Normal', 'Check', 'Radio', 'Popup'
        """

        pathlist = path.split(':')
        menuitem = self.getMenu(pathlist[:-1])
        if menuitem is None:
            return wx.NOT_FOUND

        if kind == 'Separator':
            menuitem.AppendSeparator()
        elif kind == 'Popup':
            menuitem.AppendSubMenu(wx.Menu(), pathlist[-1])
        else:
            newid = wx.NewId()
            if kind == 'Normal':
                newitem = wx.MenuItem(menuitem, newid, pathlist[-1],
                                      pathlist[-1], kind=wx.ITEM_NORMAL)
            elif kind == 'Check':
                newitem = wx.MenuItem(menuitem, newid, pathlist[-1],
                                      pathlist[-1], kind=wx.ITEM_CHECK)
            elif kind == 'Radio':
                newitem = wx.MenuItem(menuitem, newid, pathlist[-1],
                                      pathlist[-1], kind=wx.ITEM_RADIO)
            self.menuaddon[newid] = (rxsignal, updatesignal)
            menuitem.AppendItem(newitem)
            self.Bind(wx.EVT_MENU, self.OnMenuAddOn, id=newid)
            if updatesignal:
                self.Bind(wx.EVT_UPDATE_UI, self.OnMenuCmdUI, id=newid)

            return newid

    def delMenu(self, path, id):
        """delete the menu item"""
        pathlist = path.split(':')
        menuitem = self.getMenu(pathlist[:-1])
        if menuitem is None:
            return wx.NOT_FOUND

        item = menuitem.FindItemById(id)
        if item is None:
            return wx.NOT_FOUND
        menuitem.DeleteItem(item)
        self.Unbind(wx.EVT_MENU, id=id)
        del self.menuaddon[id]

        return id

    def OnMenuAddOn(self, event):
        idx = event.GetId()
        signal = self.menuaddon.get(idx, None)
        if signal:
            signal = signal[0]
            dispatcher.send(signal=signal, command=idx)

    def OnMenuCmdUI(self, event):
        idx = event.GetId()
        signal = self.menuaddon.get(idx, None)
        if signal:
            signal = signal[1]
            dispatcher.send(signal=signal, event=event)
        else:
            event.Enable(True)

    def addPanel(self, panel, title='Untitle', active=True, paneInfo=None,
                 target=None, showhidemenu=None):
        """add the panel to AUI"""
        if not panel:
            return False
        panel.Reparent(self)
        # if the target is None, find the notebook control that has the same
        # type as panel. It tries to put the same type panels in the same
        # notebook
        if target is None:
            for pane in self._mgr.GetAllPanes():
                if isinstance(pane.window, type(panel)):
                    target = pane.window
                    break
        elif isinstance(target, str):
            # find the target panel with caption
            for pane in self._mgr.GetAllPanes():
                if pane.caption == target:
                    target = pane.window
                    break
        targetpane = None
        try:
            if target:
                targetpane = self._mgr.GetPane(target)
                if targetpane and not targetpane.IsOk():
                    targetpane = None
        except:
            targetpane = None

        auipaneinfo = paneInfo

        if auipaneinfo is None:
            # default panel settings
            auipaneinfo = \
                aui.AuiPaneInfo().Caption(title).BestSize((300, 300))\
                   .DestroyOnClose(not showhidemenu).Top().Snappable()\
                   .Dockable().Layer(1).Position(1)\
                   .MinimizeButton(True).MaximizeButton(True)

        # auto generate the unique panel name
        name = "pane-%d"%framePlus.PANE_NUM
        framePlus.PANE_NUM += 1
        auipaneinfo.Name(name)

        # if showhidemenu is false, the panel will be destroy when clicking
        # on the close button; otherwise it will be hidden
        auipaneinfo.bsm_destroyonclose = not showhidemenu
        self._mgr.AddPane(panel, auipaneinfo, target=targetpane)
        if active:
            self.showPanel(panel)
        else:
            self.showPanel(panel, False)
            self._mgr.Update()

        # add the menu item to show/hide the panel
        if showhidemenu:
            id = self.addMenu(showhidemenu, 'frame.check_menu',
                              updatesignal='frame.update_menu', kind='Check')
            if id != wx.NOT_FOUND:
                self.paneaddon[id] = {'panel':panel, 'path':showhidemenu}
        return True

    def closePanel(self, panel):
        """hide and destroy the panel"""
        # delete the show hide menu
        for (id, pane) in self.paneaddon.items():
            if panel == pane['panel']:
                self.delMenu(pane['path'], id)
                del self.paneaddon[id]
                break

        # delete the pane from the manager
        pane = self._mgr.GetPane(panel)
        if pane is None or not pane.IsOk():
            return False
        pane.bsm_destroyonclose = True
        self._mgr.ClosePane(pane)
        self._mgr.Update()
        return True

    def showPanel(self, panel, show=True, focus=False):
        """show/hide the panel"""
        pane = self._mgr.GetPane(panel)
        if pane is None or not pane.IsOk():
            return False
        self._mgr.ShowPane(panel, show)
        if focus:
            panel.SetFocus()
        return True

    def TogglePanel(self, command):
        """toggle the display of the panel"""
        pane = self.paneaddon.get(command, None)
        if not pane:
            return
        panel = pane['panel']
        # find the first hidden parent. Otherwise, the panel may be hidden while
        # IsShown() returns True
        show = panel.IsShown()
        parent = panel.GetParent()
        while show and parent:
            show = parent.IsShown()
            parent = parent.GetParent()
        if pane:
            self.showPanel(panel, not show)

    def TogglePanelUI(self, event):
        """update the menu checkbox"""
        pane = self.paneaddon.get(event.GetId(), None)
        if not pane:
            return
        panel = pane['panel']
        show = panel.IsShown()
        parent = panel.GetParent()
        while show and parent:
            show = parent.IsShown()
            parent = parent.GetParent()
        event.Check(show)
