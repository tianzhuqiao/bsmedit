import traceback
import sys
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
from matplotlib._pylab_helpers import Gcf
import matplotlib.pyplot as plt
from matplotlib import rcParams
from .bsmxpm import home_xpm, back_xpm, forward_xpm, pan_xpm, zoom_xpm, \
                    cursor_xpm, save_xpm, copy_xpm
from .. import c2p
rcParams.update({'figure.autolayout': True})
matplotlib.interactive(True)

class DataCursor(object):
    xoffset, yoffset = -20, 20
    text_template = 'x: %0.2f\ny: %0.2f'

    def __init__(self):
        self.annotations = []
        self.enable = False
        self.active = None
        self.mx, self.my = None, None
        self.pickEvent = False

    def __call__(self, event):
        if not self.enable:
            return
        if not event.mouseevent.xdata or not event.mouseevent.ydata:
            return
        if not event.artist:
            return
        line = event.artist
        if self.active and self.active.get_visible():
            # Check whether the axes of active annotation is same as line,
            # which may happen in a figure with subplots. If not, create one
            # with the axes of line
            if self.active.axes != line.axes:
                self.active = None
        if self.active is None:
            self.create_annotation(line.axes)
        # find the closest point on the line
        x, y = line.get_xdata(), line.get_ydata()
        xc, yc = event.mouseevent.xdata, event.mouseevent.ydata
        idx = (numpy.square(x-xc) + numpy.square(y-yc)).argmin()
        xn, yn = x[idx], y[idx]
        if xn is not None:
            self.active.xy = xn, yn
            self.active.set_text(self.text_template % (xn, yn))
            self.active.set_visible(True)
            event.canvas.draw()
        self.pickEvent = True
    def set_enable(self, enable):
        self.enable = enable
        if self.active:
            if enable:
                self.active.get_bbox_patch().set_facecolor('yellow')
            else:
                self.active.get_bbox_patch().set_facecolor('white')

    def mouse_move(self, x, y):
        """move the annotation position"""
        # return if no active annotation or the mouse is not pressed
        if self.mx is None or self.my is None or self.active is None:
            return False
        # re-position the active annotation based on the mouse movement
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

    def mouse_pressed(self, x, y):
        """
        select the active annotation which is closest to the mouse position
        """
        # ignore the event triggered immediately after pick_event
        if self.pickEvent:
            self.pickEvent = False
            return
        # just created the new annotation, do not move to others
        if self.active and (not self.active.get_visible()):
            return False
        # search the closest annotation
        self.mx, self.my = x, y
        dm = -1
        active = None
        for ant in self.annotations:
            box = ant.get_bbox_patch().get_extents()
            if box.contains(x, y):
                active = ant
                break
        self.set_active(active)
        # return True for the parent to redraw
        return True

    def mouse_released(self, x, y):
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

    def create_annotation(self, ax):
        """create the annotation and set it active"""
        ant = ax.annotate(self.text_template, xy=(0, 0),
                xytext=(self.xoffset, self.yoffset),
                textcoords='offset points', ha='right', va='bottom',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))
        ant.set_visible(False)
        self.annotations.append(ant)
        self.set_active(ant)

    def ProcessCommand(self, cmd):
        """process the context menu command"""
        if cmd == wx.ID_DELETE:
            if not self.active:
                return False
            idx = self.annotations.index(self.active)
            self.active.remove()
            del self.annotations[idx]
            self.active = None
            return True
        elif cmd == wx.ID_CLEAR:
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
            self.active = None
            return True
        return False

class Toolbar(NavigationToolbar):
    def __init__(self, canvas, figure):
        NavigationToolbar.__init__(self, canvas)
        self.SetWindowStyle(wx.TB_HORIZONTAL | wx.TB_FLAT)
        self.figure = figure
        self.datacursor = DataCursor()
        self.canvas.mpl_connect('pick_event', self.datacursor)
        self.canvas.mpl_connect('motion_notify_event', self.OnMove)
        self.canvas.mpl_connect('button_press_event', self.OnPressed)
        self.canvas.mpl_connect('button_release_event', self.OnReleased)
        self.canvas.mpl_connect('scroll_event', self.OnZoomFun)
        # clear the view history
        wx.CallAfter(self._nav_stack.clear)
    def OnPressed(self, event):
        if self.mode != 'datatip':
            return
        # some lines may be added
        for l in self.figure.gca().lines:
            l.set_picker(5)
        if self.datacursor.mouse_pressed(event.x, event.y):
            self.canvas.draw()

    def OnReleased(self, event):
        if self.mode != 'datatip':
            return
        self.datacursor.mouse_released(event.x, event.y)

    def OnMove(self, event):
        if self.mode != 'datatip':
            return
        if self.datacursor.mouse_move(event.x, event.y):
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

        xdata = event.xdata # get event x location
        ydata = event.ydata # get event y location
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

        relx = (cur_xlim[1] - xdata)/(cur_xlim[1] - cur_xlim[0])
        rely = (cur_ylim[1] - ydata)/(cur_ylim[1] - cur_ylim[0])
        xzoom = yzoom = True
        if wx.GetKeyState(wx.WXK_CONTROL_X):
            yzoom = False
        elif wx.GetKeyState(wx.WXK_CONTROL_Y):
            xzoom = False
        if(xzoom) and new_width * (1-relx) > 0:
            ax.set_xlim([xdata - new_width * (1-relx), xdata + new_width * (relx)])
        if(yzoom) and  new_height * (1-rely) > 0:
            ax.set_ylim([ydata - new_height * (1-rely), ydata + new_height * (rely)])
        self.canvas.draw()

    def _init_toolbar(self):
        toolitems = (
            ('Home', 'Reset original view', home_xpm, 'home'),
            ('Back', 'Back to  previous view', back_xpm, 'back'),
            ('Forward', 'Forward to next view', forward_xpm, 'forward'),
            (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', pan_xpm, 'pan'),
            ('Zoom', 'Zoom to rectangle', zoom_xpm, 'zoom'),
            ('Datatip', 'Show the data tip', cursor_xpm, 'datatip'),
            (None, None, None, None),
            ('Save', 'Save the figure', save_xpm, 'save_figure'),
            ('Copy', 'Copy to clipboard', copy_xpm, 'copy_figure'),
            #(None, None, None, None),
            #('Print', 'Print the figure', print_xpm, 'print_figure'),
            )

        self._parent = self.canvas.GetParent()

        self.wx_ids = {}
        for (text, tooltip_text, image_file, callback) in toolitems:
            if text is None:
                self.AddSeparator()
                continue
            self.wx_ids[text] = wx.NewId()
            if text in ['Pan', 'Zoom', 'Datatip']:
                c2p.tbAddCheckTool(self, self.wx_ids[text], text,
                                   c2p.BitmapFromXPM(image_file),
                                   shortHelp=text, longHelp=tooltip_text)
            else:
                c2p.tbAddTool(self, self.wx_ids[text], text,
                              c2p.BitmapFromXPM(image_file), wx.NullBitmap,
                              wx.ITEM_NORMAL, tooltip_text)
            self.Bind(wx.EVT_TOOL, getattr(self, callback),
                      id=self.wx_ids[text])

        self.Realize()

    def copy_figure(self, evt):
        self.canvas.Copy_to_Clipboard(event=evt)

    def print_figure(self, evt):
        self.canvas.Printer_Print(event=evt)

    def zoom(self, *args):
        """activate the zoom mode"""
        self.ToggleTool(self.wx_ids['Datatip'], False)
        super(Toolbar, self).zoom(*args)

    def pan(self, *args):
        """activated the pan mode"""
        self.ToggleTool(self.wx_ids['Datatip'], False)
        super(Toolbar, self).pan(*args)

    def datatip(self, evt):
        """activate the datatip mode"""
        # disable the pan/zoom mode
        self.ToggleTool(self.wx_ids['Zoom'], False)
        self.ToggleTool(self.wx_ids['Pan'], False)
        self._active = None
        self._idPress = self.canvas.mpl_disconnect(self._idPress)
        self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
        self.canvas.widgetlock.release(self)
        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        for l in self.figure.gca().lines:
            l.set_picker(5)
        self.mode = "datatip"
        self.set_message(self.mode)
        self.datacursor.set_enable(evt.GetInt())

    def set_message(self, s):
        """show the status message"""
        dp.send(signal='frame.show_status_text', text=s, index=1, width=160)

class MatplotPanel(wx.Panel):
    clsFrame = None
    clsID_new_figure = wx.NOT_FOUND
    isInitialized = False
    kwargs = {}
    def __init__(self, parent, title=None, num=-1, thisFig=None):
        wx.Panel.__init__(self, parent)

        # initialize matplotlib stuff
        self.figure = thisFig
        if not self.figure:
            self.figure = Figure(None, None)
        self.canvas = FigureCanvas(self, -1, self.figure)

        self.num = num
        if title is None:
            title = 'Figure %d'%self.num
        self.title = title
        self.isdestory = False
        szAll = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(szAll)

        self.figure.set_label(title)
        self.toolbar = Toolbar(self.canvas, self.figure)

        szAll.Add(self.toolbar, 0, wx.EXPAND)
        szAll.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
        self.Bind(wx.EVT_CLOSE, self._onClose)

        self.canvas.mpl_connect('button_press_event', self._onClick)
        dp.connect(self.simLoad, 'sim.loaded')
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnProcessCommand, id=wx.ID_NEW)

    def Destroy(self):
        dp.disconnect(self.simLoad, 'sim.loaded')
        super(MatplotPanel, self).Destroy()

    def simLoad(self, num):
        for l in self.figure.gca().lines:
            if hasattr(l, 'trace'):
                sz = len(l.get_ydata())
                for s in l.trace:
                    if (not s)  or (not s.startswith(str(num)+'.')):
                        continue
                    #dispatcher.send(signal='sim.trace_buf', objects=s, size=sz)

    def _onClick(self, event):
        if event.dblclick:
            self.toolbar.home()

    def OnProcessCommand(self, evt):
        if self.toolbar.datacursor.ProcessCommand(evt.GetId()):
            self.canvas.draw()

    def OnContextMenu(self, event):
        if self.toolbar.mode == 'datatip':
            menu = wx.Menu()
            delMenu = menu.Append(wx.ID_DELETE, "Delete current datatip")
            note = self.toolbar.datacursor.active
            delMenu.Enable((note is not None) and note.get_visible())
            menu.Append(wx.ID_CLEAR, "Delete all datatips")
            self.PopupMenu(menu)
            menu.Destroy()

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

    @classmethod
    def setactive(cls, pane):
        """set the active figure"""
        if pane and isinstance(pane, MatplotPanel):
            Gcf.set_active(pane)

    @classmethod
    def addFigure(cls, title=None, num=None, thisFig=None):
        direction = cls.kwargs.get('direction', 'top')
        fig = cls(cls.clsFrame, title=title, num=num, thisFig=thisFig)
        dp.send('frame.add_panel', panel=fig, direction=direction,
                title=fig.GetTitle(), target=Gcf.get_active())
        return fig

    @classmethod
    def Initialize(cls, frame, **kwargs):
        if cls.isInitialized:
            return
        cls.isInitialized = True
        cls.clsFrame = frame
        cls.kwargs = kwargs
        resp = dp.send('frame.add_menu', path='File:New:Figure',
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
    def Initialized(self):
        dp.send('shell.run', command='from matplotlib.pyplot import *',
            prompt=False, verbose=False, history=False)

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

