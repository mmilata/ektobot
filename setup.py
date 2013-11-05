from setuptools import setup

setup(name='ektobot',
      version='0.1',
      description='Tool for manipulating music albums',
      long_description = open('README.rst').read(),
      url='http://github.com/mmilata/ektobot',
      author='Martin Milata',
      author_email='b42@srck.net',
      packages=['ektobot'],
      scripts=['bin/ektobot'],
      license='WTFPL')
