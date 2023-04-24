import sys
import keyword
import subprocess as sp
import traceback
import wx
import wx.py.dispatcher as dp
import six

aliasDict = {}

def magicSingle(command):
    if command == '':  # Pass if command is blank
        return command

    first_space = command.find(' ')

    if command[0] == ' ':  # Pass if command begins with a space
        pass
    elif command[0] == '?':  # Do help if starts with ?
        command = 'help(' + command[1:] + ')'
    elif command[0] == '!':  # Use os.system if starts with !
        command = f"sx('{command[1:]}')"
    elif command in ('ls', 'pwd'):
        # automatically use ls and pwd with no arguments
        command = command + '()'
    elif command[:3] in ('ls ', 'cd '):
        # when using the 'ls ' or 'cd ' constructs, fill in both parentheses and quotes
        command = command[:2] + '("' + command[3:].strip() + '")'
    elif command[:5] in ('help ', ):
        command = command[:4] + '("' + command[5:].strip() + '")'
    elif command[:4] in ('doc ', ):
        command = command[:3] + '("' + command[4:].strip() + '")'
    elif command[:6] == 'close ':
        arg = command[6:].strip()
        if arg.isnumeric():
            command = command[:5] + '(' + arg + ')'
        else:
            # when using the close', fill in both parentheses and quotes
            command = command[:5] + '("' + arg  + '")'

    elif command[:5] == 'clear':
        command = command[:5] + '()'
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
            command = 'sx("' + aliasDict[c[0]] + '")'
        else:
            command = 'sx("' + aliasDict[c[0]] + ' ' + ' '.join(c[1:]) + '")'
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
                    command = wd1 + '(' + command[(first_space + 1):] + ')'
    return command

def magic(command):
    continuations = wx.py.parse.testForContinuations(command)
    if len(continuations) == 2:  # Error case...
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
            commandList.append(magicSingle(
                i))  # unless this is in a larger expression, use magic
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
    startupinfo = None
    if wx.Platform == '__WXMSW__':
        startupinfo = sp.STARTUPINFO()
        startupinfo.dwFlags |= sp.STARTF_USESHOWWINDOW
    # try the standalone command first
    try:
        if wait:
            p = sp.Popen(cmd,
                         startupinfo=startupinfo,
                         stdout=sp.PIPE,
                         stderr=sp.PIPE,
                         shell=True)
            dp.send('shell.write_out', text=p.stderr.read().decode())
            dp.send('shell.write_out', text=p.stdout.read().decode())
        else:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo)
        return
    except:
        traceback.print_exc(file=sys.stdout)
    # try the shell command
    try:
        if wait:
            p = sp.Popen(cmd.split(' '),
                         startupinfo=startupinfo,
                         shell=True,
                         stdout=sp.PIPE,
                         stderr=sp.PIPE)
            dp.send('shell.write_out', text=p.stdout.read().decode())
        else:
            p = sp.Popen(cmd.split(' '), startupinfo=startupinfo, shell=True)
        return
    except:
        traceback.print_exc(file=sys.stdout)
