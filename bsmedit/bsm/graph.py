import json
import wx
import wx.py.dispatcher as dp
import numpy as np
import pandas
import matplotlib
matplotlib.use('module://bsmedit.bsm.bsmbackend')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import FigureManagerWx
from matplotlib.backend_bases import CloseEvent
from matplotlib._pylab_helpers import Gcf
import matplotlib.pyplot as plt
from matplotlib import rcParams
from .graph_common import GraphObject
from .lineeditor import LineEditor
from .graph_datatip import DataCursor
from .utility import PopupMenu, build_menu_from_list, svg_to_bitmap
from .bsmxpm import home_xpm, back_xpm, forward_xpm, pan_xpm, zoom_xpm, \
                    cursor_xpm, save_xpm, copy_xpm, line_edit_xpm, page_add_xpm, \
                    more_svg
from .. import to_byte
from .graph_toolbar import GraphToolbar
rcParams.update({'figure.autolayout': True})
rcParams.update({'toolbar': 'None'})
matplotlib.interactive(True)


class Pan(GraphObject):
    def __init__(self, figure):
        super().__init__(figure)
        self.axes = None

    def key_down(self, event):
        keycode = event.GetKeyCode()
        axes = self.axes
        if axes is None:
            if len(self.figure.get_axes()) > 1:
                return
            axes = [self.figure.gca()]
        xlims_all = []
        ylims_all = []
        for ax in axes:
            # get the xlim from all axes first, as some x-axis may be shared;
            # otherwise, the shared x-axis will be moved multiple times.
            xlims_all.append(np.array(ax.get_xlim()))
            ylims_all.append(np.array(ax.get_ylim()))
        step = 1
        if event.ShiftDown():
            step = 1/10
        for i, ax in enumerate(axes):
            xlims = xlims_all[i]
            ylims = ylims_all[i]
            rng_x = (xlims[1] - xlims[0])*step
            rng_y = (ylims[1] - ylims[0])*step
            if keycode in [wx.WXK_LEFT, wx.WXK_RIGHT]:
                if keycode == wx.WXK_LEFT:
                    xlims -= rng_x
                else:
                    xlims += rng_x

                ax.set_xlim(xlims)
                # rescale y to show data
                #ax.autoscale(axis='y')
            elif keycode in [wx.WXK_UP, wx.WXK_DOWN]:
                if keycode == wx.WXK_UP:
                    ylims += rng_y
                else:
                    ylims -= rng_y

                ax.set_ylim(ylims)
                #ax.autoscale(axis='x')
            else:
                event.Skip()
        self.figure.canvas.draw_idle()

    def mouse_pressed(self, event):
        self.axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]
        return False

class Toolbar(GraphToolbar):
    ID_AUTO_SCALE_X = wx.NewIdRef()
    ID_AUTO_SCALE_Y = wx.NewIdRef()
    ID_AUTO_SCALE_XY = wx.NewIdRef()
    ID_SPLIT_HORZ = wx.NewIdRef()
    ID_SPLIT_VERT = wx.NewIdRef()
    ID_DELETE_SUBPLOT = wx.NewIdRef()
    ID_DELETE_LINES = wx.NewIdRef()

    def __init__(self, canvas, figure):
        if matplotlib.__version__ < '3.3.0':
            self._init_toolbar = self.init_toolbar
        else:
            self._init_toolbar = self.init_toolbar_empty
        GraphToolbar.__init__(self, canvas)

        if matplotlib.__version__ >= '3.3.0':
            self.init_toolbar()
        self.figure = figure
        self.datacursor = DataCursor(self.figure, self)
        self.lineeditor = LineEditor(self.figure)
        self.pan_action = Pan(self.figure)

        self.actions = {'datatip': self.datacursor,
                        'edit': self.lineeditor,
                        'pan/zoom': self.pan_action}

        self.canvas.mpl_connect('pick_event', self.OnPick)
        self.canvas.mpl_connect('motion_notify_event', self.OnMove)
        self.canvas.mpl_connect('button_press_event', self.OnPressed)
        self.canvas.mpl_connect('button_release_event', self.OnReleased)
        self.canvas.mpl_connect('scroll_event', self.OnZoomFun)
        self.canvas.mpl_connect('key_press_event', self.OnKeyPressed)
        # clear the view history
        wx.CallAfter(self._nav_stack.clear)

        self.linestyle_ids = {}
        self.marker_ids = {}

    def GetMenu(self):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'GetMenu'):
            return []
        return action.GetMenu()

    def key_down(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'key_down'):
            return
        action.key_down(event)

    def ProcessCommand(self, cmd):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'ProcessCommand'):
            return
        action.ProcessCommand(cmd)

    def OnPick(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'pick'):
            return
        action.pick(event)

    def OnKeyPressed(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'key_pressed'):
            return
        action.key_pressed(event)

    def _set_picker_all(self):
        for g in self.figure.get_axes():
            for l in g.lines:
                if l.get_picker() is None:
                    l.set_picker(5)

    def OnPressed(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'mouse_pressed'):
            return
        # some lines may be added
        self._set_picker_all()
        if action.mouse_pressed(event):
            self.canvas.draw()

    def OnReleased(self, event):

        action = self.actions.get(self.mode, None)
        if action and hasattr(action, 'mouse_released'):
            action.mouse_released(event)
            return

        if event.button == matplotlib.backend_bases.MouseButton.RIGHT:
            self.OnContextMenu(event)
            return

        axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]
        if axes:
            self.figure.sca(axes[0])

    def OnContextMenu(self, event):
        axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]
        if not axes:
            return
        menu = wx.Menu()
        style_menu = wx.Menu()

        for k, v in matplotlib.lines.Line2D.lineStyles.items():
            if k and isinstance(k, str) and not k.isspace():
                if k not in self.linestyle_ids:
                    self.linestyle_ids[k] = wx.NewIdRef()
                v = v.replace('_draw_', '')
                v = v.replace('_', ' ')
                style_menu.Append(self.linestyle_ids[k], v)
        marker_menu = wx.Menu()
        for k, v in matplotlib.lines.Line2D.markers.items():
            if k and isinstance(k, str) and not k.isspace():
                if k not in self.marker_ids:
                    self.marker_ids[k] = wx.NewIdRef()
                marker_menu.Append(self.marker_ids[k], k)
        menu.AppendSubMenu(style_menu, "Line Style")
        menu.AppendSubMenu(marker_menu, "Marker Style")
        menu.AppendSeparator()
        menu.Append(self.ID_SPLIT_VERT, "Split Vertically")
        menu.Append(self.ID_DELETE_SUBPLOT, "Delete Plot")
        menu.Append(self.ID_DELETE_LINES, "Delete all lines")
        cmd = PopupMenu(self, menu)
        if cmd in self.linestyle_ids.values():
            style = list(self.linestyle_ids.keys())[list(self.linestyle_ids.values()).index(cmd)]
            for ax in axes:
                for l in ax.lines:
                    l.set_linestyle(style)
        elif cmd in self.marker_ids.values():
            marker = list(self.marker_ids.keys())[list(self.marker_ids.values()).index(cmd)]
            for ax in axes:
                for l in ax.lines:
                    l.set_marker(marker)
        elif cmd == self.ID_SPLIT_VERT:
            g = axes[0].get_gridspec()
            n, m, r, c = axes[0].get_subplotspec().get_geometry()
            g2 = matplotlib.gridspec.GridSpec(n+1, m)
            for ax in self.figure.axes:
                _, _, i, j = ax.get_subplotspec().get_geometry()
                if i>r:
                    i = i+1
                ax.set_subplotspec(g2[i])
            ax = self.figure.add_subplot(g2[r+1], sharex=axes[0])
            ax.grid(True)
        elif cmd == self.ID_DELETE_SUBPLOT:
            g = axes[0].get_gridspec()
            n, m, r, c = axes[0].get_subplotspec().get_geometry()
            self.figure.delaxes(axes[0])
            if n>1:
                g2 = matplotlib.gridspec.GridSpec(n-1, m)
                for ax in self.figure.axes:
                    _, _, i, j = ax.get_subplotspec().get_geometry()
                    if i>r:
                        i = i-1
                    ax.set_subplotspec(g2[i])
        elif cmd == self.ID_DELETE_LINES:
            for ax in axes:
                ax.cla()
                ax.grid(True)

    def OnMove(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'mouse_move'):
            return
        if action.mouse_move(event):
            self.canvas.draw()

    def OnZoomFun(self, event):
        # get the current x and y limits
        if not self.GetToolToggled(self.wx_ids['Zoom']):
            return
        if self._nav_stack() is None:
            self.push_current()

        axes = [a for a in self.figure.get_axes()
                if a.in_axes(event)]

        yzoom_key = xzoom_key = True
        if wx.GetKeyState(wx.WXK_CONTROL_X):
            yzoom_key = False
        elif wx.GetKeyState(wx.WXK_CONTROL_Y):
            xzoom_key = False
        xzoom = yzoom = xzoom_key, yzoom_key
        xdata, ydata = event.xdata, event.ydata
        axes = [[a, xzoom, yzoom, xdata, ydata] for a in self.figure.get_axes()
                if a.in_axes(event)]
        if not axes:
            axes = []
            for ax in self.figure.get_axes():
                x,y = event.x, event.y
                xAxes, yAxes = ax.transAxes.inverted().transform([x, y])
                if -0.1 < xAxes < 0:
                    xzoom = False
                if -0.1 < yAxes < 0:
                    yzoom = False
                xdata, ydata = ax.transData.inverted().transform([x, y])
                if not yzoom or (not xzoom and -0.05 < yAxes < 1):
                    axes.append([ax, xzoom, yzoom, xdata, ydata])
                xzoom = yzoom = xzoom_key, yzoom_key
            if not axes:
                return

        base_scale = 2.0
        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1.0 / base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1.0

        for ax, xzoom, yzoom, xdata, ydata in axes:
            if xzoom:
                cur_xlim = ax.get_xlim()
                new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
                relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
                if new_width * (1 - relx) > 0:
                    ax.set_xlim(
                        [xdata - new_width * (1 - relx), xdata + new_width * (relx)])
            if yzoom:
                cur_ylim = ax.get_ylim()
                new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
                rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

                if new_height * (1 - rely) > 0:
                    ax.set_ylim(
                        [ydata - new_height * (1 - rely), ydata + new_height * (rely)])
        self.canvas.draw()

    def init_toolbar_empty(self):
        # deprecated in 3.3.0
        pass
    def init_toolbar(self):
        toolitems = (
            ('New', 'New figure', page_add_xpm, 'OnNewFigure'),
            (None, None, None, None),
            ('Home', 'Reset original view', home_xpm, 'home'),
            ('Back', 'Back to  previous view', back_xpm, 'OnBack'),
            ('Forward', 'Forward to next view', forward_xpm, 'OnForward'),
            (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', pan_xpm,
             'pan'),
            ('Zoom', 'Zoom to rectangle', zoom_xpm, 'zoom'),
            ('Datatip', 'Show the data tip', cursor_xpm, 'datatip'),
            (None, None, None, None),
            ('Save', 'Save the figure', save_xpm, 'save_figure'),
            ('Copy', 'Copy to clipboard', copy_xpm, 'copy_figure'),
            (None, None, None, None),
            ('Edit', 'Edit curve', line_edit_xpm, 'edit_figure'),
            (None, None, None, None),
            (None, None, None, "stretch"),
            ('Auto Scale', 'Auto Scale', more_svg, 'OnMore'),
            #(None, None, None, None),
            #('Print', 'Print the figure', print_xpm, 'print_figure'),
        )

        self._parent = self.canvas.GetParent()
        self.ClearTools()
        self.wx_ids = {}
        self.SetToolBitmapSize((16, 16))
        for (text, tooltip_text, image_file, callback) in toolitems:
            if text is None:
                if callback == "stretch":
                    self.AddStretchSpacer()
                else:
                    self.AddSeparator()
                continue
            self.wx_ids[text] = wx.NewIdRef()
            if isinstance(image_file, list):
                image = wx.Bitmap(to_byte(image_file))
            else:
                image = svg_to_bitmap(image_file, win=self)
            if text in ['Pan', 'Zoom', 'Datatip', 'Edit']:
                self.AddCheckTool(self.wx_ids[text],
                                  text,
                                  image,
                                  disabled_bitmap=wx.NullBitmap,
                                  short_help_string=text,
                                  long_help_string=tooltip_text)
            else:
                self.AddTool(self.wx_ids[text], text,
                             image,
                             disabled_bitmap=wx.NullBitmap,
                             kind=wx.ITEM_NORMAL, short_help_string=tooltip_text)
            self.Bind(wx.EVT_TOOL,
                      getattr(self, callback),
                      id=self.wx_ids[text])

        self.Bind(wx.EVT_MENU, self.OnProcessMenu, id=self.ID_AUTO_SCALE_X)
        self.Bind(wx.EVT_MENU, self.OnProcessMenu, id=self.ID_AUTO_SCALE_Y)
        self.Bind(wx.EVT_MENU, self.OnProcessMenu, id=self.ID_AUTO_SCALE_XY)

        self.Realize()

    def OnMore(self, event):
        menu = wx.Menu()
        menu.Append(self.ID_AUTO_SCALE_XY, "Auto scale")
        menu.AppendSeparator()
        menu.Append(self.ID_AUTO_SCALE_X, "Auto scale x-axis")
        menu.Append(self.ID_AUTO_SCALE_Y, "Auto scale y-axis")

        # line up our menu with the button
        tb = event.GetEventObject()
        tb.SetToolSticky(event.GetId(), True)
        rect = tb.GetToolRect(event.GetId())
        pt = tb.ClientToScreen(rect.GetBottomLeft())
        pt = self.ScreenToClient(pt)

        self.PopupMenu(menu, pt)

        # make sure the button is "un-stuck"
        tb.SetToolSticky(event.GetId(), False)

    def OnProcessMenu(self, event):
        eid = event.GetId()
        if eid == self.ID_AUTO_SCALE_XY:
            self.do_auto_scale()
        if eid == self.ID_AUTO_SCALE_X:
            self.do_auto_scale('x')
        elif eid == self.ID_AUTO_SCALE_Y:
            self.do_auto_scale('y')

    def OnNewFigure(self, evt):
        dp.send('shell.run',
                command='figure();',
                prompt=False,
                verbose=False,
                debug=False,
                history=False)

    def do_auto_scale(self,axis='both'):
        for ax in self.figure.get_axes():
            ax.autoscale(axis=axis)
        self.figure.canvas.draw_idle()

    def copy_figure(self, evt):
        # self.canvas.Copy_to_Clipboard(event=evt)
        bmp_obj = wx.BitmapDataObject()
        bmp_obj.SetBitmap(self.canvas.bitmap)

        if not wx.TheClipboard.IsOpened():
            open_success = wx.TheClipboard.Open()
            if open_success:
                wx.TheClipboard.SetData(bmp_obj)
                wx.TheClipboard.Flush()
                wx.TheClipboard.Close()

    def print_figure(self, evt):
        self.canvas.Printer_Print(event=evt)

    def set_mode(self, mode):
        if mode != 'datatip':
            self.ToggleTool(self.wx_ids['Datatip'], False)
        if mode != 'edit':
            self.ToggleTool(self.wx_ids['Edit'], False)
        if mode != 'pan':
            self.ToggleTool(self.wx_ids['Pan'], False)
        if mode != 'zoom':
            self.ToggleTool(self.wx_ids['Zoom'], False)

        action = self.actions.get(self.mode, None)
        if action is not  None and  hasattr(action, 'deactivated'):
            action.deactivated()

        if mode in ['pan', 'zoom']:
            # these mode handled by the base class
            return

        self.mode = mode

        action = self.actions.get(self.mode, None)
        if action is not None and hasattr(action, 'activated'):
            action.activated()

    def zoom(self, *args):
        """activate the zoom mode"""
        self.set_mode('zoom')
        super().zoom(*args)

    def pan(self, *args):
        """activated the pan mode"""
        self.set_mode('pan')
        super().pan(*args)

    def OnBack(self, *args):
        super().back(*args)

    def back(self, *args):
        action = self.actions.get(self.mode, None)
        if action is not None:
            return
        super().back(*args)

    def OnForward(self, *args):
        super().forward(*args)

    def forward(self, *args):
        action = self.actions.get(self.mode, None)
        if action is not None:
            return
        super().forward(*args)

    def datatip(self, evt):
        """activate the datatip mode"""
        # disable the pan/zoom mode
        self._active = None
        if hasattr(self, '_idPress'):
            self._idPress = self.canvas.mpl_disconnect(self._idPress)

        if hasattr(self, '_idRelease'):
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self._set_picker_all()
        if self.mode == 'datatip':
            self.set_mode('')
        else:
            self.set_mode("datatip")
        self.set_message(self.mode)
        self.datacursor.set_enable(evt.GetInt())

    def edit_figure(self, evt):
        """activate the curve editting  mode"""
        # disable the pan/zoom mode
        self.set_message(self.mode)

        self._active = None
        if hasattr(self, '_idPress'):
            self._idPress = self.canvas.mpl_disconnect(self._idPress)

        if hasattr(self, '_idRelease'):
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self._set_picker_all()
        if self.mode == "edit":
            self.set_mode("")
        else:
            self.set_mode("edit")
        self.set_message(self.mode)

    def set_message(self, s):
        """show the status message"""
        dp.send(signal='frame.show_status_text', text=s, index=1, width=160)

class DataDropTarget(wx.DropTarget):
    def __init__(self, canvas):
        wx.DropTarget.__init__(self)
        self.obj = wx.TextDataObject()
        self.SetDataObject(self.obj)
        self.canvas = canvas
        self.SetDefaultAction(wx.DragMove)

    def OnEnter(self, x, y, d):
        #self.canvas.OnEnter(x, y, d)
        return d

    def OnLeave(self):
        #self.frame.OnLeave()
        pass

    def OnDrop(self, x, y):
        return True

    def OnData(self, x, y, d):
        if not self.GetData():
            return wx.DragNone
        #self.frame.OnDrop(x, y, self.obj.GetText())
        data = self.obj.GetText()
        try:
            data = json.loads(data)
            sz = self.canvas.GetSize()
            y = sz[1]-y
            fig = self.canvas.figure
            if len(fig.get_axes()) == 0:
                fig.gca()
                fig.gca().grid(True)
                fig.gca().set_xlabel('t(s)')
            for i, ax in enumerate(fig.get_axes()):
                if ax.bbox.contains(x, y):
                    for l in data:
                        title = l[0]
                        line = pandas.DataFrame.from_dict(json.loads(l[1]))
                        for i in range(1, len(line.columns)):
                            ax.plot(line[line.columns[0]], line[line.columns[i]], label="/".join([title, line.columns[i]]))
                    ax.legend()
                    break
        except:
            pass

        return d

    def OnDragOver(self, x, y, d):
        #self.frame.OnDragOver(x, y, d)
        return d

class MatplotPanel(wx.Panel):
    clsFrame = None
    clsID_new_figure = wx.NOT_FOUND
    isInitialized = False
    kwargs = {}
    ID_PANE_CLOSE = wx.NewIdRef()
    ID_PANE_CLOSE_OTHERS = wx.NewIdRef()
    ID_PANE_CLOSE_ALL = wx.NewIdRef()

    def __init__(self, parent, title=None, num=-1, thisFig=None):
        # set the size to positive value, otherwise the toolbar will assert
        # wxpython/ext/wxWidgets/src/gtk/bitmap.cpp(539): assert ""width > 0 &&
        # height > 0"" failed in Create(): invalid bitmap size
        wx.Panel.__init__(self, parent, size=(100, 100))
        # initialize matplotlib stuff
        self.figure = thisFig
        if not self.figure:
            self.figure = Figure(None, None)
        self.canvas = FigureCanvas(self, -1, self.figure)
        # since matplotlib 3.2, it does not allow canvas size to become smaller
        # than MinSize in wx backend. So the canvas size (e.g., (640, 480))may
        # be large than the window size.
        self.canvas.SetMinSize((1, 1))
        #self.canvas.manager = self

        self.num = num
        if title is None:
            title = 'Figure %d' % self.num
        self.title = title
        self.isdestory = False
        szAll = wx.BoxSizer(wx.VERTICAL)

        self.figure.set_label(title)
        self.toolbar = Toolbar(self.canvas, self.figure)
        szAll.Add(self.toolbar, 0, wx.EXPAND)
        szAll.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)

        self.toolbar.update()
        # set the toolbar tool size again, otherwise the separator is not
        # aligned correctly on macOS.
        self.toolbar.SetToolBitmapSize((16, 16))
        self.SetSizer(szAll)


        self.figmgr = FigureManagerWx(self.canvas, num, self)
        self.Bind(wx.EVT_CLOSE, self._onClose)

        self.canvas.mpl_connect('button_press_event', self._onClick)
        dp.connect(self.simLoad, 'sim.loaded')
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_NEW)
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

        dt = DataDropTarget(self.canvas)
        self.canvas.SetDropTarget(dt)

    def GetToolBar(self):
        """Override wxFrame::GetToolBar as we don't have managed toolbar"""
        return self.toolbar

    def simLoad(self, num):
        for ax in self.figure.get_axes():
            for l in ax.lines:
                if hasattr(l, 'trace'):
                    sz = len(l.get_ydata())
                    for s in l.trace:
                        if (not s) or (not s.startswith(str(num) + '.')):
                            continue
                        #dispatcher.send(signal='sim.trace_buf', objects=s, size=sz)

    def _onClick(self, event):
        if event.dblclick:
            self.toolbar.home()

    def OnKeyDown(self, evt):
        self.toolbar.key_down(evt)

    def OnProcessCommand(self, evt):
        if self.toolbar.datacursor.ProcessCommand(evt.GetId()):
            self.canvas.draw()

    def _show_context_menu(self):
        menus = self.toolbar.GetMenu()
        if len(menus) == 0:
            return
        menu = build_menu_from_list(menus)
        if self.canvas.HasCapture():
            self.canvas.ReleaseMouse()
        mid = PopupMenu(self, menu)
        if mid > 0:
            self.toolbar.ProcessCommand(mid)
        menu.Destroy()

    def OnContextMenu(self, event):
        # Show menu after the current and pending event handlers have been
        # completed, otherwise it causes the following error in some system
        # (e.g., xubuntu, matplotlib 3.2.2, wx 4.1.0), and the menu doesn't show.
        # GLib-GObject-CRITICAL **: g_object_set_data: assertion 'G_IS_OBJECT
        # (object)' failed
        # remove the wx.CallAfter, as the problem doesn't show on xubuntu
        # 22.04/matplotlib 3.7.1/wx 4.2.0, and on xubuntu 22.04, wx.CallAfter
        # will cause the menu to disappear as soon as the right button is up
        self._show_context_menu()

    def close_event(self):
        event = CloseEvent('close_event',  self.canvas, guiEvent=None)
        self.canvas.callbacks.process('close_event', event)

    def _onClose(self, evt):
        self.close_event()
        self.canvas.stop_event_loop()
        Gcf.destroy(self.num)

    def destroy(self, *args):
        if self.isdestory is False:
            dp.send('frame.delete_panel', panel=self)
            wx.WakeUpIdle()

    def Destroy(self, *args, **kwargs):
        self.isdestory = True
        self.close_event()
        self.canvas.stop_event_loop()
        Gcf.destroy(self.num)
        return super().Destroy(*args, **kwargs)

    def GetTitle(self):
        """return the figure title"""
        return self.title

    def SetTitle(self, title):
        """set the figure title"""
        if title == self.title:
            return
        self.title = title
        dp.send('frame.update_panel_title', pane=self, title=self.title)

    def show(self):
        """show figure"""
        if self.IsShown() is False:
            self.canvas.draw()
            dp.send('frame.show_panel', panel=self)

    def update_buffer(self, bufs):
        """update the data used in plot_trace"""
        for ax in self.figure.get_axes():
            for l in ax.lines:
                if hasattr(l, 'trace'):
                    x = l.trace[0]
                    y = l.trace[1]
                    if x is None:
                        if y in bufs:
                            l.set_data(np.arange(len(bufs[y])), bufs[y])
                    elif x in bufs or y in bufs:
                        xd = l.get_xdata()
                        yd = l.get_ydata()
                        if y in bufs:
                            yd = bufs[y]
                        if x in bufs:
                            xd = bufs[x]
                        if len(xd) != len(yd):
                            sz = min(len(xd), len(yd))
                            xd = xd[0:sz]
                            yd = yd[0:sz]
                        l.set_data(xd, yd)
                    if hasattr(l, 'autorelim') and l.autorelim:
                        #Need both of these in order to rescale
                        ax.relim()
                        ax.autoscale_view()
        self.canvas.draw()

    def plot_trace(self, x, y, autorelim, *args, **kwargs):
        """plot and trace"""
        if y is None:
            return
        if x is None:
            l, = self.figure.gca().plot(list(y.values())[0], *args, **kwargs)
            l.trace = [None, list(y.keys())[0]]
        else:
            xd = list(x.values())[0]
            yd = list(y.values())[0]
            if len(xd) != len(yd):
                sz = min(len(xd), len(yd))
                if sz > 0:
                    xd = xd[0:sz]
                    yd = yd[0:sz]
                else:
                    xd = 0
                    yd = 0
            l, = self.figure.gca().plot(xd, yd, *args, **kwargs)
            l.trace = [list(x.keys())[0], list(y.keys())[0]]
        l.autorelim = autorelim
        self.canvas.draw()

    def set_window_title(self, label):
        pass

    @classmethod
    def setactive(cls, pane):
        """set the active figure"""
        if pane and isinstance(pane, MatplotPanel):
            Gcf.set_active(pane)

    @classmethod
    def addFigure(cls, title=None, num=None, thisFig=None):
        direction = cls.kwargs.get('direction', 'top')
        fig = cls(cls.clsFrame, title=title, num=num, thisFig=thisFig)
        # set the minsize to be large enough to avoid some following assert; it
        # will not eliminate all as if a page is added to a notebook, the
        # minsize of notebook is not the max of all its children pages (check
        # frameplus.py).
        # wxpython/ext/wxWidgets/src/gtk/bitmap.cpp(539): assert ""width > 0 &&
        # height > 0"" failed in Create(): invalid bitmap size
        dp.send('frame.add_panel',
                panel=fig,
                direction=direction,
                title=fig.GetTitle(),
                target=Gcf.get_active(),
                minsize=(75, 75),
                pane_menu={'rxsignal': 'bsm.graph.pane_menu',
                           'menu': [
                               {'id':cls.ID_PANE_CLOSE, 'label':'Close\tCtrl+W'},
                               {'id':cls.ID_PANE_CLOSE_OTHERS, 'label':'Close Others'},
                               {'id':cls.ID_PANE_CLOSE_ALL, 'label':'Close All'},
                               ]})
        return fig

    @classmethod
    def Initialize(cls, frame, **kwargs):
        if cls.isInitialized:
            return
        cls.isInitialized = True
        cls.clsFrame = frame
        cls.kwargs = kwargs
        resp = dp.send('frame.add_menu',
                       path='File:New:Figure\tCtrl+P',
                       rxsignal='bsm.figure')
        if resp:
            cls.clsID_new_figure = resp[0][1]

        if cls.clsID_new_figure is not wx.NOT_FOUND:
            dp.connect(cls.ProcessCommand, 'bsm.figure')
        dp.connect(cls.Uninitialize, 'frame.exiting')
        dp.connect(cls.Initialized, 'frame.initialized')
        dp.connect(cls.setactive, 'frame.activate_panel')
        dp.connect(cls.OnBufferChanged, 'sim.buffer_changed')
        dp.connect(cls.PaneMenu, 'bsm.graph.pane_menu')

    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, MatplotPanel):
            return
        if command == cls.ID_PANE_CLOSE:
            dp.send(signal='frame.delete_panel', panel=pane)
        elif command == cls.ID_PANE_CLOSE_OTHERS:
            mgrs =  Gcf.get_all_fig_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  Gcf.get_all_fig_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def Initialized(cls):
        dp.send('shell.run',
                command='from matplotlib.pyplot import *',
                prompt=False,
                verbose=False,
                history=False)

    @classmethod
    def OnBufferChanged(cls, bufs):
        """the buffer has be changes, update the plot_trace"""
        for p in Gcf.get_all_fig_managers():
            p.update_buffer(bufs)

    @classmethod
    def Uninitialize(cls):
        """destroy the module"""
        Gcf.destroy_all()

    @classmethod
    def ProcessCommand(cls, command):
        """process the menu command"""
        if command == cls.clsID_new_figure:
            plt.figure()


def bsm_initialize(frame, **kwargs):
    """module initialization"""
    MatplotPanel.Initialize(frame, **kwargs)
