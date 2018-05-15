import six
import wx
import wx.lib.agw.aui as aui
import wx.py.dispatcher as dp
from wx.lib.agw.aui import AuiPaneButton, AuiPaneInfo
from wx.lib.agw.aui.aui_constants import AUI_BUTTON_MINIMIZE,\
                                 AUI_BUTTON_MAXIMIZE_RESTORE, AUI_BUTTON_CLOSE
from . import c2p

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

    def UpdateNotebook(self):
        """ Updates the automatic :class:`~lib.agw.aui.auibook.AuiNotebook` in
        the layout (if any exists). """

        # Workout how many notebooks we need.
        max_notebook = -1

        # destroy floating panes which have been
        # redocked or are becoming non-floating
        for paneInfo in self._panes:
            if max_notebook < paneInfo.notebook_id:
                max_notebook = paneInfo.notebook_id

        # We are the master of our domain
        extra_notebook = len(self._notebooks)
        max_notebook += 1

        for i in six.moves.range(extra_notebook, max_notebook):
            self.CreateNotebook()

        # Remove pages from notebooks that no-longer belong there ...
        for nb, notebook in enumerate(self._notebooks):
            pages = notebook.GetPageCount()
            pageCounter, allPages = 0, pages

            # Check each tab ...
            for page in six.moves.range(pages):

                if page >= allPages:
                    break

                window = notebook.GetPage(pageCounter)
                paneInfo = self.GetPane(window)
                if paneInfo.IsOk() and paneInfo.notebook_id != nb:
                    notebook.RemovePage(pageCounter)
                    window.Hide()
                    window.Reparent(self._frame)
                    pageCounter -= 1
                    allPages -= 1

                pageCounter += 1

            notebook.DoSizing()

        # Add notebook pages that aren't there already...
        for paneInfo in self._panes:
            if paneInfo.IsNotebookPage():

                title = (paneInfo.caption == "" and [paneInfo.name] or [paneInfo.caption])[0]

                notebook = self._notebooks[paneInfo.notebook_id]
                page_id = notebook.GetPageIndex(paneInfo.window)

                if page_id < 0:

                    paneInfo.window.Reparent(notebook)
                    notebook.AddPage(paneInfo.window, title, True, paneInfo.icon)

                # Update title and icon ...
                else:

                    notebook.SetPageText(page_id, title)
                    notebook.SetPageBitmap(page_id, paneInfo.icon)

                notebook.DoSizing()

            # Wire-up newly created notebooks
            elif paneInfo.IsNotebookControl() and not paneInfo.window:
                paneInfo.window = self._notebooks[paneInfo.notebook_id]

        # Delete empty notebooks, and convert notebooks with 1 page to
        # normal panes...
        remap_ids = [-1]*len(self._notebooks)
        nb_idx = 0

        for nb, notebook in enumerate(self._notebooks):
            if notebook.GetPageCount() == 1:

                # Convert notebook page to pane...
                window = notebook.GetPage(0)
                child_pane = self.GetPane(window)
                notebook_pane = self.GetPane(notebook)
                if child_pane.IsOk() and notebook_pane.IsOk():

                    child_pane.SetDockPos(notebook_pane)
                    child_pane.window.Hide()
                    child_pane.window.Reparent(self._frame)
                    child_pane.frame = None
                    child_pane.notebook_id = -1
                    if notebook_pane.IsFloating():
                        child_pane.Float()

                    self.DetachPane(notebook)

                    notebook.RemovePage(0)
                    notebook.Destroy()

                else:

                    raise Exception("Odd notebook docking")

            elif notebook.GetPageCount() == 0:

                self.DetachPane(notebook)
                notebook.Destroy()

            else:

                # Correct page ordering. The original wxPython code
                # for this did not work properly, and would misplace
                # windows causing errors.
                notebook.Freeze()
                self._notebooks[nb_idx] = notebook
                pages = notebook.GetPageCount()
                selected = notebook.GetPage(notebook.GetSelection())

                # Take each page out of the notebook, group it with
                # its current pane, and sort the list by pane.dock_pos
                # order
                pages_and_panes = []
                dock_pos = -1
                needUpdate = False
                for idx in reversed(six.moves.range(pages)):
                    page = notebook.GetPage(idx)
                    pane = self.GetPane(page)
                    pages_and_panes.append((page, pane))
                    # notebook.RemovePage(idx)
                    # check if the notebook needs to be updated to avoid
                    # unnecessary remove/insert operation, especially when
                    # resizing the window
                    if dock_pos == -1:
                        dock_pos = pane.dock_pos
                    elif dock_pos < pane.dock_pos:
                        needUpdate = True
                        dock_pos = pane.dock_pos

                if needUpdate:
                    sorted_pnp = sorted(pages_and_panes, key=lambda tup: tup[1].dock_pos)
                    for idx in reversed(six.moves.range(pages)):
                        notebook.RemovePage(idx)
                    # Grab the attributes from the panes which are ordered
                    # correctly, and copy those attributes to the original
                    # panes. (This avoids having to change the ordering
                    # of self._panes) Then, add the page back into the notebook
                    sorted_attributes = [self.GetAttributes(tup[1])
                                         for tup in sorted_pnp]
                    for attrs, tup in zip(sorted_attributes, pages_and_panes):
                        pane = tup[1]
                        self.SetAttributes(pane, attrs)
                        notebook.AddPage(pane.window, pane.caption)

                notebook.SetSelection(notebook.GetPageIndex(selected), True)
                notebook.DoSizing()
                notebook.Thaw()

                # It's a keeper.
                remap_ids[nb] = nb_idx
                nb_idx += 1

        # Apply remap...
        nb_count = len(self._notebooks)

        if nb_count != nb_idx:

            self._notebooks = self._notebooks[0:nb_idx]
            for p in self._panes:
                if p.notebook_id >= 0:
                    p.notebook_id = remap_ids[p.notebook_id]
                    if p.IsNotebookControl():
                        p.SetNameFromNotebookId()

        # Make sure buttons are correct ...
        for notebook in self._notebooks:
            want_max = True
            want_min = True
            want_close = True

            pages = notebook.GetPageCount()
            for page in six.moves.range(pages):

                win = notebook.GetPage(page)
                pane = self.GetPane(win)
                if pane.IsOk():

                    if not pane.HasCloseButton():
                        want_close = False
                    if not pane.HasMaximizeButton():
                        want_max = False
                    if not pane.HasMinimizeButton():
                        want_min = False

            notebook_pane = self.GetPane(notebook)
            if notebook_pane.IsOk():
                if notebook_pane.HasMinimizeButton() != want_min:
                    if want_min:
                        button = AuiPaneButton(AUI_BUTTON_MINIMIZE)
                        notebook_pane.state |= AuiPaneInfo.buttonMinimize
                        notebook_pane.buttons.append(button)

                    # todo: remove min/max

                if notebook_pane.HasMaximizeButton() != want_max:
                    if want_max:
                        button = AuiPaneButton(AUI_BUTTON_MAXIMIZE_RESTORE)
                        notebook_pane.state |= AuiPaneInfo.buttonMaximize
                        notebook_pane.buttons.append(button)

                    # todo: remove min/max

                if notebook_pane.HasCloseButton() != want_close:
                    if want_close:
                        button = AuiPaneButton(AUI_BUTTON_CLOSE)
                        notebook_pane.state |= AuiPaneInfo.buttonClose
                        notebook_pane.buttons.append(button)

                    # todo: remove close

        # update the icon to the notebook page
        for paneInfo in self._panes:
            if paneInfo.IsNotebookPage():
                notebook = self._notebooks[paneInfo.notebook_id]
                page_id = notebook.GetPageIndex(paneInfo.window)
                if page_id >= 0:
                    notebook.SetPageBitmap(page_id, paneInfo.icon)

                notebook.DoSizing()

class FramePlus(wx.Frame):
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
        dp.connect(self.addMenu, 'frame.add_menu')
        dp.connect(self.delMenu, 'frame.del_menu')
        dp.connect(self.addPanel, 'frame.add_panel')
        dp.connect(self.closePanel, 'frame.close_panel')
        dp.connect(self.showPanel, 'frame.show_panel')
        dp.connect(self.togglePanel, 'frame.check_menu')
        dp.connect(self.togglePanelUI, 'frame.update_menu')
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self._mgr.UnInit()
        del self._mgr
        event.Skip()

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
            for m in six.moves.range(menuitem.GetMenuItemCount()):
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
            if c2p.bsm_is_phoenix:
                menuitem.Append(newitem)
            else:
                menuitem.AppendItem(newitem)
            self.Bind(wx.EVT_MENU, self.OnMenuAddOn, id=newid)
            if updatesignal:
                self.Bind(wx.EVT_UPDATE_UI, self.OnMenuCmdUI, id=newid)

            return newid

    def delMenu(self, path, id=None):
        """delete the menu item"""
        pathlist = path.split(':')
        menuitem = self.getMenu(pathlist[:-1])
        if menuitem is None:
            return wx.NOT_FOUND
        if id is None:
            for m in six.moves.range(menuitem.GetMenuItemCount()):
                item = menuitem.FindItemByPosition(m)
                stritem = item.GetItemLabelText()
                stritem = stritem.split('\t')[0]
                if stritem == pathlist[-1] and item.IsSubMenu():
                    menuitem.DestroyItem(item)
                    return True
        else:
            item = menuitem.FindItemById(id)
            if item is None:
                return wx.NOT_FOUND
            menuitem.DestroyItem(item)
            self.Unbind(wx.EVT_MENU, id=id)
            del self.menuaddon[id]

            return id

    def OnMenuAddOn(self, event):
        idx = event.GetId()
        signal = self.menuaddon.get(idx, None)
        if signal:
            signal = signal[0]
            dp.send(signal=signal, command=idx)

    def OnMenuCmdUI(self, event):
        idx = event.GetId()
        signal = self.menuaddon.get(idx, None)
        if signal:
            signal = signal[1]
            dp.send(signal=signal, event=event)
        else:
            event.Enable(True)

    def addPanel(self, panel, title='Untitle', active=True, paneInfo=None,
                 target=None, showhidemenu=None, icon=None, maximize=False):
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
        elif isinstance(target, six.string_types):
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
                   .MinimizeButton(True).MaximizeButton(True).Icon(icon)
            if not self._mgr.GetAllPanes():
                # set the first pane to be center pane
                auipaneinfo = auipaneinfo.CenterPane()
        # auto generate the unique panel name
        name = "pane-%d"%FramePlus.PANE_NUM
        FramePlus.PANE_NUM += 1
        auipaneinfo.Name(name)

        # if showhidemenu is false, the panel will be destroy when clicking
        # on the close button; otherwise it will be hidden
        panel.bsm_destroyonclose = not showhidemenu
        self._mgr.AddPane(panel, auipaneinfo, target=targetpane)
        if maximize:
            self._mgr.MaximizePane(auipaneinfo)
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
        for (pid, pane) in six.iteritems(self.paneaddon):
            if panel == pane['panel']:
                self.delMenu(pane['path'], pid)
                del self.paneaddon[pid]
                break

        # delete the pane from the manager
        pane = self._mgr.GetPane(panel)
        if pane is None or not pane.IsOk():
            return False
        panel.bsm_destroyonclose = True
        pane.DestroyOnClose(True)
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

    def togglePanel(self, command):
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

    def togglePanelUI(self, event):
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
