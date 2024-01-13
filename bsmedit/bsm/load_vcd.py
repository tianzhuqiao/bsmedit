import os
import sys
import traceback
import re
import pandas as pd
from ply import lex, yacc
import click
import cchardet as chardet


__version__ = '0.0.1'


def _vcd_info(msg, **kwargs):
    lineno = kwargs.get('lineno', -1)
    filename = kwargs.get('filename', '') or kwargs.get('include', '')
    silent = kwargs.get('silent', False)
    indent = kwargs.get('indent', 0)
    if silent:
        return
    info = msg
    if lineno != -1:
        info = f"{lineno:3}: {info}"
    if filename:
        info = ' '.join([click.format_filename(filename), info])
    if indent:
        info = '    ' * indent + info
    click.echo(info)


def _vcd_error(msg, **kwargs):
    kwargs['silent'] = False
    _vcd_info('Error ' + msg, **kwargs)


def _vcd_warning(msg, **kwargs):
    kwargs['silent'] = False
    _vcd_info('Warning ' + msg, **kwargs)

class VCDParse:
    """
    class to parse the vcd
    """
    # lexer definition
    tokens = (
        'END',
        'VERSION',
        'DATE',
        'COMMENT',
        'TIMESCALE',
        'SCOPE',
        'VAR',
        'UPSCOPE',
        'ENDDEFINITIONS',
        'DUMPALL',
        'DUMPOFF',
        'DUMPON',
        'DUMPVARS',
        'TIME',
        'DATA_LOGIC',
        'DATA_BINARY',
        'DATA_REAL',
        'DATA_STRING',
        'ID',
        'WORD',
        'SPACE',
    )

    states = (
        ('variable', 'exclusive'),  # raw block (not parsed)
    )

    # Tokens
    t_ignore = '\t'

    def __init__(self, verbose):
        lex.lex(module=self, reflags=re.M)
        yacc.yacc(module=self, debug=verbose)

        self.verbose = verbose
        self.filename = ""
        self.contents = ''
        self.vcd = {'info':{}, 'data':{}, 'var': {}, 'comment': []}
        self.var = {} # var in current scope
        self.scope = 0
        self.t = 0

    def scan(self, txt):
        # start next scan
        self._info("scan %d ...")
        lex.lexer.lineno = 1
        yacc.parse(txt, tracking=True)

    def run(self, txt, filename="<input>", lex_only=False):
        self.filename = filename
        if lex_only:
            # output the lexer token for debugging
            lex.input(txt)
            for tok in lex.lexer:
                click.echo(tok)
            return None

        self.scan(txt)

        return self.vcd

    def _info(self, msg, **kwargs):
        info = self._scan_info(**kwargs)
        _vcd_info(msg, **info)

    def _warning(self, msg, **kwargs):
        info = self._scan_info(**kwargs)
        _vcd_warning(msg, **info)

    def _error(self, msg, **kwargs):
        info = self._scan_info(**kwargs)
        _vcd_error(msg, **info)

    def _scan_info(self, **kwargs):
        info = {'silent': not self.verbose,
                'include': self.filename,
                'indent': 0}
        info.update(kwargs)
        return info

    # lexer
    def t_error(self, t):
        self._error("illegal character '%s'" % (t.value[0]), lineno=t.lexer.lineno)
        t.lexer.skip(1)

    def t_eof(self, t):
        return None

    def t_ENDDEFINITIONS(self, t):
        r'\s*\$enddefinitions[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_END(self, t):
        r'\$end\s*'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_VERSION(self, t):
        r'\s*\$version[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_DATE(self, t):
        r'\s*\$date[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_COMMENT(self, t):
        r'\s*\$comment[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_TIMESCALE(self, t):
        r'\s*\$timescale[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_SCOPE(self, t):
        r'\s*\$scope[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_VAR(self, t):
        r'\s*\$var[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_UPSCOPE(self, t):
        r'\s*\$upscope[\n]?'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_DUMPALL(self, t):
        r'\s*\$dumpall\s*'
        t.lexer.lineno += t.value.count('\n')
        return t
    def t_DUMPOFF(self, t):
        r'\s*\$dumpoff\s*'
        t.lexer.lineno += t.value.count('\n')
        return t
    def t_DUMPON(self, t):
        r'\s*\$dumpoff\s*'
        t.lexer.lineno += t.value.count('\n')
        return t
    def t_DUMPVARS(self, t):
        r'\s*\$dumpvars\s*'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_TIME(self, t):
        r'^#\d+\s*'
        t.lexer.lineno += t.value.count('\n')
        t.value = int(t.value[1:])
        return t

    def t_DATA_LOGIC(self, t):
        r'^[01xXzZ][\s]*'
        t.lexer.lineno += t.value.count('\n')
        t.lexer.push_state('variable')
        return t

    def t_DATA_BINARY(self, t):
        r'^[bB][01xXzZ]+[\s]*'
        t.lexer.lineno += t.value.count('\n')
        t.lexer.push_state('variable')
        t.value = t.value[1:]
        if t.value.isdigit():
            t.value = int(t.value, 2)
        return t

    def t_DATA_REAL(self, t):
        r'^[rR][-+]?(?:\d*\.*\d+)[\s]*'
        t.lexer.lineno += t.value.count('\n')
        t.lexer.push_state('variable')
        t.value = float(t.value[1:])
        #print(t.value)
        return t

    def t_DATA_STRING(self, t):
        r'^[sS][\S]+[\s]*'
        t.lexer.lineno += t.value.count('\n')
        t.lexer.push_state('variable')
        #t.value = float(t.value[1:])
        #print(t.value)
        return t
    def t_variable_ID(self, t):
        r'[!-~]+'
        # match all printable char (33~126)
        t.lexer.pop_state()
        return t

    def t_SPACE(self, t):
        r'\s+'
        t.lexer.lineno += t.value.count('\n')
        return t

    def t_WORD(self, t):
        r'\S+'
        t.lexer.lineno += t.value.count('\n')
        return t

    t_variable_error = t_error
    t_variable_ignore = t_ignore
    """
    article : comment

    comment : COMMENT text END

    text : text logicline
         | logicline

    logicline : line
              | line NEWLINE

    line : line plaintext
         | plaintext

    plaintext : plaintext WORD
              | plaintext SPACE
              | WORD
              | SPACE
              | empty

    empty :
    """

    def update_data(self, d):
        for k in d.keys():
            if k in self.vcd['data']:
                d[k] = self.vcd['data'][k]
            elif isinstance(d[k], dict):
                self.update_data(d[k])

    def p_article(self, p):
        '''article : header enddefinitions content
                   | header enddefinitions'''
        for k in self.vcd['data'].keys():
            self.vcd['data'][k] = pd.DataFrame.from_records(self.vcd['data'][k], columns=['timestamp', 'value'])

        data = self.vcd['var']
        self.update_data(data)
        self.vcd['data'] = data
        #for k in list(vcd['data'].keys()):
        #    signal = k.split('.')
        #    if len(signal) > 1:
        #        d = vcd['data']
        #        for i in range(len(signal)-1):
        #            if not signal[i] in d:
        #                d[signal[i]] = {}
        #            d = d[signal[i]]
        #        d[signal[-1]] = vcd['data'].pop(k)
        #        d[signal[-1]].rename(columns={k: signal[-1]}, inplace=True)
    def p_session_multi(self, p):
        '''header : header block'''
        p[0] = p[1] + p[2]

    def p_session_single(self, p):
        '''header : block'''
        p[0] = p[1]

    def p_session_data2(self, p):
        '''content : content data'''
        p[0] = p[1] + p[2]

    def p_session_data(self, p):
        '''content : data'''
        p[0] = p[1]

    def p_time(self, p):
        '''data : TIME'''
        p[0] = ""
        self.t = p[1]

    def p_data_logic(self, p):
        '''data : DATA_LOGIC ID SPACE'''
        p[0] = ""
        if p[2] not in self.vcd['data']:
            self.vcd['data'][p[2]] = []
        self.vcd['data'][p[2]].append([self.t, p[1]])

    def p_data_binary(self, p):
        '''data : DATA_BINARY ID SPACE'''
        p[0] = ""
        if p[2] not in self.vcd['data']:
            self.vcd['data'][p[2]] = []
        self.vcd['data'][p[2]].append([self.t, p[1]])

    def p_data_real(self, p):
        '''data : DATA_REAL ID SPACE'''
        p[0] = ""
        if p[2] not in self.vcd['data']:
            self.vcd['data'][p[2]] = []
        self.vcd['data'][p[2]].append([self.t, p[1]])

    def p_data_string(self, p):
        '''data : DATA_STRING ID SPACE'''
        p[0] = p[1] + p[2]
        if p[2] not in self.vcd['data']:
            self.vcd['data'][p[2]] = []
        self.vcd['data'][p[2]].append([self.t, p[1]])

    def p_dumpall(self, p):
        '''data : DUMPALL'''
        p[0] = p[1]

    def p_dumpoff(self, p):
        '''data : DUMPOFF'''
        p[0] = p[1]

    def p_dumpon(self, p):
        '''data : DUMPON'''
        p[0] = p[1]

    def p_dumpvars(self, p):
        '''data : DUMPVARS'''
        p[0] = p[1]

    def p_version(self, p):
        '''block : VERSION text END'''
        p[0] = p[2]
        self.vcd['info']['version'] = p[2]

    def p_date(self, p):
        '''block : DATE text END'''
        p[0] = p[2]
        self.vcd['info']['date'] = p[2]

    def p_comment(self, p):
        '''block : COMMENT text END'''
        p[0] = p[2]
        self.vcd['comment'].append(p[2])

    def p_timescale(self, p):
        '''block : TIMESCALE text END'''
        p[0] = p[2]
        self.vcd['info']['timescale'] = p[2]

    def p_enddefinitions(self, p):
        '''enddefinitions : ENDDEFINITIONS text END'''
        p[0] = p[2]

    def p_scopes6(self, p):
        '''block : scopes'''
        p[0] = ""

    def p_scopes5(self, p):
        '''scopes : scopes scopes'''
        p[0] = p[1]
        p[0].update(p[2])

    def p_scopes4(self, p):
        '''scopes : scope scopes vars upscope'''
        p[0] = {p[1]: p[3]}
        p[0][p[1]].update(p[2])
        self.scope -= 1
        if self.scope == 0:
            self.vcd['var'].update(p[0])

    def p_scopes3(self, p):
        '''scopes : scope vars scopes upscope'''
        p[0] = {p[1]: p[2]}
        p[0][p[1]].update(p[3])
        self.scope -= 1
        if self.scope == 0:
            self.vcd['var'].update(p[0])

    def p_scopes2(self, p):
        '''scopes : scope scopes upscope'''
        p[0] = {p[1]: p[2]}
        self.scope -= 1
        if self.scope == 0:
            self.vcd['var'].update(p[0])

    def p_scopes(self, p):
        '''scopes : scope vars upscope'''
        p[0] = {p[1]: p[2]}
        self.scope -= 1
        if self.scope == 0:
            self.vcd['var'].update(p[0])

    def p_scope(self, p):
        '''scope : SCOPE SPACE WORD SPACE WORD SPACE END'''
        p[0] = p[5]
        self.scope += 1
    def p_upscope(self, p):
        '''upscope : UPSCOPE text END'''
        p[0] = p[2]

    def p_vars2(self, p):
        '''vars : vars var'''
        p[0] = p[1]
        p[0].update(p[2])

    def p_vars(self, p):
        '''vars : var'''
        p[0] = p[1]

    def p_var2(self, p):
        '''var : VAR SPACE WORD SPACE WORD SPACE WORD SPACE WORD SPACE WORD SPACE END'''
        p[0] = {p[7]: {'reference': p[9], 'size': int(p[5]),
                        'type': p[3], 'bit': p[11]}}
    def p_var(self, p):
        '''var : VAR SPACE WORD SPACE WORD SPACE WORD SPACE WORD SPACE END'''
        p[0] = {p[7]: {'reference': p[9], 'size': int(p[5]),
                                 'type': p[3], 'bit': None}}
    def p_text_multi(self, p):
        '''text : text logicline'''
        p[0] = p[1] + p[2]

    def p_text_single(self, p):
        '''text : logicline'''
        p[0] = p[1]

    def p_logicline(self, p):
        '''logicline : line'''
        p[0] = p[1]

    def p_line_multi(self, p):
        '''line : line plaintext'''
        p[0] = p[1] + p[2]

    def p_line(self, p):
        '''line : plaintext'''
        p[0] = p[1]

    def p_plaintext_multi(self, p):
        '''plaintext : plaintext WORD
                     | plaintext SPACE'''
        p[0] = p[1] + p[2]

    def p_plaintext_single(self, p):
        '''plaintext : WORD
                     | SPACE
                     | empty'''
        p[0] = p[1]

    def p_empty(self, p):
        '''empty : '''
        p[0] = ''

    def p_error(self, p):
        self._error(f'syntax {str(p)}', lineno=p.lineno)

def _vcd_readfile(filename, encoding=None, **kwargs):
    if not encoding and filename != '-':
        # encoding is not define, try to detect it
        with open(filename.strip(), 'rb') as fp:
            raw = fp.read()
            encoding = chardet.detect(raw)['encoding']

    _vcd_info(f'open "{filename}" with encoding "{encoding}"', **kwargs)
    with click.open_file(filename, 'r', encoding=encoding) as fp:
        txt = fp.read()
        txt = txt.encode('unicode_escape').decode()
        regexp = re.compile(r'\\u([a-zA-Z0-9]{4})', re.M + re.S)
        txt = regexp.sub(r'&#x\1;', txt)
        txt = txt.encode().decode('unicode_escape')
        return txt
    return ""


class VCD:
    """class to load vcd file"""
    def __init__(self, lex_only=False, verbose=False):
        self.verbose = verbose
        self.lex_only = lex_only
        self.parser = VCDParse(verbose=self.verbose)

    def parse_string(self, text):
        return self.parser.run(text, lex_only=self.lex_only)

    def parse(self, filename, encoding=None):
        txt = _vcd_readfile(filename, encoding, silent=not self.verbose)
        return self.parser.run(txt, filename, self.lex_only)

    def gen(self, filename, encoding=None):
        return self.parse(filename, encoding)

def load_vcd(filename, encoding=None, lex_only=False, yacc_only=False, verbose=False):
    try:
        path, filename = os.path.split(filename)
        if path:
            os.chdir(path)
        vcd = VCD(lex_only, verbose)
        if yacc_only:
            click.echo(vcd.parse(filename, encoding))
            click.echo('\n')
        else:
            return vcd.gen(filename, encoding)
    except:
        traceback.print_exc(file=sys.stdout)
    return None


