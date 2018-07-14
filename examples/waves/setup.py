from setuptools import setup, find_packages
setup(name='waves',
      version='0.0.1',
      description='Waves',
      author='Tianzhu Qiao',
      author_email='tq@feiyilin.com',
      url='http://bsmedit.feiyilin.com',
      license="MIT",
      platforms=["any"],
      packages=find_packages(),
      entry_points={
          'gui_scripts': [
              'bsmedit-waves = waves:main'
          ]
      },
      install_requires=['bsmedit']
     )
