import matplotlib
import datetime
import math
import wx
import wx.py.dispatcher as dp
import numpy as np
from .graph_common import GraphObject
from .. import propgrid as pg
from ..propgrid import prop

class DataCursor(GraphObject):
    xoffset, yoffset = -20, 20
    text_template = 'x: %0.2f\ny: %0.2f'
    MAX_DISTANCE = 5

    ID_DELETE_DATATIP = wx.NewIdRef()
    ID_CLEAR_DATATIP = wx.NewIdRef()
    ID_EXPORT_DATATIP = wx.NewIdRef()
    ID_SETTING = wx.NewIdRef()
    def __init__(self, figure, win):
        super().__init__(figure)
        self.annotations = []
        self.lines = []
        self.enable = False
        self.active = None
        self.mx, self.my = None, None
        self.window = win
        self.settings = [
                #[indent, type, name, label, value, fmt]
                prop.PropChoice({
                    (-1, 1): 'top left',
                    (0, 1): 'top',
                    (1, 1): 'top right',
                    (1, 0): 'right',
                    (1, -1): 'bottom right',
                    (0, -1): 'bottom',
                    (-1, -1): 'bottom left',
                    (-1, 0): 'left',
                    }, 'Position').Name('pos_xy').Value((-1, 1)),
                prop.PropSeparator('Format').Name('sep_fmt'),
                prop.PropText('Number').Value('.2f').Name('fmt_number').Indent(1),
                prop.PropText('Datetime').Value('%Y-%m-%d %H:%M:%S').Name('fmt_datetime').Indent(1),
                prop.PropSeparator('Color').Name('sep_color'),
                prop.PropColor('Edge').Value('#8E8E93').Name('clr_edge').Indent(1),
                prop.PropColor('Face').Value('#ffffff').Name('clr_face').Indent(1),
                prop.PropSpin(0, 100, 'Opacity').Name('clr_alpha').Value(50).Indent(1),
                prop.PropSeparator('Selected color').Name('sep_clr_selected'),
                prop.PropColor('Edge').Value('#8E8E93').Name('clr_edge_selected').Indent(1),
                prop.PropColor('Face').Value('#FF9500').Name('clr_face_selected').Indent(1),
                prop.PropSpin(0, 100, 'Opacity').Name('clr_alpha_selected').Value(50).Indent(1),
                ]
        self.LoadConfig()
        self.cx, self.cy = None, None

    def pick(self, event):
        # pick event will not always be triggered for twinx, see following linke
        # for detail
        # https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.twinx.html
        return

    def annotation_line(self, line, mx, my):
        if not self.enable:
            return False
        if self.get_annotation(mx, my) is not None:
            # click in the box of existing annotation, ignore it
            return False

        # find the closest point on the line
        # mouse position in data coordinate
        dis = self.distance_to_line(line, mx, my)
        if dis > self.MAX_DISTANCE:
            return False

        if self.active and self.active.get_visible():
            # Check whether the axes of active annotation is same as line,
            # which may happen in a figure with subplots. If not, create one
            # with the axes of line
            if self.active.axes != line.axes:
                self.set_active(None)
        if self.active is None:
            self.create_annotation(line)
        idx = self.annotations.index(self.active)
        self.lines[idx] = line

        # set the annotation
        inv = line.axes.transData.inverted()
        dmx, dmy = inv.transform((mx, my))
        didx, dx, dy = self.get_closest(line, dmx, dmy)
        self.active.xy = dx, dy
        xs, ys = line.get_data()
        self.active.xy_orig = xs[didx], ys[didx]
        self.active.set_text(self.xy_to_annotation(xs[didx], ys[didx]))
        x, y = self.active.config['pos_xy']
        wx.CallAfter(self.set_annotation_position, self.active, x, y)
        self.active.set_visible(True)
        self.figure.canvas.draw()
        return True

    def xy_to_annotation(self, x, y, fmt=None):
        if fmt is None:
            fmt = self.get_config()
        x_str = ""
        y_str = ""
        if isinstance(x, datetime.datetime):
            x_str = f'x: {x.strftime(fmt["fmt_datetime"])}'
        else:
            x_str= f'x: {x:{fmt["fmt_number"]}}'
        if isinstance(y, datetime.datetime):
            y_str = f'y: {y.strftime(fmt["fmt_datetime"])}'
        else:
            y_str= f'y: {y:{fmt["fmt_number"]}}'
        return '\n'.join([x_str, y_str])

    def keyboard_move(self, left, step=1):
        if not self.active:
            return
        idx = self.annotations.index(self.active)
        line = self.lines[idx]
        x, y = line.get_xdata(False), line.get_ydata(False)
        xc, yc = self.active.xy
        idx = (np.square(x - xc)).argmin()
        idx_new = idx
        if left:
            idx_new -= step
        else:
            idx_new += step
        idx_new = min(len(x)-1, idx_new)
        idx_new = max(0, idx_new)
        if idx == idx_new:
            return
        xn, yn = x[idx_new], y[idx_new]
        if xn is not None:
            self.active.xy = xn, yn
            xs, ys = line.get_xdata(), line.get_ydata()
            self.active.xy_orig = xs[idx_new], ys[idx_new]
            #self.active.set_text(self.text_template % (xn, yn))
            cx, cy = self.get_annotation_position(self.active)
            self.active.set_text(self.xy_to_annotation(xs[idx_new], ys[idx_new]))
            wx.CallAfter(self.set_annotation_position, self.active, cx, cy)
            self.active.set_visible(True)

    def set_enable(self, enable):
        self.enable = enable
        if self.active:
            config = self.get_config()
            if enable:
                self.active.get_bbox_patch().set_facecolor(config['clr_face_selected'])
            else:
                self.active.get_bbox_patch().set_facecolor(config['clr_face'])

    def mouse_move(self, event):
        """move the annotation position"""
        if event.button != matplotlib.backend_bases.MouseButton.LEFT:
            return False
        # return if no active annotation or the mouse is not pressed
        if self.mx is None or self.my is None or self.active is None or \
                self.cx is None or self.cy is None:
            return False
        # re-position the active annotation based on the mouse movement
        x, y = event.x, event.y
        bbox = self.active.get_bbox_patch()
        w, h = bbox.get_width(), bbox.get_height()
        dx = x - self.mx
        dy = y - self.my
        dis = math.sqrt(dx**2 + dy**2)
        if dis > 40:
            (px, py) = (0, 0)
            px = int(dx / 40)
            py = int(dy / 40)

            cx, cy = self.cx, self.cy
            cx += px
            cy += py
            cx = max(min(cx, 1), -1)
            cy = max(min(cy, 1), -1)
            self.active.config['pos_xy'] = (cx, cy)
            self.set_annotation_position(self.active, cx, cy)
            return True
        return False

    def set_annotation_position(self, ant, x, y):
        bbox = ant.get_bbox_patch()
        w, h = bbox.get_width(), bbox.get_height()
        ant.xyann = (x*w - w/2 , y*h-h/2)
        ant.config['pos_xy'] = (x, y)

    def get_annotation_position(self, ant):
        return ant.config['pos_xy']

    def get_annotation(self, x, y):
        for ant in self.annotations:
            box = ant.get_bbox_patch().get_extents()
            if box.contains(x, y):
                return ant
        return None

    def mouse_pressed(self, event):
        """
        select the active annotation which is closest to the mouse position
        """
        if event.button != matplotlib.backend_bases.MouseButton.LEFT:
            return False

        axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]
        line, dis = self.get_closest_line(axes, event.x, event.y)
        if line:
            if self.annotation_line(line, event.x, event.y):
                return True

        # just created the new annotation, do not move to others
        if self.active and (not self.active.get_visible()):
            return False
        # search the closest annotation
        x, y = event.x, event.y
        self.mx, self.my = x, y
        active = self.get_annotation(x, y)
        self.set_active(active)
        if self.active:
            self.cx, self.cy = self.get_annotation_position(self.active)
        # return True for the parent to redraw
        return True

    def mouse_released(self, event):
        """release the mouse"""
        self.mx, self.my = None, None

    def get_active(self):
        """retrieve the active annotation"""
        return self.active

    def set_active(self, ant):
        """set the active annotation"""
        if ant and not ant in self.annotations:
            return False

        if self.active == ant:
            return True
        old_active = self.active
        self.active = ant
        if old_active:
            self.ApplyConfig(old_active)
        if self.active:
            self.ApplyConfig(self.active)
        self.figure.canvas.draw_idle()
        return True

    def get_annotations(self):
        """return all the annotations"""
        return self.annotations

    def create_annotation(self, line):
        """create the annotation and set it active"""
        config = self.get_config()
        ant = line.axes.annotate(self.text_template,
                                 xy=(0, 0),
                                 xytext=(0, 0),
                                 textcoords='offset pixels',
                                 ha='left',
                                 va='bottom',
                                 bbox={'boxstyle': 'round,pad=0.5',
                                       'fc': config['clr_face_selected'],
                                       'alpha': 1},
                                 arrowprops={'arrowstyle': '->',
                                             'connectionstyle': 'arc3,rad=0'})
        ant.set_visible(False)
        ant.xy_orig = (0, 0)
        self.ApplyConfig(ant, config)
        self.annotations.append(ant)
        self.lines.append(line)
        self.set_active(ant)

    def GetMenu(self, axes):
        active_in_axes = False
        if self.active and self.active.get_visible():
            idx = self.annotations.index(self.active)
            active_in_axes = self.lines[idx].axes in axes
        ant_in_axes = any(l.axes in axes for l in self.lines)
        cmd = [{'id': self.ID_DELETE_DATATIP, 'label': 'Delete current datatip',
                'enable': active_in_axes},
               {'id': self.ID_CLEAR_DATATIP, 'label': 'Delete all datatip',
                'enable': ant_in_axes},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_EXPORT_DATATIP, 'label': 'Export datatip data...',
                'enable': ant_in_axes},
               {'type': wx.ITEM_SEPARATOR},
               {'id': self.ID_SETTING, 'label': 'Settings ...'},
               ]
        return cmd

    def key_down(self, event):
        keycode = event.GetKeyCode()
        step = 1
        if event.ShiftDown():
            step = 10
        if keycode == wx.WXK_LEFT:
            self.keyboard_move(True, step=step)
        elif keycode == wx.WXK_RIGHT:
            self.keyboard_move(False, step=step)
        else:
            event.Skip()

    def ProcessCommand(self, cmd, axes):
        """process the context menu command"""
        ant_in_axes = [l.axes in axes for l in self.lines]
        active_in_axes = False
        if self.active:
            idx = self.annotations.index(self.active)
            active_in_axes = ant_in_axes[idx]

        if cmd == self.ID_DELETE_DATATIP:
            if not active_in_axes:
                return False
            idx = self.annotations.index(self.active)
            if not ant_in_axes[idx]:
                return False
            self.active.remove()
            del self.annotations[idx]
            del self.lines[idx]
            self.active = None
            return True
        elif cmd == self.ID_CLEAR_DATATIP:
            ant_in_axes = [l.axes in axes for l in self.lines]
            annotations = []
            lines = []
            for idx, ant in enumerate(self.annotations):
                if ant_in_axes[idx]:
                    try:
                        # the call may fail. For example,
                        # 1) create a figure and plot some curve
                        # 2) create a datatip
                        # 3) call clf() to clear the figure, the datatip will be
                        #    cleared, but we will not know
                        ant.remove()
                    except:
                        pass
                else:
                    annotations.append(self.annotations[idx])
                    lines.append(self.lines[idx])
            self.annotations = annotations
            self.lines = lines
            self.active = None
            return True
        elif cmd == self.ID_EXPORT_DATATIP:
            datatip_data = []
            for idx, ant in enumerate(self.annotations):
                if ant_in_axes[idx]:
                    datatip_data.append(ant.xy_orig)
            datatip_data = np.array(datatip_data)

            np.save('_datatip.npy', datatip_data)
            dp.send('shell.run',
                    command='datatip_data = np.load("_datatip.npy", allow_pickle=True)',
                    prompt=False,
                    verbose=False,
                    history=False)
            dp.send('shell.run',
                    command='datatip_data',
                    prompt=True,
                    verbose=True,
                    history=False)
            return True
        elif cmd == self.ID_SETTING:
            settings = [s.duplicate() for s in  self.settings]
            active = None
            if active_in_axes:
                active = self.active
            if active:
                for idx, p in enumerate(settings):
                    n = settings[idx].GetName()
                    if n in active.config:
                        settings[idx].SetValue(active.config[n], True)
            dlg = DatatipSettingDlg(settings, active is not None,
                                    self.window.GetParent(),
                                    size=(600, 480))
            dlg.CenterOnParent()

            # this does not return until the dialog is closed.
            val = dlg.ShowModal()
            if val == wx.ID_OK:
                settings = dlg.get_settings()
                save_as_default = settings.get('save_as_default', False)
                apply_all = settings.get('apply_all', False)
                settings = settings['settings']
                if save_as_default:
                    self.SaveConfig(settings)
                if apply_all:
                    self.LoadConfig(settings)
                    config = self.get_config(settings)
                    for idx, ant in enumerate(self.annotations):
                        if ant_in_axes[idx]:
                            self.ApplyConfig(ant, config)
                elif active:
                    self.set_active(active)
                    self.ApplyConfig(active, self.get_config(settings))
                else:
                    self.LoadConfig(settings)

            dlg.Destroy()
        return False

    def activated(self):
        pass
    def deactivated(self):
        pass

    def get_config(self, settings=None):
        if settings is None:
            settings = self.settings
        if isinstance(settings, dict):
            return settings
        config = {p.GetName():p.GetValue() for p in settings if not p.IsSeparator()}
        return config

    def ApplyConfigAll(self, config=None):
        for ant in self.annotations:
            self.ApplyConfig(ant, config)

    def ApplyConfig(self, ant, config=None):
        if not config:
            config = ant.config
        clr = None
        alpha = 50
        if self.active == ant:
            clr_edge = config['clr_edge_selected']
            clr_face = config['clr_face_selected']
            alpha = config['clr_alpha_selected']
        else:
            clr_edge = config['clr_edge']
            clr_face = config['clr_face']
            alpha = config['clr_alpha']
        ant.get_bbox_patch().set_edgecolor(clr_edge)
        ant.get_bbox_patch().set_facecolor(clr_face)
        ant.get_bbox_patch().set_alpha(alpha/100)

        xs, ys = ant.xy_orig
        ant.set_text(self.xy_to_annotation(xs, ys, config))
        ant.config = config
        x, y = self.get_annotation_position(ant)
        wx.CallAfter(self.set_annotation_position, ant, x, y)

    def SaveConfig(self, settings):
        config = self.get_config(settings)
        dp.send('frame.set_config', group='graph_datatip', **config)

    def LoadConfig(self, config=None):
        if config is None:
            resp = dp.send('frame.get_config', group='graph_datatip')
            if resp and resp[0][1] is not None:
                config = resp[0][1]
        if not config:
            return
        for idx, p in enumerate(self.settings):
            n = p.GetName()
            if n in config:
                self.settings[idx].SetValue(config[n], True)


class DatatipSettingDlg(wx.Dialog):
    def __init__(self, settings, active, parent, id=-1, title='Settings ...',
                 size=wx.DefaultSize, pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):
        wx.Dialog.__init__(self)
        self.SetExtraStyle(wx.DIALOG_EX_CONTEXTHELP)
        self.Create(parent, id, title, pos, size, style)

        self.settings = settings
        self.propgrid = pg.PropGrid(self)
        g = self.propgrid
        g.Draggable(False)

        for p in settings:
            g.Insert(p)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(g, 1, wx.EXPAND|wx.ALL, 1)

        self.cbApplyAll = wx.CheckBox(self, label="Apply settings to existing datatips in this figure")
        self.cbSaveAsDefaultCurrent = wx.CheckBox(self, label="Save settings as default for this figure")
        self.cbSaveAsDefaultCurrent.Show(active)
        self.cbSaveAsDefault = wx.CheckBox(self, label="Save settings as default for new figures")

        sizer.Add(self.cbApplyAll, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.cbSaveAsDefaultCurrent, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(self.cbSaveAsDefault, 0, wx.EXPAND|wx.ALL, 5)

        # ok/cancel button
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.AddStretchSpacer(1)

        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALL|wx.EXPAND, 5)

        self.SetSizer(sizer)

        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

    def OnContextMenu(self, event):
        # it is necessary, otherwise when right click on the dialog, the context
        # menu of the MatplotPanel will show; it may be due to some 'bug' in
        # CaptureMouse/ReleaseMouse (canvas is a panel that capture mouse)
        # and we also need to release the mouse before show the MatplotPanel
        # context menu (wchich will eventually show this dialog)
        pass

    def rgb2hex(self, clr):
        clr = np.sum(clr * 255 * [2**16, 2**8, 1], 1).astype(np.int32)
        return ["#{:06x}".format(c) for c in clr]

    def get_settings(self):
        settings = {}

        settings['apply_all'] = self.cbApplyAll.IsChecked()
        settings['save_as_default'] = self.cbSaveAsDefault.IsChecked()
        settings['save_as_default_cur'] = self.cbSaveAsDefaultCurrent.IsChecked()
        settings['settings'] = {}
        for i in range(0, len(self.settings)):
            p = self.settings[i]
            if p.IsSeparator():
                continue
            n = p.GetName()
            settings['settings'][n] = self.propgrid.Get(n).GetValue()
        return settings
