import wx
import wx.py.dispatcher as dp
from matplotlib.backends.backend_wx import cursors
import numpy as np
import pandas as pd
import pickle
from .graph_common import GraphObject

class Timeline(GraphObject):
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
        for l in ax.lines:
            if not self._is_axvline(l):
                continue
            trans = l.axes.transData
            lx, ly = trans.transform((l.get_xdata()[0], 0))
            if np.abs(lx-x) < 15:
                return True, l
        return False, None

    def update_legend(self, axes, xdata = None):
        # update all sharex
        axes = self._get_axes(axes, sharex=True)
        for ax in axes:
            axvline = None
            if not self._has_axvline(ax):
                continue
            for l in ax.lines:
                if self._is_axvline(l):
                    axvline = l
                    continue
                label = l.get_label()
                if label.startswith('_child'):
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
            if xdata is not None and axvline is not None:
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
        return x[0] == x[1] and y[0] == 0 and y[1] == 1

    def activated(self):
        if self.initialized:
            return
        self.initialized = True
        for ax in self.figure.axes:
            # add axvline if not there
            if not self._has_axvline(ax):
                xdata = np.mean(ax.get_xlim())
                l = ax.axvline(xdata)
                l.set_zorder(10)
                l.set_color('red')
                self.update_legend([ax], xdata)

    def deactivated(self):
        self.draggable = False

    def _has_axvline(self, ax):
        # check if axes has axvline
        for l in ax.lines:
            if self._is_axvline(l):
                return True
        return False

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
                    if label.startswith('_child'):
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
                'check': False},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_EXPORT_TO_TERM,
                'label': 'Export to shell',
                'check': False},
               {'id': self.ID_EXPORT_TO_TERM_SHAREX,
                'label': 'Export all to shell with shared x-axis',
                'check': False},
               {'id': self.ID_EXPORT_TO_TERM_ALL,
                'label': 'Export all to shell',
                'check': False},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_CLEAR,
                'label': 'Clear on current subplot',
                'check': False},
               {'id': self.ID_CLEAR_SHAREX,
                'label': 'Clear all with shared x-axis',
                'check': False},
               {'id': self.ID_CLEAR_ALL,
                'label': 'Clear all',
                'check': False},

              ]

        return cmd

    def ProcessCommand(self, cmd, axes):
        if cmd == self.ID_MOVE_TIMELINE_HERE:
            for ax in axes:
                xdata = np.mean(ax.get_xlim())
                if not self._has_axvline(ax):
                    l = ax.axvline(xdata)
                    l.set_zorder(10)
                    l.set_color('red')
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
            with open('_timeline.npy', 'wb') as fp:
                pickle.dump(data, fp)
            dp.send('shell.run',
                    command='with open("_timeline.npy", "rb") as fp:\n    timeline_data = pickle.load(fp)',
                    prompt=False,
                    verbose=False,
                    history=False)
            dp.send('shell.run',
                    command='',
                    prompt=False,
                    verbose=False,
                    history=False)
            dp.send('shell.run',
                    command='timeline_data',
                    prompt=True,
                    verbose=True,
                    history=False)
