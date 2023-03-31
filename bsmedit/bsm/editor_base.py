import wx
from wx import stc
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
    def SetupColor(self, theme='solarized-dark'):
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

        # break point
        self.MarkerDefine(MARKER_BP, stc.STC_MARK_CIRCLE, emph, red)
        # paused at marker
        self.MarkerDefine(MARKER_BP_PAUSED_CUR, stc.STC_MARK_SHORTARROW, emph, green)
        self.MarkerDefine(MARKER_BP_PAUSED, stc.STC_MARK_SHORTARROW, emph, bk)

        self.MarkerDefine(MARKER_BP_CANDIDATE, stc.STC_MARK_CIRCLE, emph, '#FD8880')

        # and now set up the fold markers
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND, stc.STC_MARK_BOXPLUSCONNECTED,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL, stc.STC_MARK_LCORNER,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB, stc.STC_MARK_VLINE,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER, stc.STC_MARK_BOXPLUS,
                          bkh, body)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN, stc.STC_MARK_BOXMINUS,
                          bkh, body)

        # Global default style
        if wx.Platform == '__WXMSW__':
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              'fore:{body},back:{bk},face:Courier New')
        elif wx.Platform == '__WXMAC__':
            # TODO: if this looks fine on Linux too, remove the Mac-specific case
            # and use this whenever OS != MSW.
            self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT,
                              f'fore:{body},back:{bk},face:Monaco')
        else:
            self.StyleSetSpec(stc.STC_STYLE_DEFAULT,
                              f'fore:{body},back:{bk},face:Courier,size:14')

        # Clear styles and revert to default.
        self.StyleClearAll()
        # Following style specs only indicate differences from default.
        # The rest remains unchanged.

        # background for margin
        # Line numbers
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER, f'fore:{body},back:{bkh}')
        # fold area
        self.SetFoldMarginColour(True, bkh)
        self.SetFoldMarginHiColour(True, bkh)

        # Highlighted brace
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, f'fore:{red},back:{bkh}')
        # Unmatched brace
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, f'fore:{red},back:{bkh}')
        # Indentation guide
        self.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, f'fore:{body}')

        # Python styles
        self.StyleSetSpec(stc.STC_P_DEFAULT, f'fore:{body}')
        # Comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, f'italic,fore:{comment}')
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, f'italic,fore:{comment}')
        # Numbers
        self.StyleSetSpec(stc.STC_P_NUMBER, f'fore:{cyan}')
        # Strings and characters
        self.StyleSetSpec(stc.STC_P_STRING, f'fore:{cyan}')
        self.StyleSetSpec(stc.STC_P_CHARACTER, f'fore:{cyan}')
        # Keywords
        self.StyleSetSpec(stc.STC_P_WORD, f'fore:{green},bold')
        self.StyleSetSpec(stc.STC_P_WORD2, f'fore:{blue},bold')
        # Triple quotes
        self.StyleSetSpec(stc.STC_P_TRIPLE, f'fore:{cyan}')
        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, f'fore:{cyan}')

        # Class names
        self.StyleSetSpec(stc.STC_P_CLASSNAME, f'fore:{blue},bold')
        # Function names
        self.StyleSetSpec(stc.STC_P_DEFNAME, f'fore:{blue},bold')
        # Operators
        self.StyleSetSpec(stc.STC_P_OPERATOR, f'fore:{green},bold')
        # decorator
        self.StyleSetSpec(stc.STC_P_DECORATOR, f'fore:{blue},bold')

        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        #self.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#000000')

        # calltip
        self.CallTipSetBackground(bkh)
        self.CallTipSetForeground(emph)
        self.CallTipSetForegroundHighlight(emph)

        # Caret color
        self.SetCaretForeground(red)
        # Selection background
        self.SetSelBackground(1, bkh)
        self.SetSelBackground(True, body)
        self.SetSelForeground(True, bk)
        self.SetWrapMode(stc.STC_WRAP_WORD)
        # indicator
        self.IndicatorSetStyle(0, stc.STC_INDIC_ROUNDBOX)
        self.IndicatorSetForeground(0, red)

        # highlight current line
        self.SetCaretLineBackground(bkh)
        self.SetCaretLineBackAlpha(64)
        self.SetCaretLineVisible(True)
        self.SetCaretLineVisibleAlways(True)

    setattr(cls, 'SetupColor', SetupColor)
    return cls
