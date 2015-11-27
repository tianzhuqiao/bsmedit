import os
import wx
import wx.stc as stc
from pyeditorxpm import *
import inspect

magic_format = False
try:
    from PythonTidy import tidy_up
    import traceback
    magic_format = True
except:
    pass

class PyEditor(wx.py.editwindow.EditWindow):
    ID_COMMENT = wx.NewId()
    ID_UNCOMMENT = wx.NewId()
    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.CLIP_CHILDREN | wx.BORDER_NONE):
        wx.py.editwindow.EditWindow.__init__(self, parent, id=id, pos=pos,
                size=size, style=style)
        self.SetUpEditor()
        self.callTipInsert = True
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.filename = """"""
        # Assign handlers for keyboard events.
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.autoCompleteKeys = [ord('.')]
        rsp = wx.py.dispatcher.send(signal = 'shell.auto_complete_keys')
        if rsp: self.autoCompleteKeys = rsp[0][1]
        self.breakpointlist = {}
        self.highlight_str = """"""
        stc.EVT_STC_MARGINCLICK(self, id, self.OnMarginClick)
        stc.EVT_STC_DOUBLECLICK(self, id, self.OnDoubleClick)
        # Assign handler for the context menu
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCommandUI)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_UNDO)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_REDO)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=wx.ID_SELECTALL)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_COMMENT)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent, id=self.ID_UNCOMMENT)

    def clear_breakpoint(self):
        for key in self.breakpointlist.keys():
            id = self.breakpointlist[key]['id']
            wx.py.dispatcher.send('debugger.clearbreakpoint', ids=[id])

    def SaveFile(self, filename, filetype=wx.TEXT_TYPE_ANY):
        rtn = wx.py.editwindow.EditWindow.SaveFile(self, filename, filetype)
        if rtn:
            fname = os.path.abspath(filename)
            fname = os.path.normcase(fname)
            self.filename = fname
        return rtn

    def LoadFile(self, filename, filetype=wx.TEXT_TYPE_ANY):
        rtn = wx.py.editwindow.EditWindow.LoadFile(self, filename, filetype)
        if rtn:
            fname = os.path.abspath(filename)
            fname = os.path.normcase(fname)
            self.filename = fname
        return rtn

    def OnKillFocus(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        if self.AutoCompActive():
            self.AutoCompCancel()
        event.Skip()

    def OnChar(self, event):
        """Keypress event handler.

        Only receives an event if OnKeyDown calls event.Skip() for the
        corresponding event."""
        key = event.GetKeyCode()
        currpos = self.GetCurrentPos()
        line = self.GetCurrentLine()
        stoppos = self.PositionFromLine(line)
        # Return (Enter) needs to be ignored in this handler.
        if key in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            pass
        elif key in self.autoCompleteKeys:
            # Usually the dot (period) key activates auto completion.
            # Get the command between the prompt and the cursor.  Add
            # the autocomplete character to the end of the command.
            if self.AutoCompActive():
                self.AutoCompCancel()
            command = self.GetTextRange(stoppos, currpos) + chr(key)
            self.AddText(chr(key))
            if self.autoComplete:
                self.autoCompleteShow(command)
        elif key == ord('('):
            # The left paren activates a call tip and cancels an
            # active auto completion.
            if self.AutoCompActive():
                self.AutoCompCancel()
            # Get the command between the prompt and the cursor.  Add
            # the '(' to the end of the command.
            self.ReplaceSelection("""""")
            command = self.GetTextRange(stoppos, currpos) + '('
            self.AddText('(')
            self.autoCallTipShow(command, self.GetCurrentPos()
                                 == self.GetTextLength())
        else:
            # Allow the normal event handling to take place.
            event.Skip()

    def OnKeyDown(self, event):
        """"""
        key = event.GetKeyCode()
        control = event.ControlDown()
        # shift=event.ShiftDown()
        alt = event.AltDown()
        if key == wx.WXK_RETURN and not control and not alt \
            and not self.AutoCompActive():
            # auto-indentation
            if self.CallTipActive():
                self.CallTipCancel()
                self.calltip = 0
            line = self.GetCurrentLine()
            txt = self.GetLine(line)
            pos = self.GetCurrentPos()
            linePos = self.PositionFromLine(line)
            self.CmdKeyExecute(stc.STC_CMD_NEWLINE)
            indent = self.GetLineIndentation(line)
            tabWidth = max(1, self.GetTabWidth())
            if self.GetUseTabs():
                indentation = '\t'
            else:
                indentation = ' ' * tabWidth
            padding = indentation * (indent / tabWidth)
            newpos = self.GetCurrentPos()
            # smart indentation
            stripped = txt[:pos - linePos].split('#')[0].strip()
            firstWord = stripped.split(' ')[0]
            if stripped and self.needsIndent(firstWord, lastChar=stripped[-1]):
                padding += indentation
            elif self.needsDedent(firstWord):
                padding = padding[:-tabWidth]
            self.InsertText(newpos, padding)
            newpos += len(padding)
            self.SetCurrentPos(newpos)
            self.SetSelection(newpos, newpos)
        else:
            event.Skip()

    def OnMarginClick(self, evt):
        margin = evt.GetMargin()
        ctrldown = evt.GetControl()
        # set/edit/delete a breakpoint
        if margin == 0 or margin == 1:
            lineClicked = self.LineFromPosition(evt.GetPosition())
            txt = self.GetLine(lineClicked)
            txt = txt.strip()
            if not txt or txt[0] == '#':
                return
            # check if a breakpoint marker is at this line
            bpset = self.MarkerGet(lineClicked) & 1
            bpdata = None
            resp = wx.py.dispatcher.send(signal = 'debugger.getbreakpoint', 
                   filename = self.filename, lineno = lineClicked + 1)
            if resp:
                bpdata = resp[0][1]
            if not bpdata:
                # No breakpoint at this line, add one
                # bpdata =  {id, filename, lineno, condition, ignore_count, trigger_count}
                bp = {'filename': self.filename, 'lineno': lineClicked + 1}
                wx.py.dispatcher.send('debugger.setbreakpoint',  bpdata=bp)
            else:
                if ctrldown:
                    condition = """"""
                    if bpdata['condition']:
                        condition = bpdata['condition']
                    dlg = wx.TextEntryDialog(self,
                            caption='Breakpoint Condition:',
                            message='Condition', defaultValue="""""",
                            style=wx.OK)
                    if dlg.ShowModal() == wx.ID_OK:
                        wx.py.dispatcher.send('debugger.editbreakpoint'
                                , id=bpdata['id'],
                                condition=dlg.GetValue())
                else:
                    wx.py.dispatcher.send('debugger.clearbreakpoint',
                            ids=[bpdata['id']])
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())
                if self.GetFoldLevel(lineClicked) \
                    & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def OnDoubleClick(self, event):
        str = self.GetSelectedText()
        self.highlight_str = str
        if self.highlight_str != """""":
            self.highlight_word(str)

    def OnLeftUp(self, event):
        str = self.GetSelectedText()
        if self.highlight_str != """""" and str != self.highlight_str:
            self.highlight_word(self.highlight_str, False)
            self.highlight_str = """"""
        event.Skip()

    def highlight_word(self, strWord, highlight=True):
        current = 0
        position = -1
        flag = stc.STC_FIND_WHOLEWORD | stc.STC_FIND_MATCHCASE
        style = 0
        if highlight:
            style = stc.STC_INDIC0_MASK
        else:
            self.StartStyling(0, stc.STC_INDICS_MASK)
            self.SetStyling(self.GetLength(), style)
            return
        while True:
            position = self.FindText(current, len(self.GetText()),
                    strWord, flag)
            current = position + len(strWord)
            if position == -1:
                break
            self.StartStyling(position, stc.STC_INDICS_MASK)
            self.SetStyling(len(strWord), style)

    def needsIndent(self, firstWord, lastChar):
        '''Tests if a line needs extra indenting, ie if, while, def, etc '''
        # remove trailing : on token
        if len(firstWord) > 0:
            if firstWord[-1] == ':':
                firstWord = firstWord[:-1]
        # control flow keywords
        if firstWord in [
            'for',
            'if',
            'else',
            'def',
            'class',
            'elif',
            'try',
            'except',
            'finally',
            'while',
            ] and lastChar == ':':
            return True
        else:
            return False

    def needsDedent(self, firstWord):
        '''Tests if a line needs extra dedenting, ie break, return, etc '''
        # control flow keywords
        if firstWord in ['break', 'return', 'continue', 'yield', 'raise'
                         ]:
            return True
        else:
            return False

    def autoCompleteShow(self, command, offset=0):
        """Display auto-completion popup list."""
        self.AutoCompSetAutoHide(self.autoCompleteAutoHide)
        self.AutoCompSetIgnoreCase(self.autoCompleteCaseInsensitive)

        list = []
        # retrieve the auto complete list from bsmshell
        response = wx.py.dispatcher.send(signal='shell.auto_complete_list',
                    command = command)
        if response:
            list = response[0][1]
        if list:
            options = ' '.join(list)
            self.AutoCompShow(offset, options)

    def autoCallTipShow(self, command, insertcalltip=True, forceCallTip=False):
        """Display argument spec and docstring in a popup window."""
        if self.CallTipActive():
            self.CallTipCancel()
        (name, argspec, tip) = (None, None, None)
        # retrieve the all tip from bsmshell
        response = wx.py.dispatcher.send(signal='shell.auto_call_tip',
                    command = command)
        if response:
            (name, argspec, tip) = response[0][1]
        if tip:
            wx.py.dispatcher.send(signal='Shell.calltip', sender=self,
                                  calltip=tip)
        if not self.autoCallTip and not forceCallTip:
            return
        startpos = self.GetCurrentPos()
        if argspec and insertcalltip and self.callTipInsert:
            self.AddText(argspec + ')')
            endpos = self.GetCurrentPos()
            self.SetSelection(startpos, endpos)

    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        if wx.USE_UNICODE:
            value = value.decode('iso8859_1')
        val = self.GetReadOnly()
        self.SetReadOnly(False)
        self.SetText(value)
        self.EmptyUndoBuffer()
        self.SetSavePoint()
        self.SetReadOnly(val)

    def SetEditable(self, val):
        self.SetReadOnly(not val)

    def IsModified(self):
        return self.GetModify()

    def Clear(self):
        self.ClearAll()

    def SetInsertionPoint(self, pos):
        self.SetCurrentPos(pos)
        self.SetAnchor(pos)

    def ShowPosition(self, pos):
        line = self.LineFromPosition(pos)
        self.GotoLine(line)

    def GetLastPosition(self):
        return self.GetLength()

    def GetPositionFromLine(self, line):
        return self.PositionFromLine(line)

    def GetRange(self, start, end):
        return self.GetTextRange(start, end)

    def GetSelection(self):
        return (self.GetAnchor(), self.GetCurrentPos())

    def SetSelection(self, start, end):
        self.SetSelectionStart(start)
        self.SetSelectionEnd(end)
        if end < start:
            self.SetAnchor(start)

    def SelectLine(self, line):
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        self.SetSelection(start, end)

    def update_status_text(self):
        caretPos = self.GetCurrentPos()
        col = self.GetColumn(caretPos) + 1
        line = self.LineFromPosition(caretPos) + 1
        wx.py.dispatcher.send(signal='frame.setstatustext', text='%d,%d'
                               % (line, col), index=1, width=40)

    def OnUpdateUI(self, event):
        wx.py.editwindow.EditWindow.OnUpdateUI(self, event)
        wx.CallAfter(self.update_status_text)

    def SetUpEditor(self):
        """
        This method carries out the work of setting up the demo editor.            
        It's seperate so as not to clutter up the init code.
        """
        # key binding
        self.CmdKeyAssign(ord('R'), stc.STC_SCMOD_CTRL,
                          stc.STC_CMD_REDO)
        import keyword
        self.SetLexer(stc.STC_LEX_PYTHON)
        keywords = keyword.kwlist
        keywords.extend(['None', 'as', 'True', 'False'])
        self.SetKeyWords(0, ' '.join(keywords))
        # Enable folding
        self.SetProperty('fold', '1')
        # Highlight tab/space mixing (shouldn't be any)
        self.SetProperty('tab.timmy.whinge.level', '1')
        # Set left and right margins
        self.SetMargins(2, 2)
        # Set up the numbers in the margin for margin #1
        self.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.SetMarginWidth(0, 40)
        # Indentation and tab stuff
        self.SetIndent(4)  # Proscribed indent size for wx
        self.SetIndentationGuides(True)  # Show indent guides
        self.SetBackSpaceUnIndents(True)  # Backspace unindents rather than delete 1 space
        self.SetTabIndents(True)  # Tab key indents
        self.SetTabWidth(4)  # Proscribed tab size for wx
        self.SetUseTabs(False)  # Use spaces rather than tabs, or
                                        # TabTimmy will complain!
        # White space
        self.SetViewWhiteSpace(False)  # Don't view white space
        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.
        self.SetEOLMode(stc.STC_EOL_LF)
        self.SetViewEOL(False)
        # No right-edge mode indicator
        self.SetEdgeMode(stc.STC_EDGE_NONE)
        # Margin #1 - breakpoint symbols
        self.SetMarginType(1, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(1, ~stc.STC_MASK_FOLDERS)  # do not show fold symbols
        self.SetMarginSensitive(1, True)
        self.SetMarginWidth(1, 12)
        # break point
        self.MarkerDefine(0, stc.STC_MARK_CIRCLE, 'BLACK', 'RED')
        # paused at marker
        self.MarkerDefine(1, stc.STC_MARK_SHORTARROW, 'BLACK', 'GREEN')
        self.MarkerDefine(2, stc.STC_MARK_SHORTARROW, 'BLACK', 'WHITE')

        # Setup a margin to hold fold markers
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)
        # and now set up the fold markers
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                          stc.STC_MARK_BOXPLUSCONNECTED, 'white',
                          'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                          stc.STC_MARK_BOXMINUSCONNECTED, 'white',
                          'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL,
                          stc.STC_MARK_TCORNER, 'white', 'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,
                          stc.STC_MARK_LCORNER, 'white', 'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,
                          stc.STC_MARK_VLINE, 'white', 'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS,
                          'white', 'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,
                          stc.STC_MARK_BOXMINUS, 'white', 'black')
        # Global default style
        if wx.Platform == '__WXMSW__':
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              'fore:#000000,back:#FFFFFF,face:Courier New'
                              )
        elif wx.Platform == '__WXMAC__':
            # TODO: if this looks fine on Linux too, remove the Mac-specific case
            # and use this whenever OS != MSW.
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              'fore:#000000,back:#FFFFFF,face:Monaco')
        else:
            defsize = \
                wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              'fore:#000000,back:#FFFFFF,face:Courier,size:%d'
                               % defsize)
        # Clear styles and revert to default.
        self.StyleClearAll()
        # Following style specs only indicate differences from default.
        # The rest remains unchanged.
        # Line numbers in margin
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,
                          'fore:#000000,back:#99A9C2')
        # Highlighted brace
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,
                          'fore:#00009D,back:#FFFF00')
        # Unmatched brace
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,
                          'fore:#00009D,back:#FF0000')
        # Indentation guide
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#CDCDCD')
        # Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, 'fore:#000000')
        # Comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE,
                          'fore:#008000,back:#F0FFF0')
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK,
                          'fore:#008000,back:#F0FFF0')
        # Numbers
        self.StyleSetSpec(stc.STC_P_NUMBER, 'fore:#008080')
        # Strings and characters
        self.StyleSetSpec(stc.STC_P_STRING, 'fore:#800080')
        self.StyleSetSpec(stc.STC_P_CHARACTER, 'fore:#800080')
        # Keywords
        self.StyleSetSpec(stc.STC_P_WORD, 'fore:#000080,bold')
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE,
                          'fore:#800080,back:#FFFFEA')
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE,
                          'fore:#800080,back:#FFFFEA')
        # Class names
        self.StyleSetSpec(stc.STC_P_CLASSNAME, 'fore:#0000FF,bold')
        # Function names
        self.StyleSetSpec(stc.STC_P_DEFNAME, 'fore:#008080,bold')
        # Operators
        self.StyleSetSpec(stc.STC_P_OPERATOR, 'fore:#800000,bold')
        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#000000')
        # Caret color
        self.SetCaretForeground('BLUE')
        # Selection background
        self.SetSelBackground(1, '#66CCFF')
        self.SetSelBackground(True,
                              wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.SetSelForeground(True,
                              wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        self.SetWrapMode(stc.STC_WRAP_WORD)
        # indicator
        self.IndicatorSetStyle(0, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(0, wx.RED)

    def RegisterModifiedEvent(self, eventHandler):
        self.Bind(stc.EVT_STC_CHANGE, eventHandler)

    def prepandText(self, text):
        """Comment section"""
        doc = self
        sel = doc.GetSelection()
        start = doc.LineFromPosition(sel[0])
        end = doc.LineFromPosition(sel[1])
        end_pos = sel[1]
        if start > end:
            (start, end) = (end, start)
            end_pos = sel[0]
        if end > start and doc.GetColumn(end_pos) == 0:
            end = end - 1
        doc.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = doc.PositionFromLine(lineNumber)
            doc.InsertText(firstChar, text)
        doc.SetCurrentPos(doc.PositionFromLine(start))
        doc.SetAnchor(doc.GetLineEndPosition(end))
        doc.EndUndoAction()
        doc.Refresh()

    def deprepandText(self, text):
        """Uncomment section"""
        doc = self
        sel = doc.GetSelection()
        start = doc.LineFromPosition(sel[0])
        end = doc.LineFromPosition(sel[1])
        end_pos = sel[1]
        if start > end:
            (start, end) = (end, start)
            end_pos = sel[0]
        if end > start and doc.GetColumn(end_pos) == 0:
            end = end - 1
        doc.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = doc.PositionFromLine(lineNumber)
            if doc.GetTextRange(firstChar, firstChar + len(text)) \
                == text:
                doc.SetCurrentPos(firstChar + len(text))
                doc.DelLineLeft()
        doc.SetSelection(sel[0], doc.PositionFromLine(end + 1))
        doc.SetCurrentPos(doc.PositionFromLine(start))
        doc.EndUndoAction()
        doc.Refresh()

    def indented(self):
        tabWidth = max(1, self.GetTabWidth())
        if self.GetUseTabs():
            indentation = '\t'
        else:
            indentation = ' ' * tabWidth
        self.prepandText(indentation)

    def unindented(self):
        tabWidth = max(1, self.GetTabWidth())
        if self.GetUseTabs():
            indentation = '\t'
        else:
            indentation = ' ' * tabWidth
        self.deprepandText(indentation)

    def comment(self):
        """Comment section"""
        doc = self
        sel = doc.GetSelection()
        start = doc.LineFromPosition(sel[0])
        end = doc.LineFromPosition(sel[1])
        end_pos = sel[1]
        if start > end:
            (start, end) = (end, start)
            end_pos = sel[0]
        if end > start and doc.GetColumn(end_pos) == 0:
            end = end - 1
        doc.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = doc.PositionFromLine(lineNumber)
            doc.InsertText(firstChar, '##')
        doc.SetCurrentPos(doc.PositionFromLine(start))
        doc.SetAnchor(doc.GetLineEndPosition(end))
        doc.EndUndoAction()

    def uncomment(self):
        """Uncomment section"""
        doc = self
        sel = doc.GetSelection()
        start = doc.LineFromPosition(sel[0])
        end = doc.LineFromPosition(sel[1])
        end_pos = sel[1]
        if start > end:
            (start, end) = (end, start)
            end_pos = sel[0]
        if end > start and doc.GetColumn(end_pos) == 0:
            end = end - 1
        doc.BeginUndoAction()
        for lineNumber in range(start, end + 1):
            firstChar = doc.PositionFromLine(lineNumber)
            if chr(doc.GetCharAt(firstChar)) == '#':
                if chr(doc.GetCharAt(firstChar + 1)) == '#':
                    # line starts with ##
                    doc.SetCurrentPos(firstChar + 2)
                else:
                    # line starts with #
                    doc.SetCurrentPos(firstChar + 1)
                doc.DelLineLeft()
        doc.SetSelection(sel[0], doc.PositionFromLine(end + 1))
        doc.SetCurrentPos(doc.PositionFromLine(start))
        doc.EndUndoAction()

    def GetContextMenu(self):
        """
            Create and return a context menu for the shell.
            This is used instead of the scintilla default menu
            in order to correctly respect our immutable buffer.
        """
        menu = wx.Menu()
        menu.Append(wx.ID_UNDO, 'Undo')
        menu.Append(wx.ID_REDO, 'Redo')
        menu.AppendSeparator()
        menu.Append(wx.ID_CUT, 'Cut')
        menu.Append(wx.ID_COPY, 'Copy')
        menu.Append(wx.ID_PASTE, 'Paste')
        menu.Append(wx.ID_CLEAR, 'Clear')
        menu.AppendSeparator()
        menu.Append(wx.ID_SELECTALL, 'Select All')
        menu.AppendSeparator()
        menu.Append(self.ID_COMMENT, 'Comment')
        menu.Append(self.ID_UNCOMMENT, 'Uncomment')
        return menu

    def OnContextMenu(self, evt):
        p = self.ScreenToClient(evt.GetPosition())
        m = self.GetMarginWidth(0) + self.GetMarginWidth(1)
        print p.x, m
        menu = self.GetContextMenu()
        self.PopupMenu(menu)

    def OnUpdateCommandUI(self, evt):
        id = evt.Id
        if id in (wx.ID_CUT, wx.ID_CLEAR):
            evt.Enable(self.GetSelectionStart()
                       != self.GetSelectionEnd())
        elif id == wx.ID_COPY:
            evt.Enable(self.GetSelectionStart()
                       != self.GetSelectionEnd())
        elif id == wx.ID_PASTE:
            evt.Enable(self.CanPaste())
        elif id == wx.ID_UNDO:
            evt.Enable(self.CanUndo())
        elif id == wx.ID_REDO:
            evt.Enable(self.CanRedo())
        else:
            evt.Skip()

    def OnProcessEvent(self, evt):
        id = evt.GetId()
        if id == wx.ID_CUT:
            self.Cut()
        elif id == wx.ID_CLEAR:
            self.Clear()
        elif id == wx.ID_COPY:
            self.Copy()
        elif id == wx.ID_PASTE:
            self.Paste()
        elif id == wx.ID_UNDO:
            self.Undo()
        elif id == wx.ID_REDO:
            self.Redo()
        elif id == wx.ID_SELECTALL:
            self.SelectAll()
        elif id == self.ID_COMMENT:
            self.comment()
        elif id == self.ID_UNCOMMENT:
            self.uncomment()

class PyEditorPanel(wx.Panel):
    Gce = []
    ID_RUN_SCRIPT = wx.NewId()
    ID_DEBUG_SCRIPT = wx.NewId()
    ID_FIND_REPLACE = wx.NewId()
    ID_IMPORT_SCRIPT = wx.NewId()
    ID_CHECK_SCRIPT = wx.NewId()
    ID_RUN_LINE = wx.NewId()
    ID_FIND_NEXT = wx.NewId()
    ID_FIND_PREV = wx.NewId()
    ID_INDENT = wx.NewId()
    ID_UNINDENT = wx.NewId()
    ID_SETCURFOLDER = wx.NewId()
    ID_TIDY_SOURCE = wx.NewId()
    ID_SPLIT_VERT = wx.NewId()
    ID_SPLIT_HORZ = wx.NewId()
    ID_DBG_RUN = wx.NewId()
    ID_DBG_STOP = wx.NewId()
    ID_DBG_STEP = wx.NewId()
    ID_DBG_STEP_INTO = wx.NewId()
    ID_DBG_STEP_OUT = wx.NewId()
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=(1, 1))
        self.__findReplaceEvents__()
        self.fileName = """"""
        self.splitter = wx.SplitterWindow(self, style = wx.SP_LIVE_UPDATE)
        self.editor = PyEditor(self.splitter)
        self.editor2 = None 
        self.splitter.Initialize(self.editor)
        self.editor.RegisterModifiedEvent(self.OnCodeModified)
        self.findDialog = None
        tbitems = (
                (wx.ID_OPEN,'Open', open_xpm, 'Open Python script'),
                (wx.ID_SAVE,'Save', save_xpm, 'Save current document (Ctrl+S)'),
                (wx.ID_SAVEAS, 'Save As', page_save_xpm, 'Save current document as'),
                (None, None, None, None),
                (self.ID_FIND_REPLACE, u'Find', find_xpm, 'Find/Replace (Ctrl+F)'),
                (None, None, None, None),
                (self.ID_INDENT, 'Increase Indent', text_indent_xpm, 'Increase the indent'),
                (self.ID_UNINDENT, 'Decrease Indent', text_indent_remove_xpm, 'Decrease the indent'),
                (None, None, None, None),
                (self.ID_RUN_LINE, 'Run', tab_go_xpm, 'Run the current line or selection (Ctrl+Return)'),
                (self.ID_RUN_SCRIPT, 'Execute', page_go_xpm, 'Execute the whole script'),
                (None, None, None, None),
                (self.ID_CHECK_SCRIPT, 'Check', tick_xpm, 'Check the module'),
                (self.ID_DEBUG_SCRIPT, 'Debug', bug__arrow_xpm, 'Debug the script'),
                (None, None, None, None),
                (self.ID_SETCURFOLDER, 'Set current folder', folder_key_xpm, 'Set the file folder as current folder'),
                (None, None, None, None),
                (self.ID_SPLIT_VERT, 'Split Vert', application_tile_vertical_xpm, 'Split the window vertically'),
                (self.ID_SPLIT_HORZ, 'Split Horz', application_tile_horizontal_xpm, 'Split the window horizontally'),
                )
        self.tb = wx.ToolBar(self, wx.ID_ANY, wx.DefaultPosition,
                wx.DefaultSize, wx.TB_FLAT
                | wx.TB_HORIZONTAL)
        for (id, label, img_xpm, tooltip) in tbitems:
            if id == None:
                self.tb.AddSeparator()
                continue
            if label in ['Split Vert', 'Split Horz']:
                self.tb.AddCheckLabelTool(id , label, wx.BitmapFromXPMData(img_xpm), shortHelp = tooltip)
            else:
                self.tb.AddLabelTool(id, label, wx.BitmapFromXPMData(img_xpm), shortHelp = tooltip)
        self.tb.AddSeparator()
        self.m_cbWrapMode = wx.CheckBox(
            self.tb,
            wx.ID_ANY,
            u'Word Wrap',
            wx.DefaultPosition,
            wx.DefaultSize,
            0,
            )
        self.m_cbWrapMode.SetValue(True)
        self.tb.AddControl(self.m_cbWrapMode)
        if magic_format:
            self.tb.AddSeparator()
            self.tb.AddLabelTool(
                self.ID_TIDY_SOURCE,
                u'Format',
                wx.BitmapFromXPMData(wand_xpm),
                shortHelp = u'Format the source code',
                )

        self.tb.Realize()
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.splitter, 1, wx.EXPAND)
        self.box.Fit(self)
        self.SetSizer(self.box)
        # Connect Events
        self.Bind(wx.EVT_TOOL, self.OnPrint, id=wx.ID_PRINT)
        self.Bind(wx.EVT_TOOL, self.OnPageSetUp, id=wx.ID_PRINT_SETUP)
        self.Bind(wx.EVT_TOOL, self.OnBtnOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_TOOL, self.OnBtnSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_TOOL, self.OnBtnSaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn, id=wx.ID_SAVE)
        self.Bind(wx.EVT_TOOL, self.OnShowFindReplace, id=self.ID_FIND_REPLACE)
        self.Bind(wx.EVT_TOOL, self.OnBtnRun, id=self.ID_RUN_LINE)
        self.Bind(wx.EVT_TOOL, self.OnBtnCheck, id=self.ID_CHECK_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnRunScript, id=self.ID_RUN_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnDebugScript, id=self.ID_DEBUG_SCRIPT)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn, id=self.ID_DEBUG_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnImport, id=self.ID_IMPORT_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnFindNext, id=self.ID_FIND_NEXT)
        self.Bind(wx.EVT_TOOL, self.OnFindPrev, id=self.ID_FIND_PREV)
        self.Bind(wx.EVT_TOOL, self.OnIndent, id=self.ID_INDENT)
        self.Bind(wx.EVT_TOOL, self.OnUnindent, id=self.ID_UNINDENT)
        self.Bind(wx.EVT_TOOL, self.OnSetCurFolder, id=self.ID_SETCURFOLDER)
        self.Bind(wx.EVT_TOOL, self.OnTidySource, id=self.ID_TIDY_SOURCE)
        self.Bind(wx.EVT_TOOL, self.OnSplitVert, id=self.ID_SPLIT_VERT)
        self.Bind(wx.EVT_TOOL, self.OnSplitHorz, id=self.ID_SPLIT_HORZ)
        self.m_cbWrapMode.Bind(wx.EVT_CHECKBOX, self.OnWrap)
        self.accel = wx.AcceleratorTable([ 
            (wx.ACCEL_CTRL, ord('F'), self.ID_FIND_REPLACE),
            (wx.ACCEL_NORMAL, wx.WXK_F3, self.ID_FIND_NEXT),
            (wx.ACCEL_SHIFT, wx.WXK_F3, self.ID_FIND_PREV),
            (wx.ACCEL_CTRL, ord('H'), self.ID_FIND_REPLACE),
            (wx.ACCEL_CTRL, wx.WXK_RETURN, self.ID_RUN_SCRIPT),
            (wx.ACCEL_CTRL, ord('S'), wx.ID_SAVE),
            ])
        self.SetAcceleratorTable(self.accel)
        #wx.py.dispatcher.connect(self.debug_paused, 'debugger.paused')
        wx.py.dispatcher.connect(self.debug_ended, 'debugger.ended')
        wx.py.dispatcher.connect(self.debug_bpadded, 'debugger.breakpoint_added')
        wx.py.dispatcher.connect(self.debug_bpcleared, 'debugger.breakpoint_cleared')
        self.debug_curline = None
        PyEditorPanel.Gce.append(self)
    def __del__(self):
        del PyEditorPanel.Gce[PyEditorPanel.Gce.index(self)]
    @classmethod
    def get_instances(cls):
        for inst in cls.Gce:
            yield inst
    def Destroy(self):
        self.editor.clear_breakpoint()
        return wx.Panel.Destroy(self)

    def update_bp(self):
        for key in self.editor.breakpointlist:
            line = self.editor.MarkerLineFromHandle(key) + 1
            if line != self.editor.breakpointlist[key]['lineno']:
                ids = self.editor.breakpointlist[key]['id']
                wx.py.dispatcher.send('debugger.editbreakpoint', id=ids, lineno=line)

    def debug_bpadded(self, bpdata):
        # data =( (name,filename,lineno),
        #         self._scopes, self._active_scope,
        #         (self._can_stepin,self._can_stepout)    )
        if bpdata is None:
            return
        info = bpdata
        filename = info['filename']
        if filename == self.editor.filename:
            lineno = info['lineno']
            handler = self.editor.MarkerAdd(lineno - 1, 0)
            self.editor.breakpointlist[handler] = bpdata

    def debug_bpcleared(self, bpdata):
        # data =( (name,filename,lineno),
        #         self._scopes, self._active_scope,
        #         (self._can_stepin,self._can_stepout)    )
        # delete the current line marker
        if bpdata is None:
            return
        info = bpdata
        filename = info['filename']
        if filename == self.editor.filename:
            for key in self.editor.breakpointlist.keys():
                if self.editor.breakpointlist[key]['id'] == bpdata['id'
                        ]:
                    self.editor.MarkerDeleteHandle(key)
                    del self.editor.breakpointlist[key]
                    break

    def debug_paused(self, bpdata):
        # data =( (name,filename,lineno),
        #         self._scopes, self._active_scope,
        #         (self._can_stepin,self._can_stepout), frames)
        # delete the current line marker
        if self.debug_curline:
            self.editor.MarkerDeleteHandle(self.debug_curline)
            self.debug_curline = None
        if bpdata is None:
            return False
        info = bpdata[0]
        filename = info[1]
        
        lineno = -1
        marker = -1
        active = False
        if filename == self.editor.filename:
            lineno = info[2]
            marker = 1
            active = True
        else:
            frames=bpdata[4]
            if frames is not None:
                for frame in frames:
                    filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
                    if filename == self.fileName:
                        lineno = frame.f_lineno
                        marker = 2
                        break
        if lineno>=0 and marker>=0:
            self.debug_curline = self.editor.MarkerAdd(lineno - 1, marker)
            self.editor.EnsureVisibleEnforcePolicy(lineno-1)
            if active:
                show = self.IsShown()
                parent = self.GetParent()
                while show and parent:
                    show = parent.IsShown()
                    parent = parent.GetParent()
                if not show:
                    wx.py.dispatcher.send(signal='frame.showpanel',
                        panel=self)
            return True
        return False

    def debug_ended(self):
        if self.debug_curline:
            self.editor.MarkerDeleteHandle(self.debug_curline)
            self.debug_curline = None

    def OnWrap(self, event):
        if self.m_cbWrapMode.IsChecked():
            self.editor.SetWrapMode(stc.STC_WRAP_WORD)
        else:
            self.editor.SetWrapMode(stc.STC_WRAP_NONE)

    def JumpToLine(self, line, highlight=False):
        self.editor.GotoLine(line)
        self.editor.SetFocus()
        if highlight:
            self.editor.SelectLine(line)
        wx.FutureCall(1, self.editor.EnsureCaretVisible)

    def OnCodeModified(self, event):
        filename = 'Untile'
        if self.fileName != """""":
            (path, file) = os.path.split(self.fileName)
            filename = file
        if self.editor.IsModified():
            filename = filename + '*'
        wx.py.dispatcher.send(signal='frame.updatepanetitle',
                              pane=self, title=filename)

    def OnPrint(self, event):
        # self.editor.event.Skip()
        pass

    def OnPageSetUp(self, event):
        pass

    def openFile(self, path):
        self.editor.LoadFile(path)
        self.fileName = path
        (path, file) = os.path.split(self.fileName)
        wx.py.dispatcher.send(signal='frame.updatepanetitle',
                              pane=self, title=file)

    def OnBtnOpen(self, event):
        defaultDir = os.path.dirname(self.fileName)
        dlg = wx.FileDialog(self, 'Open', defaultDir=defaultDir,
                            wildcard='Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*'
                            , style=wx.OPEN | wx.FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.openFile(path)
        dlg.Destroy()

    def OnBtnSave(self, event):
        if self.fileName == """""":
            defaultDir = os.path.dirname(self.fileName)
            dlg = wx.FileDialog(self, 'Save As', defaultDir=defaultDir,
                                wildcard='Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*'
                                , style=wx.SAVE | wx.OVERWRITE_PROMPT
                                | wx.CHANGE_DIR)
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPaths()[0]
                self.fileName = path
            dlg.Destroy()
        self.editor.SaveFile(self.fileName)
        (path, file) = os.path.split(self.fileName)
        wx.py.dispatcher.send(signal='frame.updatepanetitle',
                              pane=self, title=file)
        self.update_bp()

    def OnBtnSaveAs(self, event):
        defaultDir = os.path.dirname(self.fileName)
        dlg = wx.FileDialog(self, 'Save As', defaultDir=defaultDir,
                            wildcard='Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*',
                            style=wx.SAVE | wx.OVERWRITE_PROMPT | wx.CHANGE_DIR)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.fileName = path
            dlg.Destroy()
        self.editor.SaveFile(self.fileName)
        (path, file) = os.path.split(self.fileName)
        wx.py.dispatcher.send(signal='frame.updatepanetitle',
                              pane=self, title=file)
        self.update_bp()

    def OnUpdateBtn(self, event):
        eid = event.GetId()
        if eid == wx.ID_SAVE:
            event.Enable(self.editor.IsModified())
    
    def OnShowFindReplace(self, event):
        """Find and Replace dialog and action."""
        # find string
        findStr = self.editor.GetSelectedText()
        if findStr and self.findDialog:
            self.findDialog.Destroy()
            self.findDialog = None
        # dialog already open, if yes give focus
        if self.findDialog:
            self.findDialog.Show(1)
            self.findDialog.Raise()
            return
        if not findStr:
            findStr = self.findStr
            self.numberMessages = 0
        # find data
        data = wx.FindReplaceData(self.findFlags)
        data.SetFindString(findStr)
        data.SetReplaceString(self.replaceStr)
        # dialog
        self.findDialog = wx.FindReplaceDialog(self, data,
                'Find & Replace', wx.FR_REPLACEDIALOG | wx.FR_NOUPDOWN)
        self.findDialog.Show(1)
        self.findDialog.data = data  # save a reference to it...

    def runcommand(self, command, prompt=False, verbose=True, debug=False):
        wx.py.dispatcher.send(signal='frame.run', command=command,
                              prompt=prompt, verbose=verbose,
                              debug=debug)

    def OnBtnRun(self, event):
        cmd = self.editor.GetSelectedText()
        if not cmd or cmd == """""":
            (cmd, pos) = self.editor.GetCurLine()
            cmd = cmd.rstrip()
        lines = cmd.split('\n')
        for line in lines:
            self.runcommand(line, prompt=True, verbose=True)
    
    def CheckModified(self):
        if self.editor.IsModified():
            wx.MessageBox('The file has been modified. Save it first and try it again!'
                          , 'BSMEditor')
            return True
        return False

    def OnBtnCheck(self, event):
        if self.CheckModified():
            return
        if self.fileName == """""":
            return
        self.runcommand('import sys', verbose=False)
        self.runcommand('_bsm_source = open(r\'%s\',\'r\').read()+\'\\n\''
                         % self.fileName, verbose=False)
        self.runcommand('compile(_bsm_source,r\'%s\',\'exec\')'
                        % self.fileName, prompt=True, verbose=True)
        self.runcommand('del _bsm_source', verbose=False)

    def OnBtnRunScript(self, event):
        if self.CheckModified():
            return
        if self.fileName == """""":
            return
        (path, file) = os.path.split(self.fileName)
        self.runcommand('import sys', verbose=False)
        self.runcommand('import imp', verbose=False)
        self.runcommand('sys.path.insert(0,r\'%s\')' % path,
                        verbose=False)
        self.runcommand('execfile(r\'%s\')' % self.fileName,
                        prompt=True, verbose=True, debug=False)
        self.runcommand('del sys.path[0]', verbose=False)

    def OnBtnDebugScript(self, event):
        if self.CheckModified():
            return
        if self.fileName == """""":
            return
        try:
            self.tb.EnableTool(self.ID_DEBUG_SCRIPT, False)
            (path, file) = os.path.split(self.fileName)
            self.runcommand('import sys', verbose=False)
            self.runcommand('import imp', verbose=False)
            self.runcommand('sys.path.insert(0,r\'%s\')' % path,
                        verbose=False)
            self.runcommand('execfile(r\'%s\')' % self.fileName,
                        prompt=True, verbose=True, debug=True)
            self.runcommand('del sys.path[0]', verbose=False)
            # make sure 'debugger.ended' is always trigged
        except:
            pass
        wx.py.dispatcher.send('debugger.ended')
        self.tb.EnableTool(self.ID_DEBUG_SCRIPT, True)

    def OnBtnImport(self, event):
        if self.CheckModified():
            return
        if self.fileName == """""":
            return
        (path, file) = os.path.split(self.fileName)
        (fileName, fileExtension) = os.path.splitext(file)
        self.runcommand('import sys', verbose=False)
        self.runcommand('import imp', verbose=False)
        self.runcommand('sys.path.insert(0,r\'%s\')' % path,
                        verbose=False)
        self.runcommand('from %s import *' % fileName, verbose=False)
        self.runcommand('del sys.path[0]', verbose=False)

    def message(self, text):
        wx.py.dispatcher.send(signal='frame.setstatustext', text=text)

    def __findReplaceEvents__(self):
        self.findStr = """"""
        self.replaceStr = """"""
        self.findFlags = 1
        self.stcFindFlags = 0
        # This can't be done with the eventManager unfortunately ;-(
        wx.EVT_COMMAND_FIND(self, -1, self.onFind)
        wx.EVT_COMMAND_FIND_NEXT(self, -1, self.onFind)
        wx.EVT_COMMAND_FIND_REPLACE(self, -1, self.onReplace)
        wx.EVT_COMMAND_FIND_REPLACE_ALL(self, -1, self.onReplaceAll)
        wx.EVT_COMMAND_FIND_CLOSE(self, -1, self.onFindClose)

    def doFind(self, strFind, forward=True, message=1):
        current = self.editor.GetCurrentPos()
        position = -1
        if forward:
            position = self.editor.FindText(current,
                    len(self.editor.GetText()), strFind,
                    self.stcFindFlags)
            if position == -1:  # wrap around
                self.wrapped = 1
                position = self.editor.FindText(0, current
                        + len(strFind), strFind, self.stcFindFlags)
        else:
            position = self.editor.FindText(current - len(strFind), 0,
                    strFind, self.stcFindFlags)
            if position == -1:  # wrap around
                self.wrapped = 1
                position = \
                    self.editor.FindText(len(self.editor.GetText()),
                        current, strFind, self.stcFindFlags)
        # not found the target, do not change the current position
        if position == -1 and message and self.numberMessages < 1:
            self.numberMessages = 1
            self.message("'%s' not found!" % strFind)
            self.numberMessages = 0
            position = current
            strFind = """"""
        self.editor.GotoPos(position)
        self.editor.SetSelection(position, position + len(strFind))
        return position

    def onFind(self, event, message=1):
        try:
            self.findStr = event.GetFindString()
            self.findFlags = event.GetFlags()
            flags = 0
            if wx.FR_WHOLEWORD & self.findFlags:
                flags |= stc.STC_FIND_WHOLEWORD
            if wx.FR_MATCHCASE & self.findFlags:
                flags |= stc.STC_FIND_MATCHCASE
            self.stcFindFlags = flags
        except:
            pass
        return self.doFind(self.findStr)

    def onFindClose(self, event):
        event.GetDialog().Destroy()
        self.numberMessages = 0

    def onReplace(self, event, message=1):
        # # Next line avoid infinite loop
        findStr = event.GetFindString()
        self.replaceStr = event.GetReplaceString()
        if findStr == self.replaceStr:
            return -1
        source = self.editor
        selection = source.GetSelectedText()
        if not event.GetFlags() & wx.FR_WHOLEWORD:
            findStr = findStr.lower()
            selection = selection.lower()
            if findStr == self.replaceStr.lower():
                return -1
        if selection == findStr:
            position = source.GetSelectionStart()
            source.ReplaceSelection(self.replaceStr)
            source.SetSelection(position, position
                                + len(self.replaceStr))
        position = self.onFind(event, message=message)
        return position

    def onReplaceAll(self, event):
        source = self.editor
        count = 0
        self.wrapped = 0
        position = start = source.GetCurrentPos()
        while position > -1 and (not self.wrapped or position < start):
            position = self.onReplace(event, message=0)
            if position != -1:
                count += 1
        if count:
            pass
        elif not count and self.numberMessages < 1:
            self.numberMessages = 1
            self.message("'%s' not found!" % event.GetFindString())
            self.numberMessages = 0

    def OnFindNext(self, event):
        findStr = self.editor.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr)

    def OnFindPrev(self, event):
        findStr = self.editor.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr, False)

    def OnIndent(self, event):
        self.editor.indented()

    def OnUnindent(self, event):
        self.editor.unindented()

    def OnSetCurFolder(self, event):
        (path, file) = os.path.split(self.fileName)
        self.runcommand('import os', verbose=False)
        self.runcommand('os.chdir(r\'%s\')' % path, verbose=False)

    def OnTidySource(self, event):
        findStr = self.editor.GetSelectedText()
        if not findStr or findStr == """""":
            self.editor.SelectAll()
            findStr = self.editor.GetSelectedText()
        try:
            output = tidy_up(findStr)
            self.editor.ReplaceSelection(output)
        except:
            traceback.print_exc()

    def OnSplitVert(self, event):
        isSplitOn = self.tb.GetToolState(self.ID_SPLIT_VERT)
        if not isSplitOn:
        # turn off the splitter
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.editor2.Hide()
        else:
        # turn on the splitter
            if not self.editor2:
                self.editor2 = PyEditor(self.splitter)
                self.editor2.SetDocPointer(self.editor.GetDocPointer())
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.splitter.SplitHorizontally(self.editor,
                        self.editor2)
                self.tb.ToggleTool(self.ID_SPLIT_HORZ, False)

    def OnSplitHorz(self, event):
        isSplitOn = self.tb.GetToolState(self.ID_SPLIT_HORZ)
        if not isSplitOn:
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.editor2.Hide()
        else:
            if not self.editor2:
                self.editor2 = PyEditor(self.splitter)
                self.editor2.SetDocPointer(self.editor.GetDocPointer())
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.splitter.SplitVertically(self.editor, self.editor2)
                self.tb.ToggleTool(self.ID_SPLIT_VERT, False)

    @classmethod
    def Initialize(cls, frame):
        cls.frame = frame
        response = wx.py.dispatcher.send(signal='frame.addmenu',
                            path='File:New:Python script\tCtrl+N', rxsignal='bsm.editor')
        if response:
            cls.ID_EDITOR_NEW = response[0][1]
        response = wx.py.dispatcher.send(signal='frame.addmenu',
                            path='File:Open:Python script\tctrl+O', rxsignal='bsm.editor')
        if response:
            cls.ID_EDITOR_OPEN = response[0][1]
        wx.py.dispatcher.connect(receiver=cls.ProcessCommand, signal='bsm.editor')
        wx.py.dispatcher.connect(receiver=cls.Uninitialize, signal='frame.exit')
        wx.py.dispatcher.connect(receiver=cls.open_script, signal='bsm.editor.openfile')
        wx.py.dispatcher.connect(receiver=cls.debugPaused, signal='debugger.paused')
        wx.py.dispatcher.connect(receiver=cls.debugUpdateScope, signal='debugger.updatescopes')
    
    @classmethod
    def debugPaused(cls, data):
        if data is None:
            return
        filename = data[0][1]
        editor = cls.open_script(filename)
        if editor:
            editor.debug_paused(data)
        for editor2 in PyEditorPanel.get_instances():
            if editor != editor2:
                editor2.debug_paused(data)

    @classmethod
    def debugUpdateScope(cls, data):
        if data is None:
            return
        for editor2 in PyEditorPanel.get_instances():
            editor2.debug_paused(data)

    @classmethod
    def Uninitialize(cls):
        pass

    @classmethod
    def ProcessCommand(cls, command):
        #print command
        if command == cls.ID_EDITOR_NEW:
            cls.add_editor()
        elif command == cls.ID_EDITOR_OPEN:
            defaultDir = os.path.dirname(os.getcwd())
            dlg = wx.FileDialog(cls.frame, 'Open',
                            wildcard='Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*',
                            style=wx.OPEN | wx.FILE_MUST_EXIST)  # defaultDir  = defaultDir,
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPaths()[0]
                cls.open_script(path)
            dlg.Destroy()

    @classmethod
    def add_editor(cls, title='Untitle', activated=True):
        panelEditor = PyEditorPanel(cls.frame)
        wx.py.dispatcher.send(signal="frame.addpanel", 
                       panel = panelEditor, 
                       title="Module",
                       active = activated)
        return panelEditor
    
    @classmethod
    def open_script(cls, filename, activated=True, lineno = 0):
        if filename:
            (fileName, fileExtension) = os.path.splitext(filename)
            if fileExtension == '.py':
                editor = cls.findEditorByFileName(filename)
                if editor is None:
                    editor = cls.add_editor()
                    editor.openFile(filename)
                    wx.py.dispatcher.send(signal = 'frame.filehistory', filename = filename)

                if editor and activated and editor.IsShown() == False:
                    wx.py.dispatcher.send(signal = 'frame.showpanel', panel = editor, focus = True)
                if lineno > 0:
                    editor.JumpToLine(lineno-1, True)
                return editor

    @classmethod
    def findEditorByFileName(self, filename):
        for editor in PyEditorPanel.get_instances():
            if str(editor.editor.filename).lower() == filename.lower():
                return editor
        return None

def bsm_Initialize(frame):
    PyEditorPanel.Initialize(frame)
