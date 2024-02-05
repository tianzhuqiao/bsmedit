import wx
import matplotlib
from ..aui import aui2 as aui
from .graph_common import GraphObject
from .graph_subplot import move_axes, get_top_gridspec, get_gridspec
class GDock(GraphObject):
    def __init__(self, figure):
        super().__init__(figure)

        self.canvas = self.figure.canvas
        self._guides = []
        self._drag_start_ax = None
        self._drag_start_pos = None

        self._hint_window = None
        self._last_hint = wx.Rect()

    def mouse_pressed(self, event):
        if not event.inaxes:
            return

        if event.button == matplotlib.backend_bases.MouseButton.LEFT:
            if len(self.figure.axes) > 1:
                self._drag_start_ax = event.inaxes
                self._drag_start_pos = (event.x, event.y)

    def mouse_move(self, event):
        if event.button != matplotlib.backend_bases.MouseButton.LEFT \
           or self._drag_start_ax is None:
            if self.IsDockingGuidesShown():
                self.ShowDockingGuides(False)
            return

        if not self.IsDockingGuidesShown():
            drag_x_threshold = max(4, wx.SystemSettings.GetMetric(wx.SYS_DRAG_X))
            drag_y_threshold = max(4, wx.SystemSettings.GetMetric(wx.SYS_DRAG_Y))
            if not (abs(event.x - self._drag_start_pos[0]) > drag_x_threshold or \
                    abs(event.y - self._drag_start_pos[1]) > drag_y_threshold):
                return
            self.ShowDockingGuides(True)

        if self._drag_start_ax is not None:
            self.UpdateDockingGuides(event.inaxes)
        if event.inaxes is None or self._drag_start_ax == event.inaxes:
            # hide the center guide if the mouse is on same axex as the one to be dragged
            self._guides[-1].host.Hide()
        elif not self._guides[-1].host.IsShown():
            self._guides[-1].host.Show()
            self._guides[-1].host.Update()

        edge, direction = self.HitTestDockGuide()
        if direction:
            if edge:
                # try to dock on edge
                frameRect = self.canvas.GetScreenRect()
                g = get_top_gridspec(self.figure.axes[0])
                r, c = g.get_geometry()
                w, h = frameRect.width, frameRect.height
                rect = wx.Rect()
                if direction == 'left':
                    rect = wx.Rect(frameRect.x, frameRect.y, w/(c+1), h)
                elif direction == 'right':
                    rect = wx.Rect(frameRect.x+w-w/(c+1), frameRect.y, w/(c+1), h)
                if direction == 'top':
                    rect = wx.Rect(frameRect.x, frameRect.y, w, h/(r+1))
                elif direction == 'bottom':
                    rect = wx.Rect(frameRect.x, frameRect.y+h-h/(r+1), w, h/(r+1))
            else:
                # try to dock around event.inaxes
                frameRect = self.GetAxesRect(event.inaxes)
                g = event.inaxes.get_gridspec()
                r, c = g.get_geometry()
                i = 0
                if (direction in ['left', 'right'] and c > 1) or \
                   (direction in ['top', 'bottom'] and r > 1):
                    # if vert, and g is also vertical, dock in g
                    # if horz, and g is also horizontal, dock in g
                    frameRect = self.GetGridRect(event.inaxes.get_gridspec())
                    r, c, i, _ = event.inaxes.get_subplotspec().get_geometry()
                else:
                    # otherwise, it will create a gridspec for event.inaxes and
                    # self._drag_start_ax
                    r, c, i = 1, 1, 0
                w, h = frameRect.width, frameRect.height
                if direction == 'left':
                    i = min(c-1, i)
                    rect = wx.Rect(frameRect.x+i*w/(c+1), frameRect.y, w/(c+1),h)
                elif direction == 'right':
                    i = min(c-1, i)
                    rect = wx.Rect(frameRect.x+(i+1)*w/(c+1), frameRect.y, w/(c+1),h)
                elif direction == 'top':
                    i = min(r-1, i)
                    rect = wx.Rect(frameRect.x, frameRect.y+i*h/(r+1), w, h/(r+1))
                if direction == 'bottom':
                    i = min(r-1, i)
                    rect = wx.Rect(frameRect.x, frameRect.y+(i+1)*h/(r+1), w,h/(r+1))
            self.ShowHint(rect)
        else:
            self.HideHint()

    def mouse_released(self, event):
        edge, direction = self.HitTestDockGuide()
        self.ShowDockingGuides(False)
        self.HideHint()
        if direction is not None:
            target = event.inaxes
            if edge and target is None:
                for ax in self.figure.axes:
                    if ax == self._drag_start_ax:
                        continue
                    target = ax
                    break
            move_axes(self._drag_start_ax, target, direction, edge=edge)
        self._drag_start_ax = None
        self._drag_start_pos = None

    def activated(self):
        pass

    def deactivated(self):
        pass

    def GetAxesRect(self, ax):
        if wx.Platform != '__WXMSW__':
            ratio = self.canvas.device_pixel_ratio
        else:
            ratio = 1
        bbox = ax.get_tightbbox()
        w, h = self.canvas.GetSize()
        rc = wx.Rect()
        topleft = (bbox.p0[0]//ratio, h-bbox.p1[1]//ratio)
        rc.SetTopLeft(self.canvas.ClientToScreen(topleft))
        rc.SetSize((bbox.width//ratio, bbox.height//ratio))
        return rc

    def GetGridRect(self, g):
        frameRect = self.canvas.GetScreenRect()
        top, left, right, bottom = frameRect.bottom, frameRect.right, frameRect.left, frameRect.top
        for a in self.figure.axes:
            ga = get_gridspec(a, g)
            if ga or a.get_gridspec() == g:
                rc = self.GetAxesRect(a)
                top = min(top, rc.top)
                bottom = max(bottom, rc.bottom)
                left = min(left, rc.left)
                right = max(right, rc.right)

        return wx.Rect(left, top, right-left+1, bottom-top+1)

    def CreateHintWindow(self):
        """ Creates the standard wxAUI hint window. """

        self.DestroyHintWindow()
        self._hint_window = aui.AuiDockingHintWindow(wx.GetTopLevelParent(self.canvas))
        self._hint_window.SetBlindMode(aui.AUI_MGR_TRANSPARENT_HINT \
                                       | aui.AUI_MGR_NO_VENETIAN_BLINDS_FADE)

    def DestroyHintWindow(self):
        """ Destroys the standard wxAUI hint window. """

        if self._hint_window:
            self._hint_window.Destroy()
            self._hint_window = None

    def ShowHint(self, rect):
        """
        Shows the AUI hint window.

        :param wx.Rect `rect`: the hint rect calculated in advance.
        """

        if rect == self._last_hint:
            return

        if not self._hint_window:
            self.CreateHintWindow()

        if self._hint_window:
            self._hint_window.SetRect(rect)
            self._hint_window.Show()

        self._last_hint = wx.Rect(*rect)

    def HideHint(self):
        if self._hint_window:
            self._hint_window.Hide()
        self._last_hint = wx.Rect()

    def CreateGuideWindows(self):
        """ Creates the VS2005 HUD guide windows. """

        self.DestroyGuideWindows()

        self._guides.append(aui.AuiDockingGuideInfo().Left().
                            Host(aui.AuiSingleDockingGuide(self.canvas, wx.LEFT)))
        self._guides.append(aui.AuiDockingGuideInfo().Top().
                            Host(aui.AuiSingleDockingGuide(self.canvas, wx.TOP)))
        self._guides.append(aui.AuiDockingGuideInfo().Right().
                            Host(aui.AuiSingleDockingGuide(self.canvas, wx.RIGHT)))
        self._guides.append(aui.AuiDockingGuideInfo().Bottom().
                            Host(aui.AuiSingleDockingGuide(self.canvas, wx.BOTTOM)))
        self._guides.append(aui.AuiDockingGuideInfo().Centre().
                            Host(aui.AuiCenterDockingGuide(self.canvas)))

    def DestroyGuideWindows(self):
        """ Destroys the VS2005 HUD guide windows. """
        for guide in self._guides:
            if guide.host:
                guide.host.Destroy()
        self._guides = []

    def IsDockingGuidesShown(self):
        for target in self._guides:
            if target.host.IsShown():
                return True
        return False

    def ShowDockingGuides(self, show):
        """
        Shows or hide the docking guide windows.

        :param `guides`: a list of :class:`AuiDockingGuide` classes;
        :param bool `show`: whether to show or hide the docking guide windows.
        """

        for target in self._guides:

            if show and not target.host.IsShown():
                target.host.Show()
                target.host.Update()

            elif not show and target.host.IsShown():
                target.host.Hide()

    def UpdateDockingGuides(self, ax):
        """
        Updates the docking guide windows positions and appearance.

        :param `paneInfo`: a :class:`AuiPaneInfo` instance.
        """

        if len(self._guides) == 0:
            self.CreateGuideWindows()

        frameRect = self.canvas.GetScreenRect()
        mousePos = wx.GetMousePosition()

        for guide in self._guides:

            pt = wx.Point()
            guide_size = guide.host.GetSize()
            if not guide.host:
                raise Exception("Invalid docking host")

            direction = guide.dock_direction

            if direction == aui.AUI_DOCK_LEFT:
                pt.x = frameRect.x + guide_size.x // 2 + 16
                pt.y = frameRect.y + frameRect.height // 2

            elif direction == aui.AUI_DOCK_TOP:
                pt.x = frameRect.x + frameRect.width // 2
                pt.y = frameRect.y + guide_size.y // 2 + 16

            elif direction == aui.AUI_DOCK_RIGHT:
                pt.x = frameRect.x + frameRect.width - guide_size.x // 2 - 16
                pt.y = frameRect.y + frameRect.height // 2

            elif direction == aui.AUI_DOCK_BOTTOM:
                pt.x = frameRect.x + frameRect.width // 2
                pt.y = frameRect.y + frameRect.height - guide_size.y // 2 - 16

            elif direction == aui.AUI_DOCK_CENTER:
                if ax is None:
                    continue
                # bbox's origin is at left bottom corner, convert the origin to
                # left top corner
                rc = self.GetAxesRect(ax)
                pt.x = rc.x + rc.width // 2
                pt.y = rc.y + rc.height // 2

            # guide will be centered around point 'pt'
            targetPosition = wx.Point(pt.x - guide_size.x // 2, pt.y - guide_size.y // 2)

            if guide.host.GetPosition() != targetPosition:
                guide.host.Move(targetPosition)

            guide.host.AeroMove(targetPosition)

            if guide.dock_direction == aui.AUI_DOCK_CENTER:
                guide.host.ValidateNotebookDocking(False)

            if guide.host.IsShownOnScreen():
                guide.host.UpdateDockGuide(mousePos)
                guide.host.Refresh()

    def HitTestDockGuide(self):
        """
        """
        screenPt = wx.GetMousePosition()

        # search the dock guides.
        # reverse order to handle the center first.
        for i in range(len(self._guides) - 1, -1, -1):
            guide = self._guides[i]
            if not guide.host.IsShown():
                continue
            # do hit testing on the guide
            direction = guide.host.HitTest(screenPt.x, screenPt.y)
            if direction == -1:  # point was outside of the dock guide
                continue

            if direction == wx.ALL:  # target is a single dock guide
                if guide.dock_direction == aui.AUI_DOCK_LEFT:
                    return True, 'left'
                elif guide.dock_direction == aui.AUI_DOCK_RIGHT:
                    return True, 'right'
                elif guide.dock_direction == aui.AUI_DOCK_TOP:
                    return True, 'top'
                elif guide.dock_direction == aui.AUI_DOCK_BOTTOM:
                    return True, 'bottom'
                return None, None

            elif direction == wx.CENTER:
                # no notebook
                pass
            else:
                if direction == wx.LEFT:
                    return False, 'left'
                elif direction == wx.UP:
                    return False, 'top'
                elif direction == wx.RIGHT:
                    return False, 'right'
                elif direction == wx.DOWN:
                    return False, 'bottom'

        return None, None
