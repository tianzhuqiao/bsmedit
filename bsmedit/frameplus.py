import six
import wx
import wx.lib.agw.aui as aui
import wx.py.dispatcher as dp
from . import c2p

class AuiManagerPlus(aui.AuiManager):
    def __init__(self, managed_window=None, agwFlags=None):
        aui.AuiManager.__init__(self, managed_window=managed_window,
                                agwFlags=agwFlags)

    def RefreshPaneCaption(self, window):
        """used to rename a panel"""
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

    def UpdateNotebook(self):
        """ Updates the automatic :class:`~lib.agw.aui.auibook.AuiNotebook` in
        the layout (if any exists). """

        super(AuiManagerPlus, self).UpdateNotebook()

        # update the icon to the notebook page
        for paneInfo in self._panes:
            if paneInfo.IsNotebookPage():
                notebook = self._notebooks[paneInfo.notebook_id]
                page_id = notebook.GetPageIndex(paneInfo.window)
                if page_id >= 0:
                    notebook.SetPageBitmap(page_id, paneInfo.icon)

                notebook.DoSizing()

class FramePlus(wx.Frame):
    def __init__(self, parent, id=wx.ID_ANY, title=u'bsmedit',
                 pos=wx.DefaultPosition, size=wx.Size(800, 600),
                 style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL):
        wx.Frame.__init__(self, parent, id=id, title=title, pos=pos, size=size,
                          style=style)
        self._mgr = AuiManagerPlus()
        self._mgr.SetManagedWindow(self)
        self.menuAddon = {}
        self.paneAddon = {}
        self._pane_num = 0
        dp.connect(self.AddMenu, 'frame.add_menu')
        dp.connect(self.DeleteMenu, 'frame.delete_menu')
        dp.connect(self.AddPanel, 'frame.add_panel')
        dp.connect(self.DeletePanel, 'frame.delete_panel')
        dp.connect(self.ShowPanel, 'frame.show_panel')
        dp.connect(self.TogglePanel, 'frame.check_menu')
        dp.connect(self.UpdateMenu, 'frame.update_menu')
        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, event):
        self._mgr.UnInit()
        del self._mgr
        event.Skip()

    def GetMenu(self, pathlist, autocreate=False):
        """
        find the menu item.

        if autocreate is True, then recursive submenu creation.
        """
        if not pathlist:
            return None
        # the top level menu
        menuidx = self.GetMenuBar().FindMenu(pathlist[0])
        if menuidx == wx.NOT_FOUND:
            if autocreate:
                self.GetMenuBar().Append(wx.Menu(), pathlist[0])
                menuidx = self.GetMenuBar().FindMenu(pathlist[0])
            else:
                return None
        menuitem = self.GetMenuBar().GetMenu(menuidx)
        for p in pathlist[1:]:
            if menuitem is None:
                return None
            for m in six.moves.range(menuitem.GetMenuItemCount()):
                child = menuitem.FindItemByPosition(m)
                if not child.IsSubMenu():
                    continue
                stritem = child.GetItemLabelText()
                stritem = stritem.split('\t')[0]
                if stritem == p.split('\t')[0]:
                    menuitem = child.GetSubMenu()
                    break
            else:
                if autocreate:
                    child = self._append_menu(menuitem, p, kind='Popup')
                    menuitem = child.GetSubMenu()
                else:
                    return None
        return menuitem

    def _append_menu(self, menu, label, id=None, rxsignal=None,
                     updatesignal=None, kind='Normal'):
        """
        append an item to menu.
            kind: 'Separator', 'Normal', 'Check', 'Radio', 'Popup'
        """
        if menu is None:
            return None

        if kind == 'Separator':
            return menu.AppendSeparator()
        elif kind == 'Popup':
            return menu.AppendSubMenu(wx.Menu(), label)
        else:
            newid = id
            if newid is None:
                newid = wx.NewId()
            if kind == 'Normal':
                newitem = wx.MenuItem(menu, newid, label,
                                      label, kind=wx.ITEM_NORMAL)
            elif kind == 'Check':
                newitem = wx.MenuItem(menu, newid, label,
                                      label, kind=wx.ITEM_CHECK)
            elif kind == 'Radio':
                newitem = wx.MenuItem(menu, newid, label,
                                      label, kind=wx.ITEM_RADIO)
            self.menuAddon[newid] = (rxsignal, updatesignal)
            child = c2p.menuAppend(menu, newitem)
            self.Bind(wx.EVT_MENU, self.OnMenuAddOn, id=newid)
            if updatesignal:
                self.Bind(wx.EVT_UPDATE_UI, self.OnMenuCmdUI, id=newid)
            return child
        return None

    def AddMenu(self, path, id=None, rxsignal=None, updatesignal=None,
                kind='Normal', autocreate=False):
        """
        add the item to menubar.
            path: e.g., New:Open:Figure

            kind: 'Separator', 'Normal', 'Check', 'Radio', 'Popup'
        """

        paths = path.split(':')
        menu = None

        if len(paths) == 1:
            # top level menu
            return self.GetMenuBar().Append(wx.Menu(), paths[0])
        elif len(paths) > 1:
            menu = self.GetMenu(paths[:-1], autocreate)
            child = self._append_menu(menu, paths[-1], id, rxsignal,
                                      updatesignal, kind)
            if child:
                return child.GetId()
        return wx.NOT_FOUND

    def DeleteMenu(self, path, id=None):
        """delete the menu item"""
        pathlist = path.split(':')
        menuitem = self.GetMenu(pathlist[:-1])
        if menuitem is None:
            return False
        if id is None:
            # delete a submenu
            for m in six.moves.range(menuitem.GetMenuItemCount()):
                item = menuitem.FindItemByPosition(m)
                stritem = item.GetItemLabelText()
                stritem = stritem.split('\t')[0]
                if stritem == pathlist[-1].split('\t')[0] and item.IsSubMenu():
                    menuitem.DestroyItem(item)
                    return True
        else:
            item = menuitem.FindItemById(id)
            if item is None:
                return False
            menuitem.DestroyItem(item)
            # unbind the event and delete from menuAddon list
            self.Unbind(wx.EVT_MENU, id=id)
            if self.menuAddon[id][1]:
                self.Unbind(wx.EVT_UPDATE_UI, id=id)
            del self.menuAddon[id]

            return True
        return False

    def OnMenuAddOn(self, event):
        idx = event.GetId()
        signal = self.menuAddon.get(idx, None)
        if signal:
            signal = signal[0]
            dp.send(signal=signal, command=idx)

    def OnMenuCmdUI(self, event):
        idx = event.GetId()
        signal = self.menuAddon.get(idx, None)
        if signal:
            signal = signal[1]
            dp.send(signal=signal, event=event)
        else:
            event.Enable(True)

    def AddPanel(self, panel, title='Untitle', active=True, paneInfo=None,
                 target=None, showhidemenu=None, icon=None, maximize=False,
                 direction='top'):
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
        dirs = {'top': aui.AUI_DOCK_TOP, 'bottom': aui.AUI_DOCK_BOTTOM,
                'left': aui.AUI_DOCK_LEFT, 'right': aui.AUI_DOCK_RIGHT,
                'center': aui.AUI_DOCK_CENTER
               }
        direction = dirs.get(direction, aui.AUI_DOCK_TOP)
        if auipaneinfo is None:
            # default panel settings. dock_row = -1 to add the pane to the
            # dock with same direction and layer, and dock_pos = 99 (a large
            # number) to add it to the right side
            auipaneinfo = aui.AuiPaneInfo().Caption(title).BestSize((300, 300))\
                          .DestroyOnClose(not showhidemenu).Snappable()\
                          .Dockable().MinimizeButton(True).MaximizeButton(True)\
                          .Icon(icon).Row(-1).Direction(direction).Position(99)

            if not self._mgr.GetAllPanes():
                # set the first pane to be center pane
                auipaneinfo.CenterPane()
                active = True
        # auto generate the unique panel name
        name = "pane-%d"%self._pane_num
        self._pane_num += 1
        auipaneinfo.Name(name)

        # if showhidemenu is false, the panel will be destroyed when clicking
        # the close button; otherwise it will be hidden.
        panel.bsm_destroyonclose = not showhidemenu
        self._mgr.AddPane(panel, auipaneinfo, target=targetpane)
        if maximize:
            self._mgr.MaximizePane(auipaneinfo)
        if targetpane:
            self.ShowPanel(targetpane.window, targetpane.IsShown())
        self.ShowPanel(panel, active)
        # add the menu item to show/hide the panel
        if showhidemenu:
            mid = self.AddMenu(showhidemenu, rxsignal='frame.check_menu',
                               updatesignal='frame.update_menu', kind='Check',
                               autocreate=True)
            if mid != wx.NOT_FOUND:
                self.paneAddon[mid] = {'panel':panel, 'path':showhidemenu}
        return True

    def DeletePanel(self, panel):
        """hide and destroy the panel"""
        # delete the show/hide menu
        for (pid, pane) in six.iteritems(self.paneAddon):
            if panel == pane['panel']:
                self.DeleteMenu(pane['path'], pid)
                del self.paneAddon[pid]
                break

        # delete the panel from the manager
        pane = self._mgr.GetPane(panel)
        if pane is None or not pane.IsOk():
            return False
        panel.bsm_destroyonclose = True
        pane.DestroyOnClose(True)
        self._mgr.ClosePane(pane)
        self._mgr.Update()
        return True

    def ShowPanel(self, panel, show=True, focus=False):
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
        pane = self.paneAddon.get(command, None)
        if not pane:
            return
        panel = pane['panel']
        # IsShown may not work, since the panel may be hidden while IsShown()
        # returns True
        show = panel.IsShownOnScreen()
        self.ShowPanel(panel, not show)

    def UpdateMenu(self, event):
        """update the menu checkbox"""
        pane = self.paneAddon.get(event.GetId(), None)
        if not pane:
            return
        panel = pane['panel']
        show = panel.IsShownOnScreen()
        event.Check(show)
