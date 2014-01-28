from setuptools import setup, find_packages

setup(name='ektobot',
      version='0.1',
      description='Tool for manipulating music albums',
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 2 :: Only',
          'Topic :: Communications :: File Sharing',
          'Topic :: Multimedia :: Sound/Audio',
      ],
      long_description = open('README.rst').read(),
      url='http://github.com/mmilata/ektobot',
      author='Martin Milata',
      author_email='b42@srck.net',
      packages=find_packages(),
      scripts=['bin/ektobot'],
      test_suite='nose.collector',
      tests_require=['nose'],
      install_requires=['eyeD3', 'gdata', 'BeautifulSoup', 'feedparser'],
      license='WTFPL')
