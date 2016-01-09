import os
import zipfile
import sys
import os
if len(sys.argv)<2:
    print 'Usage: %s filename [lite]'%os.path.basename(sys.argv[0])
    exit()
if len(sys.argv)<3 or sys.argv[2] != 'lite':
    lite = False
else:
    lite = True
filename = sys.argv[1]
def add_folder(zf, folder, ext):
    for f in os.listdir(folder):
        if f.endswith(ext):
            fn = os.path.join(folder, f)
            print fn
            zf.write(fn)
filelist = ['bsmedit.py', 'backup.py']
zf = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)

def add_folder_r(zf, path):
    for root, dirs, files in os.walk(path):
        for file in files:
            print os.path.join(root, file)
            zf.write(os.path.join(root, file))
for f in filelist:
    print f
    zf.write(f)
add_folder(zf, 'bsm', '.py')

add_folder(zf, 'main', '.py')
if not lite:
    add_folder_r(zf, 'examples' )
    add_folder_r(zf, 'systemc-2.1')
    add_folder_r(zf, 'xsc')
    add_folder_r(zf, 'libs')
zf.close()

# p = subprocess.Popen(['git', 'describe', '--match', 'hardware', '--long'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
# out, err = p.communicate()

