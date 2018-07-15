import os
import sys
import re
import traceback
import subprocess as sp
import keyword
import time
import pydoc
import six
import wx
import wx.py.shell as pyshell
import wx.py.dispatcher as dp
from wx.py.pseudo import PseudoFile
import six.moves.builtins as __builtin__
from .debugger import EngineDebugger
from ..version import BSM_VERSION

# in linux, the multiprocessing/process.py/_bootstrap will call
# sys.stdin.close(), which is missing in wx.py.pseudo.PseudoFile
def PseudoFile_close(self):
    pass
PseudoFile.close = PseudoFile_close

aliasDict = {}
def magicSingle(command):
    if command == '': # Pass if command is blank
        return command

    first_space = command.find(' ')

    if command[0] == ' ': # Pass if command begins with a space
        pass
    elif command[0] == '?': # Do help if starts with ?
        command = 'help('+command[1:]+')'
    elif command[0] == '!': # Use os.system if starts with !
        command = 'sx("'+command[1:]+'")'
    elif command in ('ls', 'pwd'):
        # automatically use ls and pwd with no arguments
        command = command+'()'
    elif command[:3] in ('ls ', 'cd '):
        # when using the 'ls ' or 'cd ' constructs, fill in both parentheses and quotes
        command = command[:2]+'("'+command[3:]+'")'
    elif command[:5] in ('help '):
        command = command[:4]+'("'+command[5:]+'")'
    elif command[:6] == 'close ':
        arg = command[6:]
        if arg.strip() == 'all':
            # when using the close', fill in both parentheses and quotes
            command = command[:5]+'("'+command[6:]+'")'
    elif command[:5] == 'clear':
        command = command[:5]+'()'
    elif command[:5] == 'alias':
        c = command[5:].lstrip().split(' ')
        if len(c) < 2:
            # delete the alias if exists
            if len(c) == 1:
                aliasDict.pop(c[0], None)
            command = ''
        else:
            n, v = c[0], ' '.join(c[1:])
            aliasDict[n] = v
            command = ''
    elif command.split(' ')[0] in six.iterkeys(aliasDict):
        c = command.split(' ')
        if len(c) < 2:
            command = 'sx("'+aliasDict[c[0]]+'")'
        else:
            command = 'sx("'+aliasDict[c[0]]+' '+' '.join(c[1:])+'")'
    elif first_space != -1:
        # if there is at least one space, add parentheses at beginning and end
        cmds = command.split(' ')
        if len(cmds) > 1:
            wd1 = cmds[0]
            wd2 = cmds[1]
            i = 1
            while wd2 == '':
                i += 1
                if len(cmds) == i:
                    break
                wd2 = cmds[i]
            if wd2 == '':
                return command
            if (wd1[0].isalpha() or wd1[0] == '_') and (wd2[0].isalnum() or\
                    (wd2[0] in """."'_""")) and \
                    not keyword.iskeyword(wd1) and not keyword.iskeyword(wd2):
                if wd1.replace('.', '').replace('_', '').isalnum():
                    # add parentheses where the first space was and at the end... hooray!
                    command = wd1+'('+command[(first_space+1):]+')'
    return command

def _help(command):
    try:
        print(pydoc.plain(pydoc.render_doc(str(command), "Help on %s")))
    except:
        print('No help found on "%s"'%command)
        #traceback.print_exc(file=sys.stdout)
def magic(command):
    continuations = wx.py.parse.testForContinuations(command)
    if len(continuations) == 2: # Error case...
        return command
    elif len(continuations) == 4:
        stringContinuationList, indentationBlockList, \
        lineContinuationList, parentheticalContinuationList = continuations

    commandList = []
    firstLine = True
    for i in command.split('\n'):
        if firstLine:
            commandList.append(magicSingle(i))
        elif stringContinuationList.pop(0) is False and \
              indentationBlockList.pop(0) is False and \
              lineContinuationList.pop(0) is False and \
              parentheticalContinuationList.pop(0) is False:
            commandList.append(magicSingle(i)) # unless this is in a larger expression, use magic
        else:
            commandList.append(i)

        firstLine = False

    return '\n'.join(commandList)

def sx(cmd, *args, **kwds):
    wait = True
    # append '&' to capture the output
    if cmd[-1] == '&':
        wait = False
        cmd = cmd[0:-1]
    startupinfo = sp.STARTUPINFO()
    startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
    # try the standalone command first
    try:
        if wait:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo,
                         stdout=sp.PIPE, stderr=sp.PIPE)
            dp.send('shell.write_out', text=p.stdout.read())
        else:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo)
        return
    except:
        pass
    # try the shell command
    try:
        if wait:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo, shell=True,
                         stdout=sp.PIPE, stderr=sp.PIPE)
            dp.send('shell.write_out', text=p.stdout.read())
        else:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo, shell=True)
        return
    except:
        pass

class Shell(pyshell.Shell):
    ID_COPY_PLUS = wx.NewId()
    ID_PASTE_PLUS = wx.NewId()
    def __init__(self, parent, id=-1, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.CLIP_CHILDREN,
                 introText='', locals=None, InterpClass=None,
                 startupScript=None, execStartupScript=True,
                 *args, **kwds):
        # variables used in push, which may be called by
        # wx.py.shell.Shell.__init__ when execStartupScript is True
        self.enable_debugger = False
        pyshell.Shell.__init__(self, parent, id, pos, size, style, introText,
                               locals, InterpClass, startupScript,
                               execStartupScript, *args, **kwds)
        #self.redirectStdout(True)
        #self.redirectStderr(True)
        #self.redirectStdin(True)
        # the default sx function (!cmd to run external command) does not work
        # on windows
        __builtin__.sx = sx
        self.callTipInsert = False
        self.searchHistory = True
        self.silent = False
        self.autoIndent = True
        self.running = False
        self.debugger = EngineDebugger()
        self.LoadHistory()
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_MENU, self.OnProcessMenu)
        self.interp.locals['clear'] = self.clear
        self.interp.locals['help'] = _help
        self.interp.locals['on'] = True
        self.interp.locals['off'] = False
        dp.connect(self.writeOut, 'shell.write_out')
        dp.connect(self.runCommand, 'shell.run')
        dp.connect(self.debugPrompt, 'shell.prompt')
        dp.connect(self.addHistory, 'shell.addToHistory')
        dp.connect(self.OnFrameExit, 'frame.exit')
        dp.connect(self.IsDebuggerOn, 'debugger.debugging')
        dp.connect(self.getAutoCompleteList, 'shell.auto_complete_list')
        dp.connect(self.getAutoCompleteKeys, 'shell.auto_complete_keys')
        dp.connect(self.getAutoCallTip, 'shell.auto_call_tip')
        dp.connect(self.OnActivatePanel, 'frame.activate_panel')
        dp.connect(self.OnActivate, 'frame.activate')

    def OnContextMenu(self, evt):
        menu = wx.Menu()
        menu.Append(wx.ID_UNDO, "Undo")
        menu.Append(wx.ID_REDO, "Redo")
        menu.AppendSeparator()
        menu.Append(wx.ID_CUT, "Cut")
        menu.Append(wx.ID_COPY, "Copy")
        menu.Append(self.ID_COPY_PLUS, "Copy with prompt")
        menu.Append(wx.ID_PASTE, "Paste")
        menu.Append(self.ID_PASTE_PLUS, "Paste & run")
        menu.Append(wx.ID_CLEAR, "Clear")
        menu.AppendSeparator()
        menu.Append(wx.ID_SELECTALL, "Select All")
        self.PopupMenu(menu)

    def OnProcessMenu(self, event):
        eid = event.GetId()
        cmd = {wx.ID_CUT: self.Cut,
               wx.ID_CLEAR: self.Clear,
               wx.ID_COPY: self.Copy,
               self.ID_COPY_PLUS: self.CopyWithPrompts,
               wx.ID_PASTE: self.Paste,
               self.ID_PASTE_PLUS: self.PasteAndRun,
               wx.ID_UNDO: self.Undo,
               wx.ID_REDO: self.Redo,
               wx.ID_SELECTALL: self.SelectAll}
        fun = cmd.get(eid, None)
        if fun:
            fun()

    def Destroy(self):
        self.debugger.release()
        dp.disconnect(self.writeOut, 'shell.write_out')
        dp.disconnect(self.runCommand, 'shell.run')
        dp.disconnect(self.debugPrompt, 'shell.prompt')
        dp.disconnect(self.addHistory, 'shell.addToHistory')
        dp.disconnect(self.OnFrameExit, 'frame.exit')
        dp.disconnect(self.IsDebuggerOn, 'debugger.debugging')
        dp.disconnect(self.getAutoCompleteList, 'shell.auto_complete_list')
        dp.disconnect(self.getAutoCompleteKeys, 'shell.auto_complete_keys')
        dp.disconnect(self.getAutoCallTip, 'shell.auto_call_tip')
        dp.disconnect(self.OnActivatePanel, 'frame.activate_panel')
        dp.disconnect(self.OnActivate, 'frame.activate')
        super(Shell, self).Destroy()

    def OnFrameExit(self):
        """the frame is exiting"""
        # save command history
        dp.send('frame.set_config', group='shell', history=self.history)
        # stop the debugger if it is on
        if self.IsDebuggerOn():
            dp.send('debugger.stop')

    def evaluate(self, word):
        if word in six.iterkeys(self.interp.locals):
            return self.interp.locals[word]
        try:
            self.interp.locals[word] = eval(word, self.interp.locals)
            return self.interp.locals[word]
        except:
            try:
                getattr(self, 'AutoCompleteIgnore').index(word)
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
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        return self.interp.getAutoCompleteList(command, *args, **kwds)

    def getAutoCallTip(self, command, signal='', sender='', *args, **kwds):
        return self.interp.getCallTip(command, *args, **kwds)

    def autoCompleteShow(self, command, offset=0):
        try:
            command = command.strip()
            # deal with the case "fun(arg.", which will return "arg."
            for i in range(len(command)):
                c = command[-i-1]
                if not (c.isalnum() or c in ('_', '.')):
                    command = command[-i:]
                    break
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        super(Shell, self).autoCompleteShow(command, offset)

    def IsDebuggerOn(self):
        """check if the debugger is on"""
        if not self.debugger:
            return False
        return self.enable_debugger

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)
        if end < start:
            self.SetAnchor(start)

    def LoadHistory(self):
        self.clearHistory()
        resp = dp.send('frame.get_config', group='shell', key='history')
        if resp and resp[0][1]:
            self.history = resp[0][1]

    def OnKillFocus(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        event.Skip()

    def OnActivate(self, activate):
        if self.AutoCompActive():
            wx.CallAfter(self.AutoCompCancel)

    def OnActivatePanel(self, pane):
        if pane != self:
            if self.AutoCompActive():
                wx.CallAfter(self.AutoCompCancel)

    def OnUpdateUI(self, event):
        eid = event.GetId()
        if eid in (wx.ID_CUT, wx.ID_CLEAR):
            event.Enable(self.CanCut())
        elif eid in (wx.ID_COPY, self.ID_COPY_PLUS):
            event.Enable(self.CanCopy())
        elif eid in (wx.ID_PASTE, self.ID_PASTE_PLUS):
            event.Enable(self.CanPaste())
        elif eid == wx.ID_UNDO:
            event.Enable(self.CanUndo())
        elif eid == wx.ID_REDO:
            event.Enable(self.CanRedo())
        # update the caret position so that it is always in valid area
        self.UpdateCaretPos()
        super(Shell, self).OnUpdateUI(event)

    def UpdateCaretPos(self):
        # when editing the command, do not allow moving the caret to
        # readonly area
        if not self.CanEdit() and \
                (self.GetCurrentLine() == self.LineFromPosition(self.promptPosEnd)):
            self.GotoPos(self.promptPosEnd)

    def OnKeyDown(self, event):
        """Key down event handler."""
        key = event.GetKeyCode()
        # If the auto-complete window is up let it do its thing.
        if self.AutoCompActive():
            event.Skip()
            return

        shiftDown = event.ShiftDown()
        controlDown = event.ControlDown()
        rawControlDown = event.RawControlDown()
        altDown = event.AltDown()
        canEdit = self.CanEdit()

        # If it is a letter or digit and the cursor is in readonly section,
        # move the cursor to the end of file
        if not canEdit and (not shiftDown) and (not controlDown) and (not altDown)\
            and (not rawControlDown) and key < 256 and (chr(key).isalnum() or\
               (key == wx.WXK_SPACE)):
            endpos = self.GetTextLength()
            self.GotoPos(endpos)
            event.Skip()
            return

        if canEdit and not self.more and (not shiftDown) and key == wx.WXK_UP:
            # Replace with the previous command from the history buffer.
            self.GoToHistory(True)
        elif canEdit and not self.more and (not shiftDown) and key == wx.WXK_DOWN:
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
                for i in six.moves.range(len(cmd)-1, -1, -1):
                    if cmd[i].isalnum() or cmd[i] == '_':
                        continue
                    cmd = cmd[i+1:]
                    break
                k = six.iterkeys(self.interp.locals)
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
            super(Shell, self).OnKeyDown(event)

    def OnLeftDClick(self, event):
        line_num = self.GetCurrentLine()
        line = self.GetLine(line_num)
        filepath = re.findall('[Ff]ile [^,]+,', line)
        if filepath:
            path = (filepath[0])[6:-2]
            linenum = re.findall(r'line \d+', line, re.IGNORECASE)
            if linenum:
                linenum = int((linenum[0])[5:])
            else:
                linenum = 1
            dp.send('frame.file_drop', filename=path, activated=True,
                    lineno=linenum)
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
            self.OnHistoryReplace(step=up * 2 - 1)
            self.searchHistory = False
            return
        # Search upwards from the current history position and loop
        # back to the beginning if we don't find anything.
        if up:
            searchOrder = six.moves.range(self.historyIndex + 1, len(self.history))
        else:
            searchOrder = six.moves.range(self.historyIndex - 1, -1, -1)
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
        if not self.silent:
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
            # disable undo
            self.EmptyUndoBuffer()
            # move the caret to the end
            self.GotoPos(self.GetTextLength())
            self.Update()

    def writeErr(self, text):
        """Replacement for stderror"""
        self.writeOut(text)

    def addHistory(self, command):
        # override the parent function to add time-stamp.
        stamp = time.strftime('#bsm#%Y/%m/%d')
        if stamp not in self.history:
            self.history.insert(0, stamp)
        super(Shell, self).addHistory(command)

    def runCommand(self, command, prompt=True, verbose=True, debug=False,
                   history=True):
        """run the command in the shell"""
        if not self.enable_debugger:
            self.enable_debugger = debug
        self.autoIndent = False
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        # Go to the very bottom of the text.
        self.SetCurrentPos(endpos)

        # save the currently typed command
        command_typed = ""
        if not self.running and not self.more:
            command_typed = self.GetTextRange(startpos, endpos)
            self.clearCommand()

        command = command.rstrip()
        if verbose:
            self.write(command)
        self.push(command, not prompt, history)

        # retrieve the typed command
        if not self.more and command_typed:
            self.write(command_typed)
        self.autoIndent = True

    def push(self, command, silent=False, history=True):
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
        if pyshell.USE_MAGIC:
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
                dp.send('debugger.ended')
                self.debugger.reset()
                self.enable_debugger = False

        sys.settrace(None)
        self.lastUpdate = None
        self.waiting = False
        self.silent = False
        if not self.more and history:
            self.addHistory(cmd_raw)
        if not silent:
            self.prompt()
        self.running = False

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
            # no need to go to the end position
            #endpos = self.GetTextLength()
            #self.GotoPos(endpos)
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
                keys = ['if', 'else', 'elif', 'for', 'while', 'def', 'class',
                        'try', 'except', 'finally']
                if pstrip[-1] == ':' and first_word in keys:
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
            dp.send('Shell.calltip', sender=self, calltip=tip)
        if not self.autoCallTip and not forceCallTip:
            return
        startpos = self.GetCurrentPos()
        if argspec and insertcalltip and self.callTipInsert:
            self.write(argspec + ')')
            endpos = self.GetCurrentPos()
            self.SetSelection(startpos, endpos)
        if argspec:
            tippos = startpos
            fallback = startpos - self.GetColumn(startpos)
            # In case there isn't enough room, only go back to the
            # fallback.
            tippos = max(tippos, fallback)
            self.CallTipShow(tippos, argspec)

    def debugPrompt(self, ismore=False, iserr=False):
        """show the debug prompt"""
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        self.GotoPos(endpos)
        self.more = ismore
        # skip the uncessary prompt, it is not ideal and will eat the typed
        # commands
        if self.GetCurLine()[0] == "K>> ":
            return
        autoIndent = self.autoIndent
        if self.more:
            self.autoIndent = True
        self.prompt()
        self.autoIndent = autoIndent
        return

    def processLine(self):
        """Process the line of text at which the user hit Enter."""

        # The user hit ENTER and we need to decide what to do. They
        # could be sitting on any line in the shell.

        thepos = self.GetCurrentPos()
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        ps2 = str(sys.ps2)
        # If they hit RETURN inside the current command, execute the
        # command.
        if self.CanEdit():
            execute = self.GetCurrentLine() == self.LineFromPosition(endpos)
            if self.more and not execute:
                # if the interpreter needs more code and the current position
                # is not on last line, insert a line after current position to
                # allow the user inputs more code
                self.prompt()
                return
            self.SetCurrentPos(endpos)
            self.interp.more = False
            command = self.GetTextRange(startpos, endpos)
            lines = command.split(os.linesep + ps2)
            lines = [line.rstrip() for line in lines]
            command = '\n'.join(lines)
            if self.reader.isreading:
                if not command:
                    # Match the behavior of the standard Python shell
                    # when the user hits return without entering a
                    # value.
                    command = '\n'
                self.reader.input = command
                self.write(os.linesep)
            else:
                self.push(command)
                wx.CallAfter(self.EnsureCaretVisible)
        # Or replace the current command with the other command.
        else:
            # If the line contains a command (even an invalid one).
            if self.getCommand(rstrip=False):
                command = self.getMultilineCommand()
                self.clearCommand()
                self.write(command)
            # Otherwise, put the cursor back where we started.
            else:
                self.SetCurrentPos(thepos)
                self.SetAnchor(thepos)
    @classmethod
    def Initialize(cls, frame, **kwargs):
        cls.frame = frame
        dp.connect(receiver=cls.Uninitialize, signal='frame.exit')
        ns = {}
        ns['wx'] = wx
        ns['app'] = wx.GetApp()
        ns['frame'] = cls.frame
        intro = 'Welcome To bsmedit ' + BSM_VERSION
        cls.panelShell = Shell(cls.frame, 1, introText=intro, locals=ns)
        active = kwargs.get('active', True)
        direction = kwargs.get('direction', 'top')
        dp.send(signal="frame.add_panel", panel=cls.panelShell, active=active,
                title="Shell", showhidemenu="View:Panels:Console",
                direction=direction)

    @classmethod
    def Uninitialize(cls):
        if cls.panelShell:
            dp.send('frame.delete_panel', panel=cls.panelShell)

def bsm_initialize(frame, **kwargs):
    Shell.Initialize(frame, **kwargs)
