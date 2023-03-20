import wx
import wx.py.dispatcher as dp
import numpy as np
from .graph_common import GraphObject

class LineEditor(GraphObject):
    ID_XY_MODE = wx.NewId()
    ID_X_MODE = wx.NewId()
    ID_Y_MODE = wx.NewId()
    ID_ROUND_Y = wx.NewId()
    ID_EXPORT_TO_TERM = wx.NewId()
    ID_LINES = []
    def __init__(self, figure, lines=None):
        super().__init__(figure)

        if lines is None:
            self.lines = self.figure.gca().lines
        else:
            self.lines = lines
        self.lines = self.lines[:]

        # marker
        # set larger zorder, so always on top
        self.marker = self.figure.gca().plot([], [], marker="o", color="red", zorder=10)[0]

        self.draggable = False
        self.marker.set_visible(self.draggable)

        self.active_line_index = None
        self.index = None

        self.mode = 'x'
        self.prev_pos = None
        self.round_y_to = 0

    def mouse_pressed(self, event):
        if not event.inaxes:
            return
        if event.button == 1:
            # left click
            self.draggable = True
            self.update(event)
        elif event.button == 3:
            self.draggable = False
        self.marker.set_visible(self.draggable)
        self.prev_pos = [event.xdata, event.ydata]

        self.figure.canvas.draw_idle()

    def mouse_move(self, event):
        if not event.inaxes:
            return

        mx, my = event.xdata, event.ydata

        if self.draggable:
            if self.round_y_to is not None:
                my = round(my, self.round_y_to)

            line = self.lines[self.active_line_index]
            x, y = line.get_data()
            x = x.copy()
            y = y.copy()
            mode = self.mode
            shift = wx.GetKeyState(wx.WXK_SHIFT)
            if mode == 'x' and shift:
                mode = 'y'
            elif mode == 'y' and shift:
                mode = 'x'
            if mode == 'x':
                idx, _, _ = self.get_closest(line, mx, None)
                if self.index > 0 and idx < self.index:
                    # move to left
                    y[idx:self.index] = y[self.index]
                    self.index = idx
                elif self.index > 0 and idx > self.index:
                    # move to right
                    y[self.index:idx+1] = y[self.index - 1]
                    self.index = idx
            elif mode == 'y':
                y[self.index] = my
            else:
                x[self.index] = mx
                y[self.index] = my
            self.marker.set_data([x[self.index]], [y[self.index]])
            line.set_data(x, y)
        self.figure.canvas.draw_idle()

    def mouse_released(self, event):
        self.draggable = False

    def update_line(self):
        # ignore the internal lines (e.g., marker)
        self.lines = [l for l in self.figure.gca().lines if l not in [self.marker]]

    def update(self, event):
        self.update_line()
        if self.active_line_index is None:
            min_dis = float("inf")
            index = -1
            gx, gy = self.get_xy_dis_gain()
            for i, line in enumerate(self.lines):
                if not line.get_visible():
                    continue
                _, x, y = self.get_closest(line, event.xdata, event.ydata)
                dis = (x-event.xdata)**2 * gx**2 + (y-event.ydata)**2 * gy**2
                if dis < min_dis:
                    min_dis = dis
                    index = i
            if index >= 0:
                self.active_line_index = index
        if self.active_line_index is None:
            return
        line = self.lines[self.active_line_index]
        self.index, x, y = self.get_closest(line, event.xdata, event.ydata)
        self.marker.set_data([x], [y])

    def get_closest(self, line, mx, my):
        """return the index of closed data point"""
        x, y = line.get_data()
        if mx is None and my is None:
            return -1
        if my is None:
            mini = np.argmin((x-mx)**2)
        elif mx is None:
            mini = np.argmin((y-my)**2)
        else:
            gx, gy = self.get_xy_dis_gain()
            mini = np.argmin((x-mx)**2 * gx**2 + (y-my)**2 * gy**2)
        return mini, x[mini], y[mini]

    def key_pressed(self, event):
        """Callback for key presses."""
        if not event.inaxes:
            return
        if event.key == 'escape':
            self.active_line_index = None
            self.marker.set_visible(False)
            self.figure.canvas.draw_idle()

    def activated(self):
        pass

    def deactivated(self):
        self.draggable = False
        self.marker.set_visible(self.draggable)

    def GetMenu(self):
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
        lines = []
        lines.append({'id': self.ID_EXPORT_TO_TERM, 'label': 'Export active line to shell ...',
                      'enable': self.active_line_index is not None})
        lines.append({'type': wx.ITEM_SEPARATOR})
        for i, line in enumerate(self.lines):
            while i >= len(self.ID_LINES):
                self.ID_LINES.append(wx.NewId())
            lines.append({'type': wx.ITEM_CHECK, 'id': self.ID_LINES[i],
                          'label': line.get_label(), 'check': self.active_line_index == i})
        if lines:
            cmd.append({'type': wx.ITEM_DROPDOWN, 'label': 'Lines', 'items': lines})
        return cmd

    def ProcessCommand(self, cmd):
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
            x, y = self.lines[self.active_line_index].get_data()
            np.save('_lineeditor.npy', (x, y))
            dp.send('shell.run',
                    command='le_data = np.load("_lineeditor.npy", allow_pickle=True)',
                    prompt=False,
                    verbose=False,
                    history=False)
            dp.send('shell.run',
                    command='le_data',
                    prompt=True,
                    verbose=True,
                    history=False)
        elif cmd in self.ID_LINES:
            self.active_line_index = self.ID_LINES.index(cmd)
