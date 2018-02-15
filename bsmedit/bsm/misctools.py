import pydoc
import os
import time
import traceback
import sys
import six
import wx
import wx.py.dispatcher as dp
import wx.html2 as html
from .dirtreectrl import DirTreeCtrl, Directory
from ._misctoolsxpm import backward_xpm, forward_xpm, goup_xpm, home_xpm
from .autocomplete import AutocompleteTextCtrl
from ._utility import FastLoadTreeCtrl
from .. import c2p

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
        c2p.tbAddTool(self.tb, wx.ID_BACKWARD, 'Back',
                      c2p.BitmapFromXPM(backward_xpm), wx.NullBitmap,
                      wx.ITEM_NORMAL, 'Go the previous page', wx.EmptyString)
        c2p.tbAddTool(self.tb, wx.ID_FORWARD, 'Forward',
                      c2p.BitmapFromXPM(forward_xpm), wx.NullBitmap,
                      wx.ITEM_NORMAL, 'Go to the next page', wx.EmptyString)
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
        response = dp.send(signal='shell.auto_complete_list', command=query)
        if response:
            root = query[0:query.rfind('.')+1]
            remain = query[query.rfind('.')+1:]
            remain = remain.lower()
            objs = [o for o in response[0][1] if o.lower().startswith(remain)]
            return objs, objs, len(query) - len(root)
        return [], [], 0
    def add_history(self, command):
        if len(self.history) == 0 or self.history[-1] != command:
            self.history.append(command)
            self.history_index = -1

    def show_help(self, command, addhistory=True):
        try:
            strhelp = pydoc.plain(pydoc.render_doc(str(command), "Help on %s"))
            htmlpage = html_template%({'title':'', 'message':strhelp})
            self.html.SetPage(htmlpage, '')
            # do not use SetValue since it will trigger the text update event, which
            # will popup the auto complete list window
            self.search.ChangeValue(command)
            if addhistory:
                self.add_history(command)
        except:
            traceback.print_exc(file=sys.stdout)
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

class HistoryPanel(wx.Panel):
    ID_CUT = wx.NewId()
    ID_COPY = wx.NewId()
    ID_EXECUTE = wx.NewId()
    ID_CLEAR = wx.NewId()
    ID_DELETE = wx.NewId()
    TIME_STAMP_HEADER = "#bsm"
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT |wx.TR_MULTIPLE |\
                wx.TR_HAS_VARIABLE_ROW_HEIGHT
        self.tree = FastLoadTreeCtrl(self, getchildren=self.get_children, style=style)
        self.history = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)
        dp.connect(receiver=self.AddHistory, signal='Shell.addHistory')
        dp.connect(receiver=self.LoadHistory, signal='frame.load_config')
        dp.connect(receiver=self.SaveHistory, signal='frame.save_config')
        self.root = self.tree.AddRoot('The Root Item')
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick, self.tree)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_EXECUTE)
        #self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_CLEAR)

        accel = [(wx.ACCEL_CTRL, ord('C'), self.ID_COPY),
                 (wx.ACCEL_CTRL, ord('X'), self.ID_CUT),
                 #(wx.ACCEL_CTRL, ord('A'), wx.ID_SELECTALL),
                 (wx.ACCEL_NORMAL, wx.WXK_DELETE, self.ID_DELETE),
                ]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)

    def get_children(self, item):
        """ callback function to return the children of item """
        if item == self.tree.GetRootItem():
            childlist = list(six.iterkeys(self.history))
            childlist.sort(reverse=True)
            is_folder = True
            clr = wx.Colour(100, 174, 100)
        else:
            stamp = self.tree.GetItemText(item)
            childlist = self.history.get(stamp, [])
            is_folder = False
            clr = None
            # free the list
            self.history.pop(stamp, None)
        children = []
        for obj in childlist:
            child = {'label': obj, 'img':-1, 'imgsel': -1, 'data':'',
                     'color': clr}
            child['is_folder'] = is_folder
            children.append(child)
        return children

    def LoadHistory(self, config):
        config.SetPath('/CommandHistory')
        stamp = time.strftime('#%Y/%m/%d')
        for i in six.moves.range(0, config.GetNumberOfEntries()):
            value = config.Read("item%d"%i)
            if value.startswith(self.TIME_STAMP_HEADER):
                stamp = value[len(self.TIME_STAMP_HEADER):]
                self.history[stamp] = self.history.get(stamp, [])
            elif self.history.get(stamp, None) is not None:
                self.history[stamp].append(value)

        self.tree.FillChildren(self.root)
        item = self.tree.GetLastChild(self.root)
        if item.IsOk():
            self.tree.Expand(item)

    def SaveHistory(self, config):
        """save the history"""
        config.DeleteGroup('/CommandHistory')
        config.SetPath('/CommandHistory')
        (item, cookie) = self.tree.GetFirstChild(self.root)
        pos = 0
        while item.IsOk():
            stamp = self.tree.GetItemText(item)
            config.Write("item%d"%pos, self.TIME_STAMP_HEADER + stamp)
            pos += 1

            childitem, childcookie = self.tree.GetFirstChild(item)
            if childitem.IsOk() and self.tree.GetItemText(childitem) != "...":
                while childitem.IsOk():
                    config.Write("item%d"%pos, self.tree.GetItemText(childitem))
                    childitem, childcookie = self.tree.GetNextChild(item, childcookie)
                    pos = pos + 1
            # save the unexpanded folder
            for child in self.history.get(stamp, []):
                config.Write("item%d"%pos, child)
                pos = pos + 1

            (item, cookie) = self.tree.GetNextChild(self.root, cookie)

    def AddHistory(self, command, stamp=""):
        """ add history to treectrl """
        command = command.strip()
        if not command:
            return
        if not stamp:
            stamp = time.strftime('#%Y/%m/%d')

        # search the time stamp
        pos = 0
        item, cookie = self.tree.GetFirstChild(self.root)
        while item.IsOk():
            if self.tree.GetItemText(item) == stamp:
                break
            elif self.tree.GetItemText(item) > stamp:
                item = self.tree.InsertItemBefore(self.root, pos, stamp)
                self.tree.SetItemTextColour(item, wx.Colour(100, 174, 100))
                break
            pos = pos + 1
            (item, cookie) = self.tree.GetNextChild(self.root, cookie)
        # not find the time stamp, create one
        if not item.IsOk():
            item = self.tree.AppendItem(self.root, stamp)
            self.tree.SetItemTextColour(item, wx.Colour(100, 174, 100))
        # append the history
        if item.IsOk():
            self.tree.Expand(item)
            child = self.tree.AppendItem(item, command)
            self.tree.EnsureVisible(child)

    def OnActivate(self, event):
        item = event.GetItem()
        if not self.tree.ItemHasChildren(item):
            command = self.tree.GetItemText(item)
            dp.send(signal='shell.run', command=command)

    def OnRightClick(self, event):
        menu = wx.Menu()
        menu.Append(self.ID_COPY, "Copy")
        menu.Append(self.ID_CUT, "Cut")
        menu.Append(self.ID_EXECUTE, "Evaluate")
        menu.AppendSeparator()
        #menu.Append(wx.ID_SELECTALL, "Select all")
        menu.AppendSeparator()
        menu.Append(self.ID_DELETE, "Delete")
        menu.Append(self.ID_CLEAR, "Clear history")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnProcessEvent(self, event):
        items = self.tree.GetSelections()
        cmd = []
        for item in items:
            cmd.append(self.tree.GetItemText(item))
        evtId = event.GetId()
        if evtId == self.ID_COPY or evtId == self.ID_CUT:
            clipData = wx.TextDataObject()
            clipData.SetText("\n".join(cmd))
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipData)
            wx.TheClipboard.Close()
            if evtId == self.ID_CUT:
                for item in items:
                    if self.tree.ItemHasChildren(item):
                        self.tree.DeleteChildren(item)
                    self.tree.Delete(item)
        elif evtId == self.ID_EXECUTE:
            for c in cmd:
                dp.send(signal='shell.run', command=c)
        elif evtId == self.ID_DELETE:
            for item in items:
                if self.tree.ItemHasChildren(item):
                    self.tree.DeleteChildren(item)
                self.tree.Delete(item)
        elif evtId == self.ID_CLEAR:
            self.tree.DeleteAllItems()

class DirPanel(wx.Panel):

    ID_GOTO_PARENT = wx.NewId()
    ID_GOTO_HOME = wx.NewId()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.tb = wx.ToolBar(self, style=wx.TB_FLAT | wx.TB_HORIZONTAL)
        c2p.tbAddTool(self.tb, self.ID_GOTO_PARENT, 'Parent',
                      c2p.BitmapFromXPM(goup_xpm), wx.NullBitmap,
                      wx.ITEM_NORMAL, 'Parent folder', wx.EmptyString)
        c2p.tbAddTool(self.tb, self.ID_GOTO_HOME, 'Home',
                      c2p.BitmapFromXPM(home_xpm), wx.NullBitmap,
                      wx.ITEM_NORMAL, 'Current folder', wx.EmptyString)
        self.tb.Realize()
        self.dirtree = DirTreeCtrl(self, style=wx.TR_DEFAULT_STYLE |
                                   wx.TR_HAS_VARIABLE_ROW_HEIGHT |
                                   wx.TR_HIDE_ROOT)
        self.dirtree.SetRootDir(os.getcwd())
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.dirtree, 1, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.Bind(wx.EVT_TOOL, self.OnGotoHome, id=self.ID_GOTO_HOME)
        self.Bind(wx.EVT_TOOL, self.OnGotoParent,
                  id=self.ID_GOTO_PARENT)

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated,
                  self.dirtree)

    def OnItemActivated(self, event):
        currentItem = event.GetItem()
        filename = self.dirtree.GetItemText(currentItem)
        parentItem = self.dirtree.GetItemParent(currentItem)
        d = c2p.treeGetData(self.dirtree, parentItem)
        if isinstance(d, Directory):
            filepath = os.path.join(d.directory, filename)
        else:
            return
        if self.dirtree.ItemHasChildren(currentItem):
            self.dirtree.SetRootDir(filepath)
            return
        (path, fileExtension) = os.path.splitext(filename)
        if fileExtension == '.py':
            dp.send(signal='bsm.editor.openfile', filename=filepath)
        else:
            os.system("start "+ filepath)

    def OnGotoHome(self, event):
        root = self.dirtree.GetRootItem()
        if not root:
            return
        d = c2p.treeGetData(self.dirtree, root)
        if isinstance(d, Directory):
            if d.directory == os.getcwd():
                return
        self.dirtree.SetRootDir(os.getcwd())

    def OnGotoParent(self, event):
        root = self.dirtree.GetRootItem()
        if not root:
            return
        d = c2p.treeGetData(self.dirtree, root)
        if isinstance(d, Directory):
            path = os.path.abspath(os.path.join(d.directory, os.path.pardir))
            if path == d.directory:
                return
            self.dirtree.SetRootDir(path)

class MiscTools(object):
    frame = None
    @classmethod
    def Initialize(cls, frame):
        if cls.frame:
            return
        cls.frame = frame
        if not frame:
            return
        # history panel
        cls.panelHistory = HistoryPanel(frame)
        dp.send(signal='frame.add_panel', panel=cls.panelHistory,
                title="History", showhidemenu='View:Panels:Command History')
        # help panel
        cls.panelHelp = HelpPanel(frame)
        dp.send(signal='frame.add_panel', panel=cls.panelHelp, title="Help",
                target='History', showhidemenu='View:Panels:Command Help')
        # directory panel
        cls.panelDir = DirPanel(frame)
        dp.send(signal='frame.add_panel', panel=cls.panelDir, title="Browsing",
                target="History", showhidemenu='View:Panels:Browsing')

        dp.connect(receiver=cls.Uninitialize, signal='frame.exit')

    @classmethod
    def Uninitialize(cls):
        """destroy the module"""
        pass

def bsm_Initialize(frame):
    """module initialization"""
    MiscTools.Initialize(frame)