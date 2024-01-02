import os
import keyword
import pprint
import six
import numpy as np
import wx
from wx import stc
import wx.py.dispatcher as dp
from ..aui import aui
from .bsmxpm import open_svg, reload_svg, save_svg, save_gray_svg, saveas_svg, \
                    play_svg, debug_svg, more_svg, indent_inc_svg, indent_dec_svg, \
                    check_svg, search_svg
from .pymgr_helpers import Gcm
from .utility import get_file_finder_name, show_file_in_finder, svg_to_bitmap
from .editor_base import *


class BreakpointSettingsDlg(wx.Dialog):
    def __init__(self, parent, condition='', hitcount='', curhitcount=0):
        wx.Dialog.__init__(self,
                           parent,
                           title="Breakpoint Condition",
                           size=wx.DefaultSize,
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        #self.SetSizeHints(wx.DefaultSize, wx.DefaultSize)
        szAll = wx.BoxSizer(wx.VERTICAL)
        label = ('When the breakkpoint location is reached, the expression is '
                 'evaluated, and the breakpoint is hit only if the expression '
                 'is true.')
        self.stInfo = wx.StaticText(self, label=label)
        self.stInfo.SetMaxSize((420, -1))
        self.stInfo.Wrap(420)
        szAll.Add(self.stInfo, 0, wx.ALL|wx.EXPAND, 15)

        szCnd = wx.BoxSizer(wx.HORIZONTAL)
        szCnd.Add(20, 0, 0)

        szCond = wx.BoxSizer(wx.VERTICAL)
        self.cbCond = wx.CheckBox(self, label="Is true")
        szCond.Add(self.cbCond, 0, wx.ALL | wx.EXPAND, 5)

        self.tcCond = wx.TextCtrl(self, wx.ID_ANY)
        szCond.Add(self.tcCond, 0, wx.ALL | wx.EXPAND, 5)

        label = "Hit count (hit count: #; for example, #>10"
        self.cbHitCount = wx.CheckBox(self, label=label)
        szCond.Add(self.cbHitCount, 0, wx.ALL, 5)

        self.tcHitCount = wx.TextCtrl(self, wx.ID_ANY)
        szCond.Add(self.tcHitCount, 0, wx.ALL | wx.EXPAND, 5)
        label = "Current hit count: %d" % curhitcount
        self.stHtCount = wx.StaticText(self, label=label)
        szCond.Add(self.stHtCount, 0, wx.ALL | wx.EXPAND, 5)

        szCnd.Add(szCond, 1, wx.EXPAND, 5)
        szCnd.Add(20, 0, 0)
        szAll.Add(szCnd, 0, wx.EXPAND, 5)

        self.stLine = wx.StaticLine(self, style=wx.LI_HORIZONTAL)
        szAll.Add(self.stLine, 0, wx.EXPAND | wx.ALL, 5)

        btnsizer = wx.StdDialogButtonSizer()

        self.btnOK = wx.Button(self, wx.ID_OK)
        self.btnOK.SetDefault()
        btnsizer.AddButton(self.btnOK)

        self.btnCancel = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(self.btnCancel)
        btnsizer.Realize()

        szAll.Add(btnsizer, 0, wx.ALIGN_RIGHT, 5)

        # initialize the controls
        self.condition = condition
        self.hitcount = hitcount
        self.SetSizer(szAll)
        self.Layout()
        szAll.Fit(self)

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


class PyEditor(EditorBase):
    ID_COMMENT = wx.NewIdRef()
    ID_UNCOMMENT = wx.NewIdRef()
    ID_EDIT_BREAKPOINT = wx.NewIdRef()
    ID_DELETE_BREAKPOINT = wx.NewIdRef()
    ID_CLEAR_BREAKPOINT = wx.NewIdRef()
    ID_WORD_WRAP = wx.NewIdRef()
    ID_INDENT_INC = wx.NewIdRef()
    ID_INDENT_DEC = wx.NewIdRef()
    ID_RUN_LINE = wx.NewIdRef()

    def __init__(self, parent):
        super().__init__(parent)

        self.break_point_candidate = None

        self.breakpointlist = {}

    def OnMotion(self, event):
        super().OnMotion(event)
        event.Skip()

        dc = wx.ClientDC(self)
        pos = event.GetLogicalPosition(dc)

        c, x, y = self.HitTest(pos)
        if self.break_point_candidate:
            self.MarkerDeleteHandle(self.break_point_candidate)
        if x == 0 and self.MarkerGet(y) & 2**0 == 0:
            style = self.GetStyleAt(self.XYToPosition(x, y))
            if style in [stc.STC_P_COMMENTLINE, stc.STC_P_COMMENTBLOCK]:
                return
            txt = self.GetLine(y)
            txt = txt.strip()
            if txt and txt[0] != '#':
                self.break_point_candidate = self.MarkerAdd(y, MARKER_BP_CANDIDATE)

    def ClearBreakpoint(self):
        """clear all the breakpoint"""
        for key in list(self.breakpointlist):
            ids = self.breakpointlist[key]['id']
            dp.send('debugger.clear_breakpoint', id=ids)

    def findBreakPoint(self, line):
        for key in self.breakpointlist:
            if line == self.MarkerLineFromHandle(key):
                return self.breakpointlist[key]
        return None

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
        menu = super().GetContextMenu()

        menu.AppendSeparator()
        menu.Append(self.ID_COMMENT, 'Comment')
        menu.Append(self.ID_UNCOMMENT, 'Uncomment')
        menu.AppendSeparator()
        item = menu.Append(self.ID_INDENT_INC, 'Increase indent')
        if wx.Platform != '__WXMAC__':
            item.SetBitmap(svg_to_bitmap(indent_inc_svg, win=self))
        item = menu.Append(self.ID_INDENT_DEC, 'Decrease indent')
        if wx.Platform != '__WXMAC__':
            item.SetBitmap(svg_to_bitmap(indent_dec_svg, win=self))
        menu.AppendSeparator()
        menu.Append(self.ID_RUN_LINE, 'Run selection/line')
        menu.AppendSeparator()
        menu.AppendCheckItem(self.ID_WORD_WRAP, 'Word wrap')
        menu.Check(self.ID_WORD_WRAP, self.GetWrapMode() != wx.stc.STC_WRAP_NONE)
        return menu

    def ToggleWrapMode(self):
        if self.GetWrapMode() == wx.stc.STC_WRAP_NONE:
            self.SetWrapMode(wx.stc.STC_WRAP_WORD)
        else:
            self.SetWrapMode(wx.stc.STC_WRAP_NONE)

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

    def SetupEditor(self):
        """
        This method carries out the work of setting up the demo editor.
        It's separate so as not to clutter up the init code.
        """
        super().SetupEditor()

        # key binding
        self.CmdKeyAssign(ord('R'), stc.STC_SCMOD_CTRL, stc.STC_CMD_REDO)
        if wx.Platform == '__WXMAC__':
            self.CmdKeyAssign(ord('R'), wx.stc.STC_SCMOD_META, wx.stc.STC_CMD_REDO)

        self.SetLexer(stc.STC_LEX_PYTHON)
        # add '.' to wordchars, so in mouse dwell event, it will capture variable
        # 'a.b'
        self.SetWordChars('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.')
        keywords = list(keyword.kwlist)
        for key in ['None', 'True', 'False']:
            if key in keywords:
                keywords.remove(key)
        self.SetKeyWords(0, ' '.join(keywords))
        self.SetKeyWords(1, ' '.join(['None', 'True', 'False']))

        # Set up the numbers in the margin for margin #1
        self.SetMarginType(NUM_MARGIN, stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.SetMarginWidth(0, 50)

        # Margin #1 - breakpoint symbols
        self.SetMarginType(MARK_MARGIN, stc.STC_MARGIN_SYMBOL)
        # do not show fold symbols
        self.SetMarginMask(MARK_MARGIN, ~stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(MARK_MARGIN, True)
        self.SetMarginWidth(MARK_MARGIN, 12)

        # Setup a margin to hold fold markers
        self.SetMarginType(FOLD_MARGIN, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(FOLD_MARGIN, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(FOLD_MARGIN, True)
        self.SetMarginWidth(FOLD_MARGIN, 12)

        self.SetCaretLineBackAlpha(64)
        self.SetCaretLineVisible(True)
        self.SetCaretLineVisibleAlways(True)

        theme = 'solarized-dark'
        resp = dp.send('frame.get_config', group='editor', key='theme')
        if resp and resp[0][1] is not None:
            theme = resp[0][1]

        self.SetupColor(theme)
        self.SetupColorPython(theme)

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
            resp = dp.send('debugger.get_breakpoint',
                           filename=self.filename,
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
                        dp.send('debugger.edit_breakpoint',
                                id=bpdata['id'],
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
        if pos == -1:
            return
        WordStart = self.WordStartPosition(pos, True)
        WordEnd = self.WordEndPosition(pos, True)
        text = self.GetTextRange(WordStart, WordEnd)
        try:
            status = resp[0][1]
            frames = status['frames']
            level = status['active_scope']
            frame = frames[level]
            f_globals = frame.f_globals
            f_locals = frame.f_locals

            tip = pprint.pformat(eval(text, f_globals, f_locals))
            self.CallTipShow(pos, "%s = %s" % (text, tip))
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
                        self.HideLines(line_number + 1, lastChild)

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

    def OnProcessEvent(self, evt):
        """process the menu command"""
        eid = evt.GetId()
        super().OnProcessEvent(evt)

        if eid == self.ID_COMMENT:
            self.comment()
        elif eid == self.ID_UNCOMMENT:
            self.uncomment()
        elif eid == self.ID_INDENT_INC:
            self.indented()
        elif eid == self.ID_INDENT_DEC:
            self.unindented()
        elif eid == self.ID_DELETE_BREAKPOINT:
            bp = self.findBreakPoint(self.GetCurrentLine())
            if bp:
                dp.send('debugger.clear_breakpoint', id=bp['id'])
        elif eid == self.ID_CLEAR_BREAKPOINT:
            self.ClearBreakpoint()
        elif eid == self.ID_EDIT_BREAKPOINT:
            bp = self.findBreakPoint(self.GetCurrentLine())
            if bp:
                dlg = BreakpointSettingsDlg(self,
                                            bp['condition'], bp['hitcount'],
                                            bp.get('tcount', 0))
                if dlg.ShowModal() == wx.ID_OK:
                    cond = dlg.GetCondition()
                    dp.send('debugger.edit_breakpoint',
                            id=bp['id'],
                            condition=cond[0],
                            hitcount=cond[1])
        elif eid == self.ID_WORD_WRAP:
            self.ToggleWrapMode()
        elif eid == self.ID_RUN_LINE:
            cmd = self.GetSelectedText()
            if not cmd or cmd == """""":
                (cmd, _) = self.GetCurLine()
                cmd = cmd.rstrip()
            dp.send('shell.run', command=cmd, prompt=True, verbose=True,
                    debug=False, history=False)

    def LoadFile(self, filename):
        """load file into editor"""
        self.ClearBreakpoint()
        if super().LoadFile(filename):
            digits = np.max([np.ceil(np.log10(self.GetLineCount())), 1])
            width = self.GetCharWidth() + 1
            self.SetMarginWidth(0, int(25+digits*width))
            return True
        return False

class PyEditorPanel(wx.Panel):
    Gce = Gcm()
    ID_RUN_SCRIPT = wx.NewIdRef()
    ID_DEBUG_SCRIPT = wx.NewIdRef()
    ID_CHECK_SCRIPT = wx.NewIdRef()
    ID_FIND_REPLACE = wx.NewIdRef()
    ID_SETCURFOLDER = wx.NewIdRef()
    ID_TIDY_SOURCE = wx.NewIdRef()
    ID_SPLIT_VERT = wx.NewIdRef()
    ID_SPLIT_HORZ = wx.NewIdRef()
    ID_DBG_RUN = wx.NewIdRef()
    ID_DBG_STOP = wx.NewIdRef()
    ID_DBG_STEP = wx.NewIdRef()
    ID_DBG_STEP_INTO = wx.NewIdRef()
    ID_DBG_STEP_OUT = wx.NewIdRef()
    ID_PANE_COPY_PATH = wx.NewIdRef()
    ID_PANE_COPY_PATH_REL = wx.NewIdRef()
    ID_PANE_SHOW_IN_FINDER = wx.NewIdRef()
    ID_PANE_SHOW_IN_BROWSING = wx.NewIdRef()
    ID_PANE_CLOSE = wx.NewIdRef()
    ID_PANE_CLOSE_OTHERS = wx.NewIdRef()
    ID_PANE_CLOSE_ALL = wx.NewIdRef()
    ID_MORE = wx.NewIdRef()

    wildcard = 'Python source (*.py)|*.py|Text (*.txt)|*.txt|All files (*.*)|*.*'
    frame = None

    def __init__(self, parent):
        wx.Panel.__init__(self, parent, size=(1, 1))

        self.fileName = """"""
        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        self.editor = PyEditor(self.splitter)
        self.editor2 = None
        self.splitter.Initialize(self.editor)
        self.Bind(stc.EVT_STC_CHANGE, self.OnCodeModified)
        item = (
            (wx.ID_OPEN, 'Open', open_svg, None, 'Open Python script'),
            (wx.ID_REFRESH, 'Reload', reload_svg, None, 'Reload script'),
            (wx.ID_SAVE, 'Save', save_svg, save_gray_svg, 'Save script (Ctrl+S)'),
            (wx.ID_SAVEAS, 'Save As', saveas_svg, None, 'Save script as'),
            (None, None, None, None, None),
            (self.ID_RUN_SCRIPT, 'Execute', play_svg, None,
             'Execute the script'),
            (None, None, None, None, None),
            (self.ID_CHECK_SCRIPT, 'Check', check_svg, None, 'Check the script'),
            (self.ID_DEBUG_SCRIPT, 'Debug', debug_svg, None, 'Debug the script'),
            (None, None, None, None, "stretch"),
            (self.ID_MORE, 'More', more_svg, None, 'More'),
        )

        self.tb = aui.AuiToolBar(self, agwStyle=aui.AUI_TB_OVERFLOW)
        for (eid, label, img, img_gray, tooltip) in item:
            if eid is None:
                if tooltip == "stretch":
                    self.tb.AddStretchSpacer()
                else:
                    self.tb.AddSeparator()
                continue
            bmp = svg_to_bitmap(img, win=self)
            bmp_gray = wx.NullBitmap
            if img_gray:
                bmp_gray = svg_to_bitmap(img_gray, win=self)
            if label in ['Split Vert', 'Split Horz']:
                self.tb.AddCheckTool(eid, label, bmp, bmp_gray, tooltip)
            else:
                self.tb.AddTool(eid, label, bmp, bmp_gray, kind=wx.ITEM_NORMAL,
                                short_help_string=tooltip)

        self.tb.Realize()
        self.box = wx.BoxSizer(wx.VERTICAL)
        self.box.Add(self.tb, 0, wx.EXPAND, 5)
        #self.box.Add(wx.StaticLine(self), 0, wx.EXPAND)
        self.box.Add(self.splitter, 1, wx.EXPAND)
        self.box.Fit(self)
        self.SetSizer(self.box)

        # Connect Events
        self.Bind(wx.EVT_TOOL, self.OnBtnOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_TOOL, self.OnBtnReload, id=wx.ID_REFRESH)
        self.Bind(wx.EVT_TOOL, self.OnBtnSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_TOOL, self.OnBtnSaveAs, id=wx.ID_SAVEAS)
        self.tb.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn)
        self.Bind(wx.EVT_TOOL, self.OnShowFindReplace, id=self.ID_FIND_REPLACE)
        self.Bind(wx.EVT_TOOL, self.OnBtnCheck, id=self.ID_CHECK_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnRunScript, id=self.ID_RUN_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnBtnDebugScript, id=self.ID_DEBUG_SCRIPT)
        #self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateBtn, id=self.ID_DEBUG_SCRIPT)
        self.Bind(wx.EVT_TOOL, self.OnSetCurFolder, id=self.ID_SETCURFOLDER)
        self.Bind(wx.EVT_MENU, self.OnSplitVert, id=self.ID_SPLIT_VERT)
        self.Bind(wx.EVT_MENU, self.OnSplitHorz, id=self.ID_SPLIT_HORZ)
        self.Bind(wx.EVT_TOOL, self.OnMore, id=self.ID_MORE)

        accel = [
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

    @classmethod
    def get_instances(cls):
        for inst in cls.Gce.get_all_managers():
            yield inst

    def Destroy(self):
        """destroy the panel"""
        self.editor.ClearBreakpoint()
        #self.CheckModified()
        self.Gce.destroy(self.num)
        return super().Destroy()

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
        handler = self.editor.MarkerAdd(lineno - 1, MARKER_BP)
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
            marker = MARKER_BP_PAUSED_CUR
            active = True
        else:
            frames = status['frames']
            if frames is not None:
                for frame in frames:
                    filename = frame.f_code.co_filename
                    if filename == self.fileName:
                        lineno = frame.f_lineno
                        marker = MARKER_BP_PAUSED
                        break
        if lineno >= 0 and marker >= 0:
            self.debug_curline = self.editor.MarkerAdd(lineno - 1, marker)
            self.editor.EnsureVisibleEnforcePolicy(lineno - 1)
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
        if self.editor.GetWrapMode() == stc.STC_WRAP_NONE:
            self.editor.SetWrapMode(stc.STC_WRAP_WORD)
        else:
            self.editor.SetWrapMode(stc.STC_WRAP_NONE)

    def JumpToLine(self, line, highlight=False):
        """jump to the line and make sure it is visible"""
        self.editor.GotoLine(line)
        self.editor.SetFocus()
        if highlight:
            self.editor.SelectLine(line)
        wx.CallLater(1, self.editor.EnsureCaretVisible)

    def OnCodeModified(self, event):
        """called when the file is modified"""
        filename = 'untitled'
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
        style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
        dlg = wx.FileDialog(self,
                            'Open',
                            defaultDir=defaultDir,
                            wildcard=self.wildcard,
                            style=style)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPaths()[0]
            self.LoadFile(path)
        dlg.Destroy()

    def OnBtnReload(self, event):
        """reload file"""
        if self.fileName:
            self.LoadFile(self.fileName)

    def saveFile(self):
        if self.fileName == "":
            defaultDir = os.path.dirname(self.fileName)
            # use top level frame as parent, otherwise it may crash when
            # it is called in Destroy()
            style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR
            dlg = wx.FileDialog(self.GetTopLevelParent(),
                                'Save As',
                                defaultDir=defaultDir,
                                wildcard=self.wildcard,
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
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT | wx.FD_CHANGE_DIR
        dlg = wx.FileDialog(self,
                            'Save As',
                            defaultDir=defaultDir,
                            wildcard=self.wildcard,
                            style=style)
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
        elif eid == wx.ID_REFRESH:
            event.Enable(self.fileName != "")

    def OnShowFindReplace(self, event):
        """Find and Replace dialog and action."""
        # find string
        self.editor.OnShowFindReplace(event)

    def RunCommand(self, command, prompt=False, verbose=True, debug=False):
        """run command in shell"""
        dp.send('shell.run',
                command=command,
                prompt=prompt,
                verbose=verbose,
                debug=debug,
                history=False)

    def OnBtnRun(self, event):
        """execute the selection or current line"""
        cmd = self.editor.GetSelectedText()
        if not cmd or cmd == """""":
            (cmd, _) = self.editor.GetCurLine()
            cmd = cmd.rstrip()
        self.RunCommand(cmd, prompt=True, verbose=True)

    def CheckModified(self):
        """check whether it is modified"""
        if self.editor.GetModify():
            filename = 'untitled'
            if self.fileName != "":
                (_, filename) = os.path.split(self.fileName)
            msg = f'"{filename}" has been modified. Save it first?'
            # use top level frame as parent, otherwise it may crash when
            # it is called in Destroy()
            dlg = wx.MessageDialog(self.GetTopLevelParent(), msg, 'bsmedit',
                                   wx.YES_NO)
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
        self.RunCommand('_bsm_source = open(r\'%s\',\'r\').read()+\'\\n\'' %
                        self.fileName,
                        verbose=False)
        self.RunCommand('_bsm_code = compile(_bsm_source,r\'%s\',\'exec\')' %
                        self.fileName,
                        prompt=True,
                        verbose=False)
        self.RunCommand('del _bsm_source', verbose=False)

    def OnBtnRunScript(self, event):
        """execute the script"""
        if self.CheckModified():
            return
        if not self.fileName:
            return
        self.RunCommand('import six', verbose=False)
        cmd = "compile(open(r'{0}', 'rb').read(), r'{0}', 'exec')".format(
            self.fileName)
        self.RunCommand('six.exec_(%s)' % cmd,
                        prompt=True,
                        verbose=False,
                        debug=False)

    def OnBtnDebugScript(self, event):
        """execute the script in debug mode"""
        if self.CheckModified():
            return
        if not self.fileName:
            return
        self.RunCommand('import six', verbose=False)
        # disable the debugger button
        self.tb.EnableTool(self.ID_DEBUG_SCRIPT, False)

        cmd = "compile(open(r'{0}', 'rb').read(), r'{0}', 'exec')".format(
            self.fileName)
        self.RunCommand('six.exec_(%s)' % cmd,
                        prompt=True,
                        verbose=False,
                        debug=True)

        #dp.send('debugger.ended')
        self.tb.EnableTool(self.ID_DEBUG_SCRIPT, True)

    def OnSetCurFolder(self, event):
        """set the current folder to the folder with the file"""
        if not self.fileName:
            return
        path, _ = os.path.split(self.fileName)
        self.RunCommand('import os', verbose=False)
        self.RunCommand('os.chdir(r\'%s\')' % path, verbose=False)

    def OnSplitVert(self, event):
        """show splitter window vertically"""
        show = not (self.splitter.IsSplit() and
                    self.splitter.GetSplitMode() == wx.SPLIT_VERTICAL)
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

    def OnSplitHorz(self, event):
        """show splitter window horizontally"""
        show = not (self.splitter.IsSplit() and
                    self.splitter.GetSplitMode() == wx.SPLIT_HORIZONTAL)
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

    def OnMore(self, event):
        menu = wx.Menu()
        menu.Append(self.ID_SETCURFOLDER, "Set as current folder")
        menu.AppendSeparator()
        item = menu.AppendCheckItem(self.ID_SPLIT_VERT, "Split editor right")
        item.Check(self.splitter.IsSplit() and
                   (self.splitter.GetSplitMode() == wx.SPLIT_VERTICAL))
        item = menu.AppendCheckItem(self.ID_SPLIT_HORZ, "Split editor down")
        item.Check(self.splitter.IsSplit() and
                   (self.splitter.GetSplitMode() == wx.SPLIT_HORIZONTAL))

        # line up our menu with the button
        tb = event.GetEventObject()
        tb.SetToolSticky(event.GetId(), True)
        rect = tb.GetToolRect(event.GetId())
        pt = tb.ClientToScreen(rect.GetBottomLeft())
        pt = self.ScreenToClient(pt)
        self.PopupMenu(menu)

        # make sure the button is "un-stuck"
        tb.SetToolSticky(event.GetId(), False)

    @classmethod
    def Initialize(cls, frame, **kwargs):
        """initialize the module"""
        if cls.frame:
            # if it has already initialized, simply return
            return
        cls.frame = frame
        cls.kwargs = kwargs
        resp = dp.send('frame.add_menu',
                       path='File:New:Python script\tCtrl+N',
                       rxsignal='bsm.editor.menu')
        if resp:
            cls.ID_EDITOR_NEW = resp[0][1]
        resp = dp.send('frame.add_menu',
                       path='File:Open:Python script\tCtrl+O',
                       rxsignal='bsm.editor.menu')
        if resp:
            cls.ID_EDITOR_OPEN = resp[0][1]
        dp.connect(cls.ProcessCommand, 'bsm.editor.menu')
        dp.connect(cls.PaneMenu, 'bsm.editor.pane_menu')
        dp.connect(cls.Uninitialize, 'frame.exit')
        dp.connect(cls.OnFrameClosing, 'frame.closing')
        dp.connect(cls.OnFrameClosePane, 'frame.close_pane')
        dp.connect(cls.OpenScript, 'frame.file_drop')
        dp.connect(cls.DebugPaused, 'debugger.paused')
        dp.connect(cls.DebugUpdateScope, 'debugger.update_scopes')
        dp.connect(cls.SetActive, 'frame.activate_panel')
        dp.connect(receiver=cls.Initialized, signal='frame.initialized')


    @classmethod
    def PaneMenu(cls, pane, command):
        if not pane or not isinstance(pane, PyEditorPanel):
            return
        if command in [cls.ID_PANE_COPY_PATH, cls.ID_PANE_COPY_PATH_REL]:
            if wx.TheClipboard.Open():
                filepath = pane.fileName
                if command == cls.ID_PANE_COPY_PATH_REL:
                    filepath = os.path.relpath(filepath, os.getcwd())
                wx.TheClipboard.SetData(wx.TextDataObject(filepath))
                wx.TheClipboard.Close()
        elif command == cls.ID_PANE_SHOW_IN_FINDER:
            show_file_in_finder(pane.fileName)
        elif command == cls.ID_PANE_SHOW_IN_BROWSING:
            dp.send(signal='dirpanel.goto', filepath=pane.fileName, show=True)
        elif command == cls.ID_PANE_CLOSE:
            dp.send(signal='frame.delete_panel', panel=pane)
        elif command == cls.ID_PANE_CLOSE_OTHERS:
            mgrs =  PyEditorPanel.Gce.get_all_managers()
            for mgr in mgrs:
                if mgr == pane:
                    continue
                dp.send(signal='frame.delete_panel', panel=mgr)
        elif command == cls.ID_PANE_CLOSE_ALL:
            mgrs =  PyEditorPanel.Gce.get_all_managers()
            for mgr in mgrs:
                dp.send(signal='frame.delete_panel', panel=mgr)

    @classmethod
    def SetActive(cls, pane):
        """set the active figure"""
        if pane and isinstance(pane, PyEditorPanel):
            cls.Gce.set_active(pane)

    @classmethod
    def DebugPaused(cls):
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
    def DebugUpdateScope(cls):
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
    def Initialized(cls):
        resp = dp.send('frame.get_config', group='editor', key='opened')
        if resp and resp[0][1]:
            files = resp[0][1]
            if len(files[0]) == 2:
                files = [ f+[False] for f in files]
            for f, line, shown in files:
                cls.OpenScript(f, activated=False, lineno=line, add_to_history=False)

    @classmethod
    def OnFrameClosePane(cls, event):
        """closing a pane"""
        pane = event.GetPane().window
        if isinstance(pane, aui.auibook.AuiNotebook):
            for i in range(pane.GetPageCount()):
                page = pane.GetPage(i)
                if isinstance(page, PyEditorPanel):
                    if page.CheckModified():
                        # the file has been modified, stop closing
                        event.Veto()
        elif isinstance(pane, PyEditorPanel):
            if pane.CheckModified():
                # the file has been modified, stop closing
                event.Veto()

    @classmethod
    def OnFrameClosing(cls, event):
        """the frame is exiting"""
        for panel in cls.Gce.get_all_managers():
            if panel.CheckModified():
                # the file has been modified, stop closing
                event.Veto()
                break

    @classmethod
    def Uninitialize(cls):
        """unload the module"""
        files = []
        for panel in cls.Gce.get_all_managers():
            editor = panel.editor
            files.append([editor.filename, editor.GetCurrentLine(), panel.IsShownOnScreen()])

        for panel in cls.Gce.get_all_managers():
            dp.send('frame.delete_panel', panel=panel)
        dp.send('frame.set_config', group='editor', opened=files)

    @classmethod
    def ProcessCommand(cls, command):
        """process the menu command"""
        if command == cls.ID_EDITOR_NEW:
            cls.AddEditor()
        elif command == cls.ID_EDITOR_OPEN:
            defaultDir = os.path.dirname(os.getcwd())

            style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
            dlg = wx.FileDialog(cls.frame,
                                'Open',
                                defaultDir=defaultDir,
                                wildcard=cls.wildcard,
                                style=style)
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPaths()[0]
                cls.OpenScript(path)
            dlg.Destroy()

    @classmethod
    def AddEditor(cls, title='untitled', activated=True):
        """create a editor panel"""
        editor = PyEditorPanel(cls.frame)

        direction = cls.kwargs.get('direction', 'top')
        dp.send("frame.add_panel",
                panel=editor,
                title=title,
                active=activated,
                direction=direction,
                pane_menu={'rxsignal': 'bsm.editor.pane_menu',
                           'menu': [
                               {'id':cls.ID_PANE_CLOSE, 'label':'Close\tCtrl+W'},
                               {'id':cls.ID_PANE_CLOSE_OTHERS, 'label':'Close Others'},
                               {'id':cls.ID_PANE_CLOSE_ALL, 'label':'Close All'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id':cls.ID_PANE_COPY_PATH, 'label':'Copy Path\tAlt+Ctrl+C'},
                               {'id':cls.ID_PANE_COPY_PATH_REL, 'label':'Copy Relative Path\tAlt+Shift+Ctrl+C'},
                               {'type': wx.ITEM_SEPARATOR},
                               {'id': cls.ID_PANE_SHOW_IN_FINDER, 'label':f'Reveal in  {get_file_finder_name()}\tAlt+Ctrl+R'},
                               {'id': cls.ID_PANE_SHOW_IN_BROWSING, 'label':'Reveal in Browsing panel'},
                               ]})
        return editor

    @classmethod
    def OpenScript(cls, filename, activated=True, lineno=0, add_to_history=True):
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
            if add_to_history:
                dp.send('frame.add_file_history', filename=filename)

        if editor and activated and not editor.IsShown():
            dp.send('frame.show_panel', panel=editor, focus=True)
        if lineno > 0:
            editor.JumpToLine(lineno - 1)
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
