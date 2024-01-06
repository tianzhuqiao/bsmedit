import os
import six
import wx
from wx import stc
import wx.py.dispatcher as dp
from .utility import _dict

NUM_MARGIN = 0
MARK_MARGIN = 1
FOLD_MARGIN = 2

MARKER_BP = 0
MARKER_BP_PAUSED_CUR = 1
MARKER_BP_PAUSED = 2
MARKER_BP_CANDIDATE = 3

# the color is copied from solarized theme
# https://ethanschoonover.com/solarized/
CLR = {
'base03':    '#002b36',
'base02':    '#073642',
'base01':    '#586e75',
'base00':    '#657b83',
'base0':     '#839496',
'base1':     '#93a1a1',
'base2':     '#eee8d5',
'base3':     '#fdf6e3',
'yellow':    '#b58900',
'orange':    '#cb4b16',
'red':       '#dc322f',
'magenta':   '#d33682',
'violet':    '#6c71c4',
'blue':      '#268bd2',
'cyan':      '#2aa198',
'green':     '#859900',
}

def EditorTheme(cls):
    def GetTheme(self, theme='solarized-dark'):
        resp = dp.send('frame.get_config', group='theme', key=theme)
        themes = None
        if resp and resp[0][1] is not None:
            themes = resp[0][1]
        theme_default = 'solarized-dark' if 'dark' in theme else 'solarized-light'
        themes_default = {'color': self.GetThemeColor(theme),
                          'font': self.GetThemeFont(theme)}
        if themes is None:
            themes = themes_default
            # save the theme in configuration as example
            dp.send('frame.set_config', group='theme', **{theme_default: themes_default})
        else:
            for item in ['color', 'font']:
                if item not in themes:
                    themes[item] = {}
                # use default value for any missing item
                themes_default[item].update(themes[item])
                themes[item] = themes_default[item]

        return themes

    def GetThemeColor(self, theme='solarized-dark'):
        if 'dark' in theme:
            bk = CLR['base03']
            bkh = CLR['base02']
            comment = CLR['base01']
            body = CLR['base0']
            emph = CLR['base1']
        else:
            bk = CLR['base3']
            bkh = CLR['base2']
            comment = CLR['base1']
            body = CLR['base00']
            emph = CLR['base01']

        green = CLR['green']
        cyan = CLR['cyan']
        red = CLR['red']
        blue = CLR['blue']
        c = _dict()
        c.background = bk
        c.background_highlight = bkh
        c.body = body
        c.emphasized = emph
        c.green = green
        c.cyan = cyan
        c.red = red
        c.blue = blue
        c.default = f'fore:{body},back:{bk}'
        c.character = f'fore:{cyan}' # 'abc'
        c.classname = f'fore:{blue}'
        c.defname = f'fore:{blue}'
        c.comment = f'fore:{comment}'
        c.comment_block = f'fore:{comment}' # start with '##
        c.decorator = f'fore:{blue}'
        c.identifier = f'fore:{body}'
        c.number = f'fore:{cyan}'
        c.operator = f'fore:{green}'
        c.string = f'fore:{cyan}'
        c.string_eol = c.string # end of line with unclosed string
        c.triple = f'fore:{cyan}'
        c.triple_double = f'fore:{cyan}'
        c.keyword = f'fore:{green}'
        c.keyword2 = f'fore:{blue}'
        c.line_number = f'fore:{body},back:{bkh}'
        c.brace_highlight = f'fore:{red},back:{bkh}'
        c.brace_bad = f'fore:{red},back:{bkh}'
        c.indent_guide = f'fore:{body}'
        c.calltip = {'fore':emph, 'back': bkh, 'highlight': emph}
        c.indicator = {'fore': red, 'hover': red}
        c.selection = {'fore': bk, 'back': body}
        c.caret = red
        c.caret_line = bkh
        c.margin_fold = {'back': bkh, 'highlight': bkh}
        c.marker_fold = {'fore': body, 'back': bkh}
        c.marker_bp = {'fore': red, 'back': emph}
        c.marker_bp2 = {'fore': '#FD8880', 'back': emph}
        c.marker_bp_paused = {'fore': blue, 'back': emph}
        c.marker_bp_paused2 = {'fore': bk, 'back': emph}
        return c

    def GetThemeFont(self, theme='solarized-dark'):
        font = {}
        font['__WXMSW__'] = {'default': 'face:Consolas,size:14'}
        font['__WXMAC__'] = {'default': 'face:Monaco,size:16'}
        font['default'] = {'default': 'face:Courier,size:14'}

        s = _dict()
        s.character = ''
        s.classname = 'bold'
        s.defname = 'bold'
        s.comment = 'italic' # start with '##
        s.comment_block = 'italic' # start with '##
        s.decorator = 'bold'
        s.identifier = ''
        s.number = ''
        s.operator = 'bold'
        s.string = ''
        s.string_eol = '' # end of line with unclosed string
        s.triple = ''
        s.triple_double = ''
        s.keyword = 'bold'
        s.keyword2 = 'bold'
        s.line_number = ''
        s.brace_highlight = ''
        s.brace_bad = ''
        s.indent_guide = ''
        s.calltip = ''

        for key in font:
            font[key].update(s)
        return font

    def SetupColor(self, theme='solarized-dark'):
        t = self.GetTheme(theme)
        c = t['color']
        f = t['font']
        f = f.get(wx.Platform) or f.get('default')

        s = {}
        for e in ['character', 'classname', 'comment', 'comment_block',
                  'decorator', 'default', 'defname', 'identifier', 'keyword',
                  'keyword2', 'number', 'operator', 'string', 'string_eol',
                  'triple', 'triple_double', 'line_number', 'brace_highlight',
                  'brace_bad', 'indent_guide']:
            s[e] = f'{c[e]},{f[e]}'

        # break point
        self.MarkerDefine(MARKER_BP, stc.STC_MARK_CIRCLE,
                          c['marker_bp']['back'],
                          c['marker_bp']['fore'])
        self.MarkerDefine(MARKER_BP_CANDIDATE, stc.STC_MARK_CIRCLE,
                          c['marker_bp2']['back'],
                          c['marker_bp2']['fore'])

        # paused at marker
        self.MarkerDefine(MARKER_BP_PAUSED_CUR, stc.STC_MARK_SHORTARROW,
                          c['marker_bp_paused']['back'],
                          c['marker_bp_paused']['fore'])
        self.MarkerDefine(MARKER_BP_PAUSED, stc.STC_MARK_SHORTARROW,
                          c['marker_bp_paused2']['back'],
                          c['marker_bp_paused2']['fore'])

        # and now set up the fold markers
        fold_fore, fold_back = c['marker_fold']['back'], c['marker_fold']['fore']
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND, stc.STC_MARK_BOXPLUSCONNECTED,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_LCORNER,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_VLINE,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS,
                          fold_fore, fold_back)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS,
                          fold_fore, fold_back)

        # Global default style
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, s['default'])

        # Clear styles and revert to default.
        self.StyleClearAll()

        # Following style specs only indicate differences from default.
        # The rest remains unchanged.

        # background for margin
        # Line numbers
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER, s['line_number'])
        # fold area
        self.SetFoldMarginColour(True, c['margin_fold']['back'])
        self.SetFoldMarginHiColour(True, c['margin_fold']['highlight'])

        # Highlighted brace
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, s['brace_highlight'])
        # Unmatched brace
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, s['brace_bad'])
        # Indentation guide
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, s['indent_guide'])

        # calltip
        self.CallTipSetBackground(c['calltip']['back'])
        self.CallTipSetForeground(c['calltip']['fore'])
        self.CallTipSetForegroundHighlight(c['calltip']['highlight'])

        # Caret color
        self.SetCaretForeground(c['caret'])
        # highlight current line
        self.SetCaretLineBackground(c['caret_line'])

        # Selection background
        self.SetSelBackground(True, c['selection']['back'])
        self.SetSelForeground(True, c['selection']['fore'])

        # indicator
        self.IndicatorSetForeground(0, c['indicator']['fore'])
        self.IndicatorSetHoverForeground(0, c['indicator']['hover'])

    def SetupColorPython(self, theme):
        t = self.GetTheme(theme)
        c = t['color']
        f = t['font']
        f = f.get(wx.Platform) or f.get('default')

        s = {}
        for e in ['character', 'classname', 'comment', 'comment_block',
                  'decorator', 'default', 'defname', 'identifier', 'keyword',
                  'keyword2', 'number', 'operator', 'string', 'string_eol',
                  'triple', 'triple_double', 'line_number', 'brace_highlight',
                  'brace_bad', 'indent_guide']:
            s[e] = f'{c[e]},{f[e]}'

        # Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, s['default'])
        # Comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, s['comment'])
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, s['comment_block'])
        # Numbers
        self.StyleSetSpec(stc.STC_P_NUMBER, s['number'])
        # Strings and characters
        self.StyleSetSpec(stc.STC_P_STRING, s['string'])
        self.StyleSetSpec(stc.STC_P_CHARACTER, s['character'])
        self.StyleSetSpec(stc.STC_P_STRINGEOL, s['string_eol'])
        # Keywords
        self.StyleSetSpec(stc.STC_P_WORD, s['keyword'])
        self.StyleSetSpec(stc.STC_P_WORD2, s['keyword2'])
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE, s['triple'])
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, s['triple_double'])

        # Class names
        self.StyleSetSpec(stc.STC_P_CLASSNAME, s['classname'])
        # Function names
        self.StyleSetSpec(stc.STC_P_DEFNAME, s['defname'])
        # Operators
        self.StyleSetSpec(stc.STC_P_OPERATOR, s['operator'])
        # decorator
        self.StyleSetSpec(stc.STC_P_DECORATOR, s['decorator'])

        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        self.StyleSetSpec(stc.STC_P_IDENTIFIER, s['identifier'])


    setattr(cls, 'SetupColor', SetupColor)
    setattr(cls, 'SetupColorPython', SetupColorPython)
    setattr(cls, 'GetThemeColor', GetThemeColor)
    setattr(cls, 'GetThemeFont', GetThemeFont)
    setattr(cls, 'GetTheme', GetTheme)
    return cls

def EditorFind(cls):
    def SetupFind(self):
        # find & replace dialog
        self.findDialog = None
        self.findStr = ""
        self.replaceStr = ""
        self.findFlags = 1
        self.stcFindFlags = 0
        self.findDialogStyle = wx.FR_REPLACEDIALOG
        self.wrapped = 0

        self.Bind(wx.EVT_TOOL, self.OnShowFindReplace, id=self.ID_FIND_REPLACE)
        self.Bind(wx.EVT_TOOL, self.OnFindNext, id=self.ID_FIND_NEXT)
        self.Bind(wx.EVT_TOOL, self.OnFindPrev, id=self.ID_FIND_PREV)

        accel = [
            (wx.ACCEL_CTRL, ord('F'), self.ID_FIND_REPLACE),
            (wx.ACCEL_SHIFT, wx.WXK_F3, self.ID_FIND_PREV),
            (wx.ACCEL_CTRL, ord('H'), self.ID_FIND_REPLACE),
            (wx.ACCEL_RAW_CTRL, ord('H'), self.ID_FIND_REPLACE),
        ]
        self.accel = wx.AcceleratorTable(accel)
        self.SetAcceleratorTable(self.accel)

    def OnShowFindReplace(self, event):
        """Find and Replace dialog and action."""
        # find string
        findStr = self.GetSelectedText()
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
        title = 'Find'
        if self.findDialogStyle & wx.FR_REPLACEDIALOG:
            title = 'Find & Replace'

        self.findDialog = wx.FindReplaceDialog(
            self, data, title, self.findDialogStyle)
        # bind the event to the dialog, see the example in wxPython demo
        self.findDialog.Bind(wx.EVT_FIND, self.OnFind)
        self.findDialog.Bind(wx.EVT_FIND_NEXT, self.OnFind)
        self.findDialog.Bind(wx.EVT_FIND_REPLACE, self.OnReplace)
        self.findDialog.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnReplaceAll)
        self.findDialog.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.findDialog.Show(1)
        self.findDialog.data = data  # save a reference to it...

    def message(self, text):
        """show the message on statusbar"""
        dp.send('frame.show_status_text', text=text)

    def _find_text(self, minPos, maxPos, text, flags=0):
        position = self.FindText(minPos, maxPos, text, flags)
        if isinstance(position, tuple):
            position = position[0] # wx ver 4.1.0 returns (start, end)
        return position

    def doFind(self, strFind, forward=True):
        """search the string"""
        current = self.GetCurrentPos()
        position = -1
        if forward:
            position = self._find_text(current, len(self.GetText()),
                                       strFind, self.stcFindFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self._find_text(0, current + len(strFind), strFind,
                                           self.stcFindFlags)
        else:
            position = self._find_text(current - len(strFind), 0, strFind,
                                       self.stcFindFlags)
            if position == -1:
                # wrap around
                self.wrapped += 1
                position = self._find_text(len(self.GetText()), current,
                                           strFind, self.stcFindFlags)

        # not found the target, do not change the current position
        if position == -1:
            self.message("'%s' not found!" % strFind)
            position = current
            strFind = """"""
        self.GotoPos(position)
        self.SetSelection(position, position + len(strFind))
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
        return self.doFind(self.findStr, wx.FR_DOWN & self.findFlags)

    def OnFindClose(self, event):
        """close find & replace dialog"""
        event.GetDialog().Destroy()

    def OnReplace(self, event):
        """replace"""
        # Next line avoid infinite loop
        findStr = event.GetFindString()
        self.replaceStr = event.GetReplaceString()

        source = self
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
        source = self
        count = 0
        self.wrapped = 0
        position = start = source.GetCurrentPos()
        while position > -1 and (not self.wrapped or position < start):
            position = self.OnReplace(event)
            if position != -1:
                count += 1
            if self.wrapped >= 2:
                break
        self.GotoPos(start)
        if not count:
            self.message("'%s' not found!" % event.GetFindString())

    def OnFindNext(self, event):
        """go the previous instance of search string"""
        findStr = self.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr)

    def OnFindPrev(self, event):
        """go the previous instance of search string"""
        findStr = self.GetSelectedText()
        if findStr:
            self.findStr = findStr
        if self.findStr:
            self.doFind(self.findStr, False)
    ID_FIND_REPLACE = wx.NewIdRef()
    ID_FIND_NEXT = wx.NewIdRef()
    ID_FIND_PREV = wx.NewIdRef()
    setattr(cls, 'ID_FIND_REPLACE', ID_FIND_REPLACE)
    setattr(cls, 'ID_FIND_NEXT', ID_FIND_NEXT)
    setattr(cls, 'ID_FIND_PREV', ID_FIND_PREV)
    setattr(cls, 'SetupFind', SetupFind)
    setattr(cls, 'OnShowFindReplace', OnShowFindReplace)
    setattr(cls, 'message', message)
    setattr(cls, '_find_text', _find_text)
    setattr(cls, 'doFind', doFind)
    setattr(cls, 'OnFind', OnFind)
    setattr(cls, 'OnFindClose', OnFindClose)
    setattr(cls, 'OnReplace', OnReplace)
    setattr(cls, 'OnReplaceAll', OnReplaceAll)
    setattr(cls, 'OnFindNext', OnFindNext)
    setattr(cls, 'OnFindPrev', OnFindPrev)
    return cls

@EditorFind
@EditorTheme
class EditorBase(wx.py.editwindow.EditWindow):
    ID_CUT = wx.NewIdRef()
    ID_COPY = wx.NewIdRef()
    ID_PASTE = wx.NewIdRef()
    ID_SELECTALL = wx.NewIdRef()
    ID_CLEAR = wx.NewIdRef()
    ID_UNDO = wx.NewIdRef()
    ID_REDO = wx.NewIdRef()

    def __init__(self, parent, style=wx.CLIP_CHILDREN | wx.BORDER_NONE):
        wx.py.editwindow.EditWindow.__init__(self, parent, style=style)

        self.SetupEditor()
        # disable the auto-insert the call tip
        self.callTipInsert = False
        self.filename = ""
        self.autoCompleteKeys = [ord('.')]
        rsp = dp.send('shell.auto_complete_keys')
        if rsp:
            self.autoCompleteKeys = rsp[0][1]
        self.highlightStr = ""
        self.SetMouseDwellTime(500)

        self.trim_trailing_whitespace = True
        resp = dp.send('frame.get_config', group='editor', key='trim_trailing_whitespace')
        if resp and resp[0][1] is not None:
            self.trim_trailing_whitespace = resp[0][1]

        # Assign handlers for keyboard events.
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(stc.EVT_STC_DOUBLECLICK, self.OnDoubleClick)
        self.Bind(stc.EVT_STC_DWELLSTART, self.OnMouseDwellStart)
        self.Bind(stc.EVT_STC_DWELLEND, self.OnMouseDwellEnd)
        self.Bind(stc.EVT_STC_ZOOM, self.OnZoom)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        # Assign handler for the context menu
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateCommandUI)
        self.Bind(wx.EVT_MENU, self.OnProcessEvent)

        self.CmdKeyAssign(ord('Z'), wx.stc.STC_SCMOD_CTRL, wx.stc.STC_CMD_UNDO)
        self.CmdKeyAssign(ord('Z'), wx.stc.STC_SCMOD_CTRL | wx.stc.STC_SCMOD_SHIFT, wx.stc.STC_CMD_REDO)

        self.LoadConfig()
        # this line after bind wx.EVT_MENU
        self.SetupFind()

    def LoadConfig(self):
        resp = dp.send('frame.get_config', group='editor', key='zoom')
        if resp and resp[0][1] is not None:
            self.SetZoom(resp[0][1])

    def OnZoom(self, event):
        pass

    def OnMotion(self, event):
        pass

    def TrimTrailingWhiteSpace(self):
        for i in range(self.GetLineCount()):
            line=self.GetLine(i).rstrip()
            if len(line) != self.GetLineLength(i):
                start = self.PositionFromLine(i)
                end = start + self.GetLineLength(i)
                self.Replace(start, end, line)

    def SaveFile(self, filename):
        """save file"""
        if self.trim_trailing_whitespace:
            self.TrimTrailingWhiteSpace()

        if super().SaveFile(filename):
            # remember the filename
            fname = os.path.abspath(filename)
            fname = os.path.normcase(fname)
            self.filename = fname
            return True
        return False

    def LoadFile(self, filename):
        """load file into editor"""
        if super().LoadFile(filename):
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
            self.autoCallTipShow(command,
                                 self.GetCurrentPos() == self.GetTextLength())
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

    def OnMouseDwellStart(self, event):
        pass

    def OnMouseDwellEnd(self, event):
        pass

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
        if self.highlightStr and sel != self.highlightStr:
            self.highlightText(self.highlightStr, False)

        event.Skip()

    def highlightText(self, strWord, highlight=True):
        """highlight the text"""
        current = 0
        position = -1
        flag = stc.STC_FIND_WHOLEWORD | stc.STC_FIND_MATCHCASE
        if not highlight:
            self.IndicatorClearRange(0, self.GetLength())
            self.highlightStr = ""
            return

        self.highlightStr = strWord
        self.SetIndicatorCurrent(0)
        while True:
            position = self.FindText(current, len(self.GetText()), strWord,
                                     flag)
            if isinstance(position, tuple):
                position = position[0] # wx ver 4.1.0 returns (start, end)
            current = position + len(strWord)
            if position == -1:
                break
            self.IndicatorFillRange(position, len(strWord))

    def needsIndent(self, firstWord, lastChar):
        '''Tests if a line needs extra indenting, i.e., if, while, def, etc '''
        # remove trailing ":" on token
        if firstWord and firstWord[-1] == ':':
            firstWord = firstWord[:-1]
        # control flow keywords
        keys = [
            'for', 'if', 'else', 'def', 'class', 'elif', 'try', 'except',
            'finally', 'while', 'with'
        ]
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
        total_lines = self.GetLineCount()
        percent = int(line*100/total_lines) if total_lines > 0 else 100
        dp.send('frame.show_status_text',
                text=f'{percent}% Ln:{line}/{total_lines}:{col}',
                index=1,
                width=150)

    def OnUpdateUI(self, event):
        super().OnUpdateUI(event)
        self.UpdateStatusText()

    def SetupEditor(self):
        """
        This method carries out the work of setting up the demo editor.
        It's separate so as not to clutter up the init code.
        """
        # Enable folding
        self.SetProperty('fold', '1')
        # Highlight tab/space mixing (shouldn't be any)
        self.SetProperty('tab.timmy.whinge.level', '1')
        # Set left and right margins
        self.SetMargins(2, 2)
        # Indentation and tab stuff
        self.SetIndent(4)
        self.SetIndentationGuides(wx.stc.STC_IV_LOOKBOTH)
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

        self.IndicatorSetStyle(0, stc.STC_INDIC_ROUNDBOX)
        self.SetWrapMode(stc.STC_WRAP_WORD)

        theme = 'solarized-dark'
        resp = dp.send('frame.get_config', group='editor', key='theme')
        if resp and resp[0][1] is not None:
            theme = resp[0][1]
        self.SetupColor(theme)

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

    def GetContextMenu(self):
        """
            Create and return a context menu for the shell.
            This is used instead of the scintilla default menu
            in order to correctly respect our immutable buffer.
        """
        menu = wx.Menu()
        menu.Append(self.ID_UNDO, 'Undo')
        menu.Append(self.ID_REDO, 'Redo')
        menu.AppendSeparator()
        menu.Append(self.ID_CUT, 'Cut')
        menu.Append(self.ID_COPY, 'Copy')
        menu.Append(self.ID_PASTE, 'Paste')
        menu.Append(self.ID_CLEAR, 'Clear')
        menu.AppendSeparator()
        menu.Append(self.ID_SELECTALL, 'Select All')
        return menu

    def OnContextMenu(self, evt):
        p = self.ScreenToClient(evt.GetPosition())
        m = self.GetMarginWidth(0) + self.GetMarginWidth(1)
        if p.x > m:
            # show edit menu when the mouse is in editable area
            menu = self.GetContextMenu()
            self.PopupMenu(menu)

    def OnUpdateCommandUI(self, evt):
        eid = evt.GetId()
        if eid in (self.ID_CUT, self.ID_CLEAR):
            evt.Enable(self.CanCut() and self.GetSelectionStart() != self.GetSelectionEnd())
        elif eid == self.ID_COPY:
            evt.Enable(self.CanCopy() and self.GetSelectionStart() != self.GetSelectionEnd())
        elif eid == self.ID_PASTE:
            evt.Enable(self.CanPaste())
        elif eid == self.ID_UNDO:
            evt.Enable(self.CanUndo())
        elif eid == self.ID_REDO:
            evt.Enable(self.CanRedo())
        else:
            evt.Skip()

    def OnProcessEvent(self, evt):
        """process the menu command"""
        eid = evt.GetId()
        if eid == self.ID_CUT:
            self.Cut()
        elif eid == self.ID_CLEAR:
            self.ClearAll()
        elif eid == self.ID_COPY:
            self.Copy()
        elif eid == self.ID_PASTE:
            self.Paste()
        elif eid == self.ID_UNDO:
            self.Undo()
        elif eid == self.ID_REDO:
            self.Redo()
        elif eid == self.ID_SELECTALL:
            self.SelectAll()
