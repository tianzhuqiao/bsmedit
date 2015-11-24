import subprocess
import os 

BSM_VERSION_MAJOR = '3'
BSM_VERSION_MIDDLE = '0'
BSM_VERSION_MINOR = '9999'
def git_commit_num():
    p = subprocess.Popen(['git', 'describe', '--match', 'bsmedit', '--long'], 
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if out:
        idx1 = out.find('-')
        idx2 = out.rfind('-')
        if idx1 and idx2:
            return out[idx1+1:idx2]

BSM_VERSION_MINOR = git_commit_num()
BSM_VERSION = '.'.join([BSM_VERSION_MAJOR, BSM_VERSION_MIDDLE, BSM_VERSION_MINOR])
# write the version number to main\version.py
f = open('main/version.py', 'w')
f.write('BSM_VERSION_MAJOR = "%s"\n'%BSM_VERSION_MAJOR)
f.write('BSM_VERSION_MIDDLE = "%s"\n'%BSM_VERSION_MIDDLE)
f.write('BSM_VERSION_MINOR = "%s"\n'%BSM_VERSION_MINOR)
f.write('BSM_VERSION = "%s"\n'%BSM_VERSION)
f.close()

# installer
# update the version number
f = open('bsmedit.nsi', 'r')
lines = f.readlines()
for i in range(0, len(lines)):
    if "!define VERSION" in lines[i]:
        lines[i] = '  !define VERSION "%s"\n'%BSM_VERSION
        break
f.close()
f = open('bsmedit.nsi', 'w')
f.write(''.join(lines))
f.close()
subprocess.call(['c:/Program Files (x86)/NSIS/makensis.exe', 'bsmedit.nsi'])

# zip
import zipfile
from os import walk
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

def add_folder(zf, folder, ext, compression):
    try:
        for (dirpath, dirnames, filenames) in walk(folder):
            for fn in filenames:
                if not fn.endswith(ext):
                    continue
                print 'adding %s/%s'%(dirpath, fn)
                zf.write('%s/%s'%(dirpath, fn), compress_type=compression)
    except:
        pass
modes = { zipfile.ZIP_DEFLATED: 'deflated',
          zipfile.ZIP_STORED:   'stored',
          }

def add_folder_r(zf, path, compression):
    for root, dirs, files in os.walk(path):
        for file in files:
            print os.path.join(root, file)
            zf.write(os.path.join(root, file), compress_type=compression)

print 'creating archive'
zf = zipfile.ZipFile('release/bsmedit-%s.zip'%BSM_VERSION, mode='w')
filelist = ['bsmedit.py', 'License', 'readme.txt']
try:
    add_folder(zf, 'bsm', '.py', compression)
    add_folder(zf, 'main', '.py', compression)
    add_folder_r(zf, 'examples', compression)
    add_folder_r(zf, 'systemc-2.1', compression)
    add_folder_r(zf, 'xsc', compression)
    add_folder_r(zf, 'libs', compression)
    for fn in filelist:
        print 'adding %s'%fn
        zf.write(fn, compress_type=compression)
finally:
    print 'closing'
zf.close()


