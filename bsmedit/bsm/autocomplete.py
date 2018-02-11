# -*- coding: utf-8 -*-
__license__ = """Copyright (c) 2008-2010, Toni Ruža, All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE."""

__author__ = u"Toni Ruža <gmr.gaf@gmail.com>"
__url__ = "http://bitbucket.org/raz/wxautocompletectrl"

import six
import wx
from .. import c2p

class SuggestionsPopup(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(
            self, parent,
            style=wx.NO_BORDER|wx.FRAME_TOOL_WINDOW|wx.FRAME_NO_TASKBAR|
                  wx.FRAME_FLOAT_ON_PARENT|wx.STAY_ON_TOP
        )
        self._suggestions = self._listbox(self)
        self._suggestions.SetItemCount(0)
        self._unformated_suggestions = None

    class _listbox(c2p.HtmlListBox):
        items = None

        def OnGetItem(self, n):
            return self.items[n]

    def SetSuggestions(self, suggestions, unformated_suggestions):
        self._suggestions.items = suggestions
        self._suggestions.SetItemCount(len(suggestions))
        self._suggestions.SetSelection(0)
        self._suggestions.Refresh()
        self._unformated_suggestions = unformated_suggestions

    def CursorUp(self):
        selection = self._suggestions.GetSelection()
        if selection > 0:
            self._suggestions.SetSelection(selection - 1)

    def CursorDown(self):
        selection = self._suggestions.GetSelection()
        last = self._suggestions.GetItemCount() - 1
        if selection < last:
            self._suggestions.SetSelection(selection + 1)

    def CursorHome(self):
        if self.IsShown():
            self._suggestions.SetSelection(0)

    def CursorEnd(self):
        if self.IsShown():
            self._suggestions.SetSelection(self._suggestions.GetItemCount() - 1)

    def GetSelectedSuggestion(self):
        return self._unformated_suggestions[self._suggestions.GetSelection()]

    def GetSuggestion(self, n):
        return self._unformated_suggestions[n]


class AutocompleteTextCtrl(wx.TextCtrl):
    def __init__(self, parent, height=300, completer=None, multiline=False,
                 frequency=250, value=""):
        style = wx.TE_PROCESS_ENTER
        if multiline:
            style = style | wx.TE_MULTILINE
        wx.TextCtrl.__init__(self, parent, value=value, style=style)
        self.height = height
        self.frequency = frequency
        if completer:
            self.SetCompleter(completer)
        self.queued_popup = False
        self.skip_event = False
        self._string = value

    def SetCompleter(self, completer):
        """
        Initializes the autocompletion. The 'completer' has to be a function
        with one argument (the current value of the control, ie. the query)
        and it has to return two lists: formated (html) and unformated
        suggestions.
        """
        self.completer = completer

        frame = self.Parent
        while frame and (not isinstance(frame, wx.Frame)) and\
              (not isinstance(frame, wx.Dialog)):
            frame = frame.Parent

        self.popup = SuggestionsPopup(frame)

        frame.Bind(wx.EVT_MOVE, self.OnMove)
        self.Bind(wx.EVT_TEXT, self.OnTextUpdate)
        self.Bind(wx.EVT_SIZE, self.OnSizeChange)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.popup._suggestions.Bind(wx.EVT_LEFT_DOWN, self.OnSuggestionClicked)
        self.popup._suggestions.Bind(wx.EVT_KEY_DOWN, self.OnSuggestionKeyDown)

    def AdjustPopupPosition(self):
        self.popup.Position = self.ClientToScreen((0, self.Size.height)).Get()

    def OnMove(self, event):
        self.AdjustPopupPosition()
        event.Skip()

    def OnTextUpdate(self, event):
        # only show the popup when the text has changed; so type in 'Enter'
        # will not bring the popup
        if event.GetString() != self._string:
            self._string = event.GetString()
            if self.skip_event:
                self.skip_event = False
            elif not self.queued_popup:
                wx.CallLater(self.frequency, self.AutoComplete)
                self.queued_popup = True
        event.Skip()

    def AutoComplete(self, *args, **kwargs):
        self.queued_popup = False
        if self.Value != "":
            formated, unformated, offset = self.completer(self.Value)
            if formated:
                self.auto_comp_offset = offset
                self.popup.SetSuggestions(formated, unformated)
                self.AdjustPopupPosition()
                self.Unbind(wx.EVT_KILL_FOCUS)
                self.popup.ShowWithoutActivating()
                self.SetFocus()
                # in linux, SetFocus may select the whole string, de-select it
                self.SelectNone()
                self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
            else:
                self.popup.Hide()
        else:
            self.popup.Hide()

    def OnSizeChange(self, event):
        self.popup.Size = (self.Size[0], self.height)
        event.Skip()

    def OnKeyDown(self, event):
        key = event.GetKeyCode()

        if key == wx.WXK_UP:
            self.popup.CursorUp()
            return

        elif key == wx.WXK_DOWN:
            self.popup.CursorDown()
            return

        elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and self.popup.Shown:
            self.skip_event = True

            txt = self.popup.GetSelectedSuggestion()
            start = end = self.GetLastPosition()
            if self.auto_comp_offset:
                start -= self.auto_comp_offset
            self.Replace(start, end, txt)
            self.SetInsertionPointEnd()
            self.popup.Hide()
            return

        elif key == wx.WXK_HOME:
            self.popup.CursorHome()

        elif key == wx.WXK_END:
            self.popup.CursorEnd()

        elif event.ControlDown() and six.unichr(key).lower() == "a":
            self.SelectAll()

        elif key == wx.WXK_ESCAPE:
            self.popup.Hide()
            return

        event.Skip()

    def OnSuggestionClicked(self, event):
        self.skip_event = True
        n = self.popup._suggestions.HitTest(event.Position)
        self.Value = self.popup.GetSuggestion(n)
        self.SetInsertionPointEnd()
        wx.CallAfter(self.SetFocus)
        event.Skip()

    def OnSuggestionKeyDown(self, event):
        key = event.GetKeyCode()
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            self.skip_event = True
            self.SetValue(self.popup.GetSelectedSuggestion())
            self.SetInsertionPointEnd()
            self.popup.Hide()
        event.Skip()

    def OnKillFocus(self, event):
        if not self.popup.IsActive():
            self.popup.Hide()
        event.Skip()

