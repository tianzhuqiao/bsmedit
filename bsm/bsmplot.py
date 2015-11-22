import wx
import wx.aui
import wx.py
from bsmplotxpm import *
try:
    import numpy
    import matplotlib
    matplotlib.use('module://bsm.backend_bsm')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
    from matplotlib.backends.backend_wxagg import NavigationToolbar2Wx as NavigationToolbar
    from matplotlib._pylab_helpers import Gcf
    import matplotlib.pyplot as plt
    matplotlib.interactive(True)
    class DataCursor(object):
        text_template = 'x: %0.2f\ny: %0.2f'
        x, y = 0.0, 0.0
        xoffset, yoffset = -20, 20
        text_template = 'x: %0.2f\ny: %0.2f'

        def __init__(self, ax):
            self.ax = ax
            self.annotation = ax.annotate(self.text_template, 
                    xy=(self.x, self.y), xytext=(self.xoffset, self.yoffset), 
                    textcoords='offset points', ha='right', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                    arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                    )
            self.annotation.set_visible(False)
            self.enable = False;
        def __call__(self, event):
            if not self.enable:
                return
            self.event = event
            #xdata, ydata = event.artist.get_data()
            #self.x, self.y = xdata[event.ind], ydata[event.ind]
            self.x, self.y = event.mouseevent.xdata, event.mouseevent.ydata
            #self.x, self.y = event.artist.get_xdata(), event.artist.get_ydata()
            if self.x is not None:
                self.annotation.xy = self.x, self.y
                self.annotation.set_text(self.text_template % (self.x, self.y))
                self.annotation.set_visible(True)
                event.canvas.draw()
        def set_enable(self, enable):
            self.enable = enable;
    #
    # we override the matplotlib toolbar class to remove the subplots function,
    #  which we do not use
    #
    
    class Toolbar(NavigationToolbar):
    
        def __init__(self, canvas, figure):
            NavigationToolbar.__init__(self, canvas)
            self.SetWindowStyle(wx.TB_HORIZONTAL | wx.TB_FLAT)
            self.figure = figure
            self.datacursor =DataCursor(self.figure.gca());
            self.canvas.mpl_connect('pick_event', self.datacursor)
        def _init_toolbar(self):
            toolitems = (
                ('Home', 'Reset original view', home_xpm, 'home'),
                ('Back', 'Back to  previous view', stock_left_xpm, 'back'),
                ('Forward', 'Forward to next view', stock_right_xpm,
                 'forward'),
                (None, None, None, None),
                ('Pan', 'Pan axes with left mouse, zoom with right',
                 moveto2_xpm, 'pan'),
                ('Zoom', 'Zoom to rectangle', zoom_in_xpm, 'zoom'),
                ('Datatip', 'Show the data tip', cursor_xpm, 'datatip'),
                (None, None, None, None),
                ('Save', 'Save the figure', saveas_xpm, 'save_figure'),
                ('Copy', 'Copy to clipboard', page_copy_xpm, 'copy_figure'
                 ),
                (None, None, None, None),
                ('Print', 'Print the figure', printer_xpm, 'print_figure'),
                )
    
            self._parent = self.canvas.GetParent()
    
            self.wx_ids = {}
            for (text, tooltip_text, image_file, callback) in toolitems:
                if text is None:
                    self.AddSeparator()
                    continue
                self.wx_ids[text] = wx.NewId()
                if text in ['Pan', 'Zoom', 'Datatip']:
                    self.AddCheckTool(self.wx_ids[text],
                                      wx.BitmapFromXPMData(image_file),
                                      shortHelp=text, longHelp=tooltip_text)
                else:
                    self.AddSimpleTool(self.wx_ids[text],
                                       wx.BitmapFromXPMData(image_file),
                                       text, tooltip_text)
                self.Bind(wx.EVT_TOOL, getattr(self, callback),
                          id=self.wx_ids[text])
    
            self.Realize()
    
        def copy_figure(self, evt):
            self.canvas.Copy_to_Clipboard(event=evt)  # bmp image
    
        def print_figure(self, evt):
            self.canvas.Printer_Print(event=evt)  # bmp image
        def datatip(self,evt):
            self.datacursor.set_enable(evt.GetInt())
   
    class MatplotPanel(wx.Panel):
    
        clsFrame = None
        clsID_new_figure = wx.NOT_FOUND
    
        def __init__(self, parent, title=None, num=-1, thisFig = None):
            wx.Panel.__init__(self, parent)
            
            # initialize matplotlib stuff
            self.figure = thisFig
            if not self.figure:
                self.figure = Figure(None,None, **kwargs)
            self.canvas = FigureCanvas(self, -1, self.figure)

            self.num = num
            if title == None: title = 'Figure %d'%self.num
            self.parent = parent
            self.title = title
            self.isdestory = False
            self.sizer = wx.BoxSizer(wx.VERTICAL)
            self.SetSizer(self.sizer)
    
            self.figure.set_label(title)
            self.subplot = self.figure.add_subplot(111)
    
            self.toolbar = Toolbar(self.canvas,self.figure)
    
            self.sizer.Add(self.toolbar, 0, wx.EXPAND)
            self.sizer.Add(self.canvas, 1, wx.LEFT | wx.TOP | wx.GROW)
            self.Bind(wx.EVT_CLOSE, self._onClose)
            connection_id = self.canvas.mpl_connect('button_press_event',
                    self._onClick)
        def _onClick(self, event):
            if event.dblclick:
                self.toolbar.home()
            # event.Skip()
    
        def _onClose(self, evt):
            self.canvas.close_event()
            self.canvas.stop_event_loop()
            Gcf.destroy(self.num)
    
        def destroy(self, *args):
            if self.isdestory == False:
                wx.py.dispatcher.send(signal='frame.closepanel', panel=self)
                wx.WakeUpIdle()
    
        def Destroy(self):
            self.isdestory = True
            self.canvas.close_event()
            self.canvas.stop_event_loop()
            Gcf.destroy(self.num)
            return super(MatplotPanel, self).Destroy()
    
        @classmethod
        def setactive(cls, pane, force=False, notify=False):
            if force or pane and isinstance(pane, MatplotPanel):
                Gcf.set_active(pane)
    
        def GetTitle(self):
            return self.title
    
        def set_window_title(self, title):
            if title == self.title: return
            self.title = title
            wx.py.dispatcher.send(signal='frame.updatepanetitle',
                                  pane=self, title=self.title)
    
        def show(self):
            if self.IsShown() == False:
                self.canvas.draw()
                wx.py.dispatcher.send(signal='frame.showpanel', panel=self)

        def update_buffer(self, bufs):
            for l in self.figure.gca().lines:
                if hasattr(l, 'trace'):
                    x = l.trace[0]
                    y = l.trace[1]
                    if x is None:
                        if y in bufs.keys():
                            l.set_data(numpy.arange(len(bufs[y])), bufs[y])
                    elif x in bufs.keys() or y in bufs.keys():
                        xd = l.get_xdata()
                        yd = l.get_ydata()
                        if y in bufs.keys():
                            yd = bufs[y]
                        if x in bufs.keys():
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
            if y is None:
                return
            if x is None:
                l, = self.figure.gca().plot(y.values()[0], *args, **kwargs)
                l.trace = [None, y.keys()[0]]
            else:
                xd = x.values()[0]
                yd = y.values()[0]
                if len(xd) != len(yd):
                    sz = min(len(xd), len(yd))
                    if sz>0:
                        xd = xd[0:sz]
                        yd = yd[0:sz]
                    else:
                        xd = 0
                        yd = 0
                l, = self.figure.gca().plot(xd, yd, *args, **kwargs)
                l.trace = [x.keys()[0], y.keys()[0]]
            l.autorelim = autorelim
            self.canvas.draw()
            
        @classmethod
        def addFigure(cls, title=None, num=None, thisFig = None):
            panelFigure = cls(cls.clsFrame, title=title, num=num, thisFig = thisFig)
            wx.py.dispatcher.send(signal='frame.addpanel',
                                  panel=panelFigure,
                                  title=panelFigure.GetTitle(),
                                  target=Gcf.get_active())
            return panelFigure
    
        @classmethod
        def Initialize(cls, frame):
            cls.clsFrame = frame
            response = wx.py.dispatcher.send(signal='frame.addmenu',
                    path='File:New:Figure', rxsignal='bsm.figure')
            if response:
                cls.clsID_new_figure = response[0][1]
            if cls.clsID_new_figure is not wx.NOT_FOUND:
                wx.py.dispatcher.connect(cls.ProcessCommand,
                        signal='bsm.figure')
            wx.py.dispatcher.connect(receiver=cls.Uninitialize,
                                     signal='frame.exit')
            wx.py.dispatcher.connect(receiver=cls.setactive,
                                     signal='frame.activatepane')
            wx.py.dispatcher.connect(receiver=cls.OnBufferChanged,
                                     signal='sim.buffer_changed')
        @classmethod
        def OnBufferChanged(cls, bufs):
            for p in Gcf.get_all_fig_managers():
                p.update_buffer(bufs)
        @classmethod
        def Uninitialize(cls):
            Gcf.destroy_all()
    
        @classmethod
        def ProcessCommand(cls, command):
            if command == cls.clsID_new_figure:
                plt.figure()
    
    
    def bsm_Initialize(frame):
        MatplotPanel.Initialize(frame)
        wx.py.dispatcher.send(signal='frame.run',
                              command='from matplotlib.pyplot import *',
                              prompt=False, verbose=False)
except ImportError,e:
    def bsm_Initialize(frame):
        pass

