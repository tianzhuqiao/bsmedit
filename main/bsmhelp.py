import pydoc
import wx
import wx.py.dispatcher as dispatcher
import wx.html2 as html
from bsmhelpxpm import * # for toolbar icon
from bsm.autocomplete import AutocompleteTextCtrl

html_template = '''
<html>
    <head>
        <title>%(title)s</title>
    </head>
    <body>
    <FONT FACE= "Courier New">
    <pre>
%(message)s
    </pre>
    </body>
</html>
'''
class HelpPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.search = AutocompleteTextCtrl(self, completer=self.completer)

        self.html = html.WebView.New(self)

        self.tb = wx.ToolBar(self, style=wx.TB_FLAT|wx.TB_HORIZONTAL|
                             wx.NO_BORDER|wx.TB_NODIVIDER)
        self.tb.AddLabelTool(
            wx.ID_BACKWARD,
            'Back',
            wx.BitmapFromXPMData(arrow_180_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            'Go the previous page',
            wx.EmptyString,
            )
        self.tb.AddLabelTool(
            wx.ID_FORWARD,
            'Forward',
            wx.BitmapFromXPMData(arrow_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            'Go to the next page',
            wx.EmptyString,
            )
        self.tb.Realize()

        # Setup the layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(self.tb, 0, wx.ALL|wx.EXPAND, 5)
        sizer2.Add(self.search, 1, wx.ALL|wx.EXPAND, 5)
        sizer.Add(sizer2, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.html, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

        self.history = []
        self.history_index = -1
        self.findStr = ""
        self.findFlags = html.WEBVIEW_FIND_DEFAULT | html.WEBVIEW_FIND_WRAP

        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.search)
        self.Bind(html.EVT_WEBVIEW_NAVIGATING, self.OnWebViewNavigating, self.html)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=wx.ID_FORWARD)
        self.Bind(wx.EVT_TOOL, self.OnBack, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_TOOL, self.OnForward, id=wx.ID_FORWARD)
        self.Bind(wx.EVT_TOOL, self.OnShowFind, id=wx.ID_FIND)
        # hook the event to invoke 'Find' dialog when 'Ctrl+F' is pressed
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKeyDown)

    def OnKeyDown(self, event):
        controlDown = event.ControlDown()
        rawControlDown = event.RawControlDown()
        key = event.GetKeyCode()

        if (rawControlDown or controlDown) and key in (ord('f'), ord('F')):
            self.OnShowFind(None)
        event.Skip()

    def OnShowFind(self, evt):
        self.html.Find("")
        findData = wx.FindReplaceData()
        dlg = wx.FindReplaceDialog(self, findData, "Find")
        dlg.findData = findData
        dlg.Bind(wx.EVT_FIND, self.OnFind)
        dlg.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        dlg.Show(True)

    def OnFind(self, evt):
        self.findStr = evt.GetFindString()
        flags = evt.GetFlags()
        self.findFlags = html.WEBVIEW_FIND_DEFAULT | html.WEBVIEW_FIND_WRAP
        if wx.FR_WHOLEWORD & flags:
            self.findFlags |= html.WEBVIEW_FIND_ENTIRE_WORD
        if wx.FR_MATCHCASE & flags:
            self.findFlags |= html.WEBVIEW_FIND_MATCH_CASE
        if not(wx.FR_DOWN & flags):
            self.findFlags |= html.WEBVIEW_FIND_BACKWARDS
        self.html.Find(self.findStr, self.findFlags)

    def completer(self, query):
        response = dispatcher.send(signal='shell.auto_complete_list',
                                   command=query)
        if response:
            root = query[0:query.rfind('.')+1]
            remain = query[query.rfind('.')+1:]
            remain = remain.lower()
            objs = [root + o for o in response[0][1] if o.lower().startswith(remain)]
            return objs, objs

    def add_history(self, command):
        if len(self.history) == 0 or self.history[-1] != command:
            self.history.append(command)
            self.history_index = -1

    def show_help(self, command, addhistory=True):
        strhelp = pydoc.plain(pydoc.render_doc(str(command), "Help on %s"))
        htmlpage = html_template%({'title':'', 'message':strhelp})
        self.html.SetPage(htmlpage, '')
        # do not use SetValue since it will trigger the text update event, which
        # will popup the auto complete list window
        self.search.ChangeValue(command)
        if addhistory:
            self.add_history(command)
        return

    def OnDoSearch(self, evt):
        command = self.search.GetValue()
        self.show_help(command)

    def OnWebViewNavigating(self, evt):
        # this event happens prior to trying to get a resource
        strURL = evt.GetURL()
        if strURL[:8] == 'bsmhelp:':
            # This is how you can cancel loading a page.
            evt.Veto()
            command = strURL[8:]
            self.show_help(command)

    def OnUpdateUI(self, event):
        idx = event.GetId()
        h_idx = -1
        h_len = len(self.history)
        if h_len > 0:
            h_idx = self.history_index%h_len
        if idx == wx.ID_FORWARD:
            event.Enable(h_idx >= 0 and h_idx < h_len-1)
        elif idx == wx.ID_BACKWARD:
            event.Enable(h_idx > 0)

    def OnBack(self, event):
        # the button is only enabled when history_index>0
        self.history_index -= 1
        command = self.history[self.history_index]
        self.show_help(command, False)

    def OnForward(self, event):
        # the button is only enable when history_index hasn't reached the last
        # one
        self.history_index += 1
        command = self.history[self.history_index]
        self.show_help(command, False)
