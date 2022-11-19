import wx
import wx.py.dispatcher as dp
import numpy as np

class LineEditor():
    ID_XY_MODE = wx.NewId()
    ID_X_MODE = wx.NewId()
    ID_Y_MODE = wx.NewId()
    ID_ROUND_Y = wx.NewId()
    ID_EXPORT_TO_TERM = wx.NewId()
    ID_LINES = []
    def __init__(self, figure, lines=None):
        self.figure = figure
        if lines is None:
            self.lines = self.figure.gca().lines
        else:
            self.lines = lines
        self.lines = self.lines[:]

        # marker
        # set larger zorder, so always on top
        self.marker = self.figure.gca().plot([0], [0], marker="o", color="red", zorder=10)[0]

        # cross hair
        self.horizontal_line = self.figure.gca().axhline(color='g', lw=0.8, ls='--', zorder=10)
        self.vertical_line = self.figure.gca().axvline(color='g', lw=0.8, ls='--', zorder=10)
        self.show_cross_hair = False

        self.draggable = False
        self.marker.set_visible(self.draggable)
        self.horizontal_line.set_visible(False)
        self.vertical_line.set_visible(False)

        self.active_line_index = None
        self.index = None

        self.mode = 'x'
        self.prev_pos = None
        self.round_y_to = 0

    def set_cross_hair_visible(self, visible):
        need_redraw = self.horizontal_line.get_visible() != visible
        self.horizontal_line.set_visible(visible)
        self.vertical_line.set_visible(visible)
        #self.text.set_visible(visible)
        return need_redraw

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
            need_redraw = self.set_cross_hair_visible(False)
            if need_redraw:
                self.figure.canvas.draw_idle()
            return

        mx, my = event.xdata, event.ydata
        self.set_cross_hair_visible(self.show_cross_hair)
        self.horizontal_line.set_ydata(my)
        self.vertical_line.set_xdata(mx)

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
                    y[self.index:idx] = y[self.index - 1]
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

    def get_xy_dis_gain(self):
        # the gain applied to x/y when calculate the distance between to point
        # e.g., a data point to the mouse position
        # for example, if the figure is square (width == height), but
        # x range is [0, 100], and y range is [0, 0.1], the physical distance
        # in y axis will be `ignored` as x is 1000 times larger than y.
        xlim = self.figure.gca().get_xlim()
        ylim = self.figure.gca().get_ylim()
        box = self.figure.gca().get_window_extent()
        if xlim[1] - xlim[0] == 0 or ylim[1] - ylim[0] == 0:
            return 1, 1
        gx = box.width / (xlim[1] - xlim[0])
        gy = box.height / (ylim[1] - ylim[0])
        return gx, gy

    def update(self, event):
        # ignore the first 3 lines (marker + 2 cross hair)
        self.lines = self.figure.gca().lines[3:]
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
        self.horizontal_line.set_visible(False)
        self.vertical_line.set_visible(False)

    def GetMenu(self):
        cmd = [[self.ID_XY_MODE, 'x/y mode', True, self.mode == ''],
               [self.ID_X_MODE, 'x only mode', True, self.mode == 'x'],
               [self.ID_Y_MODE, 'y only mode', True, self.mode == 'y'],
               [self.ID_ROUND_Y, 'Round y to', True, self.round_y_to != None],
               [],
              ]

        self.lines = self.figure.gca().lines[3:]
        lines = []
        lines.append([self.ID_EXPORT_TO_TERM, 'Export active line to shell ...', self.active_line_index != None])
        lines.append([])
        for i, line in enumerate(self.lines):
            while i >= len(self.ID_LINES):
                self.ID_LINES.append(wx.NewId())
            lines.append([self.ID_LINES[i], line.get_label(), True, self.active_line_index == i])
        if lines:
            cmd.append(['Lines', lines])
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
