import sys
import inspect
import six
import wx
import wx.py.dispatcher as dp
import wx.lib.mixins.listctrl as listmix
import wx.lib.agw.aui as aui
from .bsmxpm import run_xpm, step_over_xpm, step_into_xpm, step_out_xpm, stop_xpm
from .. import c2p

class StackListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin,
                    listmix.ListRowHighlighter):

    def __init__(self, *args, **kwargs):
        wx.ListCtrl.__init__(self, *args, **kwargs)

        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.ListRowHighlighter.__init__(self, mode=listmix.HIGHLIGHT_ODD)
        self.SetHighlightColor(wx.Colour(240, 240, 250))

class StackPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.listctrl = StackListCtrl(self, style=wx.LC_REPORT
                                      | wx.BORDER_NONE
                                      | wx.LC_EDIT_LABELS | wx.LC_VRULES
                                      | wx.LC_HRULES | wx.LC_SINGLE_SEL)
                                      # | wx.BORDER_SUNKEN
                                      # | wx.LC_SORT_ASCENDING
                                      # | wx.LC_NO_HEADER
        self.listctrl.InsertColumn(0, 'Name')
        self.listctrl.InsertColumn(1, 'Line')
        self.listctrl.InsertColumn(2, 'File')
        sizer.Add(self.listctrl, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated,
                  self.listctrl)
        dp.connect(self.OnDebugEnded, 'debugger.ended')
        dp.connect(self.OnDebugUpdateScopes, 'debugger.update_scopes')
        dp.connect(self.OnDebugUpdateScopes, 'debugger.paused')

    def Destroy(self):
        dp.disconnect(self.OnDebugEnded, 'debugger.ended')
        dp.disconnect(self.OnDebugUpdateScopes, 'debugger.update_scopes')
        dp.disconnect(self.OnDebugUpdateScopes, 'debugger.paused')
        super(StackPanel, self).Destroy()

    def OnDebugEnded(self):
        """debugger is ended"""
        # clear the scopes
        self.listctrl.DeleteAllItems()

    def OnDebugUpdateScopes(self):
        """debugger changes the scope"""
        self.listctrl.DeleteAllItems()
        resp = dp.send(signal='debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        frames = status['frames']
        level = status['active_scope']
        if frames is not None:
            for frame in frames:
                name = frame.f_code.co_name
                filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
                lineno = frame.f_lineno
                if c2p.bsm_is_phoenix:
                    index = self.listctrl.InsertItem(six.MAXSIZE, name)
                    self.listctrl.SetItem(index, 2, filename)
                    self.listctrl.SetItem(index, 1, '%d' % lineno)
                else:
                    index = self.listctrl.InsertStringItem(six.MAXSIZE, name)
                    self.listctrl.SetStringItem(index, 2, filename)
                    self.listctrl.SetStringItem(index, 1, '%d' % lineno)
        if level >= 0 and level < self.listctrl.GetItemCount():
            self.listctrl.SetItemTextColour(level, 'blue')
        self.listctrl.RefreshRows()

    def OnItemActivated(self, event):
        currentItem = event.m_itemIndex
        filename = self.listctrl.GetItem(currentItem, 2).GetText()
        lineno = self.listctrl.GetItem(currentItem, 1).GetText()
        # open the script first
        dp.send(signal='frame.file_drop', filename=filename,
                lineno=int(lineno))
        # ask the debugger to trigger the update scope event to set mark
        dp.send(signal='debugger.set_scope', level=currentItem)

class DebugTool(object):
    isInitialized = False
    frame = None
    showStackPanel = True
    @classmethod
    def Initialize(cls, frame, **kwargs):
        if cls.isInitialized:
            return
        cls.isInitialized = True
        cls.frame = frame
        # stack panel
        cls.panelStack = StackPanel(frame)
        dp.send('frame.add_panel', panel=cls.panelStack, title="Call Stack",
                active=False, showhidemenu='View:Panels:Call Stack')

        # debugger toolbar
        dp.send('frame.add_menu', path='Tools:Debug', rxsignal='',
                kind='Popup')
        cls.tbDebug = aui.AuiToolBar(frame, style=wx.TB_FLAT | wx.TB_HORIZONTAL)
        items = (('Run\tF5', 'resume', run_xpm, 'paused'),
                 ('Stop\tShift-F5', 'stop', stop_xpm, 'paused'),
                 ('Step\tF10', 'step', step_over_xpm, 'paused'),
                 ('Step Into\tF11', 'step_into', step_into_xpm, 'can_stepin'),
                 ('Step Out\tShift-F11', 'step_out', step_out_xpm, 'can_stepout'),
                )
        cls.menus = {}
        for label, signal, xpm, status in items:
            resp = dp.send('frame.add_menu', path='Tools:Debug:'+label,
                           rxsignal='debugger.'+signal,
                           updatesignal='debugtool.updateui')
            if not resp:
                continue
            cls.menus[resp[0][1]] = status
            cls.tbDebug.AddSimpleTool(resp[0][1], label,
                                      c2p.BitmapFromXPM(xpm), label)
        cls.tbDebug.Realize()

        dp.send('frame.add_panel', panel=cls.tbDebug, title='Debugger',
                active=False, paneInfo=aui.AuiPaneInfo().Name('debugger')
                .Caption('Debugger').ToolbarPane().Top(),
                showhidemenu='View:Toolbars:Debugger')
        dp.connect(cls.OnUpdateMenuUI, 'debugtool.updateui')
        dp.connect(cls.OnDebugPaused, 'debugger.paused')
        dp.connect(cls.OnDebugEnded, 'debugger.ended')
        dp.connect(cls.Uninitialize, 'frame.exit')

    @classmethod
    def Uninitialize(cls):
        """destroy the module"""
        pass

    @classmethod
    def OnDebugPaused(cls):
        """update the debug toolbar status"""
        resp = dp.send('debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        paused = status['paused']
        for k, s in six.iteritems(cls.menus):
            cls.tbDebug.EnableTool(k, paused and status.get(s, False))
        cls.tbDebug.Refresh(False)
        if paused and not cls.tbDebug.IsShown():
            dp.send('frame.show_panel', panel=cls.tbDebug)

        if cls.showStackPanel and paused and not cls.panelStack.IsShown():
            dp.send('frame.show_panel', panel=cls.panelStack)
            # allow the use to hide the Stack panel
            cls.showStackPanel = False
    @classmethod
    def OnDebugEnded(cls):
        """debugger is ended"""
        # disable and hide the debugger toolbar
        for k in six.iterkeys(cls.menus):
            cls.tbDebug.EnableTool(k, False)
        cls.tbDebug.Refresh(False)

        # hide the debugger toolbar and Stack panel
        dp.send('frame.show_panel', panel=cls.tbDebug, show=False)
        dp.send('frame.show_panel', panel=cls.panelStack, show=False)
        # show the Stack panel next time
        cls.showStackPanel = True
    @classmethod
    def OnUpdateMenuUI(cls, event):
        """update the debugger toolbar"""
        eid = event.GetId()
        resp = dp.send('debugger.get_status')
        enable = False
        if resp and resp[0][1]:
            status = resp[0][1]
            paused = status['paused']

            s = cls.menus.get(eid, 'paused')

            enable = paused and status[s]
        event.Enable(enable)

def bsm_initialize(frame, **kwargs):
    """module initialization"""
    DebugTool.Initialize(frame, **kwargs)
