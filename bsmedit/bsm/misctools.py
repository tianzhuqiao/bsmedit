import pydoc
import os
import time
import traceback
import sys
import re
import shutil
import six
import wx
from  wx.lib.agw import aui
import wx.py.dispatcher as dp
import wx.html2 as html
import wx.svg
from .dirtreectrl import DirTreeCtrl, Directory
from .bsmxpm import backward_svg, forward_svg, goup_xpm, home_xpm
from .autocomplete import AutocompleteTextCtrl
from .utility import FastLoadTreeCtrl, svg_to_bitmap, open_file_with_default_app, \
                     show_file_in_finder

from .. import to_byte

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

        self.html = html.WebView.New(self)

        agwStyle = aui.AUI_TB_OVERFLOW | aui.AUI_TB_PLAIN_BACKGROUND
        self.tb = aui.AuiToolBar(self, agwStyle=agwStyle)
        self.tb.AddSimpleTool(wx.ID_BACKWARD, 'Back',
                              svg_to_bitmap(backward_svg),
                              'Go the previous page')

        self.tb.AddSimpleTool(wx.ID_FORWARD, 'Forward',
                              svg_to_bitmap(forward_svg),
                              'Go to the next page')
        self.search = AutocompleteTextCtrl(self.tb, completer=self.completer)
        item = self.tb.AddControl(self.search)
        item.SetProportion(1)
        self.tb.Realize()

        # Setup the layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tb, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.html, 1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(sizer)

        self.history = []
        self.history_index = -1
        self.findStr = ""
        self.findFlags = html.WEBVIEW_FIND_DEFAULT | html.WEBVIEW_FIND_WRAP

        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.search)
        self.Bind(html.EVT_WEBVIEW_NAVIGATING, self.OnWebViewNavigating,
                  self.html)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUI)
        self.Bind(wx.EVT_TOOL, self.OnBack, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_TOOL, self.OnForward, id=wx.ID_FORWARD)
        self.Bind(wx.EVT_TOOL, self.OnShowFind, id=wx.ID_FIND)

        accel = [(wx.ACCEL_CTRL, ord('F'), wx.ID_FIND)]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)

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
        if not (wx.FR_DOWN & flags):
            self.findFlags |= html.WEBVIEW_FIND_BACKWARDS
        self.html.Find(self.findStr, self.findFlags)

    def completer(self, query):
        response = dp.send(signal='shell.auto_complete_list', command=query)
        if response:
            root = query[0:query.rfind('.') + 1]
            remain = query[query.rfind('.') + 1:]
            remain = remain.lower()
            objs = [o for o in response[0][1] if o.lower().startswith(remain)]
            return objs, objs, len(query) - len(root)
        return [], [], 0

    def add_history(self, command):
        if not self.history or self.history[-1] != command:
            self.history.append(command)
            self.history_index = -1

    def show_help(self, command, addhistory=True):
        try:
            strhelp = pydoc.plain(pydoc.render_doc(str(command), "Help on %s"))
            htmlpage = html_template % ({'title': '', 'message': strhelp})
            self.html.SetPage(htmlpage, '')
            # do not use SetValue since it will trigger the text update event, which
            # will popup the auto complete list window
            self.search.ChangeValue(command)
            if addhistory:
                self.add_history(command)
        except:
            traceback.print_exc(file=sys.stdout)

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
            h_idx = self.history_index % h_len
        if idx == wx.ID_FORWARD:
            event.Enable(0 <= h_idx < h_len - 1)
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
    ID_EXECUTE = wx.NewId()
    TIME_STAMP_HEADER = "#bsm"

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        style = wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT |wx.TR_MULTIPLE |\
                wx.TR_HAS_VARIABLE_ROW_HEIGHT
        # no need to sort the commands, as they are naturally sorted by
        # execution time
        self.tree = FastLoadTreeCtrl(self,
                                     getchildren=self.get_children,
                                     style=style,
                                     sort=False)

        agwStyle = aui.AUI_TB_OVERFLOW | aui.AUI_TB_PLAIN_BACKGROUND
        self.tb = aui.AuiToolBar(self)
        self.search = AutocompleteTextCtrl(self.tb, completer=self.completer)
        self.search.SetHint('command pattern (*)')
        item = self.tb.AddControl(self.search)
        item.SetProportion(1)
        self.tb.SetMargins(right=15)
        self.tb.Realize()

        self.history = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.tb, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(sizer)
        dp.connect(receiver=self.AddHistory, signal='Shell.addHistory')
        self.root = self.tree.AddRoot('The Root Item')
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick, self.tree)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_EXECUTE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)

        accel = [
            (wx.ACCEL_CTRL, ord('C'), wx.ID_COPY),
            (wx.ACCEL_CTRL, ord('X'), wx.ID_CUT),
            (wx.ACCEL_CTRL, ord('E'), self.ID_EXECUTE),
            (wx.ACCEL_NORMAL, wx.WXK_DELETE, wx.ID_DELETE),
        ]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)
        self.LoadHistory()

    def completer(self, query):
        response = dp.send(signal='shell.auto_complete_list', command=query)
        if response:
            root = query[0:query.rfind('.') + 1]
            remain = query[query.rfind('.') + 1:]
            remain = remain.lower()
            objs = [o for o in response[0][1] if o.lower().startswith(remain)]
            return objs, objs, len(query) - len(root)
        return [], [], 0

    def Destroy(self):
        dp.disconnect(receiver=self.AddHistory, signal='Shell.addHistory')
        super(HistoryPanel, self).Destroy()

    def get_children(self, item):
        """ callback function to return the children of item """
        if item == self.tree.GetRootItem():
            childlist = list(six.iterkeys(self.history))
            # sort by time-stamp
            childlist.sort()
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
        for obj in reversed(childlist):
            child = {
                'label': obj,
                'img': -1,
                'imgsel': -1,
                'data': '',
                'color': clr
            }
            child['is_folder'] = is_folder
            children.append(child)
        return children

    def filterHistory(self, history):
        pattern = self.search.GetValue()
        if not pattern:
            return history

        pattern = re.compile(pattern)
        return [h for h in history if h.startswith(self.TIME_STAMP_HEADER) or pattern.search(h) is not None]

    def LoadHistory(self):
        resp = dp.send('frame.get_config', group='shell', key='history')
        history = []
        if resp and resp[0][1]:
            history = resp[0][1]

        history = self.filterHistory(history)

        stamp = time.strftime('#%Y/%m/%d')
        for i in six.moves.range(len(history) - 1, -1, -1):
            value = history[i]
            if value.startswith(self.TIME_STAMP_HEADER):
                stamp = value[len(self.TIME_STAMP_HEADER):]
                self.history[stamp] = self.history.get(stamp, [])
            elif self.history.get(stamp, None) is not None:
                self.history[stamp].append(value)
        self.tree.DeleteChildren(self.root)
        self.tree.FillChildren(self.root)
        item, cookie = self.tree.GetFirstChild(self.root)
        if item.IsOk():
            self.tree.Expand(item)
            child, _ = self.tree.GetFirstChild(item)
            if child.IsOk():
                self.tree.SelectItem(child)
                self.tree.EnsureVisible(child)

    def SaveHistory(self, config):
        """save the history"""
        config.DeleteGroup('/CommandHistory')
        config.SetPath('/CommandHistory')
        (item, cookie) = self.tree.GetFirstChild(self.root)
        pos = 0
        while item.IsOk():
            stamp = self.tree.GetItemText(item)
            config.Write("item%d" % pos, self.TIME_STAMP_HEADER + stamp)
            pos += 1

            childitem, childcookie = self.tree.GetFirstChild(item)
            if childitem.IsOk() and self.tree.GetItemText(childitem) != "...":
                while childitem.IsOk():
                    config.Write("item%d" % pos,
                                 self.tree.GetItemText(childitem))
                    childitem, childcookie = self.tree.GetNextChild(
                        item, childcookie)
                    pos = pos + 1
            # save the unexpanded folder
            for child in self.history.get(stamp, []):
                config.Write("item%d" % pos, child)
                pos = pos + 1

            (item, cookie) = self.tree.GetNextChild(self.root, cookie)

    def AddHistory(self, command, stamp=""):
        """ add history to treectrl """
        command = command.strip()
        if not command:
            return
        if not stamp:
            stamp = time.strftime('#%Y/%m/%d')

        if not self.filterHistory([command]):
            # not match the pattern
            return

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
            item = self.tree.PrependItem(self.root, stamp)
            self.tree.SetItemTextColour(item, wx.Colour(100, 174, 100))
        # append the history
        if item.IsOk():
            self.tree.Expand(item)
            child = self.tree.PrependItem(item, command)
            self.tree.EnsureVisible(child)

    def OnActivate(self, event):
        item = event.GetItem()
        if not self.tree.ItemHasChildren(item):
            command = self.tree.GetItemText(item)
            dp.send(signal='shell.run', command=command)

    def OnRightClick(self, event):
        menu = wx.Menu()
        menu.Append(wx.ID_COPY, "Copy\tCtrl+C")
        menu.Append(wx.ID_CUT, "Cut\tCtrl+X")
        menu.Append(self.ID_EXECUTE, "Evaluate\tCtrl+E")
        menu.AppendSeparator()
        menu.AppendSeparator()
        menu.Append(wx.ID_DELETE, "Delete\tDel")
        menu.Append(wx.ID_CLEAR, "Clear history")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnProcessEvent(self, event):
        items = self.tree.GetSelections()
        cmd = []
        for item in items:
            cmd.append(self.tree.GetItemText(item))
        evtId = event.GetId()
        if evtId in (wx.ID_COPY, wx.ID_CUT):
            clipData = wx.TextDataObject()
            clipData.SetText("\n".join(cmd))
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(clipData)
            wx.TheClipboard.Close()
            if evtId == wx.ID_CUT:
                for item in items:
                    if self.tree.ItemHasChildren(item):
                        self.tree.DeleteChildren(item)
                    self.tree.Delete(item)
        elif evtId == self.ID_EXECUTE:
            for c in cmd:
                dp.send(signal='shell.run', command=c)
        elif evtId == wx.ID_DELETE:
            for item in items:
                if self.tree.ItemHasChildren(item):
                    self.tree.DeleteChildren(item)
                self.tree.Delete(item)
        elif evtId == wx.ID_CLEAR:
            self.tree.DeleteAllItems()

    def OnDoSearch(self, evt):
        self.LoadHistory()

class DirPanel(wx.Panel):

    ID_GOTO_PARENT = wx.NewId()
    ID_GOTO_HOME = wx.NewId()
    ID_COPY_PATH = wx.NewId()
    ID_COPY_PATH_REL = wx.NewId()
    ID_OPEN_IN_FINDER = wx.NewId()
    ID_RENAME = wx.NewId()
    ID_PASTE_FOLDER = wx.NewId()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        agwStyle = aui.AUI_TB_OVERFLOW | aui.AUI_TB_PLAIN_BACKGROUND
        self.tb = aui.AuiToolBar(self, agwStyle=agwStyle)
        self.tb.AddSimpleTool(self.ID_GOTO_PARENT, 'Parent',
                              wx.Bitmap(to_byte(goup_xpm)), 'Parent folder')
        self.tb.AddSimpleTool(self.ID_GOTO_HOME, 'Home',
                              wx.Bitmap(to_byte(home_xpm)), 'Current folder')
        self.tb.AddSeparator()
        self.cbShowHidden = wx.CheckBox(self.tb, wx.ID_ANY, 'Show hidden file/folder')
        self.cbShowHidden.SetValue(True)
        self.tb.AddControl(self.cbShowHidden)

        self.tb.Realize()
        self.dirtree = DirTreeCtrl(self,
                                   style=wx.TR_DEFAULT_STYLE
                                   | wx.TR_HAS_VARIABLE_ROW_HEIGHT
                                   | wx.TR_HIDE_ROOT
                                   | wx.TR_EDIT_LABELS)

        agwStyle = aui.AUI_TB_OVERFLOW | aui.AUI_TB_PLAIN_BACKGROUND
        self.tb2 = aui.AuiToolBar(self)
        self.search = AutocompleteTextCtrl(self.tb2)
        self.search.SetHint('file pattern (*.*)')
        item = self.tb2.AddControl(self.search)
        item.SetProportion(1)
        self.tb2.SetMargins(right=15)
        self.tb2.Realize()

        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 0)
        #self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.dirtree, 1, wx.EXPAND)
        self.box.Add(self.tb2, 0, wx.EXPAND)

        self.box.Fit(self)
        self.SetSizer(self.box)

        self.SetRootDir(os.getcwd())

        self.Bind(wx.EVT_TOOL, self.OnGotoHome, id=self.ID_GOTO_HOME)
        self.Bind(wx.EVT_TOOL, self.OnGotoParent, id=self.ID_GOTO_PARENT)

        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnItemActivated,
                  self.dirtree)

        self.Bind(wx.EVT_TEXT, self.OnDoSearch, self.search)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnRightClick, self.dirtree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClickItem, self.dirtree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnRename, self.dirtree)
        self.Bind(wx.EVT_CHECKBOX, self.OnShowHidden, self.cbShowHidden)

        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_OPEN_IN_FINDER)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_COPY_PATH)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_COPY_PATH_REL)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_RENAME)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_PASTE_FOLDER)

        self.active_items = []
    def get_file_path(self, item):
        if item == self.dirtree.GetRootItem():
            d = self.dirtree.GetItemData(item)
            if isinstance(d, Directory):
                return d.directory
            return None

        filename = self.dirtree.GetItemText(item)
        parentItem = self.dirtree.GetItemParent(item)
        d = self.dirtree.GetItemData(parentItem)
        if isinstance(d, Directory):
            filepath = os.path.join(d.directory, filename)
        else:
            return None
        return filepath

    def open(self, items):
        for item in items:
            filename = self.dirtree.GetItemText(item)
            parentItem = self.dirtree.GetItemParent(item)
            d = self.dirtree.GetItemData(parentItem)
            if isinstance(d, Directory):
                filepath = os.path.join(d.directory, filename)
            else:
                return
            if self.dirtree.ItemHasChildren(item):
                self.SetRootDir(filepath)
                return
            (_, ext) = os.path.splitext(filename)
            if ext == '.py':
                dp.send(signal='frame.file_drop', filename=filepath)
            else:
                open_file_with_default_app(filepath)

    def open_in_finder(self, items):
        for item in items:
            filepath = self.get_file_path(item)
            show_file_in_finder(filepath)

    def OnItemActivated(self, event):
        currentItem = event.GetItem()
        self.open([currentItem])

    def OnGotoHome(self, event):
        root = self.dirtree.GetRootItem()
        if not root:
            return
        d = self.dirtree.GetItemData(root)
        if isinstance(d, Directory):
            if d.directory == os.getcwd():
                return
        self.SetRootDir(os.getcwd())

    def OnGotoParent(self, event):
        root = self.dirtree.GetRootItem()
        if not root:
            return
        d = self.dirtree.GetItemData(root)
        if isinstance(d, Directory):
            path = os.path.abspath(os.path.join(d.directory, os.path.pardir))
            if path == d.directory:
                return
            self.SetRootDir(path)

    def OnDoSearch(self, evt):
        self.SetRootDir(os.getcwd())

    def OnRightClick(self, event):
        self.active_items = [self.dirtree.GetRootItem()]
        menu = wx.Menu()
        menu.Append(wx.ID_NEW, "New Folder")
        menu.Append(self.ID_OPEN_IN_FINDER, "Reveal in Finder\tAlt+Ctrl+R")
        menu.AppendSeparator()
        item = menu.Append(self.ID_PASTE_FOLDER, "Paste\tCtrl+V")
        item.Enable(False)
        if wx.TheClipboard.Open():
            data = wx.FileDataObject()
            item.Enable(wx.TheClipboard.GetData(data))
            wx.TheClipboard.Close()

        menu.AppendSeparator()
        menu.Append(self.ID_COPY_PATH, "Copy Path\tAlt+Ctrl+C")
        menu.Append(self.ID_COPY_PATH_REL, "Copy Relative Path\tAlt+Shift+Ctrl+C")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnRightClickItem(self, event):
        self.active_items = self.dirtree.GetSelections()
        menu = wx.Menu()
        menu.Append(wx.ID_OPEN, "Open\tRAWCTRL+Return")
        menu.Append(self.ID_OPEN_IN_FINDER, "Reveal in Finder\tAlt+Ctrl+R")
        menu.AppendSeparator()
        menu.Append(wx.ID_CUT, "Cut\tCtrl+X")
        menu.Append(wx.ID_COPY, "Copy\tCtrl+C")
        menu.AppendSeparator()
        menu.Append(self.ID_COPY_PATH, "Copy Path\tAlt+Ctrl+C")
        menu.Append(self.ID_COPY_PATH_REL, "Copy Relative Path\tAlt+Shift+Ctrl+C")
        menu.AppendSeparator()
        menu.Append(self.ID_RENAME, "Rename\tReturn")
        menu.Append(wx.ID_DELETE, "Delete\tCtrl+Delete")
        self.PopupMenu(menu)
        menu.Destroy()

    def copy(self, items):
        data = wx.FileDataObject()
        for item in items:
            data.AddFile(self.get_file_path(item))

        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(data)
        wx.TheClipboard.Close()

    def delete(self, items):
        for item in items:
            os.remove(self.get_file_path(item))
            self.dirtree.Delete(item)

    def OnProcessEvent(self, event):
        evtId = event.GetId()
        self.do_process(evtId, self.active_items)
        self.active_items = []

    def do_process(self, evtId, items):
        if evtId == wx.ID_OPEN:
            self.open(items)
        elif evtId == self.ID_OPEN_IN_FINDER:
            self.open_in_finder(items)
        elif evtId in (wx.ID_COPY, wx.ID_CUT):
            self.copy(items)
            if evtId == wx.ID_CUT:
                self.delete(items)
        elif evtId == wx.ID_DELETE:
            self.delete(items)
        elif evtId == wx.ID_CLEAR:
            self.tree.DeleteAllItems()
        elif evtId in (self.ID_COPY_PATH, self.ID_COPY_PATH_REL):
            self.copy_path(items, relative=self.ID_COPY_PATH_REL==evtId)
        elif evtId == self.ID_RENAME:
            if items:
                # only edit the first item
                self.dirtree.EditLabel(items[0])
        elif evtId == wx.ID_NEW:
            self.new_folder()
        elif evtId == self.ID_PASTE_FOLDER:
            if wx.TheClipboard.Open():
                data = wx.FileDataObject()
                files_copied = []
                root_item = self.dirtree.GetRootItem()
                if wx.TheClipboard.GetData(data):
                    root_dir = self.get_file_path(root_item)
                    for src in data.GetFilenames():
                        des = os.path.join(root_dir, os.path.basename(src))
                        shutil.copy2(src, des)
                        files_copied.append(os.path.basename(src))
                wx.TheClipboard.Close()
                if files_copied:
                    self.SetRootDir(root_dir)
                    root_item = self.dirtree.GetRootItem()
                    item, cookie = self.dirtree.GetFirstChild(root_item)
                    while item.IsOk():
                        text = self.dirtree.GetItemText(item)
                        if text in files_copied:
                            self.dirtree.SelectItem(item)
                            self.dirtree.EnsureVisible(item)
                        item, cookie = self.dirtree.GetNextChild(root_item, cookie)

    def new_folder(self):
        dlg = wx.TextEntryDialog(self, "Folder name", caption='bsmedit', value='')
        dlg.ShowModal()
        filename = dlg.GetValue()
        dlg.Destroy()
        if not filename:
            return
        root_item = self.dirtree.GetRootItem()
        root_dir = self.get_file_path(root_item)
        new_folder = os.path.join(root_dir, filename)
        if  os.path.exists(new_folder):
            msg = f"{filename} already exists. Please choose a different name."
            dlg = wx.GenericMessageDialog(self, msg, 'bsmedit', style=wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return

        os.makedirs(new_folder)
        self.SetRootDir(root_dir)

        item, cookie = self.dirtree.GetFirstChild(root_item)
        while item.IsOk():
            text = self.dirtree.GetItemText(item)
            if text.lower() == filename.lower():
                self.dirtree.SelectItem(item)
                self.dirtree.EnsureVisible(item)
                break
            item, cookie = self.dirtree.GetNextChild(root_item, cookie)


    def copy_path(self, items, relative=False):
        file_path = []
        for item in items:
            path = self.get_file_path(item)
            if relative:
                path = os.path.relpath(path, os.getcwd())
            file_path.append(path)

        clipData = wx.TextDataObject()
        clipData.SetText("\n".join(file_path))
        wx.TheClipboard.Open()
        wx.TheClipboard.SetData(clipData)
        wx.TheClipboard.Close()

    def OnRename(self, event):
        label = event.GetLabel()
        item = event.GetItem()
        old_label = self.dirtree.GetItemText(item)
        if label == old_label:
            return
        old_path = self.get_file_path(item)
        new_path = os.path.join(os.path.dirname(old_path), label)
        os.rename(old_path, new_path)

    def SetRootDir(self, root_dir=None):
        if not root_dir:
            root_dir = self.get_file_path(self.dirtree.GetRootItem())
        pattern = self.search.GetValue()
        show_hidden =  self.cbShowHidden.IsChecked()
        self.dirtree.SetRootDir(root_dir, pattern=pattern, show_hidden=show_hidden)

    def OnShowHidden(self, event):
        self.SetRootDir()

class MiscTools(object):
    frame = None

    @classmethod
    def Initialize(cls, frame, **kwargs):
        if cls.frame:
            return
        cls.frame = frame
        if not frame:
            return

        active = kwargs.get('active', True)
        direction = kwargs.get('direction', 'top')
        # history panel
        cls.panelHistory = HistoryPanel(frame)
        dp.send(signal='frame.add_panel',
                panel=cls.panelHistory,
                title="History",
                showhidemenu='View:Panels:Command History',
                active=active,
                direction=direction)
        # help panel
        cls.panelHelp = HelpPanel(frame)
        dp.send(signal='frame.add_panel',
                panel=cls.panelHelp,
                title="Help",
                target='History',
                showhidemenu='View:Panels:Command Help',
                active=active,
                direction=direction)
        # directory panel
        cls.panelDir = DirPanel(frame)
        dp.send(signal='frame.add_panel',
                panel=cls.panelDir,
                title="Browsing",
                target="History",
                showhidemenu='View:Panels:Browsing',
                active=active,
                direction=direction)

        dp.connect(receiver=cls.Uninitialize, signal='frame.exit')

    @classmethod
    def Uninitialize(cls):
        """destroy the module"""


def bsm_initialize(frame, **kwargs):
    """module initialization"""
    MiscTools.Initialize(frame, **kwargs)
