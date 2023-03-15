from setuptools import setup, find_packages
exec(open("bsmedit/version.py").read())

long_description = """
**bsmedit** is a C/C++/SystemC Visualizer.
- [Documentation](http://bsmedit.feiyilin.com)
"""
setup(python_requires='>=3.0',
      name='bsmedit',
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
      entry_points={'gui_scripts': ['bsmedit = bsmedit.__main__:main']},
      install_requires=[
          'wxpython>=4.2.0', 'matplotlib', 'numpy', 'click', 'PyOpenGL',
          'PyOpenGL_accelerate'
      ])
