# TODO: set up a setup.py this way:
# https://jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/

# TODO: requirements.txt (jinja2), or setuptools install_requires=?
# TODO: nosetest

from setuptools import setup

# https://chriswarrick.com/blog/2014/09/15/python-apps-the-right-way-entry_points-and-scripts/
setup(name='woeman',
      version='0.0.1',
      packages=['woeman'],
      entry_points={
          'console_scripts': [
              'woeman = woeman.__main__:main'
          ]
      },
      )
