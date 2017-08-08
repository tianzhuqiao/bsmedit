#from distutils.core import setup
from setuptools import setup
setup(name='bsmedit',
      version='3.0.0',
      description='another C/C++/SystemC Simulation Controller',
      author='Tianzhu Qiao',
      author_email='tq@feiyilin.com',
      url='http://bsmedit.feiyilin.com',
      license="MIT",
      platforms=["any"],
      #scripts=['bsmedit.py'],
      packages=['bsmedit', 'bsmedit.bsm'],
      entry_points={
          'gui_scripts': [
              'bsmedit = bsmedit.__main__:main'
          ]
      },
      install_requires=['wxpython', 'matplotlib', 'numpy']
     )
