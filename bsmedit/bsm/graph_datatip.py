import datetime
import copy
import math
import wx
import wx.py.dispatcher as dp
import numpy as np
from .graph_common import GraphObject
from .. import propgrid as pg
from ..propgrid import formatters as fmt

class DataCursor(GraphObject):
    xoffset, yoffset = -20, 20
    text_template = 'x: %0.2f\ny: %0.2f'

    ID_DELETE_DATATIP = wx.NewId()
    ID_CLEAR_DATATIP = wx.NewId()
    ID_EXPORT_DATATIP = wx.NewId()
    def __init__(self, figure, win):
        super().__init__(figure)
        self.annotations = []
        self.lines = []
        self.enable = False
        self.active = None
        self.mx, self.my = None, None
        self.pickEvent = False
        self.window = win
        self.settings = [
                #[indent, type, name, label, value, fmt]
                [0, 'choice', 'pos_xy', 'position', (-1, 1), {
                    (-1, 1): 'top left',
                    (0, 1): 'top',
                    (1, 1): 'top right',
                    (1, 0): 'right',
                    (1, -1): 'bottom right',
                    (0, -1): 'bottom',
                    (-1, -1): 'bottom left',
                    (-1, 0): 'left',
                    }],
                [0, 'separator', 'sep_fmt', 'Format', '', None],
                [1, 'string', 'fmt_number', 'Number', '.2f', None],
                [1, 'string', 'fmt_datetime', 'Datetime', '%Y-%m-%d %H:%M:%S', None],
                [0, 'separator', 'sep_clr', 'Color', '', None],
                [1, 'color', 'clr_edge', 'Edge', '#8E8E93', None],
                [1, 'color', 'clr_face', 'Face', '#ffffff', None],
                [1, 'spin', 'clr_alpha', 'Opacity', 50, (0, 100)],
                [0, 'separator', 'sep_clr_selected', 'Selected color', '', None],
                [1, 'color', 'clr_edge_selected', 'Edge', '#8E8E93', None],
                [1, 'color', 'clr_face_selected', 'Face', '#ffff00', None],
                [1, 'spin', 'clr_alpha_selected', 'Opacity', 5, (0, 100)],
                ]
        self.LoadConfig()

    def pick(self, event):
        if not self.enable:
            return
        if not event.mouseevent.xdata or not event.mouseevent.ydata:
            return
        if not event.artist:
            return
        xm, ym = event.mouseevent.x, event.mouseevent.y
        if self.get_annotation(xm, ym) is not None:
            # click in the box of existing annotation, ignore it
            return

        line = event.artist
        if self.active and self.active.get_visible():
            # Check whether the axes of active annotation is same as line,
            # which may happen in a figure with subplots. If not, create one
            # with the axes of line
            if self.active.axes != line.axes:
                self.active = None
        if self.active is None:
            self.create_annotation(line)
        idx = self.annotations.index(self.active)
        self.lines[idx] = line

        # find the closest point on the line
        x, y = line.get_xdata(False), line.get_ydata(False)
        xc, yc = event.mouseevent.xdata, event.mouseevent.ydata
        gx, gy = self.get_xy_dis_gain()
        idx = (np.square(x - xc) * gx**2 + np.square(y - yc) * gy**2).argmin()
        xn, yn = x[idx], y[idx]
        if xn is not None:
            self.active.xy = xn, yn
            xs, ys = line.get_data()
            self.active.xy_orig = xs[idx], ys[idx]
            #self.active.set_text(self.text_template % (xs[idx], ys[idx]))
            self.active.set_text(self.xy_to_annotation(xs[idx], ys[idx]))
            x, y = self.active.config['pos_xy']
            wx.CallAfter(self.set_annotation_position, self.active, x, y)
            self.active.set_visible(True)
            event.canvas.draw()
        self.pickEvent = True

    def xy_to_annotation(self, x, y, fmt=None):
        if fmt is None:
            fmt = self.get_config()
        anno = ""
        if isinstance(x, datetime.datetime):
            anno = f'x: {x.strftime(fmt["fmt_datetime"])}\ny: {y.strftime(fmt["fmt_datetime"])}'
        else:
            anno = f'x: {x:{fmt["fmt_number"]}}\ny: {y:{fmt["fmt_number"]}}'
        return anno

    def keyboard_move(self, left, step=1):
        if not self.active:
            return
        idx = self.annotations.index(self.active)
        line = self.lines[idx]
        x, y = line.get_xdata(True), line.get_ydata(True)
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
        # return if no active annotation or the mouse is not pressed
        if self.mx is None or self.my is None or self.active is None:
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
        # ignore the event triggered immediately after pick_event
        if self.pickEvent:
            self.pickEvent = False
            return False
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
                                 bbox=dict(boxstyle='round,pad=0.5',
                                           fc=config['clr_face_selected'],
                                           alpha=1),
                                 arrowprops=dict(arrowstyle='->',
                                                 connectionstyle='arc3,rad=0'))
        ant.set_visible(False)
        ant.xy_orig = (0, 0)
        self.ApplyConfig(ant, config)
        self.annotations.append(ant)
        self.lines.append(line)
        self.set_active(ant)

    def GetMenu(self):
        cmd = [[self.ID_DELETE_DATATIP, 'Delete current datatip',
                self.active is not None and self.active.get_visible()],
               [self.ID_CLEAR_DATATIP, 'Delete all datatip', len(self.annotations) > 0],
               [],
               [self.ID_EXPORT_DATATIP, 'Export datatip data...', len(self.annotations) > 0],
               [],
               [wx.ID_PREFERENCES, 'Settings ...', True],
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

    def ProcessCommand(self, cmd):
        """process the context menu command"""
        if cmd == self.ID_DELETE_DATATIP:
            if not self.active:
                return False
            idx = self.annotations.index(self.active)
            self.active.remove()
            del self.annotations[idx]
            del self.lines[idx]
            self.active = None
            return True
        elif cmd == self.ID_CLEAR_DATATIP:
            for ant in self.annotations:
                try:
                    # the call may fail. For example,
                    # 1) create a figure and plot some curve
                    # 2) create a datatip
                    # 3) call clf() to clear the figure, the datatip will be
                    #    cleared, but we will not know
                    ant.remove()
                except:
                    pass
            self.annotations = []
            self.lines = []
            self.active = None
            return True
        elif cmd == self.ID_EXPORT_DATATIP:
            datatip_data = []
            for ant in self.annotations:
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
        elif cmd == wx.ID_PREFERENCES:
            settings = copy.deepcopy(self.settings)
            active = self.active
            if active:
                for idx, (i, t, n, l, v, f) in enumerate(settings):
                    settings[idx][4] = active.config.get(n, v)

            dlg = DatatipSettingDlg(settings, active is not None,
                                    self.window.GetTopLevelParent(),
                                    size=(600, 400))
            dlg.CenterOnParent()
            self.window.Enable(False)

            # this does not return until the dialog is closed.
            val = dlg.ShowModal()
            self.window.Enable(True)
            if val == wx.ID_OK:
                settings = dlg.get_settings()
                save_as_default = settings.get('save_as_default', False)
                apply_all = settings.get('apply_all', False)
                settings = settings['settings']
                if save_as_default:
                    self.SaveConfig(settings)
                if apply_all:
                    self.settings = settings
                    self.ApplyConfigAll(self.get_config(settings))
                elif active:
                    self.set_active(active)
                    self.ApplyConfig(active, self.get_config(settings))
                else:
                    self.settings = settings

            dlg.Destroy()
        return False

    def activated(self):
        pass
    def deactivated(self):
        pass

    def get_config(self, settings=None):
        if settings is None:
            settings = self.settings

        config = {n:v for i, t, n, l, v, f in settings if t != 'separator'}
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

    def LoadConfig(self):
        resp = dp.send('frame.get_config', group='graph_datatip')
        if resp and resp[0][1] is not None:
            config = resp[0][1]
            for idx, (i, t, n, l, v, f) in enumerate(self.settings):
                if n in config:
                    self.settings[idx][4] = config[n]


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

        for i, t, n, l, v, f in settings:
            if t == 'separator':
                p = g.InsertSeparator(n, l)
            elif t == 'string':
                p = g.InsertProperty(n, l, v)
            elif t == 'color':
                c = v
                p = g.InsertProperty(n, l, c)
                p.SetBgColor(c, c, c)
                p.SetFormatter(fmt.ColorFormatter())
                t = wx.Colour(c)
                t.SetRGB(t.GetRGB() ^ 0xFFFFFF)
                t = t.GetAsString(wx.C2S_HTML_SYNTAX)
                p.SetTextColor(t, t, t)
            elif t == 'int':
                p = g.InsertProperty(n, l, v)
                p.SetFormatter(fmt.IntFormatter(-1, 1))
            elif t == 'choice':
                p = g.InsertProperty(n, l, v)
                p.SetFormatter(fmt.ChoiceFormatter(f))
            elif t == 'spin':
                p = g.InsertProperty(n, l, v)
                p.SetControlStyle('spin')
                p.SetFormatter(fmt.IntFormatter(f[0], f[1]))
            else:
                raise ValueError()
            p.SetIndent(i)

        sizer = wx.BoxSizer(wx.VERTICAL)

        sizer.Add(g, 1, wx.EXPAND|wx.ALL, 5)

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
        #sizer.Fit(self)
        #self.Layout()
        self.Bind(pg.EVT_PROP_CHANGED, self.OnPropChanged)

    def OnPropChanged(self, evt):
        p = evt.GetProperty()
        if 'clr_' in p.GetName():
            t = wx.Colour(p.GetValue())
            c = t.GetAsString(wx.C2S_HTML_SYNTAX)
            p.SetBgColor(c, c, c)
            t.SetRGB(t.GetRGB() ^ 0xFFFFFF)
            t = t.GetAsString(wx.C2S_HTML_SYNTAX)
            p.SetTextColor(t, t, t)

    def rgb2hex(self, clr):
        clr = np.sum(clr * 255 * [2**16, 2**8, 1], 1).astype(np.int32)
        return ["#{:06x}".format(c) for c in clr]

    def get_settings(self):
        settings = {}

        settings['apply_all'] = self.cbApplyAll.IsChecked()
        settings['save_as_default'] = self.cbSaveAsDefault.IsChecked()
        settings['save_as_default_cur'] = self.cbSaveAsDefaultCurrent.IsChecked()
        settings['settings'] = self.settings.copy()
        for i in range(0, len(self.settings)):
            _, t, n, l, v, f = self.settings[i]
            if t == 'seperator':
                continue

            self.settings[i][4] = self.propgrid.GetProperty(n).GetValue()
        return settings

