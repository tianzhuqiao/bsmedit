import math
import wx
import wx.aui
import wx.py.dispatcher as dp
import numpy
import matplotlib
matplotlib.use('module://bsmedit.bsm.bsmbackend')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wx import NavigationToolbar2Wx as NavigationToolbar
from matplotlib.backends.backend_wx import FigureManagerWx
from matplotlib._pylab_helpers import Gcf
import matplotlib.pyplot as plt
from matplotlib import rcParams
from .lineeditor import LineEditor
from .utility import PopupMenu
from .bsmxpm import home_xpm, back_xpm, forward_xpm, pan_xpm, zoom_xpm, \
                    cursor_xpm, save_xpm, copy_xpm, line_edit_xpm, page_add_xpm
from .. import to_byte
rcParams.update({'figure.autolayout': True})
rcParams.update({'toolbar': 'None'})
matplotlib.interactive(True)


class DataCursor(object):
    xoffset, yoffset = -20, 20
    text_template = 'x: %0.2f\ny: %0.2f'

    ID_DELETE_DATATIP = wx.NewId()
    ID_CLEAR_DATATIP = wx.NewId()
    def __init__(self):
        self.annotations = []
        self.lines = []
        self.enable = False
        self.active = None
        self.mx, self.my = None, None
        self.pickEvent = False

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
        x, y = line.get_xdata(), line.get_ydata()
        xc, yc = event.mouseevent.xdata, event.mouseevent.ydata
        idx = (numpy.square(x - xc) + numpy.square(y - yc)).argmin()
        xn, yn = x[idx], y[idx]
        if xn is not None:
            self.active.xy = xn, yn
            self.active.set_text(self.text_template % (xn, yn))
            self.active.set_visible(True)
            event.canvas.draw()
        self.pickEvent = True

    def keyboard_move(self, left, step=1):
        if not self.active:
            return
        idx = self.annotations.index(self.active)
        line = self.lines[idx]
        x, y = line.get_xdata(), line.get_ydata()
        xc, yc = self.active.xy
        idx = (numpy.square(x - xc)).argmin()
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
            self.active.set_text(self.text_template % (xn, yn))
            self.active.set_visible(True)

    def set_enable(self, enable):
        self.enable = enable
        if self.active:
            if enable:
                self.active.get_bbox_patch().set_facecolor('yellow')
            else:
                self.active.get_bbox_patch().set_facecolor('white')

    def mouse_move(self, event):
        """move the annotation position"""
        # return if no active annotation or the mouse is not pressed
        if self.mx is None or self.my is None or self.active is None:
            return False
        # re-position the active annotation based on the mouse movement
        x, y = event.x, event.y
        dx = x - self.mx
        dy = y - self.my
        dis = math.sqrt(dx**2 + dy**2)
        if dis > 50:
            (px, py) = (-20, 20)
            if dx > 80:
                px = 60
            elif dx > 40:
                px = 20
            if dy < -80:
                py = -60
            elif dy < -40:
                py = -20
            self.active.xyann = (px, py)
            return True
        return False

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
        if ant and (ant not in self.annotations):
            return False
        if self.active == ant:
            return True
        if self.active:
            self.active.get_bbox_patch().set_facecolor('white')
        self.active = ant
        if self.active:
            self.active.get_bbox_patch().set_facecolor('yellow')
        return True

    def get_annotations(self):
        """return all the annotations"""
        return self.annotations

    def create_annotation(self, line):
        """create the annotation and set it active"""
        ant = line.axes.annotate(self.text_template,
                                 xy=(0, 0),
                                 xytext=(self.xoffset, self.yoffset),
                                 textcoords='offset points',
                                 ha='right',
                                 va='bottom',
                                 bbox=dict(boxstyle='round,pad=0.5',
                                           fc='yellow',
                                           alpha=0.5),
                                 arrowprops=dict(arrowstyle='->',
                                                 connectionstyle='arc3,rad=0'))
        ant.set_visible(False)
        self.annotations.append(ant)
        self.lines.append(line)
        self.set_active(ant)

    def GetMenu(self):
        cmd = [[self.ID_DELETE_DATATIP, 'Delete current datatip',
                self.active is not None and self.active.get_visible()],
               [self.ID_CLEAR_DATATIP, 'Delete all datatip', len(self.annotations) > 0]
              ]
        return cmd

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
        return False

    def activated(self):
        pass
    def deactivated(self):
        pass

class Toolbar(NavigationToolbar):
    def __init__(self, canvas, figure):
        if matplotlib.__version__ < '3.3.0':
            self._init_toolbar = self.init_toolbar
        else:
            self._init_toolbar = self.init_toolbar_empty
        NavigationToolbar.__init__(self, canvas)

        if matplotlib.__version__ >= '3.3.0':
            self.init_toolbar()
        self.SetWindowStyle(wx.TB_HORIZONTAL | wx.TB_FLAT)
        self.figure = figure
        self.datacursor = DataCursor()
        self.lineeditor = LineEditor(self.figure)

        self.actions = {'datatip': self.datacursor,
                        'edit': self.lineeditor}

        self.canvas.mpl_connect('pick_event', self.OnPick)
        self.canvas.mpl_connect('motion_notify_event', self.OnMove)
        self.canvas.mpl_connect('button_press_event', self.OnPressed)
        self.canvas.mpl_connect('button_release_event', self.OnReleased)
        self.canvas.mpl_connect('scroll_event', self.OnZoomFun)
        self.canvas.mpl_connect('key_press_event', self.OnKeyPressed)
        # clear the view history
        wx.CallAfter(self._nav_stack.clear)

    def GetMenu(self):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'GetMenu'):
            return []
        return action.GetMenu()

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

    def OnPressed(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'mouse_pressed'):
            return
        # some lines may be added
        for l in self.figure.gca().lines:
            l.set_picker(5)
        if action.mouse_pressed(event):
            self.canvas.draw()

    def OnReleased(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'mouse_released'):
            return
        action.mouse_released(event)

    def OnMove(self, event):
        action = self.actions.get(self.mode, None)
        if action is None or not hasattr(action, 'mouse_move'):
            return
        if action.mouse_move(event):
            self.canvas.draw()

    def OnZoomFun(self, event):
        # get the current x and y limits
        if not self.GetToolState(self.wx_ids['Zoom']):
            return
        if self._nav_stack.empty():
            self.push_current()
        base_scale = 2.0
        ax = self.figure.gca()
        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        xdata = event.xdata  # get event x location
        ydata = event.ydata  # get event y location
        if xdata is None:
            return
        if ydata is None:
            return

        if event.button == 'down':
            # deal with zoom in
            scale_factor = 1.0 / base_scale
        elif event.button == 'up':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1.0

        new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        xzoom = yzoom = True
        if wx.GetKeyState(wx.WXK_CONTROL_X):
            yzoom = False
        elif wx.GetKeyState(wx.WXK_CONTROL_Y):
            xzoom = False
        if (xzoom) and new_width * (1 - relx) > 0:
            ax.set_xlim(
                [xdata - new_width * (1 - relx), xdata + new_width * (relx)])
        if (yzoom) and new_height * (1 - rely) > 0:
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
            #(None, None, None, None),
            #('Print', 'Print the figure', print_xpm, 'print_figure'),
        )

        self._parent = self.canvas.GetParent()
        self.ClearTools()
        self.wx_ids = {}
        self.SetToolBitmapSize((16, 16))
        for (text, tooltip_text, image_file, callback) in toolitems:
            if text is None:
                self.AddSeparator()
                continue
            self.wx_ids[text] = wx.NewId()
            if text in ['Pan', 'Zoom', 'Datatip', 'Edit']:
                self.AddCheckTool(self.wx_ids[text],
                                  text,
                                  wx.Bitmap(to_byte(image_file)),
                                  shortHelp=text,
                                  longHelp=tooltip_text)
            else:
                self.AddTool(self.wx_ids[text], text,
                             wx.Bitmap(to_byte(image_file)),
                             kind=wx.ITEM_NORMAL, shortHelp=tooltip_text)
            self.Bind(wx.EVT_TOOL,
                      getattr(self, callback),
                      id=self.wx_ids[text])

        self.Realize()

    def OnNewFigure(self, evt):
        dp.send('shell.run',
                command='figure();',
                prompt=True,
                verbose=False,
                debug=False)

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
        super(Toolbar, self).zoom(*args)

    def pan(self, *args):
        """activated the pan mode"""
        self.set_mode('pan')
        super(Toolbar, self).pan(*args)

    def OnBack(self, *args):
        super().back(*args)

    def back(self, *args):
        if self.mode == 'datatip':
            return
        super().back(*args)

    def OnForward(self, *args):
        super().forward(*args)

    def forward(self, *args):
        if self.mode == 'datatip':
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

        for l in self.figure.gca().lines:
            l.set_picker(5)
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

        for l in self.figure.gca().lines:
            l.set_picker(5)
        if self.mode == "edit":
            self.set_mode("")
        else:
            self.set_mode("edit")
        self.set_message(self.mode)

    def set_message(self, s):
        """show the status message"""
        dp.send(signal='frame.show_status_text', text=s, index=1, width=160)


class MatplotPanel(wx.Panel):
    clsFrame = None
    clsID_new_figure = wx.NOT_FOUND
    isInitialized = False
    kwargs = {}

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

    def GetToolBar(self):
        """Override wxFrame::GetToolBar as we don't have managed toolbar"""
        return self.toolbar

    def simLoad(self, num):
        for l in self.figure.gca().lines:
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
        if self.toolbar.mode != 'datatip':
            return
        keycode = evt.GetKeyCode()
        step = 1
        if evt.ShiftDown():
            step = 10
        if keycode == wx.WXK_LEFT:
            self.toolbar.datacursor.keyboard_move(True, step=step)
        elif keycode == wx.WXK_RIGHT:
            self.toolbar.datacursor.keyboard_move(False, step=step)
        else:
            evt.Skip()

    def OnProcessCommand(self, evt):
        if self.toolbar.datacursor.ProcessCommand(evt.GetId()):
            self.canvas.draw()

    def _create_context_menu(self, menus):
        menu = wx.Menu()
        for m in menus:
            if len(m) == 0:
                item = menu.AppendSeparator()
            elif isinstance(m[0], str):
                child = self._create_context_menu(m[1])
                menu.AppendSubMenu(child, m[0])
            elif len(m) == 3:
                # normal item
                item = menu.Append(m[0], m[1])
                item.Enable(m[2])
            elif len(m) == 4:
                # checkable item
                item = menu.AppendCheckItem(m[0], m[1])
                item.Check(m[3])
                item.Enable(m[2])
        return menu

    def _show_context_menu(self):
        menus = self.toolbar.GetMenu()
        if len(menus) == 0:
            return
        menu = self._create_context_menu(menus)

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
        wx.CallAfter(self._show_context_menu)

    def _onClose(self, evt):
        self.canvas.close_event()
        self.canvas.stop_event_loop()
        Gcf.destroy(self.num)

    def destroy(self, *args):
        if self.isdestory is False:
            dp.send('frame.delete_panel', panel=self)
            wx.WakeUpIdle()

    def Destroy(self, *args, **kwargs):
        self.isdestory = True
        self.canvas.close_event()
        self.canvas.stop_event_loop()
        Gcf.destroy(self.num)
        return super(MatplotPanel, self).Destroy(*args, **kwargs)

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
        for l in self.figure.gca().lines:
            if hasattr(l, 'trace'):
                x = l.trace[0]
                y = l.trace[1]
                if x is None:
                    if y in bufs:
                        l.set_data(numpy.arange(len(bufs[y])), bufs[y])
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
                    self.figure.gca().relim()
                    self.figure.gca().autoscale_view()
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
                minsize=(75, 75))
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
        dp.connect(cls.Uninitialize, 'frame.exit')
        dp.connect(cls.Initialized, 'frame.initialized')
        dp.connect(cls.setactive, 'frame.activate_panel')
        dp.connect(cls.OnBufferChanged, 'sim.buffer_changed')

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
