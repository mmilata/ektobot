
import re
import time
import logging
import os.path

from utils import *

old_ektoplazm_description = u'''Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Download the full album from Ektoplazm: {albumurl}'''

ektoplazm_description = u'''Download the full album from Ektoplazm: {albumurl}

Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}'''


default_description = u'''Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Uploaded by ektobot http://github.com/mmilata/ektobot'''

templates = {
    'default'  : default_description,
    'ektoplazm': ektoplazm_description
}

def ytlogin(email, passwd, dry_run=False):
    import gdata.youtube.service

    (email, passwd) = ask_email_password(email, passwd)

    yt_service = gdata.youtube.service.YouTubeService()
    #yt_service.ssl = True
    yt_service.developer_key = 'AI39si5d9grkxFwwm603wvh2toZxshBqVkCWalTT3UXB4b3W3TJz0bCwBv0qqRN9LeQDz0FAXOfCaSW35mAbtj3pnI8cXKu7YA'
    yt_service.source = 'ektobot'
    yt_service.client_id = USER_AGENT
    yt_service.email = email
    yt_service.password = passwd
    if not dry_run:
        yt_service.ProgrammaticLogin()

    return yt_service

def ytupload(dirname, dry_run, email, passwd, url=None):
    import gdata.youtube

    logger = logging.getLogger('youtube')

    def yt_upload_video(yt_service, filename, title, description):
        media_group = gdata.media.Group(
            title       = gdata.media.Title(text=title),
            description = gdata.media.Description(description_type='plain', text=description),
            keywords    = gdata.media.Keywords(text='ektoplazm, music'),
            category    = gdata.media.Category(text='Music', label='Music', scheme='http://gdata.youtube.com/schemas/2007/categories.cat'),
            player      = None
        )

        video_entry = gdata.youtube.YouTubeVideoEntry(media=media_group)
        new_entry = yt_service.InsertVideoEntry(video_entry, filename)
        return new_entry.id.text.split('/')[-1]

    def yt_create_playlist(yt_service, meta, ids, dry_run=False):
        formats_artist = [
            u'{artist} - {album} ({year})',
            u'{artist} - {album}',
            u'{album}' ]
        formats_va = [
            u'{album} ({year})',
            u'{album}' ]

        formats = formats_va if meta['artist'] == 'VA' else formats_artist

        for fmt in formats:
            title = fmt.format(**meta)
            if len(title) <= 60:
                break
        title = title[:60]
        description = ''

        logger.info(u'Creating playlist {0}'.format(title))

        if not dry_run:
            playlist = yt_service.AddPlaylist(title, description)
            playlist_uri = playlist.feed_link[0].href #magic...
            for video_id in ids:
                playlist_entry = yt_service.AddPlaylistVideoEntryToPlaylist(playlist_uri, video_id)

    meta = read_dirmeta(dirname)
    playlist_ids = []

    desc_template = templates['default']
    if url and 'ektoplazm.com' in url:
        desc_template = templates['ektoplazm']

    yt_service = ytlogin(email, passwd, dry_run)

    for trk in meta['tracks']:
        filename = os.path.join(dirname, trk['video_file'])
        title = u'{0} - {1}'.format(trk['artist'], trk['track'])
        description = desc_template.format(
            artist = trk['artist'],
            track = trk['track'],
            album = meta['album'],
            trackno = trk['num'],
            albumurl = url if url else 'http://www.example.org/' #'http://www.ektoplazm.com/'
        )
        logger.info(u'Uploading {0}'.format(title))
        logger.debug(u'Filename {0}'.format(filename))
        logger.debug(u'Description:\n{0}'.format(description))
        if not dry_run:
            vid_id = yt_upload_video(yt_service, filename, title, description)
            playlist_ids.append(vid_id)
        logger.debug('Upload complete')
        time.sleep(60) # youtube's not happy when we're uploading too fast

    yt_create_playlist(yt_service, meta, playlist_ids, dry_run)

#def parse_format(string, fmt, variables):
#    # create RE
#    fmt = re.escape(fmt)
#    for var in variables:
#        fmt = fmt.replace('\{'+var+'\}', '(?P<'+var+'>.*)')
#
#    # run RE on string
#    m = re.match(fmt, string)
#    if m:
#        return m.groupdict()
#
#    raise ValueError('String did not match input format')
#
#def transform_format(string, informat, outformat, variables):
#    parsed = parse_format(string, informat, variables)
#    return outformat.format(**parsed)
#
#def reorder_video_description(yt_service, video_id):
#    entry = yt_service.GetYouTubeVideoEntry(video_id=video_id)
#    entry.media.description.text = transform_format(
#            entry.media.description.text,
#            old_ektoplazm_description,
#            ektoplazm_description,
#            ['artist', 'track', 'album', 'trackno', 'albumurl'])
#    yt_service.debug = True                  # problem somewhere here
#    print yt_service.UpdateVideoEntry(entry) #
