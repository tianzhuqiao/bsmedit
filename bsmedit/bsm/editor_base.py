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

    setattr(cls, 'SetupColor', SetupColor)
    setattr(cls, 'GetThemeColor', GetThemeColor)
    setattr(cls, 'GetThemeFont', GetThemeFont)
    setattr(cls, 'GetTheme', GetTheme)
    return cls
