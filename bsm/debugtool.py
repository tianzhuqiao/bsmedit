import sys
import inspect
import wx
import wx.py.dispatcher as dispatcher
import wx.lib.mixins.listctrl as listmix
import wx.lib.agw.aui as aui
from _debugtoolxpm import run_xpm, step_xpm, step_into_xpm, step_out_xpm,\
                          stop_xpm

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
        dispatcher.connect(self.OnDebugEnded, 'debugger.ended')
        dispatcher.connect(self.OnDebugUpdateScopes, 'debugger.update_scopes')

    def OnDebugEnded(self):
        """debugger is ended"""
        # clear the scopes
        self.listctrl.DeleteAllItems()

    def OnDebugUpdateScopes(self):
        """debugger changes the scope"""
        self.listctrl.DeleteAllItems()
        resp = dispatcher.send(signal='debugger.get_status')
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
                index = self.listctrl.InsertStringItem(sys.maxint, name)
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
        dispatcher.send(signal='bsm.editor.openfile', filename=filename,
                        lineno=int(lineno))
        # ask the debugger to trigger the update scope event to set mark
        dispatcher.send(signal='debugger.set_scope', level=currentItem)

class DebugTool(object):
    isInitialized = False
    frame = None
    @classmethod
    def Initialize(cls, frame):
        if cls.isInitialized:
            return
        cls.isInitialized = True
        cls.frame = frame
        # stack panel
        cls.panelStack = StackPanel(frame)
        dispatcher.send(signal='frame.add_panel', panel=cls.panelStack,
                        title="Call Stack",
                        active=False,
                        showhidemenu='View:Panels:Call Stack')

        # debugger toolbar
        dispatcher.send(signal='frame.add_menu', path='Tools:Debug',
                        rxsignal='', kind='Popup')
        cls.tbDebug = aui.AuiToolBar(frame, style=wx.TB_FLAT | wx.TB_HORIZONTAL)
        items = (('Run\tF5', 'resume', run_xpm, 'paused'),
                 ('Stop\tShift-F5', 'stop', stop_xpm, 'paused'),
                 ('Step\tF10', 'step', step_xpm, 'paused'),
                 ('Step Into\tF11', 'step_into', step_into_xpm, 'can_stepin'),
                 ('Step Out\tShift-F11', 'step_out', step_out_xpm, 'can_stepout'),
                )
        cls.menus = {}
        for label, signal, xpm, status in items:
            resp = dispatcher.send(signal='frame.add_menu',
                                   path='Tools:Debug:'+label,
                                   rxsignal='debugger.'+signal,
                                   updatesignal='debugtool.updateui')
            if not resp:
                continue
            cls.menus[resp[0][1]] = status
            cls.tbDebug.AddSimpleTool(resp[0][1], label,
                                      wx.BitmapFromXPMData(xpm), label)
        cls.tbDebug.Realize()

        dispatcher.send(signal='frame.add_panel', panel=cls.tbDebug,
                        title='Debugger', active=False,
                        paneInfo=aui.AuiPaneInfo().Name('debugger')
                        .Caption('Debugger').ToolbarPane().Top(),
                        showhidemenu='View:Toolbars:Debugger')
        dispatcher.connect(receiver=cls.OnUpdateMenuUI, signal='debugtool.updateui')
        dispatcher.connect(cls.OnDebugPaused, 'debugger.paused')
        dispatcher.connect(cls.OnDebugEnded, 'debugger.ended')

        dispatcher.connect(receiver=cls.Uninitialize, signal='frame.exit')
    @classmethod
    def Uninitialize(cls):
        """destroy the module"""
        pass
    @classmethod
    def OnDebugPaused(cls):
        """update the debug toolbar status"""
        resp = dispatcher.send(signal='debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        paused = status['paused']
        for k, s in cls.menus.iteritems():
            cls.tbDebug.EnableTool(k, paused and status.get(s, False))
        cls.tbDebug.Refresh(False)
        if paused and not cls.tbDebug.IsShown():
            dispatcher.send(signal='frame.show_panel', panel=cls.tbDebug)

        if paused and not cls.panelStack.IsShown():
            dispatcher.send(signal='frame.show_panel', panel=cls.panelStack)
    @classmethod
    def OnDebugEnded(cls):
        """debugger is ended"""
        # disable and hide the debugger toolbar
        for k in cls.menus.keys():
            cls.tbDebug.EnableTool(k, False)
        cls.tbDebug.Refresh(False)

        dispatcher.send(signal='frame.show_panel', panel=cls.tbDebug,
                        show=False)
        dispatcher.send(signal='frame.show_panel', panel=cls.panelStack,
                        show=False)
    @classmethod
    def OnUpdateMenuUI(cls, event):
        """update the debugger toolbar"""
        eid = event.GetId()
        resp = dispatcher.send(signal='debugger.get_status')
        enable = False
        if resp and resp[0][1]:
            status = resp[0][1]
            paused = status['paused']

            s = cls.menus.get(eid, 'paused')

            enable = paused and status[s]
        event.Enable(enable)

def bsm_Initialize(frame):
    """module initialization"""
    DebugTool.Initialize(frame)
