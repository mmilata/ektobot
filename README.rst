
#######
ektobot
#######

Tool for manipulating music albums. Written with mp3 archives from
http://www.ektoplazm.com in mind.

Written by b42 in 2013.

requirements
============

Python library eyeD3 needs to be installed.

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

video
-----

Example:

::

    ektobot.py video .

Converts all mp3 files in current directory to videos stored in subdirectory
named ``video``.

youtube
-------

Does not work yet.

license
=======

WTFPL.
