import wx
import matplotlib
from ..aui import aui
from .graph_common import GraphObject
from .graph_subplot import move_axes
class GDock(GraphObject):
    def __init__(self, figure):
        super().__init__(figure)

        self.canvas = self.figure.canvas
        self._guides = []
        self._drag_start_ax = None
        self._drag_start_pos = None

    def mouse_pressed(self, event):
        if not event.inaxes:
            return

        if event.button == matplotlib.backend_bases.MouseButton.LEFT:
            self._drag_start_ax = event.inaxes
            self._drag_start_pos = (event.x, event.y)
            #self.UpdateDockingGuides(event.inaxes)
            #self.ShowDockingGuides(True)

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
        self.HitTestDockGuide()

    def mouse_released(self, event):
        self.ShowDockingGuides(False)
        edge, direction = self.HitTestDockGuide()
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

        captionSize = 0
        frameRect = self.canvas.GetScreenRect()
        mousePos = wx.GetMousePosition()

        for indx, guide in enumerate(self._guides):

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
                bbox = ax.get_tightbbox()
                w, h = self.canvas.GetSize()
                rc = wx.Rect()
                topleft = (bbox.p0[0], h-bbox.p1[1])
                rc.SetTopLeft(self.canvas.ClientToScreen(topleft))
                rc.SetSize((bbox.width, bbox.height))
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

            # do hit testing on the guide
            dir = guide.host.HitTest(screenPt.x, screenPt.y)
            if dir == -1:  # point was outside of the dock guide
                continue

            if dir == wx.ALL:  # target is a single dock guide
                if guide.dock_direction == aui.AUI_DOCK_LEFT:
                    return True, 'left'
                elif guide.dock_direction == aui.AUI_DOCK_RIGHT:
                    return True, 'right'
                elif guide.dock_direction == aui.AUI_DOCK_TOP:
                    return True, 'top'
                elif guide.dock_direction == aui.AUI_DOCK_BOTTOM:
                    return True, 'bottom'
                return None, None

            elif dir == wx.CENTER:
                pass
            else:
                if dir == wx.LEFT:
                    return False, 'left'
                elif dir == wx.UP:
                    return False, 'top'
                elif dir == wx.RIGHT:
                    return False, 'right'
                elif dir == wx.DOWN:
                    return False, 'bottom'

        return None, None
