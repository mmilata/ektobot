ektobot
=======

Tool for manipulating music albums. Written with mp3 archives from
http://www.ektoplazm.com in mind.

For detailed usage, run

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
