from setuptools import setup, find_packages
exec(open("bsmedit/version.py").read())

long_description = """
**bsmedit** is a C/C++/SystemC Visualizer.
- [Documentation](http://bsmedit.feiyilin.com)
"""
setup(name='bsmedit',
      version=__version__,
      description='C/C++/SystemC Visualizer',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='Tianzhu Qiao',
      author_email='tq@feiyilin.com',
      url='http://bsmedit.feiyilin.com',
      license="MIT",
      platforms=["any"],
      packages=find_packages(),
      include_package_data=True,
      entry_points={'gui_scripts': ['bsmedit = bsmedit.main:main']},
      install_requires=[
          'wxpython>=4.0.4', 'matplotlib', 'numpy', 'click', 'PyOpenGL',
          'PyOpenGL_accelerate'
      ])
