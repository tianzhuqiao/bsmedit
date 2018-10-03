from setuptools import setup, find_packages
exec(open("bsmedit/version.py").read())
setup(name='bsmedit',
      version=BSM_VERSION,
      description='C/C++/SystemC Visualizer',
      author='Tianzhu Qiao',
      author_email='tq@feiyilin.com',
      url='http://bsmedit.feiyilin.com',
      license="MIT",
      platforms=["any"],
      packages=find_packages(),
      include_package_data = True,
      entry_points={
          'gui_scripts': [
              'bsmedit = bsmedit.main:main'
          ]
      },
      install_requires=['wxpython', 'matplotlib', 'numpy', 'click', 'PyOpenGL',
                        'PyOpenGL_accelerate']
     )
