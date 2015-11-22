import wx
import wx.py.introspect as introspect
import wx.html2 as html
import imp
import os
from bsmhelpxpm import *
import pydoc
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

    def __init__(self, parent, namespace={}):
        wx.Panel.__init__(self, parent)

        self.search = wx.SearchCtrl(self, size=(200, -1),
                                    style=wx.TE_PROCESS_ENTER)
        self.html = html.WebView.New(self)
        self.namespace = namespace

        self.tb = wx.ToolBar(self, wx.ID_ANY, wx.DefaultPosition,
                                 wx.DefaultSize, wx.TB_FLAT
                                 | wx.TB_HORIZONTAL|wx.NO_BORDER|wx.TB_NODIVIDER)
        self.tb.AddLabelTool(
            wx.ID_BACKWARD,
            u'Back',
            wx.BitmapFromXPMData(arrow_180_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            u'Go the previous page',
            wx.EmptyString,
            )
        self.tb.AddLabelTool(
            wx.ID_FORWARD,
            u'Forward',
            wx.BitmapFromXPMData(arrow_xpm),
            wx.NullBitmap,
            wx.ITEM_NORMAL,
            u'Go to the next page',
            wx.EmptyString,
            )
        self.tb.Realize()
        # Setup the layout

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(self.tb, 0, wx.ALL|wx.EXPAND, 5)
        sizer2.Add(self.search, 1,wx.ALL|wx.EXPAND, 5)
        sizer.Add(sizer2, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.html, 1, wx.ALL | wx.EXPAND, 5)
        self.search.ShowSearchButton(True)
        self.SetSizer(sizer)

        self.history=[]
        self.history_cursor = -1
        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.search)
        self.Bind(html.EVT_WEBVIEW_NAVIGATING, self.OnWebViewNavigating, self.html)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI, id=wx.ID_FORWARD)
        self.Bind(wx.EVT_TOOL, self.OnBack, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_TOOL, self.OnForward, id=wx.ID_FORWARD)
        self.search.Bind(wx.EVT_CHAR, self.OnChar)
    def OnChar(self, evt):
        #key = evt.GetKeyCode()
        #if key == ord('.'):
        #    # Usually the dot (period) key activates auto completion.
        #    # Get the command between the prompt and the cursor.  Add
        #    # the autocomplete character to the end of the command.
        #    if self.AutoCompActive():
        #        self.AutoCompCancel()
        #    command = self.GetTextRange(stoppos, currpos) + chr(key)
        #    if self.autoComplete:
        #        self.autoCompleteShow(command)
        #elif key == ord('('):
        #    # The left paren activates a call tip and cancels an
        #    # active auto completion.
        #    if self.AutoCompActive():
        #        self.AutoCompCancel()
        #    # Get the command between the prompt and the cursor.  Add
        #    # the '(' to the end of the command.
        #    self.ReplaceSelection("""""")
        #    command = self.GetTextRange(stoppos, currpos) + '('
        #    self.AddText('(')
        #    self.autoCallTipShow(command, self.GetCurrentPos()
        #                         == self.GetTextLength())

        evt.Skip()
    def add_history(self,command,type):
        if len(self.history)==0 or self.history[-1]!=command:
            self.history.append((command,type))
            self.history_cursor = -1
    def show_help(self,command,type=None, addhistory=True):
        response = wx.py.dispatcher.send(signal='shell.auto_complete_list',
                    command = command+'.')
        strhelp = pydoc.plain(pydoc.render_doc(str(command), "Help on %s"))
        htmlpage = html_template%({'title':'','message':strhelp})
        self.html.SetPage(htmlpage,'')
        self.search.SetValue(command)
        if addhistory:
            self.add_history(command,'module')
        return
        connent = ""
        if type==None or type == 'module':
            try:
                response = wx.py.dispatcher.send(signal='shell.auto_complete_list',
                    command = command+'.')
                tip = ''
                
                if response:
                    tip = response[0][1]
                print tip
                content = os.linesep.join([ '<a href="bsmhelp:%s%s">%s</a><br>'%(command+'.',x,x) for x in tip])
                #htmlpage = html_template%({'title':'','message':content})
                #self.html.SetPage(htmlpage,'')
                #self.html.SetPage('<p>' + content + '</p>','')
                #self.search.SetValue(command)
                #if addhistory:
                #    self.add_history(command,'module')
            except ImportError:
                pass
        if type==None or type == 'method':
            (name, argspec, tip) = introspect.getCallTip(command,
                    self.namespace)
            tip2 = tip.split('\n')
            content = os.linesep.join([ '%s<br>'%x for x in tip2]) + content
        htmlpage = html_template%({'title':'','message':content})
        self.html.SetPage(htmlpage,'')
            
        self.search.SetValue(command)
        if addhistory:
           self.add_history(command,'method')
    def OnDoSearch(self, evt):
        command = self.search.GetValue()
        self.show_help(command)

    # WebView events
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
        if h_len>0:
            h_idx = self.history_cursor%h_len
        if idx == wx.ID_FORWARD:
            event.Enable(h_idx>=0 and h_idx<h_len-1)
        elif idx == wx.ID_BACKWARD:
            event.Enable(h_idx>0)
    def OnBack(self,event):
        self.history_cursor -=1
        command,type = self.history[self.history_cursor]
        self.show_help(command,type,False)
    def OnForward(self,event):
        self.history_cursor +=1
        command,type = self.history[self.history_cursor]
        self.show_help(command,type,False)
