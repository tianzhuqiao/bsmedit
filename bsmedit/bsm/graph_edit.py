import wx
import numpy as np
import pandas as pd
from .graph_common import GraphObject
from .utility import send_data_to_shell

class LineEditor(GraphObject):
    marker_label = '_bsm_marker'
    ID_XY_MODE = wx.NewIdRef()
    ID_X_MODE = wx.NewIdRef()
    ID_Y_MODE = wx.NewIdRef()
    ID_ROUND_Y = wx.NewIdRef()
    ID_EXPORT_TO_TERM = wx.NewIdRef()
    ID_LINES = []
    def __init__(self, figure):
        super().__init__(figure)

        self.lines = {}
        self.axes = None

        # marker
        # set larger zorder, so always on top
        self.marker = {}

        self.draggable = False
        #self.marker.set_visible(self.draggable)

        self.active_line = None
        self.index = None

        self.mode = 'x'
        self.round_y_to = 100

    def update_marker(self):
        # update marker
        for g in self.marker:
            self.marker[g].set_visible(False)

        if self.draggable and self.active_line:
            self.marker[self.active_line.axes].set_visible(True)

    def _update_marker(self, axes):
        for g in axes:
            if self.marker.get(g, None) is None or self.marker[g] not in g.lines:
                self.marker[g] = g.plot([], [], marker="o", color="red", zorder=10,
                                        label=self.marker_label)[0]
                self.marker[g].set_visible(False)
            else:
                if self.marker[g].get_linestyle() != 'None':
                    self.marker[g].set_linestyle('None')
                elif self.marker[g].get_marker() != '.':
                    self.marker[g].set_marker('.')

    def mouse_pressed(self, event):
        if not event.inaxes:
            return
        axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]
        self.axes = axes
        self._update_marker(axes)

        if event.button == 1:
            # left click
            self.draggable = True
            self.update(event)
            self.update_marker()
        elif event.button == 3:
            self.draggable = False

        self.figure.canvas.draw_idle()

    def mouse_move(self, event):
        if not event.inaxes:
            return
        self._update_marker([event.inaxes])
        mx, my = event.xdata, event.ydata

        if self.draggable and self.active_line:
            inv = self.active_line.axes.transData.inverted()
            mx, my = inv.transform((event.x, event.y))
            if self.round_y_to is not None:
                my = round(my, self.round_y_to)

            x, y = self.active_line.get_data()
            x = x.copy()
            y = y.copy()
            mode = self.mode
            shift = wx.GetKeyState(wx.WXK_SHIFT)
            if mode == 'x' and shift:
                mode = 'y'
            elif mode == 'y' and shift:
                mode = 'x'
            if mode == 'x':
                # search the index based on x-axis only
                idx, _, _ = self.get_closest(self.active_line, mx, None, 5)
                if isinstance(idx, np.ndarray):
                    idx_closest = np.argmin(np.abs(idx - self.index))
                    idx = idx[idx_closest]
                # search based on x and y
                #idx2, _, _ = self.get_closest(self.active_line, mx, my)
                # find the index that is close to the current position
                #if abs(idx2 - self.index) < abs(idx - self.index):
                #    idx = idx2

                if self.index > 0 and idx < self.index:
                    # move to left
                    y[idx:self.index] = y[self.index]
                    self.index = idx
                elif self.index > 0 and idx > self.index:
                    # move to right
                    y[self.index:idx+1] = y[self.index - 1]
                    self.index = idx
                else:
                    self.index = idx
            elif mode == 'y':
                y[self.index] = my
            else:
                x[self.index] = mx
                y[self.index] = my
            self.marker[self.active_line.axes].set_data([x[self.index]], [y[self.index]])
            self.active_line.set_data(x, y)
        self.figure.canvas.draw_idle()

    def mouse_released(self, event):
        self.draggable = False

    def update_line(self):
        # ignore the internal lines (e.g., marker)
        self.lines = {}
        for g in self.axes:
            self.lines[g] = [l for l in g.lines if l != self.marker.get(g, None)]

        if self.active_line:
            if self.active_line not in self.lines.get(self.active_line.axes, []):
                self.active_line = None

    def update(self, event):
        self.update_line()
        if self.active_line is None:
            active_line, _ = self.get_closest_line(self.axes, event.x, event.y)
            if active_line:
                self.active_line = active_line
        if self.active_line is None:
            return
        inv = self.active_line.axes.transData.inverted()
        mx, my = inv.transform((event.x, event.y))
        self.index, x, y = self.get_closest(self.active_line, mx, my)
        self.marker[self.active_line.axes].set_data([x], [y])

    def key_pressed(self, event):
        """Callback for key presses."""
        if not event.inaxes:
            return
        if event.key == 'escape':
            if self.active_line:
                self.marker[self.active_line.axes].set_visible(False)
            self.active_line = None
            self.draggable = False
            self.figure.canvas.draw_idle()

    def activated(self):
        pass

    def deactivated(self):
        self.draggable = False
        if self.active_line:
            if self.active_line.axes in self.marker:
                self.marker[self.active_line.axes].set_visible(False)

    def GetMenu(self, axes):
        cmd = [{'type': wx.ITEM_CHECK, 'id': self.ID_XY_MODE, 'label': 'x/y mode',
                'check': self.mode == ''},
               {'type': wx.ITEM_CHECK, 'id': self.ID_X_MODE, 'label': 'x only mode',
                'check': self.mode == 'x'},
               {'type': wx.ITEM_CHECK, 'id': self.ID_Y_MODE, 'label': 'y only mode',
                'check': self.mode == 'y'},
               {'type': wx.ITEM_CHECK, 'id': self.ID_ROUND_Y, 'label': 'Round y to',
                'check': self.round_y_to is not None},
               {'type': wx.ITEM_SEPARATOR},
              ]

        self.update_line()
        menu_lines = []
        menu_lines.append({'id': self.ID_EXPORT_TO_TERM, 'label': 'Export active line to shell ...',
                      'enable': self.active_line is not None})
        menu_lines.append({'type': wx.ITEM_SEPARATOR})
        i = 0
        for _, lines in self.lines.items():
            for line in lines:
                while i >= len(self.ID_LINES):
                    self.ID_LINES.append(wx.NewIdRef())
                menu_lines.append({'type': wx.ITEM_CHECK, 'id': self.ID_LINES[i],
                              'label': line.get_label(), 'check': self.active_line == line})
                i += 1
        if menu_lines:
            cmd.append({'type': wx.ITEM_DROPDOWN, 'label': 'Lines', 'items': menu_lines})
        return cmd

    def ProcessCommand(self, cmd, axes):
        if cmd == self.ID_XY_MODE:
            self.mode = ''
        elif cmd == self.ID_X_MODE:
            self.mode = 'x'
        elif cmd == self.ID_Y_MODE:
            self.mode = 'y'
        elif cmd == self.ID_ROUND_Y:
            msg = 'Rounded y to ndigits precision after the decimal point:'
            ry = self.round_y_to
            if ry is None:
                ry = 0
            ry = wx.GetTextFromUser(message=msg, caption="bsmedit", default_value=f'{ry}')
            if not ry:
                # cancel is clicked
                return

            try:
                ry = int(ry)
            except:
                ry = None
            self.round_y_to = ry

        elif cmd == self.ID_EXPORT_TO_TERM:
            x, y = self.active_line.get_data()
            data = pd.DataFrame()
            data['x'] = x
            data['y'] = y
            send_data_to_shell('le_line', data)

        elif cmd in self.ID_LINES:
            i = 0
            for _, lines in self.lines.items():
                for line in lines:
                    if i == self.ID_LINES.index(cmd):
                        self.active_line = line
                        break
                    i += 1
                else:
                    # if not found in lines, keep searching
                    continue
                break
