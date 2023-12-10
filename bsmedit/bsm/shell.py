import os
import sys
import re
import traceback
import time
import pydoc
import glob
import shlex
import six.moves.builtins as __builtin__
import six
import wx
import wx.py.shell as pyshell
import wx.py.dispatcher as dp
from wx import stc
from wx.py.pseudo import PseudoFile
from .debugger import EngineDebugger
from ..version import __version__
from .editor_base import EditorTheme, EditorFind
from .shell_base import magic, aliasDict, sx


# in linux, the multiprocessing/process.py/_bootstrap will call
# sys.stdin.close(), which is missing in wx.py.pseudo.PseudoFile
def PseudoFile_close(self):
    pass

PseudoFile.close = PseudoFile_close


def _help(command):
    try:
        if isinstance(command, str):
            print(pydoc.plain(pydoc.render_doc(command, "Help on %s")))
        else:
            print(command.__doc__)
    except:
        print(f'No help found on "{command}"')

def _doc(command):
    if isinstance(command, str):
        dp.send('help.show', command=command)
    else:
        _help(command)

@EditorFind
@EditorTheme
class Shell(pyshell.Shell):
    ID_COPY_PLUS = wx.NewIdRef()
    ID_PASTE_PLUS = wx.NewIdRef()
    ID_WRAP_MODE = wx.NewIdRef()

    def __init__(self,
                 parent,
                 id=-1,
                 pos=wx.DefaultPosition,
                 size=wx.DefaultSize,
                 style=wx.CLIP_CHILDREN,
                 introText='',
                 locals=None,
                 InterpClass=None,
                 startupScript=None,
                 execStartupScript=True,
                 *args,
                 **kwds):
        # variables used in push, which may be called by
        # wx.py.shell.Shell.__init__ when execStartupScript is True
        self.enable_debugger = False
        self.silent = True
        pyshell.Shell.__init__(self, parent, id, pos, size, style, introText,
                               locals, InterpClass, startupScript,
                               execStartupScript, useStockId=False, *args, **kwds)

        theme = 'solarized-dark'
        resp = dp.send('frame.get_config', group='shell', key='theme')
        if resp and resp[0][1] is not None:
            theme = resp[0][1]
        self.SetupColor(theme)
        c = self.GetThemeColor()
        self.SetCaretForeground(c['emphasized'])
        self.SetCaretStyle(wx.stc.STC_CARETSTYLE_BLOCK)
        # the default sx function (!cmd to run external command) does not work
        # on windows
        __builtin__.sx = sx
        self.callTipInsert = False
        self.searchHistory = True
        self.silent = False
        self.autoIndent = True
        self.running = False
        self.debugger = EngineDebugger(pyshell.USE_MAGIC)
        self.LoadHistory()
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(stc.EVT_STC_DO_DROP, self.OnDoDrop)
        self.Bind(stc.EVT_STC_START_DRAG, self.OnStartDrag)
        self.Bind(wx.EVT_MENU, self.OnWrapMode, self.ID_WRAP_MODE)

        self.interp.locals['clear'] = self.clear
        self.interp.locals['help'] = _help
        self.interp.locals['doc'] = _doc
        self.interp.locals['on'] = True
        self.interp.locals['off'] = False
        dp.connect(self.writeOut, 'shell.write_out')
        dp.connect(self.runCommand, 'shell.run')
        dp.connect(self.debugPrompt, 'shell.prompt')
        dp.connect(self.addHistory, 'shell.add_to_history')
        dp.connect(self.clearHistory, 'shell.clear_history')
        dp.connect(self.deleteHistory, 'shell.delete_history')
        dp.connect(self.IsDebuggerOn, 'debugger.debugging')
        dp.connect(self.getAutoCompleteList, 'shell.auto_complete_list')
        dp.connect(self.getAutoCompleteKeys, 'shell.auto_complete_keys')
        dp.connect(self.getAutoCallTip, 'shell.auto_call_tip')
        dp.connect(self.OnActivatePanel, 'frame.activate_panel')
        dp.connect(self.OnActivate, 'frame.activate')
        dp.connect(self.OnFrameClosing, 'frame.closing')

        self.CmdKeyAssign(ord('Z'), wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_UNDO)
        self.CmdKeyAssign(ord('Z'), wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_REDO)

        self.CmdKeyAssign(ord('E'), wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_LINEEND)
        self.CmdKeyAssign(ord('A'), wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_VCHOME)
        if wx.Platform == '__WXMAC__':
            # ctrl+E/A on macOS
            self.CmdKeyAssign(ord('E'), wx.stc.STC_SCMOD_META, wx.stc.STC_CMD_LINEEND)
            self.CmdKeyAssign(ord('A'), wx.stc.STC_SCMOD_META, wx.stc.STC_CMD_VCHOME)

        self.Bind(wx.EVT_UPDATE_UI, lambda evt: evt.Enable(True), id=self.ID_CLEAR)
        self.Bind(wx.EVT_MENU, lambda evt: self.clear(), id=self.ID_CLEAR)

        # find dialog
        self.SetupFind()
        # disable replace
        self.findDialogStyle = 0

        eid_ctl_c = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self.OnCtrlC, id=eid_ctl_c)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL, ord('F'), self.ID_FIND_REPLACE),
                                         (wx.ACCEL_RAW_CTRL, ord('C'), eid_ctl_c)])
        self.SetAcceleratorTable(accel_tbl)

        self.LoadConfig()
    def SetConfig(self):
        dp.send('frame.set_config', group='shell', wrap=self.GetWrapMode() != wx.stc.STC_WRAP_NONE)

    def LoadConfig(self):
        resp = dp.send('frame.get_config', group='shell', key='wrap')
        if resp and resp[0][1] is not None:
            if resp[0][1]:
                self.SetWrapMode(wx.stc.STC_WRAP_WORD)
            else:
                self.SetWrapMode(wx.stc.STC_WRAP_NONE)
    def clear(self):
        super().clear()
        self.prompt()

    def OnCtrlC(self, event):
        if self.CanCopy():
            self.Copy()
        else:
            self.interp.more = False
            endpos = self.GetTextLength()
            self.GotoPos(endpos)
            self.push('', history=False)

    def Destroy(self):
        self.debugger.release()
        # save command history
        dp.send('frame.set_config', group='shell', history=self.history)
        dp.send('frame.set_config', group='shell', alias=aliasDict)
        dp.send('frame.set_config', group='shell', zoom=self.GetZoom())

        dp.disconnect(self.writeOut, 'shell.write_out')
        dp.disconnect(self.runCommand, 'shell.run')
        dp.disconnect(self.debugPrompt, 'shell.prompt')
        dp.disconnect(self.addHistory, 'shell.add_to_history')
        dp.disconnect(self.IsDebuggerOn, 'debugger.debugging')
        dp.disconnect(self.getAutoCompleteList, 'shell.auto_complete_list')
        dp.disconnect(self.getAutoCompleteKeys, 'shell.auto_complete_keys')
        dp.disconnect(self.getAutoCallTip, 'shell.auto_call_tip')
        dp.disconnect(self.OnActivatePanel, 'frame.activate_panel')
        dp.disconnect(self.OnActivate, 'frame.activate')
        dp.disconnect(self.OnFrameClosing, 'frame.closing')
        super().Destroy()

    def OnFrameClosing(self, event):
        """the frame is exiting"""
        if self.IsDebuggerOn() and event.CanVeto():
            # stop closing if the debugger is running, otherwise it may crash
            # as some events (e.g., ID_DEBUG_SCRIPT in editor) may be
            # called after some window (e.g., editor) has been destroyed.
            msg = 'The debugger is running.\n Turn it off first!'
            dlg = wx.MessageDialog(self.GetTopLevelParent(), msg, 'bsmedit',
                                   wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            event.Veto()

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

    def Paste(self):
        """Replace selection with clipboard contents."""
        if self.CanPaste() and wx.TheClipboard.Open():
            ps2 = str(sys.ps2)
            # on mac 11.4, it always return false
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)) or\
               wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    self.ReplaceSelection('')
                    command = data.GetText()
                    command = command.rstrip()
                    command = self.fixLineEndings(command)
                    command = self.lstripPrompt(text=command)
                    command = command.replace(os.linesep + ps2, '\n')
                    command = command.replace(os.linesep, '\n')
                    command = command.replace('\n', os.linesep + ps2)
                    self.write(command)
            wx.TheClipboard.Close()

    def PasteAndRun(self):
        """Replace selection with clipboard contents, run commands."""
        text = ''
        if wx.TheClipboard.Open():
            if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_TEXT)) or\
               wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_UNICODETEXT)):
                data = wx.TextDataObject()
                if wx.TheClipboard.GetData(data):
                    text = data.GetText()
            wx.TheClipboard.Close()
        if text:
            self.Execute(text)

    def getAutoCompleteKeys(self):
        return self.interp.getAutoCompleteKeys()

    def getAutoCompleteList(self, command, *args, **kwds):
        # remove additional key from wx.py.dispatcher.send
        kwds.pop('sender', None)
        kwds.pop('signal', None)
        try:
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        cmp = self.interp.getAutoCompleteList(command, *args, **kwds)
        part = command[command.rfind('.') + 1:]
        if part:
            part = part.lower()
            cmp = [c for c in cmp if c.lower().startswith(part)]
        return cmp

    def getPathList(self, path=None, prefix='', files=True, folders=True):
        paths = []
        if path is None:
            path = os.getcwd()
        def _getPathList(pattern):
            # get folders or files
            f = glob.glob(pattern)
            # remove common "path"
            f = [os.path.relpath(folder, path) for folder in f]
            # check if start with prefix
            f = [folder for folder in f if folder.lower().startswith(prefix.lower())]
            # replace ' ' with '\ ' or put the path in quotes to indicate it is a
            # space in path not in command
            if wx.Platform == '__WXMSW__':
                f = [ f'"{p}"' if ' ' in p else p for p in f]
            else:
                f = [p.replace(' ', r'\ ') for p in f]
            return f

        if folders:
            f = _getPathList(os.path.join(path, '*/'))
            f = [folder + '/' for folder in f]
            paths += sorted(f, key=str.casefold)
        if files:
            f = _getPathList(os.path.join(path, '*.*'))
            paths += sorted(f, key=str.casefold)

        return paths

    def getAutoCallTip(self, command, *args, **kwds):
        # remove additional key from wx.py.dispatcher.send
        kwds.pop('sender', None)
        kwds.pop('signal', None)
        return self.interp.getCallTip(command, *args, **kwds)

    def autoCompleteShow(self, command, offset=0):
        try:
            command = command.strip()
            # deal with the case "fun(arg.", which will return "arg."
            for i in range(len(command)):
                c = command[-i - 1]
                if not (c.isalnum() or c in ('_', '.')):
                    command = command[-i:]
                    break
            cmd = wx.py.introspect.getRoot(command, '.')
            self.evaluate(cmd)
        except:
            pass
        super().autoCompleteShow(command, offset)

    def IsDebuggerOn(self):
        """check if the debugger is on"""
        if not self.debugger:
            return False
        return self.enable_debugger

    def IsDebuggerPaused(self):
        return self.IsDebuggerOn() and self.debugger._paused

    def SetSelection(self, from_, to_):
        self.SetSelectionStart(from_)
        self.SetSelectionEnd(to_)
        if to_ < from_:
            self.SetAnchor(from_)

    def LoadHistory(self):
        self.clearHistory()
        resp = dp.send('frame.get_config', group='shell', key='history')
        if resp and resp[0][1]:
            self.history = resp[0][1]
        resp = dp.send('frame.get_config', group='shell', key='alias')
        if resp and resp[0][1]:
            aliasDict.update(resp[0][1])
        resp = dp.send('frame.get_config', group='shell', key='zoom')
        if resp and resp[0][1]:
            try:
                self.SetZoom(int(resp[0][1]))
            except:
                pass

    def OnKillFocus(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        if self.AutoCompActive():
            self.AutoCompCancel()
        event.Skip()

    def OnActivate(self, activate):
        # not work on mac
        if wx.Platform == '__WXMAC__':
            return

        if self.AutoCompActive():
            self.AutoCompCancel()

    def OnActivatePanel(self, pane):
        if pane != self:
            if self.AutoCompActive():
                self.AutoCompCancel()

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
        super().OnUpdateUI(event)

    def UpdateCaretPos(self):
        # when editing the command, do not allow moving the caret to
        # readonly area
        if not self.CanEdit() and \
                (self.GetCurrentLine() == self.LineFromPosition(self.promptPosEnd)):
            self.GotoPos(self.promptPosEnd)

    def GetContextMenu(self):
        menu = super().GetContextMenu()
        menu.AppendSeparator()
        menu.AppendCheckItem(self.ID_WRAP_MODE, 'Word wrap')
        menu.Check(self.ID_WRAP_MODE, self.GetWrapMode() != wx.stc.STC_WRAP_NONE)
        return menu

    def OnWrapMode(self, event):
        if self.GetWrapMode() == wx.stc.STC_WRAP_NONE:
            self.SetWrapMode(wx.stc.STC_WRAP_WORD)
        else:
            self.SetWrapMode(wx.stc.STC_WRAP_NONE)
        self.SetConfig()

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
        elif canEdit and not self.more and (
                not shiftDown) and key == wx.WXK_DOWN:
            # Replace with the next command from the history buffer.
            self.GoToHistory(False)
        elif canEdit and (not shiftDown) and key == wx.WXK_TAB:
            # show auto-complete list with TAB
            # first try to get the autocompletelist from the package
            cmd = self.getCommandLeft(rstrip=False)
            k = self.getAutoCompleteList(cmd)
            lengthEntered = 0
            if k:
                lengthEntered = len(cmd[cmd.rfind('.') + 1:])
            sep = ' '
            if not k:
                # check path
                # use shlex.split to handle cases like:
                # '!ls /Users/my\ folder'
                try:
                    cmds = shlex.split(cmd)
                    cmd_main = cmds[0]
                    prefix = cmds[-1] if len(cmds) > 1 else ''
                    path, prefix = os.path.split(prefix)
                    if cmd_main in ['cd', '!cd', '!rmdir', '!mkdir']:
                        k = self.getPathList(path=path, prefix=prefix, files=False)
                    elif cmd_main in ['ls', '!ls', '!less', '!more', '!cp', '!mv',\
                                      '!rm', '!gvim']:
                        k = self.getPathList(path=path, prefix=prefix)
                    lengthEntered = len(prefix)
                    if ' ' in prefix:
                        if wx.Platform == '__WXMSW__':
                            lengthEntered += 2
                        else:
                            lengthEntered += prefix.count(' ')
                    # use a character that will not appear in path
                    if k:
                        sep = '`'
                except:
                    pass

            # if failed, search the locals()
            if not k and cmd:
                for i in six.moves.range(len(cmd) - 1, -1, -1):
                    if cmd[i].isalnum() or cmd[i] == '_':
                        continue
                    if cmd[i] in ['.']:
                        # invalid
                        cmd = ''
                        break
                    cmd = cmd[i + 1:]
                    break
                if cmd:
                    k = six.iterkeys(self.interp.locals)
                    k = [s for s in k if s.startswith(cmd)]
                    k.sort()

            if k:
                self.AutoCompSetSeparator(ord(sep))
                self.AutoCompSetAutoHide(self.autoCompleteAutoHide)
                self.AutoCompSetIgnoreCase(self.autoCompleteCaseInsensitive)
                options = sep.join(k)
                lengthEntered = len(cmd) if all(item.lower().startswith(cmd.lower()) for item in k) else lengthEntered
                self.AutoCompShow(lengthEntered, options)
                self.AutoCompSetSeparator(ord(' '))
            return
        else:
            self.searchHistory = True
            # Reset the history position.
            self.historyIndex = -1
            super().OnKeyDown(event)

    def getCommandLeft(self, rstrip=True):
        # get the command up to the cursor
        startpos = self.promptPosEnd
        endpos = self.GetCurrentPos()
        command = self.GetTextRange(startpos, endpos)
        if rstrip:
            command = command.rstrip()
        return command

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
            dp.send('frame.file_drop',
                    filename=path,
                    activated=True,
                    lineno=linenum)
        event.Skip()

    def GoToHistory(self, up=True):
        """Search up the history buffer for the text in front of the cursor."""
        if not self.CanEdit():
            return
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        fullText = self.GetTextRange(startpos, endpos)
        startpos = self.GetCurrentPos()
        # The text up to the cursor is what we search for.
        numCharsAfterCursor = self.GetTextLength() - startpos
        searchText = fullText
        if numCharsAfterCursor > 0:
            searchText = searchText[:-numCharsAfterCursor]
        if not searchText or not self.searchHistory:
            self.OnHistoryReplace(step=up * 2 - 1)
            self.searchHistory = False
            return
        # Search upwards from the current history position and loop
        # back to the beginning if we don't find anything.
        if up:
            searchOrder = six.moves.range(self.historyIndex + 1,
                                          len(self.history))
        else:
            searchOrder = six.moves.range(self.historyIndex - 1, -1, -1)
        for i in searchOrder:
            command = self.history[i]
            if command[:len(searchText)] == searchText and fullText != command:
                # ignore the exact same command
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
        try:
            if not self.silent:
                # not use wx.CallAfter in this function, otherwise it may
                # crash when close the app (e.g., shell is destroyed when
                # wx.CallAfter function is called
                self.AutoCompCancel()
                # move the cursor to the end to protect the readonly section
                endpos = self.GetTextLength()
                # remember the current position (relative to end)
                offset = endpos - self.GetCurrentPos()
                if not self.CanEdit():
                    self.SetCurrentPos(endpos)
                if not self.waiting:# or self.IsDebuggerPaused():
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
                # move the caret to the previous position
                self.GotoPos(self.GetTextLength()-offset)
                self.Update()
            else:
                if self.stdout:
                    print(text, file=self.stdout)
                #for line in traceback.format_stack():
                #    print(line.strip(), file=self.stdout)
        except:
            if self.stdout:
                print(text, file=self.stdout)
            traceback.print_exc(file=self.stdout)

    def writeErr(self, text):
        """Replacement for stderror"""
        self.writeOut(text)

    def addHistory(self, command):
        # override the parent function to add time-stamp.
        stamp = time.strftime('#bsm#%Y/%m/%d')
        if stamp not in self.history:
            self.history.insert(0, stamp)
        super().addHistory(command)

    def deleteHistory(self, command, timestamp="", index=-1):
        for i in six.moves.range(len(self.history) - 1, -1, -1):
            if self.history[i] == timestamp:
                if command == timestamp:
                    # delete folder
                    m = 1
                    while(i-m>=0 and not self.history[i-m].startswith('#bsm#')):
                        m += 1
                    del self.history[i-m+1:i]
                    break
                else:
                    idx = i-index-1
                    if idx>=0 and self.history[idx] == command:
                        del self.history[idx]
                    break

    def runCommand(self,
                   command,
                   prompt=True,
                   verbose=True,
                   debug=False,
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

    def push_multiple_line(self, command, silent=False, history=True):
        commands = command.splitlines(keepends=False)
        if command.endswith('\n'):
            # keep the newline at the end, so an empty line will finish
            # the statement
            commands.append('')
        if not commands:
            # run the empty command (e.g., to start the prompt in a new line)
            commands = ['']

        # run the command line by line
        cmd_raw = []
        for idx, cmd in enumerate(commands):
            if idx != len(commands) -1 and not cmd and cmd_raw:
                p = cmd_raw[-1]
                cmd = p[:len(p) - len(p.lstrip())]
            cmd_raw.append(cmd)
            if pyshell.USE_MAGIC:
                cmd = magic(cmd)
            if len(cmd) > 1 and cmd[-1] == ';':
                self.silent = True
            self.waiting = True
            self.lastUpdate = None
            try:
                if self.enable_debugger:
                    self.debugger.reset()
                    sys.settrace(self.debugger)
                self.more = self.interp.push(cmd)
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
                # finished a statement, add it to history
                self.addHistory('\n'.join(cmd_raw))
                cmd_raw = []
        if not silent:
            self.prompt()

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
        self.push_multiple_line(command, silent=silent, history=history)
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
                keys = [
                    'if', 'else', 'elif', 'for', 'while', 'def', 'class',
                    'try', 'except', 'finally'
                ]
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
                wx.CallAfter(self.SetFocus)
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

    def setStyles(self, faces):
        super().setStyles(faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
                          'fore:#3C3C43,back:#F2F2F7')

    def OnStartDrag(self, event):
        event.SetText('')

    def OnDoDrop(self, event):
        allow = self.CanEdit() and (event.GetPosition() >= self.promptPosEnd)
        if allow:
            self.InsertText(event.GetPosition(), event.GetText())
        event.SetText('')

    @classmethod
    def Initialize(cls, frame, **kwargs):
        cls.frame = frame
        dp.connect(receiver=cls.initialized, signal='frame.initialized')
        dp.connect(receiver=cls.Uninitialize, signal='frame.exit')
        cls.debug = kwargs.get('debug', False)
        ns = {}
        ns['wx'] = wx
        ns['app'] = wx.GetApp()
        ns['frame'] = cls.frame
        intro = 'Welcome To bsmedit ' + __version__
        cls.panelShell = Shell(cls.frame, introText=intro, locals=ns)
        active = kwargs.get('active', True)
        direction = kwargs.get('direction', 'top')
        dp.send(signal="frame.add_panel",
                panel=cls.panelShell,
                active=active,
                title="Shell",
                direction=direction)

    @classmethod
    def initialized(cls):
        if cls.panelShell and not cls.debug:
            # not redirect if in debug mode
            redirect = True
            resp = dp.send('frame.get_config', group='shell', key='redirect_stdout')
            if resp and resp[0][1] is not None:
                redirect = resp[0][1]
            cls.panelShell.redirectStdout(redirect)

            redirect = True
            resp = dp.send('frame.get_config', group='shell', key='redirect_stderr')
            if resp and resp[0][1] is not None:
                redirect = resp[0][1]
            cls.panelShell.redirectStderr(redirect)

    @classmethod
    def Uninitialize(cls):
        if cls.panelShell:
            cls.panelShell.redirectStdout(False)
            cls.panelShell.redirectStderr(False)
            dp.send('frame.delete_panel', panel=cls.panelShell)


def bsm_initialize(frame, **kwargs):
    Shell.Initialize(frame, **kwargs)
