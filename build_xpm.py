import re
#pyeditor
#filelist=[u"res/printer.xpm",u"res/page_gear.xpm",u"res/open.xpm",u"res/save.xpm",u"res/find.xpm",u"res/page_go.xpm",u"res/package_go.xpm", u'res/tick.xpm',u'res/tab_go.xpm', u'res/page_save.xpm',u'res/text_indent.xpm', u'res/text_indent_remove.xpm',u'res/folder_key.xpm', u'res/bug--arrow.xpm',u'res/wand.xpm',u'res/application_tile_vertical.xpm',u'res/application_tile_horizontal.xpm']
#output = 'pyeditorxpm.py'

#bsmplot
#filelist=[u"res/home.xpm",u"res/stock_left.xpm",u"res/stock_right.xpm",u"res/moveto2.xpm", u"res/zoom_in.xpm", u"res/saveas.xpm",u"res/page_copy.xpm",u"res/printer.xpm"]
#output = 'bsmplotxpm.py'

#debug toolbar
#filelist=[u"res/control-stop-square.xpm",u"res/arrow-stop-270.xpm",u"res/arrow.xpm",u"res/arrow-step-over.xpm", u"res/arrow-step-out.xpm", u"res/arrow-step.xpm"]
#output = 'debuggerxpm.py'

#Dir panel
#filelist=[u"res/arrow-090.xpm",u"res/folder-horizontal.xpm",u"res/home.xpm",u"res/page.xpm"]
#output = 'dirpanelxpm.py'

# listview
#filelist=[u"res/folder_database.xpm",u"res/database_add.xpm"]
#output = 'listviewpanelxpm.py'

# helpview
filelist=[u"res/arrow.xpm",u"res/arrow-180.xpm"]
output = 'bsmhelpxpm.py'

# mainframe
filelist=[u"res/setting.xpm",u"res/plugin.xpm",u"res/about.xpm",u"res/accept.xpm",u"res/cancel.xpm",u"res/cog.xpm",u"res/header.xpm",u"res/save_sim.xpm"]
output = 'mainframexpm.py'

# bsmprop
filelist = [u"res/radio.xpm", u"res/tree.xpm"]
output = 'bsmpropxpm.py'

# sim
filelist = [u"res/module.xpm", u"res/switch.xpm", u"res/in.xpm", u"res/out.xpm", u"res/inout.xpm", u"res/module_grey.xpm", u"res/switch_grey.xpm", u"res/in_grey.xpm", u"res/out_grey.xpm", u"res/inout_grey.xpm", u"res/step.xpm", u"res/step_grey.xpm", u"res/run.xpm", u"res/run_grey.xpm", u"res/pause.xpm", u"res/pause_grey.xpm", u"res/setting.xpm", u"res/setting_grey.xpm"]
output = 'simxpm.py'
def comment_remover(text):
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return ""
        else:
            return s
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, replacer, text)

fout = open(output,'w')
for fin in filelist:
    fxpm = open(fin)
    xpm = fxpm.readlines()
    xpm = comment_remover(''.join(xpm))
    xpm = xpm.replace('static char *','')
    xpm = xpm.replace('[] = {','=[')
    xpm = xpm.replace('};',']')
    xpm = xpm.strip()+'\n'
    fout.write(xpm )
    fxpm.close()
    
    
fout.close()
