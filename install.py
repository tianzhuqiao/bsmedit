import subprocess

ver = '3.0-beta1'
# exe
subprocess.call(['c:/Program Files (x86)/NSIS/makensis.exe', 'bsmedit.nsi'])

# zip
import zipfile
from os import walk
try:
    import zlib
    compression = zipfile.ZIP_DEFLATED
except:
    compression = zipfile.ZIP_STORED

def add_folder(zf, folder, compression):
    try:
        for (dirpath, dirnames, filenames) in walk(folder):
            for fn in filenames:
                if not fn.endswith('.py'):
                    continue
                print 'adding %s/%s'%(dirpath, fn)
                zf.write('%s/%s'%(dirpath, fn), compress_type=compression)
    except:
        pass
modes = { zipfile.ZIP_DEFLATED: 'deflated',
          zipfile.ZIP_STORED:   'stored',
          }

print 'creating archive'
zf = zipfile.ZipFile('bsmedit-%s.zip'%ver, mode='w')
filelist = ['bsmedit.py', 'License', 'readme.txt']
try:
    add_folder(zf, 'bsm', compression)
    add_folder(zf, 'main', compression)
    for fn in filelist:
        print 'adding %s'%fn
        zf.write(fn, compress_type=compression)
finally:
    print 'closing'
zf.close()


