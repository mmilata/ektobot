
#######
ektobot
#######

Tool for manipulating music albums. Written with mp3 archives from
http://www.ektoplazm.com in mind.

Written by b42 in 2013-2014.

requirements
============

- For encoding videos, you need the ``ffmpeg`` program and ``eyeD3`` python
  module.
- For youtube uploads, you need to have the ``gdata`` module.
- For the rss functionality, you need the ``feedparser`` and ``BeautifulSoup``
  modules.

subcommands
===========

For detailed optional argument explanation, run

::

    ektobot.py --help

or::

    ektobot.py <subcommand> --help

unpack
------

Example:

::

    ektobot.py unpack "Artist - Album - 2013 - MP3.zip"

Unpacks the archive into directory ``Artist_-_Album``.

videos
------

Example:

::

    ektobot.py videos .

Converts all mp3 files in current directory to videos stored in subdirectory
named ``video``.

youtube
-------

Example:

::

    ektobot.py youtube Artist_-_Album/video

Uploads videos in ``Artist_-_Album/video`` to youtube. It will ask you for
username and password. The video directory has to be created by ektobot, the
command will fail otherwise.

additional info
===============

The script is quite messy and this documentation incomplete. I doubt anyone
else will ever use this module - let me know if you want to and I might improve
the code and/or documentation.

license
=======

WTFPL <http://www.wtfpl.net/>.
