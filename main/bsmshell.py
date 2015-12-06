import wx
import wx.py
import os
#from wx.py.magic import magic, magicSingle
from wx.py.shell import USE_MAGIC
import sys
import time
import wx.html2 as html
import pprint
import inspect
import re
from debugger import EngineDebugger
import wx.lib.mixins.listctrl as listmix
import traceback
import subprocess as sp
import keyword
aliasDict = {}
def magicSingle(command):
    if command=='': # Pass if command is blank
        return command
    
    first_space=command.find(' ')
    
    if command[0]==' ': # Pass if command begins with a space
        pass
    elif command[0]=='?': # Do help if starts with ?
        command='help('+command[1:]+')'
    elif command[0]=='!': # Use os.system if starts with !
        command='sx("'+command[1:]+'")'
    elif command in ('ls','pwd'): # automatically use ls and pwd with no arguments
        command=command+'()'
    elif command[:3] in ('ls ','cd '): # when using the 'ls ' or 'cd ' constructs, fill in both parentheses and quotes
        command=command[:2]+'("'+command[3:]+'")'
    elif command[:6] in ('clear '):
        command=command[:5]+'()'
        print command
    elif command[:6] == 'alias ':
        c = command[6:].lstrip().split(' ')
        if len(c)<2:
            #print 'Not enough arguments for alias!'
            command = ''
        else:
            n,v = c[0],' '.join(c[1:])
            aliasDict[n]=v
            command = ''
    elif command.split(' ')[0] in aliasDict.keys():
        c = command.split(' ')
        if len(c)<2:
            command = 'sx("'+aliasDict[c[0]]+'")'
        else:
            command = 'sx("'+aliasDict[c[0]]+' '+' '.join(c[1:])+'")'
    elif first_space!=-1:       # if there is at least one space, add parentheses at beginning and end
        cmds=command.split(' ')
        if len(cmds)>1:
            wd1=cmds[0]
            wd2=cmds[1]
            i=1
            while wd2=='':
                i+=1
                if len(cmds)==i:
                    break
                wd2=cmds[i]
            if wd2=='':
                return command
            if (wd1[0].isalpha() or wd1[0]=='_') and (wd2[0].isalnum() or (wd2[0] in """."'_""")) and not keyword.iskeyword(wd1) and not keyword.iskeyword(wd2):
                if wd1.replace('.','').replace('_','').isalnum():
                    command=wd1+'('+command[(first_space+1):]+')' # add parentheses where the first space was and at the end... hooray!
    return command

def magic(command):
    continuations = wx.py.parse.testForContinuations(command) 
    if len(continuations)==2: # Error case...
        return command
    elif len(continuations)==4:
        stringContinuationList,indentationBlockList, \
        lineContinuationList,parentheticalContinuationList = continuations
    
    commandList=[]
    firstLine = True
    for i in command.split('\n'):
        if firstLine:
            commandList.append(magicSingle(i))
        elif stringContinuationList.pop(0)==False and \
              indentationBlockList.pop(0)==False and \
              lineContinuationList.pop(0)==False and \
              parentheticalContinuationList.pop(0)==False:
            commandList.append(magicSingle(i)) # unless this is in a larger expression, use magic
        else:
            commandList.append(i)
        
        firstLine=False
    
    return '\n'.join(commandList)

def sx(str, *args, **kwds):
    wait = True
    # append '&' to capture the output
    if str[-1] == '&':
        wait = False
        str = str[0:-1]
    startupinfo = sp.STARTUPINFO()
    startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
    # try the standalone command first
    try:
        if wait:
            p =sp.Popen(str.split(' '), startupinfo = startupinfo, 
                                            stdout = sp.PIPE, stderr = sp.PIPE)
            wx.py.dispatcher.send(signal = 'shell.writeout', text = p.stdout.read())
        else:
            p = sp.Popen(str.split(' '), startupinfo = startupinfo)
        return
    except:
        pass
    # try the shell command
    try:
        if wait:
            p = sp.Popen(str.split(' '),startupinfo = startupinfo, shell = True,
                                              stdout = sp.PIPE, stderr = sp.PIPE)
            wx.py.dispatcher.send(signal = 'shell.writeout', text = p.stdout.read())
        else:
            p = sp.Popen(str.split(' '), startupinfo = startupinfo)
        return
    except:
        pass

class bsmShell(wx.py.shell.Shell):

    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, 
                 size=wx.DefaultSize, style=wx.CLIP_CHILDREN, 
                 introText='', locals=None, InterpClass=None,
                 startupScript=None, execStartupScript=True,
                 *args, **kwds):
        # variables used in push, which may be called by
        # wx.py.shell.Shell.__init__ when execStartupScript is True
        self.enable_debugger = False
        self.saveHistory = True
        wx.py.shell.Shell.__init__(self, parent, id, pos, size, style,
                                   introText, locals, InterpClass,
                                   startupScript, execStartupScript,
                                   *args, **kwds)
        self.redirectStdout()
        self.redirectStderr()
        self.redirectStdin()
        # the default sx function (!cmd to run external command) does not work
        # on windows
        import __builtin__
        __builtin__.sx = sx
        self.searchHistory = True
        self.silent = False
        self.autoIndent = True
        self.running = False
        self.debugger = EngineDebugger()
        self.redirectStdout()
        self.redirectStderr()
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        # Add 'pp' (pretty print) to the interpreter's locals.
        self.interp.locals['pp'] = self.ppDisplay
        self.interp.locals['clear'] = self.clear
        wx.py.dispatcher.connect(receiver=self.writeOut, signal='shell.writeout')
        wx.py.dispatcher.connect(receiver=self.debugPrompt, signal='shell.prompt')
        wx.py.dispatcher.connect(receiver=self.addHistory, signal='shell.addToHistory')
        wx.py.dispatcher.connect(receiver=self.LoadHistory, signal='frame.loadconfig')

        wx.py.dispatcher.connect(receiver=self.IsDebuggerOn,
                                 signal='debugger.debugging')
        wx.py.dispatcher.connect(receiver=self.getAutoCompleteList, signal = 'shell.auto_complete_list')
        wx.py.dispatcher.connect(receiver=self.getAutoCompleteKeys, signal = 'shell.auto_complete_keys')
        wx.py.dispatcher.connect(receiver=self.getAutoCallTip, signal = 'shell.auto_call_tip')

    def evaluate(self, word):
        if word in self.interp.locals.keys():
            return self.interp.locals[word]
        try:
            self.interp.locals[word] = eval(word, self.interp.locals)
            return self.interp.locals[word]
        except:
            try:
                self.get('AutoCompleteIgnore').index(word)
                return None
            except:
                try:
                    components = word.split('.')
                    try:
                        mod = __import__(word)
                    except:
                        if len(components) < 2:
                            return None
                        mod = '.'.join(components[:-1])
                        try:
                            mod = __import__(mod)
                        except:
                            return None
                    for comp in components[1:]:
                        mod = getattr(mod, comp)
                    self.interp.locals[word] = mod
                    return mod
                except:
                    return None
    def getAutoCompleteKeys(self):
        return self.interp.getAutoCompleteKeys()

    def getAutoCompleteList(self, command='', signal='', sender='', *args, **kwds):
        try:
            # the command may look like: 
            # numpy.
            # x = numpy.
            # for the later case, remove the lvalue 
            #cmd = re.search('([\w\.]+)$', command).group()
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        return self.interp.getAutoCompleteList(command, *args, **kwds)

    def getAutoCallTip(self, command, signal='', sender='', *args, **kwds):
        return self.interp.getCallTip(command, *args, **kwds)
 
    def autoCompleteShow(self, command, offset = 0):
        try:
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        super(bsmShell, self).autoCompleteShow(command, offset)

    def IsDebuggerOn(self):
        return self.debugger and self.debugger._paused

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)
        if end < start:
            self.SetAnchor(start)
    
    def ppDisplay(self, item):
        display = Display(self.GetTopLevelParent(), item,
                          self.interp.locals)
        wx.py.dispatcher.send(signal='frame.addpanel', panel=display,
                              title='Display')
        display.Update()
    
    def LoadHistory(self, config):
        self.clearHistory()
        config.SetPath('/CommandHistory')
        for i in range(0, config.GetNumberOfEntries()):    
            value = config.Read("item%d"%i)
            if value.find("#==bsm==") == -1:
                self.history.insert(0, value)

    def OnKillFocus(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        if self.AutoCompActive():
            self.AutoCompCancel()
        event.Skip()

    def OnKeyDown(self, event):
        """Key down event handler."""
        key = event.GetKeyCode()
        # If the auto-complete window is up let it do its thing.
        if self.AutoCompActive():
            event.Skip()
            return
        # If it is a letter or digit and the cursor is in readonly section,
        # move the cursor to the end of file
        if not self.CanEdit() and ((key >= ord('A') and key <= ord('Z')) or\
               (key >= ord('a') and key <= ord('z')) or\
               (key >= ord('0') and key <= ord('9')) or\
               (key == wx.WXK_SPACE)):
            endpos = self.GetTextLength()
            self.GotoPos(endpos)
            event.Skip()
            return
        
        shiftDown = event.ShiftDown()
        controlDown = event.ControlDown()
        rawControlDown = event.RawControlDown()
        altDown = event.AltDown()
        shiftDown = event.ShiftDown()
        canEdit = self.CanEdit()

        if canEdit and (not shiftDown) and key == wx.WXK_UP:
            # Replace with the previous command from the history buffer.
            self.GoToHistory(True)
        elif canEdit and (not shiftDown) and key == wx.WXK_DOWN:
            # Replace with the next command from the history buffer.
            self.GoToHistory(False)
        elif canEdit and (not shiftDown) and key == wx.WXK_TAB:
            # show auto-complete list with TAB
            # first try to get the autocompletelist from the package 
            cmd = self.getCommand()
            k = self.getAutoCompleteList(cmd)
            cmd = cmd[cmd.rfind('.')+1:]
            # if failed, search the locals()
            if not k:
                k = self.interp.locals.keys()
                for i in range(len(cmd)-1,-1,-1):
                    if cmd[i].isalnum() or cmd[i] == '_':
                        continue
                    cmd = cmd[i+1:]
                    break
                k = [s for s in k if s.startswith(cmd)]
                k.sort()
            if k:
                self.AutoCompSetAutoHide(self.autoCompleteAutoHide)
                self.AutoCompSetIgnoreCase(self.autoCompleteCaseInsensitive)
                options = ' '.join(k)
                self.AutoCompShow(len(cmd), options)
            return
        else:
            self.searchHistory = True
            super(bsmShell, self).OnKeyDown(event)

    def OnLeftDClick(self, event):
        line_num = self.GetCurrentLine()
        line = self.GetLine(line_num)
        filepath = re.findall('[Ff]ile [^,]+,', line)
        if len(filepath) > 0:
            path = (filepath[0])[6:-2]
            linenum = re.findall('line \d+', line, re.IGNORECASE)
            if len(linenum) > 0:
                linenum = int((linenum[0])[5:])
            else:
                linenum = 1
            wx.py.dispatcher.send(signal='bsm.editor.openfile',
                                  filename=path, activated = True, lineno=linenum)
        event.Skip()

    def GoToHistory(self, up=True):
        """Search up the history buffer for the text in front of the cursor."""
        if not self.CanEdit():
            return
        startpos = self.GetCurrentPos()
        # The text up to the cursor is what we search for.
        numCharsAfterCursor = self.GetTextLength() - startpos
        searchText = self.getCommand(rstrip=False)
        if numCharsAfterCursor > 0:
            searchText = searchText[:-numCharsAfterCursor]
        if not searchText or self.searchHistory == False:
            self.OnHistoryReplace(step = up * 2 - 1)
            self.searchHistory = False
            return
        # Search upwards from the current history position and loop
        # back to the beginning if we don't find anything.
        if up:
            searchOrder = range(self.historyIndex + 1, len(self.history))
        else:
            searchOrder = range(self.historyIndex - 1, -1, -1)
        for i in searchOrder:
            command = self.history[i]
            if command[:len(searchText)] == searchText:
                # Replace the current selection with the one we found.
                endpos = self.GetTextLength()
                self.SetSelection(startpos, endpos)
                self.ReplaceSelection(command[len(searchText):])
                endpos = self.GetCurrentPos()
                self.SetSelection(endpos, startpos)
                # We've now warped into middle of the history.
                self.historyIndex = i
                break
            self.historyIndex = i

    def writeOut(self, text):
        """Replacement for stdout."""
        # only output the text when it is not silent
        if self.silent == False:
            # move the cursor to the end to protect the readonly section
            endpos = self.GetTextLength()
            if not self.CanEdit():
                self.SetCurrentPos(endpos)
            if not self.waiting:
                # if the shell is in idle status, output the text right before the prompt
                self.SetCurrentPos(self.promptPosStart)
                self.write(text)
                self.promptPosStart += self.GetTextLength() - endpos
                self.promptPosEnd += self.GetTextLength() - endpos
            else:
                if self.GetCurrentLine() \
                                == self.LineFromPosition(self.promptPosEnd):
                    self.write(os.linesep)
                self.write(text)
            self.EmptyUndoBuffer()

    def writeErr(self, text):
        self.writeOut(text)

    def runCommand(self, command, prompt=True, verbose=True, debug=False):
        self.enable_debugger = debug
        self.autoIndent = False
        savehistory = self.saveHistory
        self.historyOn(verbose)
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        # Go to the very bottom of the text.
        self.SetCurrentPos(endpos)
        command_typed = ""
        if not self.running and not self.more :
            command_typed = self.GetTextRange(startpos, endpos)
            self.clearCommand()
        
        command = command.rstrip()

        if verbose: self.write(command)
        self.push(command, not prompt)
        self.historyOn(savehistory)
        if not self.more and command_typed:
            self.write(command_typed)
        self.autoIndent = True

    def push(self, command, silent=False):
        """Send command to the interpreter for execution."""
        self.running = True
        if not silent:
            self.write(os.linesep)
        # push to the debugger
        if self.waiting and self.IsDebuggerOn():
            self.debugger.push_line(command)
            return
        # DNM
        cmd_raw = command
        if USE_MAGIC:
            command = magic(command)
        if len(command) > 1 and command[-1] == ';':
            self.silent = True
        
        self.waiting = True
        self.lastUpdate = None
        try:
            if self.enable_debugger:
                self.debugger.reset()
                sys.settrace(self.debugger)
            self.more = self.interp.push(command)
        except:
            traceback.print_exc(file=sys.stdout)
        finally:
            # make sure debugger.ended is always sent; more does not hurt
            if self.enable_debugger: 
                wx.py.dispatcher.send('debugger.ended')
            self.enable_debugger = False
            
        sys.settrace(None)
        self.lastUpdate = None
        self.waiting = False
        self.silent = False
        if not self.more and self.saveHistory:
            self.addHistory(cmd_raw)
        if not silent:
            self.prompt()
        self.running = False;

    def historyOn(self, bSave=True):
        self.saveHistory = bSave
    
    def lstripPrompt(self, text):
        """Return text without a leading prompt."""
        ps = [str(sys.ps1), str(sys.ps2), str(sys.ps3), str("K>> ")]
        # Strip the prompt off the front of text.
        for p in ps:
            if text[:len(p)] == p:
                text = text[len(p):]
                break
        return text

    def prompt(self):
        """Display proper prompt for the context: ps1, ps2 or ps3.

        If this is a continuation line, autoindent as necessary."""
        isreading = self.reader.isreading
        skip = False
        if isreading:
            prompt = str(sys.ps3)
        elif self.more:
            prompt = str(sys.ps2)
        elif self.waiting and self.IsDebuggerOn():
            prompt = 'K>> '
        else:
            prompt = str(sys.ps1)
        pos = self.GetCurLine()[1]
        if pos > 0:
            if isreading:
                skip = True
            else:
                self.write(os.linesep)
        if not self.more:
            self.promptPosStart = self.GetCurrentPos()
        if not skip:
            self.write(prompt)
        if not self.more:
            self.promptPosEnd = self.GetCurrentPos()
            # Keep the undo feature from undoing previous responses.
            self.EmptyUndoBuffer()
        if self.more:
            line_num = self.GetCurrentLine()
            currentLine = self.GetLine(line_num)
            previousLine = self.GetLine(line_num - 1)[len(prompt):]
            pstrip = previousLine.strip()
            lstrip = previousLine.lstrip()
            # Get the first alnum word:
            first_word = []
            for i in pstrip:
                if i.isalnum():
                    first_word.append(i)
                else:
                    break
            first_word = ''.join(first_word)
            if pstrip == '':
                # because it is all whitespace!
                indent = previousLine.strip('\n').strip('\r')
            else:
                indent = previousLine[:len(previousLine) - len(lstrip)]
                if pstrip[-1] == ':' and first_word in [
                    'if', 'else', 'elif', 'for', 'while', 'def', 'class',
                    'try', 'except', 'finally']:
                    indent += ' ' * 4
            if self.autoIndent:
                self.write(indent)
        self.SetSavePoint()
        self.EnsureCaretVisible()
        self.ScrollToColumn(0)

    def autoCallTipShow(self, command, insertcalltip=True, forceCallTip=False):
        """Display argument spec and docstring in a popup window."""
        if self.CallTipActive():
            self.CallTipCancel()
        (name, argspec, tip) = self.interp.getCallTip(command)
        if tip:
            wx.py.dispatcher.send(signal='Shell.calltip', sender=self,
                                  calltip=tip)
        if not self.autoCallTip and not forceCallTip:
            return
        startpos = self.GetCurrentPos()
        if argspec and insertcalltip and self.callTipInsert:
            self.write(argspec + ')')
            endpos = self.GetCurrentPos()
            self.SetSelection(startpos, endpos)

    def debugPrompt(self, ismore=False, iserr=False):
        if not self.IsModified():
            return
        self.more = ismore
        autoIndent = self.autoIndent
        if self.more:
            self.autoIndent = True
        self.prompt()
        self.autoIndent = autoIndent

    def debugExecuteCommand(self, command):
        if command:
            self.addHistory(command)

    def debug_ended(self):
        pass
        #self.prompt()

class HistoryPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.tree = wx.TreeCtrl(self, -1, style=wx.TR_DEFAULT_STYLE
                                | wx.TR_HIDE_ROOT |wx.TR_MULTIPLE) 
        # wx.TR_HAS_BUTTONS | wx.TR_EDIT_LABELS
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)
        wx.py.dispatcher.connect(receiver=self.addHistory,
                                 signal='Shell.addHistory')
        wx.py.dispatcher.connect(receiver=self.LoadHistory,
                                 signal='frame.loadconfig')
        wx.py.dispatcher.connect(receiver=self.SaveHistory,
                                 signal='frame.saveconfig')
        self.root = self.tree.AddRoot('The Root Item')
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnRightClick, self.tree)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_EXECUTE)
        #self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CLEAR)
        
        self.accel = wx.AcceleratorTable(
                [(wx.ACCEL_CTRL, ord('C'), wx.ID_COPY),
                 (wx.ACCEL_CTRL, ord('X'), wx.ID_CUT),
                 #(wx.ACCEL_CTRL, ord('A'), wx.ID_SELECTALL),
                 (wx.ACCEL_NORMAL, wx.WXK_DELETE, wx.ID_DELETE),
                ])
        self.SetAcceleratorTable(self.accel)

    def LoadHistory(self, config):
        config.SetPath('/CommandHistory')
        stamp = "";
        for i in range(0, config.GetNumberOfEntries()):
            value = config.Read("item%d"%i)
            if value.find("#==bsm==")==0:
                stamp = value[8:]
            else:
                self.addHistory(value, stamp)

    def SaveHistory(self, config):
        config.DeleteGroup('/CommandHistory')
        config.SetPath('/CommandHistory')
        (item, cookie) = self.tree.GetFirstChild(self.root)
        pos = 0;
        while item.IsOk():
            config.Write("item%d"%pos, "#==bsm=="+self.tree.GetItemText(item))
            pos = pos + 1

            (childitem, childcookie) = self.tree.GetFirstChild(item)
            while childitem.IsOk():
                config.Write("item%d"%pos, self.tree.GetItemText(childitem))
                (childitem, childcookie) = self.tree.GetNextChild(item, childcookie)
                pos = pos + 1
            (item, cookie) = self.tree.GetNextChild(self.root, cookie)

    def addHistory(self, command, stamp=""):
        command = command.strip();
        if stamp:
            day = stamp
        else:
            day = time.strftime('#%m/%d/%Y')

        (item, cookie) = self.tree.GetFirstChild(self.root)
        pos = 0
        while item.IsOk():
            if self.tree.GetItemText(item) == day:
                break
            elif self.tree.GetItemText(item) > day:
                item = self.tree.InsertItemBefore(self.root, pos, day)
                self.tree.SetItemTextColour(item, wx.Colour(100,174,100))
                break
            pos = pos + 1
            (item, cookie) = self.tree.GetNextChild(self.root, cookie)
        if not item.IsOk():
            item = self.tree.AppendItem(self.root, day)
            self.tree.SetItemTextColour(item, wx.Colour(100,174,100))
        if item.IsOk():
            child = self.tree.AppendItem(item, command)
            self.tree.EnsureVisible(child)

    def OnActivate(self, event):
        item = event.GetItem()
        if not self.tree.ItemHasChildren(item):
            command = self.tree.GetItemText(item)
            wx.py.dispatcher.send(signal='frame.run', command=command)

    def OnRightClick(self, event):
        menu = wx.Menu()
        item1 = menu.Append(wx.ID_COPY, "Copy")
        item2 = menu.Append(wx.ID_CUT, "Cut")
        item2 = menu.Append(wx.ID_EXECUTE, "Evaluate")
        menu.AppendSeparator()
        #menu.Append(wx.ID_SELECTALL, "Select all")
        menu.AppendSeparator()
        menu.Append(wx.ID_DELETE, "Delete")
        menu.Append(wx.ID_CLEAR, "Clear history")
        self.PopupMenu(menu)
        menu.Destroy()

    def OnProcessEvent(self, event):
        items = self.tree.GetSelections()
        cmd = [];
        for item in items:
            cmd.append(self.tree.GetItemText(item))
        evtId = event.GetId()
        if evtId == wx.ID_COPY or evtId == wx.ID_CUT:
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
        elif evtId == wx.ID_EXECUTE:
            for c in cmd:
                wx.py.dispatcher.send(signal='frame.run', command=c)
        #elif evtId == wx.ID_SELECTALL:
        #    (item, cookie) = self.tree.GetFirstChild(self.root)
        #    while item.IsOk():
        #        self.tree.SelectChildren(item)
        #        self.tree.SelectItem(item)
        #        (item, cookie) = self.tree.GetNextChild(self.root, cookie)
        elif evtId == wx.ID_DELETE:
            for item in items:
                if self.tree.ItemHasChildren(item):
                    self.tree.DeleteChildren(item)
                self.tree.Delete(item)
        elif evtId == wx.ID_CLEAR:
            self.tree.DeleteAllItems()
                
class Display(wx.Panel):

    def __init__(self, parent, item, namespace):
        wx.Panel.__init__(self, parent)
        self.search = wx.SearchCtrl(self, size=(200, -1),
                                    style=wx.TE_PROCESS_ENTER)
        self.html = html.WebView.New(self)
        # Setup the layout
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(self.search, 1, wx.ALL | wx.EXPAND, 5)
        sizer.Add(sizer2, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.html, 1, wx.ALL | wx.EXPAND, 5)
        self.search.ShowSearchButton(True)
        self.SetSizer(sizer)
        # self.Update()
        self.set_item(item)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnDoSearch, self.search)
        self.namespace = namespace
        wx.py.dispatcher.connect(receiver=self.push,
                                 signal='Interpreter.push')

    def refresh_item(self):
        if not hasattr(self, 'item'):
            return
        if self.item is not None:
            text = pprint.pformat(self.item)
        else:
            text = ''
        self.html.SetPage('<pre>' + text + '</pre>','')

    def set_item(self, item):
        self.item = item
        self.refresh_item()

    def OnDoSearch(self, evt):
        command = self.search.GetValue()
        self.set_item(self.namespace.get(command, None))

    def push(self, command, more, source):
        """Receiver for Interpreter.push signal."""
        self.refresh_item()

class stackListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin,
     listmix.ListRowHighlighter):

    def __init__(self, parent, ID, pos=wx.DefaultPosition, size=wx.DefaultSize, 
                 style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)

        listmix.ListCtrlAutoWidthMixin.__init__(self)
        listmix.ListRowHighlighter.__init__(self,
                mode=listmix.HIGHLIGHT_ODD)
        self.SetHighlightColor(wx.Colour(240,240,250))

class StackPanel(wx.Panel):

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.listctrl = stackListCtrl(self, wx.ID_ANY, style=wx.LC_REPORT
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
        wx.py.dispatcher.connect(self.debug_ended, 'debugger.ended')
        wx.py.dispatcher.connect(self.debug_update_scopes, 'debugger.updatescopes')

    def debug_ended(self):
        self.listctrl.DeleteAllItems()

    def debug_update_scopes(self, data):
        #data =( (name,self._abs_filename( filename ),lineno), 
        #        self._scopes, self._active_scope, 
        #        (self._can_stepin,self._can_stepout),self._frames)
        self.listctrl.DeleteAllItems()
        frames = data[4]
        level = data[2]
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
        wx.py.dispatcher.send(signal='bsm.editor.openfile', filename=filename, 
                              lineno=int(lineno))
        # ask the debugger to trigger the update scope event to set mark
        wx.py.dispatcher.send(signal='debugger.setscope', level=currentItem)
