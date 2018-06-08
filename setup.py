from setuptools import setup
from bsmedit.version import BSM_VERSION
setup(name='bsmedit',
      version=BSM_VERSION,
      description='Another C/C++/SystemC Simulation Controller',
      author='Tianzhu Qiao',
      author_email='tq@feiyilin.com',
      url='http://bsmedit.feiyilin.com',
      license="MIT",
      platforms=["any"],
      packages=['bsmedit', 'bsmedit.bsm'],
      entry_points={
          'gui_scripts': [
              'bsmedit = bsmedit.__main__:main'
          ]
      },
      install_requires=['wxpython', 'matplotlib', 'numpy', 'click']
     )
