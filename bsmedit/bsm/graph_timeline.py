import wx
from matplotlib.backends.backend_wx import cursors
import numpy as np
import pandas as pd
from .graph_common import GraphObject
from .utility import send_data_to_shell

class Timeline(GraphObject):
    axvline_label = "_bsm_axvline"
    ID_CLEAR = wx.NewIdRef()
    ID_CLEAR_SHAREX = wx.NewIdRef()
    ID_CLEAR_ALL = wx.NewIdRef()
    ID_EXPORT_TO_TERM = wx.NewIdRef()
    ID_EXPORT_TO_TERM_SHAREX = wx.NewIdRef()
    ID_EXPORT_TO_TERM_ALL = wx.NewIdRef()
    ID_MOVE_TIMELINE_HERE = wx.NewIdRef()
    def __init__(self, figure):
        super().__init__(figure)

        self.axvline_idx = {}

        self.draggable = False
        self.axvline = None

        self.index = None
        self.initialized = False

    def mouse_pressed(self, event):
        if not event.inaxes:
            return

        x, y = event.x, event.y
        ret, self.axvline = self._is_close_to_axvline(event.inaxes, x, y)
        if ret:
            self.draggable = True

    def _is_close_to_axvline(self, ax, x, y):
        # check if (x, y) is close to the axvline in ax
        axvline = self._get_axvline(ax)
        if axvline is not None:
            trans = axvline.axes.transData
            lx, ly = trans.transform((axvline.get_xdata()[0], 0))
            if wx.Platform != '__WXMSW__':
                ratio = self.figure.canvas.device_pixel_ratio
            else:
                ratio = 1
            if np.abs(lx-x) < 10*ratio:
                return True, axvline
        return False, None

    def update_legend(self, axes, xdata = None):
        # update all sharex
        axes = self._get_axes(axes, sharex=True)
        for ax in axes:
            axvline, x, y, idx = None, None, None, None
            if not self._has_axvline(ax):
                continue
            for l in ax.lines:
                if self._is_axvline(l):
                    axvline = l
                    continue
                label = l.get_label()
                if label.startswith('_'):
                    continue

                label = label.split(' ')
                if len(label) > 1:
                    label = label[:-1]
                label = ' '.join(label)
                if xdata is not None:
                    x = l.get_xdata()
                    y = l.get_ydata()
                    idx = np.argmin(np.abs(x - xdata))
                    label = f'{label} {y[idx]}'
                l.set_label(label)
            if xdata is not None and axvline is not None and x is not None and \
               y is not None and idx is not None:
                axvline.set_xdata([x[idx], x[idx]])
                self.axvline_idx[ax] = idx
            ax.legend()

    def mouse_move(self, event):
        # TODO remove unnecessary set_cursor
        self.figure.canvas.set_cursor(cursors.POINTER)
        if not event.inaxes:
            return

        x, y = event.x, event.y

        ret, _ = self._is_close_to_axvline(event.inaxes, x, y)
        if ret or self.draggable:
            self.figure.canvas.set_cursor(cursors.RESIZE_HORIZONTAL)
        if self.draggable:
            self.update_legend([event.inaxes], event.xdata)

    def mouse_released(self, event):
        self.draggable = False

    def _get_sharex(self, ax):
        sharex = ax
        if sharex and sharex._sharex:
            sharex = sharex._sharex
        return sharex

    def key_pressed(self, event):
        """Callback for key presses."""
        if not event.inaxes:
            return
        if event.key in ['shift+left', 'left', 'shift+right', 'right']:
            if event.inaxes in self.axvline_idx:
                x = None
                for l in event.inaxes.lines:
                    if self._is_axvline(l):
                        continue
                    x = l.get_xdata()
                    break
                if x is not None:
                    idx = self.axvline_idx[event.inaxes]
                    step = 10 if 'shift' in event.key else 1
                    if 'left' in event.key:
                        idx = max(0, idx-step)
                    elif 'right' in event.key:
                        idx = min(len(x)-1, idx+step)
                    self.update_legend([event.inaxes], x[idx])

    def _is_axvline(self, l):
        x = l.get_xdata()
        if len(x) != 2:
            return False
        y = l.get_ydata()
        return x[0] == x[1] and y[0] == 0 and y[1] == 1 and l.get_label() == self.axvline_label

    def has_visible_lines(self, ax):
        for l in ax.lines:
            label = l.get_label()
            if label.startswith('_bsm'):
                continue
            if l.get_visible():
                return True
        return False

    def create_axvline_if_needed(self, ax):
        if self._has_axvline(ax) or not self.has_visible_lines(ax):
            return None
        xdata = np.mean(ax.get_xlim())
        l = ax.axvline(xdata, label=self.axvline_label)
        l.set_zorder(10)
        l.set_color('red')
        return True

    def activated(self):
        if self.initialized:
            return
        self.initialized = True
        for ax in self.figure.axes:
            # add axvline if not there
            if self.create_axvline_if_needed(ax):
                xdata = np.mean(ax.get_xlim())
                self.update_legend([ax], xdata)

    def deactivated(self):
        self.draggable = False

    def _get_axvline(self, ax):
        for l in ax.lines:
            if self._is_axvline(l):
                return l
        return None

    def _has_axvline(self, ax):
        # check if axes has axvline
        return self._get_axvline(ax) is not None

    def _get_axes(self, axes, sharex=False, all_axes=False):
        if all_axes:
            axes = self.figure.axes
        elif sharex:
            sharexes = set()
            for ax in axes:
                sharexes.add(self._get_sharex(ax))
            axes = []
            for ax in self.figure.axes:
                if self._get_sharex(ax) in sharexes:
                    axes.append(ax)
        return axes

    def _clear_axvline(self, axes):
        for ax in axes:
            # remove all axvline
            axvline = None
            for l in ax.lines:
                if self._is_axvline(l):
                    axvline = l
                else:
                    label = l.get_label()
                    if label.startswith('_'):
                        # ignore line without label
                        continue
                    label = label.split(' ')
                    if len(label) > 1:
                        label = label[:-1]
                    label = ' '.join(label)
                    l.set_label(label)
            if axvline:
                axvline.remove()
            ax.legend()

    def _export(self, axes):
        data = {}
        for ax in axes:
            if not self._has_axvline(ax) or ax not in self.axvline_idx:
                continue
            idx = self.axvline_idx[ax]
            for l in ax.lines:
                if self._is_axvline(l):
                    continue
                label = l.get_label()
                if label.startswith('_'):
                    continue
                label = label.split(' ')
                if len(label) > 1:
                    label = label[:-1]
                label = ' '.join(label)
                x = l.get_xdata()
                y = l.get_ydata()
                sharex = self._get_sharex(ax)
                if sharex not in data:
                    data[sharex] = pd.DataFrame()
                    data[sharex]['x'] = [x[idx]]
                data[sharex][label] = [y[idx]]
        data = list(data.values())
        if len(data) == 1:
            data = data[0]
        return data

    def GetMenu(self, axes):
        cmd = [{'id': self.ID_MOVE_TIMELINE_HERE,
                'label': 'Move timeline in view',
                'enable': self.has_visible_lines(axes[0])},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_EXPORT_TO_TERM,
                'label': 'Export to shell'},
               {'id': self.ID_EXPORT_TO_TERM_SHAREX,
                'label': 'Export all to shell with shared x-axis'},
               {'id': self.ID_EXPORT_TO_TERM_ALL,
                'label': 'Export all to shell'},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_CLEAR,
                'label': 'Clear on current subplot'},
               {'id': self.ID_CLEAR_SHAREX,
                'label': 'Clear all with shared x-axis'},
               {'id': self.ID_CLEAR_ALL,
                'label': 'Clear all'},
              ]

        return cmd

    def ProcessCommand(self, cmd, axes):
        if cmd == self.ID_MOVE_TIMELINE_HERE:
            for ax in axes:
                if self.create_axvline_if_needed(ax):
                    xdata = np.mean(ax.get_xlim())
                    self.update_legend([ax], xdata)
        elif cmd == self.ID_CLEAR:
            self._clear_axvline(axes)
        elif cmd == self.ID_CLEAR_SHAREX:
            self._clear_axvline(self._get_axes(axes, sharex=True))
        elif cmd == self.ID_CLEAR_ALL:
            self._clear_axvline(self._get_axes(axes, all_axes=True))
        elif cmd in [self.ID_EXPORT_TO_TERM, self.ID_EXPORT_TO_TERM_SHAREX,
                     self.ID_EXPORT_TO_TERM_ALL]:
            if cmd == self.ID_EXPORT_TO_TERM_ALL:
                axes = self._get_axes(axes, all_axes=True)
            elif cmd == self.ID_EXPORT_TO_TERM_SHAREX:
                axes = self._get_axes(axes, sharex=True)

            data = self._export(axes)
            send_data_to_shell('timeline_data', data)
