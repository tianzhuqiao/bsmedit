import os
import sys
import traceback                        #for formatting errors
import inspect
import keyword
import pprint
import six
import wx
import wx.stc as stc
import wx.py.dispatcher as dp
import wx.lib.agw.aui as aui
from ..auibarpopup import AuiToolBarPopupArt
from .bsmxpm import open_xpm, save_xpm, saveas_xpm, find_xpm, indent_xpm, \
                    dedent_xpm, run_xpm, execute_xpm, check_xpm, debug_xpm, \
                    folder_xpm, vert_xpm, horz_xpm
from .pymgr_helpers import Gcm
from .. import c2p

class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition='', hitcount='', curhitcount=0):
        wx.Dialog.__init__(self, parent, title="Breakpoint Condition",
                           size=wx.Size(431, 290),
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)
        szAll = wx.BoxSizer(wx.VERTICAL)
        label = ('When the breakkpoint location is reached, the expression is '
                 'evaluated and the breakpoint is hit only if the expression '
                 'is true.')
        self.stInfo = wx.StaticText(self, label=label)
        self.stInfo.Wrap(-1)
        szAll.Add(self.stInfo, 1, wx.ALL, 15)
        szCnd = wx.BoxSizer(wx.HORIZONTAL)

        szCnd.AddSpacer((20, 0), 0, wx.EXPAND, 5)

        szCond = wx.BoxSizer(wx.VERTICAL)

        self.cbCond = wx.CheckBox(self, label="Is true")
        szCond.Add(self.cbCond, 0, wx.ALL|wx.EXPAND, 5)

        self.tcCond = wx.TextCtrl(self, wx.ID_ANY)
        szCond.Add(self.tcCond, 0, wx.ALL|wx.EXPAND, 5)

        label = "Hit count (hit count: #; for example, #>10"
        self.cbHitCount = wx.CheckBox(self, label=label)
        szCond.Add(self.cbHitCount, 0, wx.ALL, 5)

        self.tcHitCount = wx.TextCtrl(self, wx.ID_ANY)
        szCond.Add(self.tcHitCount, 0, wx.ALL|wx.EXPAND, 5)
        label = "Current hit count: %d"%curhitcount
        self.stHtCount = wx.StaticText(self, label=label)
        szCond.Add(self.stHtCount, 0, wx.ALL|wx.EXPAND, 5)

        szCnd.Add(szCond, 1, wx.EXPAND, 5)

        szAll.Add(szCnd, 1, wx.EXPAND, 5)

        self.stLine = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.stLine, 0, wx.EXPAND |wx.ALL, 5)

        szConfirm = wx.BoxSizer(wx.HORIZONTAL)

        self.btnOK = wx.Button(self, wx.ID_OK, "OK")
        szConfirm.Add(self.btnOK, 0, wx.ALL, 5)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL, "Cancel")
        szConfirm.Add(self.btnCancel, 0, wx.ALL, 5)

        szAll.Add(szConfirm, 0, wx.ALIGN_RIGHT, 5)

        self.SetSizer(szAll)
        self.Layout()

        # initialize the controls
        self.condition = condition
        self.hitcount = hitcount
        self.SetSizer(szAll)
        self.Layout()
        if self.condition == '':
            self.cbCond.SetValue(False)
            self.tcCond.Disable()
        else:
            self.cbCond.SetValue(True)
        self.tcCond.SetValue(self.condition)
        if self.hitcount == '':
            self.cbHitCount.SetValue(False)
            self.tcHitCount.Disable()
        else:
            self.cbHitCount.SetValue(True)
        self.tcHitCount.SetValue(self.hitcount)
        # Connect Events
        self.cbCond.Bind(wx.EVT_CHECKBOX, self.OnRadioButton)
        self.cbHitCount.Bind(wx.EVT_CHECKBOX, self.OnRadioButton)
        self.btnOK.Bind(wx.EVT_BUTTON, self.OnBtnOK)

    def OnRadioButton(self, event):
        self.tcCond.Enable(self.cbCond.GetValue())
        self.tcHitCount.Enable(self.cbHitCount.GetValue())
        event.Skip()

    def OnBtnOK(self, event):
        # set condition to empty string to indicate the breakpoint will be
        # trigged when the value is changed
        if self.cbCond.GetValue():
            self.condition = self.tcCond.GetValue()
        else:
            self.condition = ''
        if self.cbHitCount.GetValue():
            self.hitcount = self.tcHitCount.GetValue()
        else:
            self.hitcount = ""
        event.Skip()

    def GetCondition(self):
        return (self.condition, self.hitcount)

NUM_MARGIN = 0
MARK_MARGIN = 1
FOLD_MARGIN = 2

class PyEditor(wx.py.editwindow.EditWindow):
    ID_COMMENT = wx.NewId()
    ID_UNCOMMENT = wx.NewId()
    ID_EDIT_BREAKPOINT = wx.NewId()
    ID_DELETE_BREAKPOINT = wx.NewId()
    ID_CLEAR_BREAKPOINT = wx.NewId()
    def __init__(self, parent, style=wx.CLIP_CHILDREN | wx.BORDER_NONE):
        wx.py.editwindow.EditWindow.__init__(self, parent, style=style)
        self.SetUpEditor()
        # disable the auto-insert the call tip
        self.callTipInsert = False
        self.filename = ""
        self.autoCompleteKeys = [ord('.')]
        rsp = dp.send('shell.auto_complete_keys')
        if rsp:
            self.autoCompleteKeys = rsp[0][1]
        self.breakpointlist = {}
        self.highlightStr = ""
        self.SetMouseDwellTime(500)

        # Assign handlers for keyboard events.
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(stc.EVT_STC_DOUBLECLICK, self.OnDoubleClick)
        self.Bind(stc.EVT_STC_DWELLSTART, self.OnMouseDwellStart)
        self.Bind(stc.EVT_STC_DWELLEND, self.OnMouseDwellEnd)
        # Assign handler for the context menu
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCommandUI)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent)

    def ClearBreakpoint(self):
        """clear all the breakpoint"""
        for key in list(self.breakpointlist):
            ids = self.breakpointlist[key]['id']
            dp.send('debugger.clear_breakpoint', id=ids)

    def SaveFile(self, filename):
        """save file"""
        if super(PyEditor, self).SaveFile(filename):
            # remember the filename
            fname = os.path.abspath(filename)
            fname = os.path.normcase(fname)
            self.filename = fname
            return True
        return False

    def LoadFile(self, filename):
        """load file into editor"""
        self.ClearBreakpoint()
        if super(PyEditor, self).LoadFile(filename):
            # remember the filename
            fname = os.path.abspath(filename)
            fname = os.path.normcase(fname)
            self.filename = fname
            return True
        return False

    def OnKillFocus(self, event):
        """lose focus"""
        # close the autocomplete and calltip windows
        if self.CallTipActive():
            self.CallTipCancel()
        # crash on mac
        #if self.AutoCompActive():
        #    self.AutoCompCancel()
        event.Skip()

    def OnChar(self, event):
        """
        Keypress event handler.

        Only receives an event if OnKeyDown calls event.Skip() for the
        corresponding event.
        """
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
        """key down"""
        key = event.GetKeyCode()
        control = event.ControlDown()
        # shift=event.ShiftDown()
        alt = event.AltDown()
        if key == wx.WXK_RETURN and not control and not alt \
            and not self.AutoCompActive():
            # auto-indentation
            if self.CallTipActive():
                self.CallTipCancel()
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
            padding = indentation * (int(indent / tabWidth))
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
        """left mouse button click on margin"""
        margin = evt.GetMargin()
        ctrldown = evt.GetControl()
        # set/edit/delete a breakpoint
        if margin in [NUM_MARGIN, MARK_MARGIN]:
            lineClicked = self.LineFromPosition(evt.GetPosition())
            txt = self.GetLine(lineClicked)
            txt = txt.strip()
            if not txt or txt[0] == '#':
                return
            # check if a breakpoint marker is at this line
            bpset = self.MarkerGet(lineClicked) & 1
            bpdata = None
            resp = dp.send('debugger.get_breakpoint', filename=self.filename,
                           lineno=lineClicked + 1)
            if resp:
                bpdata = resp[0][1]
            if not bpdata:
                # No breakpoint at this line, add one
                # bpdata =  {id, filename, lineno, condition, ignore_count, trigger_count}
                bp = {'filename': self.filename, 'lineno': lineClicked + 1}
                dp.send('debugger.set_breakpoint', bpdata=bp)
            else:
                if ctrldown:
                    condition = """"""
                    if bpdata['condition']:
                        condition = bpdata['condition']
                    dlg = wx.TextEntryDialog(self,
                                             caption='Breakpoint Condition:',
                                             message='Condition',
                                             defaultValue="""""",
                                             style=wx.OK)
                    if dlg.ShowModal() == wx.ID_OK:
                        dp.send('debugger.edit_breakpoint', id=bpdata['id'],
                                condition=dlg.GetValue())
                else:
                    dp.send('debugger.clear_breakpoint', id=bpdata['id'])
        # fold and unfold as needed
        if evt.GetMargin() == FOLD_MARGIN:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())
                level = self.GetFoldLevel(lineClicked)
                if level & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        # expand node and all subnodes
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 100, level)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            # collapse all subnodes
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0, level)
                        else:
                            # expand all subnodes
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100, level)
                    else:
                        self.ToggleFold(lineClicked)

    def OnMouseDwellStart(self, event):
        resp = dp.send(signal='debugger.get_status')
        if not resp or not resp[0][1]:
            return

        pos = event.GetPosition()
        #line = self.LineFromPosition(pos) # 0, 1, 2
        if pos == -1:
            return
        c = self.GetWordChars()
        self.SetWordChars(c + '.')
        WordStart = self.WordStartPosition(pos, True)
        WordEnd = self.WordEndPosition(pos, True)
        text = self.GetTextRange(WordStart, WordEnd)
        self.SetWordChars(c)
        try:
            status = resp[0][1]
            frames = status['frames']
            level = status['active_scope']
            frame = frames[level]
            f_globals = frame.f_globals
            f_locals = frame.f_locals

            tip = pprint.pformat(eval(text, f_globals, f_locals))
            self.CallTipShow(pos, "%s = %s"%(text, tip))
        except:
            #traceback.print_exc(file=sys.stdout)
            pass

    def OnMouseDwellEnd(self, event):
        if self.CallTipActive():
            self.CallTipCancel()

    def FoldAll(self):
        """open all margin folders"""
        line_count = self.GetLineCount()
        expanding = True
        # find out if we are folding or unfolding
        for line_num in six.moves.range(line_count):
            if self.GetFoldLevel(line_num) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(line_num)
                break
        line_number = 0

        while line_number < line_count:
            level = self.GetFoldLevel(line_number)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(line_number, True)
                    line_number = self.Expand(line_number, True)
                    line_number = line_number - 1
                else:
                    lastChild = self.GetLastChild(line_number, -1)
                    self.SetFoldExpanded(line_number, False)

                    if lastChild > line_number:
                        self.HideLines(line_number+1, lastChild)

            line_number = line_number + 1

    def Expand(self, line, do_expand, force=False, vis_levels=0, level=-1):
        """open the margin folder"""
        last_child = self.GetLastChild(line, level)
        line = line + 1

        while line <= last_child:
            if force:
                if vis_levels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if do_expand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & wx.stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    self.SetFoldExpanded(line, vis_levels > 1)
                    line = self.Expand(line, do_expand, force, vis_levels - 1)
                else:
                    if do_expand:
                        if self.GetFoldExpanded(line):
                            self.SetFoldExpanded(line, True)
                    line = self.Expand(line, do_expand, force, vis_levels - 1)
            else:
                line = line + 1
        return line

    def OnDoubleClick(self, event):
        """left mouse button double click"""
        # highlight all the instances of the selected text
        sel = self.GetSelectedText()
        if sel != "":
            self.highlightText(sel)

        event.Skip()

    def OnLeftUp(self, event):
        """left mouse button released"""
        # remove the highlighting when click somewhere else
        sel = self.GetSelectedText()
        if self.highlightStr != "" and sel != self.highlightStr:
            self.highlightText(self.highlightStr, False)

        event.Skip()

    def highlightText(self, strWord, highlight=True):
        """highlight the text"""
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
            position = self.FindText(current, len(self.GetText()), strWord, flag)
            current = position + len(strWord)
            if position == -1:
                break
            self.StartStyling(position, stc.STC_INDICS_MASK)
            self.SetStyling(len(strWord), style)
        if highlight:
            self.highlightStr = strWord
        else:
            self.highlightStr = ""

    def needsIndent(self, firstWord, lastChar):
        '''Tests if a line needs extra indenting, i.e., if, while, def, etc '''
        # remove trailing ":" on token
        if firstWord and firstWord[-1] == ':':
            firstWord = firstWord[:-1]
        # control flow keywords
        keys = ['for', 'if', 'else', 'def', 'class', 'elif', 'try', 'except',
                'finally', 'while', 'with']
        return firstWord in keys and lastChar == ':'

    def needsDedent(self, firstWord):
        '''Tests if a line needs extra dedenting, i.e., break, return, etc '''
        # control flow keywords
        return firstWord in ['break', 'return', 'continue', 'yield', 'raise']

    def autoCompleteShow(self, command, offset=0):
        """Display auto-completion popup list."""
        self.AutoCompSetAutoHide(self.autoCompleteAutoHide)
        self.AutoCompSetIgnoreCase(self.autoCompleteCaseInsensitive)

        options = []
        # retrieve the auto complete list from shell
        response = dp.send('shell.auto_complete_list', command=command)
        if response:
            options = response[0][1]
        if options:
            self.AutoCompShow(offset, ' '.join(options))

    def autoCallTipShow(self, command, insertcalltip=True, forceCallTip=False):
        """Display argument spec and docstring in a popup window."""
        if self.CallTipActive():
            self.CallTipCancel()
        (argspec, tip) = (None, None)
        # retrieve the all tip from shell
        response = dp.send('shell.auto_call_tip', command=command)
        if response:
            # name, argspec, tip
            (_, argspec, tip) = response[0][1]
        if tip:
            dp.send('Shell.calltip', sender=self, calltip=tip)
        if not self.autoCallTip and not forceCallTip:
            return
        startpos = self.GetCurrentPos()
        if argspec and insertcalltip and self.callTipInsert:
            self.AddText(argspec + ')')
            endpos = self.GetCurrentPos()
            self.SetSelection(startpos, endpos)
        if argspec:
            tippos = startpos
            fallback = startpos - self.GetColumn(startpos)
            # In case there isn't enough room, only go back to the
            # fallback.
            tippos = max(tippos, fallback)
            self.CallTipShow(tippos, argspec)
    # Some methods to make it compatible with how the wxTextCtrl is used
    def SetValue(self, value):
        # if wx.USE_UNICODE:
        #    value = value.decode('iso8859_1')
        val = self.GetReadOnly()
        self.SetReadOnly(False)
        self.SetText(value)
        self.EmptyUndoBuffer()
        self.SetSavePoint()
        self.SetReadOnly(val)

    def SelectLine(self, line):
        """select the line"""
        start = self.PositionFromLine(line)
        end = self.GetLineEndPosition(line)
        self.SetSelection(start, end)

    def UpdateStatusText(self):
        """update the info on statusbar"""
        caretPos = self.GetCurrentPos()
        col = self.GetColumn(caretPos) + 1
        line = self.LineFromPosition(caretPos) + 1
        dp.send('frame.show_status_text', text='%d, %d'%(line, col), index=1,
                width=100)

    def OnUpdateUI(self, event):
        super(PyEditor, self).OnUpdateUI(event)
        wx.CallAfter(self.UpdateStatusText)

    def SetUpEditor(self):
        """
        This method carries out the work of setting up the demo editor.
        It's separate so as not to clutter up the init code.
        """
        # key binding
        self.CmdKeyAssign(ord('R'), stc.STC_SCMOD_CTRL,
                          stc.STC_CMD_REDO)
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
        self.SetMarginType(NUM_MARGIN, stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.SetMarginWidth(0, 50)
        # Indentation and tab stuff
        self.SetIndent(4)
        self.SetIndentationGuides(True)
        # Backspace unindents rather than delete 1 space
        self.SetBackSpaceUnIndents(True)
        self.SetTabIndents(True)

        # Use spaces rather than tabs, or TabTimmy will complain!
        self.SetUseTabs(False)
        # Don't view white space
        self.SetViewWhiteSpace(False)
        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.
        self.SetEOLMode(stc.STC_EOL_LF)
        self.SetViewEOL(False)
        # No right-edge mode indicator
        self.SetEdgeMode(stc.STC_EDGE_NONE)
        # Margin #1 - breakpoint symbols
        self.SetMarginType(MARK_MARGIN, stc.STC_MARGIN_SYMBOL)
        # do not show fold symbols
        self.SetMarginMask(MARK_MARGIN, ~stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(MARK_MARGIN, True)
        self.SetMarginWidth(MARK_MARGIN, 12)
        # break point
        self.MarkerDefine(0, stc.STC_MARK_CIRCLE, 'BLACK', 'RED')
        # paused at marker
        self.MarkerDefine(1, stc.STC_MARK_SHORTARROW, 'BLACK', 'GREEN')
        self.MarkerDefine(2, stc.STC_MARK_SHORTARROW, 'BLACK', 'WHITE')

        # Setup a margin to hold fold markers
        self.SetMarginType(FOLD_MARGIN, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(FOLD_MARGIN, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(FOLD_MARGIN, True)
        self.SetMarginWidth(FOLD_MARGIN, 12)
        # and now set up the fold markers
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,
                          stc.STC_MARK_BOXPLUSCONNECTED, 'white', 'black')
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID,
                          stc.STC_MARK_BOXMINUSCONNECTED, 'white', 'black')
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
            #defsize = \
            #    wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
            defsize = 14
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              'fore:#000000,back:#FFFFFF,face:Courier,size:%d'
                              %defsize)
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
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, 'fore:#008000,back:#F0FFF0')
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000,back:#F0FFF0')
        # Numbers
        self.StyleSetSpec(stc.STC_P_NUMBER, 'fore:#008080')
        # Strings and characters
        self.StyleSetSpec(stc.STC_P_STRING, 'fore:#800080')
        self.StyleSetSpec(stc.STC_P_CHARACTER, 'fore:#800080')
        # Keywords
        self.StyleSetSpec(stc.STC_P_WORD, 'fore:#000080,bold')
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE, 'fore:#800080,back:#FFFFEA')
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, 'fore:#800080,back:#FFFFEA')
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
                              c2p.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.SetSelForeground(True,
                              c2p.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        self.SetWrapMode(stc.STC_WRAP_WORD)
        # indicator
        self.IndicatorSetStyle(0, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(0, wx.RED)

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
        for line in six.moves.range(start, end + 1):
            firstChar = doc.PositionFromLine(line)
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
        for line in six.moves.range(start, end + 1):
            firstChar = doc.PositionFromLine(line)
            txt = doc.GetLine(line)
            if txt.startswith(text):
                doc.SetCurrentPos(firstChar + len(text))
                doc.DelLineLeft()
        doc.SetSelection(sel[0], doc.PositionFromLine(end + 1))
        doc.SetCurrentPos(doc.PositionFromLine(start))
        doc.EndUndoAction()
        doc.Refresh()

    def indented(self):
        """increase the indent"""
        tabWidth = max(1, self.GetTabWidth())
        if self.GetUseTabs():
            indentation = '\t'
        else:
            indentation = ' ' * tabWidth
        self.prepandText(indentation)

    def unindented(self):
        """decrease the indent"""
        tabWidth = max(1, self.GetTabWidth())
        if self.GetUseTabs():
            indentation = '\t'
        else:
            indentation = ' ' * tabWidth
        self.deprepandText(indentation)

    def comment(self):
        """Comment section"""
        self.prepandText('##')

    def uncomment(self):
        """Uncomment section"""
        self.deprepandText('##')

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
        if p.x > m:
            # show edit menu when the mouse is in editable area
            menu = self.GetContextMenu()
            self.PopupMenu(menu)
        elif p.x > self.GetMarginWidth(0):
            # in breakpoint area
            cline = self.LineFromPosition(self.PositionFromPoint(p))
            for key in self.breakpointlist:
                line = self.MarkerLineFromHandle(key)
                if line == cline:
                    self.GotoLine(line)
                    break
            else:
                return
            menu = wx.Menu()
            menu.Append(self.ID_DELETE_BREAKPOINT, 'Delete Breakpoint')
            menu.AppendSeparator()
            menu.Append(self.ID_EDIT_BREAKPOINT, 'Condition...')
            menu.AppendSeparator()
            menu.Append(self.ID_CLEAR_BREAKPOINT, 'Delete All Breakpoints')
            self.PopupMenu(menu)

    def OnUpdateCommandUI(self, evt):
        eid = evt.Id
        if eid in (wx.ID_CUT, wx.ID_CLEAR):
            evt.Enable(self.GetSelectionStart()
                       != self.GetSelectionEnd())
        elif eid == wx.ID_COPY:
            evt.Enable(self.GetSelectionStart()
                       != self.GetSelectionEnd())
        elif eid == wx.ID_PASTE:
            evt.Enable(self.CanPaste())
        elif eid == wx.ID_UNDO:
            evt.Enable(self.CanUndo())
        elif eid == wx.ID_REDO:
            evt.Enable(self.CanRedo())
        else:
            evt.Skip()

    def findBreakPoint(self, line):
        for key in self.breakpointlist:
            if line == self.MarkerLineFromHandle(key):
                return self.breakpointlist[key]
        return None

    def OnProcessEvent(self, evt):
        """process the menu command"""
        eid = evt.GetId()
        if eid == wx.ID_CUT:
            self.Cut()
        elif eid == wx.ID_CLEAR:
            self.ClearAll()
        elif eid == wx.ID_COPY:
            self.Copy()
        elif eid == wx.ID_PASTE:
            self.Paste()
        elif eid == wx.ID_UNDO:
            self.Undo()
        elif eid == wx.ID_REDO:
            self.Redo()
        elif eid == wx.ID_SELECTALL:
            self.SelectAll()
        elif eid == self.ID_COMMENT:
            self.comment()
        elif eid == self.ID_UNCOMMENT:
            self.uncomment()
        elif eid == self.ID_DELETE_BREAKPOINT:
            bp = self.findBreakPoint(self.GetCurrentLine())
            if bp:
                dp.send('debugger.clear_breakpoint', id=bp['id'])
        elif eid == self.ID_CLEAR_BREAKPOINT:
            self.ClearBreakpoint()
        elif eid == self.ID_EDIT_BREAKPOINT:
            bp = self.findBreakPoint(self.GetCurrentLine())
            if bp:
                dlg = BreakpointSettingsDlg(self, bp['condition'],
                                            bp['hitcount'], bp.get('tcount', 0))
                if dlg.ShowModal() == wx.ID_OK:
                    cond = dlg.GetCondition()
                    dp.send('debugger.edit_breakpoint', id=bp['id'],
                            condition=cond[0], hitcount=cond[1])

class PyEditorPanel(wx.Panel):
    Gce = Gcm()
    ID_RUN_SCRIPT = wx.NewId()
    ID_DEBUG_SCRIPT = wx.NewId()
    ID_FIND_REPLACE = wx.NewId()
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
    wildcard = 'Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*'
    frame = None
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=(1, 1))
        # find & replace dialog
        self.findStr = ""
        self.replaceStr = ""
        self.findFlags = 1
        self.stcFindFlags = 0
        self.wrapped = 0

        self.fileName = """"""
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.editor = PyEditor(self.splitter)
        self.editor2 = None
        self.splitter.Initialize(self.editor)
        self.Bind(stc.EVT_STC_CHANGE, self.OnCodeModified)
        self.findDialog = None
        item = ((wx.ID_OPEN, 'Open', open_xpm, 'Open Python script'),
                (wx.ID_SAVE, 'Save', save_xpm, 'Save current document (Ctrl+S)'),
                (wx.ID_SAVEAS, 'Save As', saveas_xpm, 'Save current document as'),
                (None, None, None, None),
                (self.ID_FIND_REPLACE, 'Find', find_xpm, 'Find/Replace (Ctrl+F)'),
                (None, None, None, None),
                (self.ID_INDENT, 'Increase Indent', indent_xpm, 'Increase the indent'),
                (self.ID_UNINDENT, 'Decrease Indent', dedent_xpm, 'Decrease the indent'),
                (None, None, None, None),
                (self.ID_RUN_LINE, 'Run', run_xpm, 'Run the current line or selection (Ctrl+Return)'),
                (self.ID_RUN_SCRIPT, 'Execute', execute_xpm, 'Execute the whole script'),
                (None, None, None, None),
                (self.ID_CHECK_SCRIPT, 'Check', check_xpm, 'Check the module'),
                (self.ID_DEBUG_SCRIPT, 'Debug', debug_xpm, 'Debug the script'),
                (None, None, None, None),
                (self.ID_SETCURFOLDER, 'Set current folder', folder_xpm, 'Set the file folder as current folder'),
                (None, None, None, None),
                (self.ID_SPLIT_VERT, 'Split Vert', vert_xpm, 'Split the window vertically'),
                (self.ID_SPLIT_HORZ, 'Split Horz', horz_xpm, 'Split the window horizontally'),
               )

        self.toolbarart = AuiToolBarPopupArt(self)
        self.tb = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_OVERFLOW | aui.AUI_TB_PLAIN_BACKGROUND)
        for (eid, label, img_xpm, tooltip) in item:
            if eid == None:
                self.tb.AddSeparator()
                continue
            bmp = c2p.BitmapFromXPM(img_xpm)
            if label in ['Split Vert', 'Split Horz']:
                self.tb.AddCheckTool(eid, label, bmp, wx.NullBitmap, tooltip)
            else:
                self.tb.AddSimpleTool(eid, label, bmp, tooltip)
        self.tb.AddSeparator()
        self.cbWrapMode = wx.CheckBox(self.tb, wx.ID_ANY, 'Word Wrap')
        self.cbWrapMode.SetValue(True)
        self.tb.AddControl(self.cbWrapMode)

        self.tb.SetArtProvider(self.toolbarart)
        self.tb.Realize()
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.splitter, 1, wx.EXPAND)
        self.box.Fit(self)
        self.SetSizer(self.box)
        # Connect Events
        self.Bind(wx.EVT_TOOL, self.OnBtnOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_TOOL, self.OnBtnSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_TOOL, self.OnBtnSaveAs, id=wx.ID_SAVEAS)
        self.tb.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn)
        self.Bind(wx.EVT_TOOL, self.OnShowFindReplace, id=self.ID_FIND_REPLACE)
        self.Bind(wx.EVT_TOOL, self.OnBtnRun, id=self.ID_RUN_LINE)
        self.Bind(wx.EVT_TOOL, self.OnBtnCheck, id=self.ID_CHECK_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnRunScript, id=self.ID_RUN_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnDebugScript, id=self.ID_DEBUG_SCRIPT)
        #self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn, id=self.ID_DEBUG_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnFindNext, id=self.ID_FIND_NEXT)
        self.Bind(wx.EVT_TOOL, self.OnFindPrev, id=self.ID_FIND_PREV)
        self.Bind(wx.EVT_TOOL, self.OnIndent, id=self.ID_INDENT)
        self.Bind(wx.EVT_TOOL, self.OnUnindent, id=self.ID_UNINDENT)
        self.Bind(wx.EVT_TOOL, self.OnSetCurFolder, id=self.ID_SETCURFOLDER)
        self.Bind(wx.EVT_TOOL, self.OnSplitVert, id=self.ID_SPLIT_VERT)
        self.Bind(wx.EVT_TOOL, self.OnSplitHorz, id=self.ID_SPLIT_HORZ)
        self.cbWrapMode.Bind(wx.EVT_CHECKBOX, self.OnWrap)
        accel = [(wx.ACCEL_CTRL, ord('F'), self.ID_FIND_REPLACE),
                 (wx.ACCEL_NORMAL, wx.WXK_F3, self.ID_FIND_NEXT),
                 (wx.ACCEL_SHIFT, wx.WXK_F3, self.ID_FIND_PREV),
                 (wx.ACCEL_CTRL, ord('H'), self.ID_FIND_REPLACE),
                 (wx.ACCEL_CTRL, wx.WXK_RETURN, self.ID_RUN_LINE),
                 (wx.ACCEL_CTRL, ord('S'), wx.ID_SAVE),
                ]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)
        #dp.connect(self.debug_paused, 'debugger.paused')
        dp.connect(self.debug_ended, 'debugger.ended')
        dp.connect(self.debug_bpadded, 'debugger.breakpoint_added')
        dp.connect(self.debug_bpcleared, 'debugger.breakpoint_cleared')
        self.debug_curline = None
        self.num = self.Gce.get_next_num()
        self.Gce.set_active(self)

    def Destroy(self):
        dp.disconnect(self.debug_ended, 'debugger.ended')
        dp.disconnect(self.debug_bpadded, 'debugger.breakpoint_added')
        dp.disconnect(self.debug_bpcleared, 'debugger.breakpoint_cleared')
        super(PyEditorPanel, self).Destroy()

    @classmethod
    def get_instances(cls):
        for inst in cls.Gce.get_all_managers():
            yield inst

    def Destroy(self, *args, **kwargs):
        """destroy the panel"""
        self.editor.ClearBreakpoint()
        self.CheckModified()
        self.Gce.destroy(self.num)
        return super(PyEditorPanel, self).Destroy(*args, **kwargs)

    def update_bp(self):
        """update the breakpoints"""
        for key in self.editor.breakpointlist:
            line = self.editor.MarkerLineFromHandle(key) + 1
            if line != self.editor.breakpointlist[key]['lineno']:
                ids = self.editor.breakpointlist[key]['id']
                dp.send('debugger.edit_breakpoint', id=ids, lineno=line)

    def debug_bpadded(self, bpdata):
        """the breakpoint is added"""
        if bpdata is None:
            return
        info = bpdata
        filename = info['filename']
        if filename != self.editor.filename:
            return
        for key in self.editor.breakpointlist:
            if self.editor.breakpointlist[key]['id'] == bpdata['id']:
                return
        lineno = info['lineno']
        handler = self.editor.MarkerAdd(lineno - 1, 0)
        self.editor.breakpointlist[handler] = bpdata

    def debug_bpcleared(self, bpdata):
        """the breakpoint is cleared"""
        if bpdata is None:
            return
        info = bpdata
        filename = info['filename']
        if filename != self.editor.filename:
            return
        for key in self.editor.breakpointlist:
            if self.editor.breakpointlist[key]['id'] == bpdata['id']:
                self.editor.MarkerDeleteHandle(key)
                del self.editor.breakpointlist[key]
                break

    def debug_paused(self, status):
        """the debug is paused"""
        # delete the current line marker
        if self.debug_curline:
            self.editor.MarkerDeleteHandle(self.debug_curline)
            self.debug_curline = None
        if status is None:
            return False
        filename = status['filename']

        lineno = -1
        marker = -1
        active = False
        if filename == self.editor.filename:
            lineno = status['lineno']
            marker = 1
            active = True
        else:
            frames = status['frames']
            if frames is not None:
                for frame in frames:
                    filename = inspect.getsourcefile(frame) or inspect.getfile(frame)
                    if filename == self.fileName:
                        lineno = frame.f_lineno
                        marker = 2
                        break
        if lineno >= 0 and marker >= 0:
            self.debug_curline = self.editor.MarkerAdd(lineno - 1, marker)
            self.editor.EnsureVisibleEnforcePolicy(lineno-1)
            #self.JumpToLine(lineno-1)
            #self.editor.GotoLine(lineno-1)
            #self.editor.EnsureVisible(lineno-1)
            #self.editor.EnsureCaretVisible()

            if active:
                show = self.IsShown()
                parent = self.GetParent()
                while show and parent:
                    show = parent.IsShown()
                    parent = parent.GetParent()
                if not show:
                    dp.send('frame.show_panel', panel=self)
            return True
        return False

    def debug_ended(self):
        """debugging finished"""
        if self.debug_curline:
            # hide the marker
            self.editor.MarkerDeleteHandle(self.debug_curline)
            self.debug_curline = None

    def OnWrap(self, event):
        """turn on/off the wrap mode"""
        if self.cbWrapMode.IsChecked():
            self.editor.SetWrapMode(stc.STC_WRAP_WORD)
        else:
            self.editor.SetWrapMode(stc.STC_WRAP_NONE)

    def JumpToLine(self, line, highlight=False):
        """jump to the line and make sure it is visible"""
        self.editor.GotoLine(line)
        self.editor.SetFocus()
        if highlight:
            self.editor.SelectLine(line)
        wx.FutureCall(1, self.editor.EnsureCaretVisible)

    def OnCodeModified(self, event):
        """called when the file is modified"""
        filename = 'untiled'
        if self.fileName != "":
            (_, filename) = os.path.split(self.fileName)
        if self.editor.GetModify():
            filename = filename + '*'
        dp.send('frame.set_panel_title', pane=self, title=filename)

    def LoadFile(self, path):
        """open file"""
        self.editor.LoadFile(path)
        self.fileName = path
        (_, filename) = os.path.split(self.fileName)
        dp.send('frame.set_panel_title', pane=self, title=filename)

    def OnBtnOpen(self, event):
        """open the script"""
        defaultDir = os.path.dirname(self.fileName)
        if c2p.bsm_is_phoenix:
            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        else:
            style = wx.OPEN | wx.FILE_MUST_EXIST
        dlg = wx.FileDialog(self, 'Open', defaultDir=defaultDir,
                            wildcard=self.wildcard, style=style)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.LoadFile(path)
        dlg.Destroy()

    def saveFile(self):
        if self.fileName == "":
            defaultDir = os.path.dirname(self.fileName)
            # use top level frame as parent, otherwise it may crash when
            # it is called in Destroy()
            if c2p.bsm_is_phoenix:
                style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR
            else:
                style = wx.SAVE | wx.OVERWRITE_PROMPT | wx.CHANGE_DIR
            dlg = wx.FileDialog(self.GetTopLevelParent(), 'Save As',
                                defaultDir=defaultDir, wildcard=self.wildcard,
                                style=style)
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
                self.fileName = path
            dlg.Destroy()
        self.editor.SaveFile(self.fileName)
        (path, filename) = os.path.split(self.fileName)
        dp.send('frame.set_panel_title', pane=self, title=filename)
        self.update_bp()

    def OnBtnSave(self, event):
        """save the script"""
        self.saveFile()

    def OnBtnSaveAs(self, event):
        """save the script with different filename"""
        defaultDir = os.path.dirname(self.fileName)
        if c2p.bsm_is_phoenix:
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR
        else:
            style = wx.SAVE | wx.OVERWRITE_PROMPT | wx.CHANGE_DIR
        dlg = wx.FileDialog(self, 'Save As', defaultDir=defaultDir,
                            wildcard=self.wildcard, style=style)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.fileName = path
            dlg.Destroy()
        self.editor.SaveFile(self.fileName)
        (path, filename) = os.path.split(self.fileName)
        dp.send('frame.set_panel_title', pane=self, title=filename)
        self.update_bp()

    def OnUpdateBtn(self, event):
        """update the toolbar button status"""
        eid = event.GetId()
        if eid == wx.ID_SAVE:
            event.Enable(self.editor.GetModify())
        elif eid == self.ID_DEBUG_SCRIPT:
            resp = dp.send('debugger.debugging')
            if resp:
                event.Enable(not resp[0][1])
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
        # find data
        data = wx.FindReplaceData(self.findFlags)
        data.SetFindString(findStr)
        data.SetReplaceString(self.replaceStr)
        # dialog
        self.findDialog = wx.FindReplaceDialog(self, data, 'Find & Replace',
                                               wx.FR_REPLACEDIALOG | wx.FR_NOUPDOWN)
        # bind the event to the dialog, see the example in wxPython demo
        self.findDialog.Bind(c2p.EVT_COMMAND_FIND, self.OnFind)
        self.findDialog.Bind(c2p.EVT_COMMAND_FIND_NEXT, self.OnFind)
        self.findDialog.Bind(c2p.EVT_COMMAND_FIND_REPLACE, self.OnReplace)
        self.findDialog.Bind(c2p.EVT_COMMAND_FIND_REPLACE_ALL, self.OnReplaceAll)
        self.findDialog.Bind(c2p.EVT_COMMAND_FIND_CLOSE, self.OnFindClose)
        self.findDialog.Show(1)
        self.findDialog.data = data  # save a reference to it...

    def RunCommand(self, command, prompt=False, verbose=True, debug=False):
        """run command in shell"""
        dp.send('shell.run', command=command, prompt=prompt, verbose=verbose,
                debug=debug)

    def OnBtnRun(self, event):
        """execute the selection or current line"""
        cmd = self.editor.GetSelectedText()
        if not cmd or cmd == """""":
            (cmd, _) = self.editor.GetCurLine()
            cmd = cmd.rstrip()
        lines = cmd.split('\n')
        for line in lines:
            self.RunCommand(line, prompt=True, verbose=True)

    def CheckModified(self):
        """check whether it is modified"""
        if self.editor.GetModify():
            msg = 'The file has been modified. Save it first?'
            # use top level frame as parent, otherwise it may crash when
            # it is called in Destroy()
            dlg = wx.MessageDialog(self.GetTopLevelParent(), msg,
                                   'bsmedit', wx.YES_NO)
            result = dlg.ShowModal() == wx.ID_YES
            dlg.Destroy()
            if result:
                self.saveFile()
            return self.editor.GetModify()
        return False

    def OnBtnCheck(self, event):
        """check the syntax"""
        if self.CheckModified():
            return
        if self.fileName == """""":
            return
        self.RunCommand('import sys', verbose=False)
        self.RunCommand('_bsm_source = open(r\'%s\',\'r\').read()+\'\\n\''
                        %self.fileName, verbose=False)
        self.RunCommand('compile(_bsm_source,r\'%s\',\'exec\')'
                        %self.fileName, prompt=True, verbose=True)
        self.RunCommand('del _bsm_source', verbose=False)

    def OnBtnRunScript(self, event):
        """execute the script"""
        if self.CheckModified():
            return
        if not self.fileName:
            return
        (path, _) = os.path.split(self.fileName)
        cmd = "compile(open(r'{0}', 'rb').read(), r'{0}', 'exec')".format(self.fileName)
        self.RunCommand('six.exec_(%s)'%cmd, prompt=True, verbose=True,
                        debug=False)

    def OnBtnDebugScript(self, event):
        """execute the script in debug mode"""
        if self.CheckModified():
            return
        if not self.fileName:
            return
        # disable the debugger button
        self.tb.EnableTool(self.ID_DEBUG_SCRIPT, False)

        (path, _) = os.path.split(self.fileName)
        cmd = "compile(open(r'{0}', 'rb').read(), r'{0}', 'exec')".format(self.fileName)
        self.RunCommand('six.exec_(%s)'%cmd, prompt=True, verbose=True,
                        debug=True)

        #dp.send('debugger.ended')
        self.tb.EnableTool(self.ID_DEBUG_SCRIPT, True)

    def message(self, text):
        """show the message on statusbar"""
        dp.send('frame.show_status_text', text=text)

    def doFind(self, strFind, forward=True):
        """search the string"""
        current = self.editor.GetCurrentPos()
        position = -1
        if forward:
            position = self.editor.FindText(current,
                                            len(self.editor.GetText()), strFind,
                                            self.stcFindFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self.editor.FindText(0, current + len(strFind),
                                                strFind, self.stcFindFlags)
        else:
            position = self.editor.FindText(current-len(strFind), 0, strFind,
                                            self.stcFindFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self.editor.FindText(len(self.editor.GetText()),
                                                current, strFind,
                                                self.stcFindFlags)
        # not found the target, do not change the current position
        if position == -1:
            self.message("'%s' not found!" % strFind)
            position = current
            strFind = """"""
        self.editor.GotoPos(position)
        self.editor.SetSelection(position, position + len(strFind))
        return position

    def OnFind(self, event):
        """search the string"""
        self.findStr = event.GetFindString()
        self.findFlags = event.GetFlags()
        flags = 0
        if wx.FR_WHOLEWORD & self.findFlags:
            flags |= stc.STC_FIND_WHOLEWORD
        if wx.FR_MATCHCASE & self.findFlags:
            flags |= stc.STC_FIND_MATCHCASE
        self.stcFindFlags = flags
        return self.doFind(self.findStr)

    def OnFindClose(self, event):
        """close find & replace dialog"""
        event.GetDialog().Destroy()

    def OnReplace(self, event):
        """replace"""
        # Next line avoid infinite loop
        findStr = event.GetFindString()
        self.replaceStr = event.GetReplaceString()

        source = self.editor
        selection = source.GetSelectedText()
        if not event.GetFlags() & wx.FR_MATCHCASE:
            findStr = findStr.lower()
            selection = selection.lower()

        if selection == findStr:
            position = source.GetSelectionStart()
            source.ReplaceSelection(self.replaceStr)
            source.SetSelection(position, position + len(self.replaceStr))
        # jump to next instance
        position = self.OnFind(event)
        return position

    def OnReplaceAll(self, event):
        """replace all the instances"""
        source = self.editor
        count = 0
        self.wrapped = 0
        position = start = source.GetCurrentPos()
        while position > -1 and (not self.wrapped or position < start):
            position = self.OnReplace(event)
            if position != -1:
                count += 1
            if self.wrapped >= 2:
                break
        self.editor.GotoPos(start)
        if not count:
            self.message("'%s' not found!" % event.GetFindString())

    def OnFindNext(self, event):
        """go the previous instance of search string"""
        findStr = self.editor.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr)

    def OnFindPrev(self, event):
        """go the previous instance of search string"""
        findStr = self.editor.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr, False)

    def OnIndent(self, event):
        """increase the indent"""
        self.editor.indented()

    def OnUnindent(self, event):
        """decrease the indent"""
        self.editor.unindented()

    def OnSetCurFolder(self, event):
        """set the current folder to the folder with the file"""
        if not self.fileName:
            return
        path, = os.path.split(self.fileName)
        self.RunCommand('import os', verbose=False)
        self.RunCommand('os.chdir(r\'%s\')' % path, verbose=False)

    def OnSplitVert(self, event):
        """show splitter window vertically"""
        show = self.tb.GetToolState(self.ID_SPLIT_VERT)
        if not show:
            # hide the splitter window
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.editor2.Hide()
        else:
            # show splitter window
            if not self.editor2:
                # create the splitter window
                self.editor2 = PyEditor(self.splitter)
                self.editor2.SetDocPointer(self.editor.GetDocPointer())
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.splitter.SplitHorizontally(self.editor, self.editor2)
                self.tb.ToggleTool(self.ID_SPLIT_HORZ, False)

    def OnSplitHorz(self, event):
        """show splitter window horizontally"""
        show = self.tb.GetToolState(self.ID_SPLIT_HORZ)
        if not show:
            # hide the splitter window
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.editor2.Hide()
        else:
            # show splitter window
            if not self.editor2:
                # create the splitter window
                self.editor2 = PyEditor(self.splitter)
                self.editor2.SetDocPointer(self.editor.GetDocPointer())
            if self.editor2:
                if self.splitter.IsSplit():
                    self.splitter.Unsplit(self.editor2)
                self.splitter.SplitVertically(self.editor, self.editor2)
                self.tb.ToggleTool(self.ID_SPLIT_VERT, False)

    @classmethod
    def Initialize(cls, frame, **kwargs):
        """initialize the module"""
        if cls.frame:
            # if it has already initialized, simply return
            return
        cls.frame = frame
        cls.kwargs = kwargs
        resp = dp.send('frame.add_menu', path='File:New:Python script\tCtrl+N',
                       rxsignal='bsm.editor.menu')
        if resp:
            cls.ID_EDITOR_NEW = resp[0][1]
        resp = dp.send('frame.add_menu', path='File:Open:Python script\tctrl+O',
                       rxsignal='bsm.editor.menu')
        if resp:
            cls.ID_EDITOR_OPEN = resp[0][1]
        dp.connect(cls.ProcessCommand, 'bsm.editor.menu')
        dp.connect(cls.Uninitialize, 'frame.exit')
        dp.connect(cls.OpenScript, 'frame.file_drop')
        dp.connect(cls.debugPaused, 'debugger.paused')
        dp.connect(cls.debugUpdateScope, 'debugger.update_scopes')

    @classmethod
    def debugPaused(cls):
        """the debugger has paused, update the editor margin marker"""
        resp = dp.send('debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        filename = status['filename']
        # open the file if necessary
        editor = cls.OpenScript(filename)
        if editor:
            editor.debug_paused(status)
        for editor2 in PyEditorPanel.get_instances():
            if editor != editor2:
                editor2.debug_paused(status)
    @classmethod
    def debugUpdateScope(cls):
        """
        the debugger scope has been changed, update the editor margin marker
        """
        resp = dp.send('debugger.get_status')
        if not resp or not resp[0][1]:
            return
        status = resp[0][1]
        for editor in PyEditorPanel.get_instances():
            editor.debug_paused(status)

    @classmethod
    def Uninitialize(cls):
        """unload the module"""
        pass

    @classmethod
    def ProcessCommand(cls, command):
        """process the menu command"""
        if command == cls.ID_EDITOR_NEW:
            cls.AddEditor()
        elif command == cls.ID_EDITOR_OPEN:
            defaultDir = os.path.dirname(os.getcwd())

            if c2p.bsm_is_phoenix:
                style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            else:
                style = wx.OPEN | wx.FILE_MUST_EXIST
            dlg = wx.FileDialog(cls.frame, 'Open', defaultDir=defaultDir,
                                wildcard=cls.wildcard, style=style)
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPaths()[0]
                cls.OpenScript(path)
            dlg.Destroy()

    @classmethod
    def AddEditor(cls, title='untitle', activated=True):
        """create a editor panel"""
        editor = PyEditorPanel(cls.frame)

        direction = cls.kwargs.get('direction', 'top')
        dp.send("frame.add_panel", panel=editor, title=title,
                active=activated, direction=direction)
        return editor

    @classmethod
    def OpenScript(cls, filename, activated=True, lineno=0):
        """open the file"""
        if not filename:
            return None
        (_, fileExtension) = os.path.splitext(filename)
        if fileExtension.lower() != '.py':
            return None

        editor = cls.findEditorByFileName(filename)
        if editor is None:
            editor = cls.AddEditor()
            editor.LoadFile(filename)
            dp.send('frame.add_file_history', filename=filename)

        if editor and activated and not editor.IsShown():
            dp.send('frame.show_panel', panel=editor, focus=True)
        if lineno > 0:
            editor.JumpToLine(lineno-1, True)
        return editor

    @classmethod
    def findEditorByFileName(cls, filename):
        """
        find the editor by filename

        If the file is opened in multiple editors, return the first one.
        """
        for editor in PyEditorPanel.get_instances():
            if str(editor.editor.filename).lower() == filename.lower():
                return editor
        return None

def bsm_initialize(frame, **kwargs):
    """initialize the model"""
    PyEditorPanel.Initialize(frame, **kwargs)
