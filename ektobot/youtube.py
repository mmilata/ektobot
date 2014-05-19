
import re
import time
import random
import logging
import os.path

import urllib2
import httplib
import httplib2

httplib2.RETRIES = 1

from apiclient.discovery import build
from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client.tools import run_flow

from utils import *
from source import Ektoplazm

class YouTube(object):
    MAX_RETRIES = 10
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, httplib.NotConnected,
        httplib.IncompleteRead, httplib.ImproperConnectionState,
        httplib.CannotSendRequest, httplib.CannotSendHeader,
        httplib.ResponseNotReady, httplib.BadStatusLine)
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

    class WtfGoogle(object):
        noauth_local_webserver = True
        logging_level = 'DEBUG'

    def __init__(self, secrets_file, dry_run=False):
        init_logger(self)
        self.dry_run = dry_run
        self.service = self._get_authenticated_service(secrets_file)
        self.sleeper = Sleeper(self.logger)

    def _get_authenticated_service(self, secrets_file):
        if self.dry_run:
            return None

        try:
            flow = flow_from_clientsecrets(secrets_file,
                scope='https://www.googleapis.com/auth/youtube')
        except oauth2client.clientsecrets.InvalidClientSecretsError:
            self.logger.error('Missing client secrets file {0}. '+
                    'Please obtain it from https://console.developers.google.com/')
            raise RuntimeError('Client secrets missing')

        storage = Storage('{0}-storage'.format(secrets_file))
        credentials = storage.get()

        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, self.WtfGoogle())

        return build('youtube', 'v3', http=credentials.authorize(httplib2.Http()))

    def upload_video(self, filename, title, description, tags=[]):
        self.logger.info(u'Uploading {0}'.format(title))
        self.logger.debug(u'Filename {0}'.format(filename))
        self.logger.debug(u'Description:\n{0}'.format(description))

        if self.dry_run:
            return 'dry-run-video-id'

        self.sleeper.sleep(30)

        insert_request = self.service.videos().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': '10' # 10 = music
                },
                'status': {
                    'privacyStatus': 'public'
                }
            },
            media_body=MediaFileUpload(filename, chunksize=-1, resumable=True)
        )

        response = None
        error = False
        retry = 0
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if 'id' in response:
                    self.logger.debug('Upload complete, id: {0}'.format(response['id']))
                    return response['id']
                else:
                    self.logger.error(u'Upload failed: {0}'.format(response))
                    raise RuntimeError('Error uploading video')
            except HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    self.logger.exception('Retriable HTTP error {0}'.format(e.resp.status))
                    error = True
                else:
                    raise
            except self.RETRIABLE_EXCEPTIONS as e:
                self.logger.exception('Retriable error')
                error = True

            if error:
                retry += 1
                if retry > self.MAX_RETRIES:
                    self.logger.error('Max retries exceeded')
                    raise RuntimeError('Error uploading video')

                max_sleep = 2 ** retry
                sleep_seconds = random.randint(0, max_sleep)
                self.logger.info('Retrying in {0} seconds'.format(sleep_seconds))
                time.sleep(sleep_seconds)

    def create_playlist(self, title, video_ids, description='', tags=[]):
        self.logger.info(u'Creating playlist {0}'.format(title))

        if self.dry_run:
            return 'dry-run-playlist-id'

        playlist_insert_response = self.service.playlists().insert(
            part='snippet,status',
            body={
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags
                },
                'status': {
                    'privacyStatus': 'public'
                }
            }
        ).execute()
        if 'id' not in playlist_insert_response:
            self.logger.error(u'Failed to create playlist: {0}'.format(response))
        playlist_id = playlist_insert_response['id']
        self.logger.debug(u'Playlist created, id: {0}'.format(playlist_id))

        for video_id in video_ids:
            insert_response = self.service.playlistItems().insert(
                part='snippet',
                body={
                    'snippet': {
                        'playlistId': playlist_id,
                        'resourceId': {
                            'kind': 'youtube#video',
                            'videoId': video_id
                        }
                    }
                }
            ).execute()

            if 'id' not in insert_response:
                self.logger.error(u'Failed to insert playlist item: {0}'.format(response))
                raise RuntimeError('Error adding playlist item')

            time.sleep(2)

        return playlist_id

    def update_video(self, video_id, desc_fn, tags_fn):
        if self.dry_run:
            return

        video_response = self.service.videos().list(
            part='id,snippet',
            id=video_id
        ).execute()

        try:
            snippet = video_response['items'][0]['snippet']
        except (IndexError, KeyError):
            raise RuntimeError('Video {0} not found: {1}'.format(video_id, video_response))

        snippet['tags'] = tags_fn(snippet.get('tags', []))
        snippet['description'] = desc_fn(snippet['description'])

        self.sleeper.sleep(2)
        response = self.service.videos().update(
            part='snippet',
            body={
                'snippet': snippet,
                'id': video_id
            }
        ).execute()
        return response['snippet']


old_ektoplazm_description = u'''Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Download the full album from Ektoplazm: {albumurl}'''

ektoplazm_description = u'''Download the full album from Ektoplazm: {albumurl}

Artist: {artist}
Track: {track}
Album: {album}
Track number: {trackno}

Tags: {tags}
License: {license}'''

ektoplazm_description_without_tags = u'''Download the full album from Ektoplazm: {albumurl}

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

def playlist_title(meta):
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

    return title[:60]

def ytupload(dirname, dry_run, secrets_file, url=None):
    meta = read_dirmeta(dirname)
    if 'url' not in meta:
        if url:
            e = Ektoplazm(url)
            meta['url'] = url
            meta['license'] = e.license.url
            meta['tags'] = e.tags
        else:
            meta['url'] = 'http://example.org'
            meta['license'] = ''
            meta['tags'] = set()

    video_ids = []

    desc_template = templates['default']
    tag_list = list(meta['tags'])
    if 'ektoplazm.com' in meta['url']:
        desc_template = templates['ektoplazm']
        tag_list += ['ektoplazm', 'music']

    youtube = YouTube(secrets_file, dry_run)

    for trk in meta['tracks']:
        filename = os.path.join(dirname, trk['video_file'])
        title = u'{0} - {1}'.format(trk['artist'], trk['track'])
        description = desc_template.format(
            artist = trk['artist'],
            track = trk['track'],
            album = meta['album'],
            trackno = trk['num'],
            tags = ', '.join(meta['tags']),
            license = meta['license'],
            albumurl = meta['url']
        )
        video_ids.append(youtube.upload_video(filename, title, description, tag_list))

    playlist_id = youtube.create_playlist(playlist_title(meta), video_ids, tags=tag_list)
    return (playlist_id, video_ids)

def parse_format(string, fmt, variables):
    # create RE
    fmt = re.escape(fmt)
    for var in variables:
        fmt = fmt.replace('\{'+var+'\}', '(?P<'+var+'>.*)')

    # run RE on string
    m = re.match(fmt, string)
    if m:
        return m.groupdict()

    return None

def ytdesc_process_album(youtube, urlmeta):
    logger = logging.getLogger('ytdesc')

    try:
        e = Ektoplazm(urlmeta.url)
    except urllib2.HTTPError as e:
        if e.code == 502:
            logger.warning('Bad gateway, trying again')
            time.sleep(10)
            e = Ektoplazm(urlmeta.url)
        else:
            raise

    urlmeta.tags = e.tags
    try:
        urlmeta.license = e.license.url
    except SyntaxError:
        logger.warning('No license link for {0}'.format(urlmeta.url))
        urlmeta.license = urlmeta.url

    def desc_fn(orig_desc):
        vidmeta = parse_format(orig_desc, ektoplazm_description,
                ['albumurl', 'artist', 'track', 'album', 'trackno', 'tags', 'license'])
        if vidmeta:
            logger.debug('Has new description, not updating')
            return orig_desc

        vidmeta = parse_format(orig_desc, old_ektoplazm_description,
                ['albumurl', 'artist', 'track', 'album', 'trackno'])
        if not vidmeta:
            vidmeta = parse_format(orig_desc, ektoplazm_description_without_tags,
                    ['albumurl', 'artist', 'track', 'album', 'trackno'])
        assert vidmeta

        vidmeta['tags'] = ', '.join(urlmeta.tags)
        vidmeta['license'] = urlmeta.license

        new_desc = ektoplazm_description.format(**vidmeta)
        logger.debug(u'Old description:\n{0}'.format(orig_desc))
        logger.debug(u'New description:\n{0}'.format(new_desc))
        return new_desc

    def tags_fn(ignored):
        return ['ektoplazm', 'music'] + list(e.tags)

    for video_id in urlmeta.youtube.videos:
        logger.debug('Updating {0}'.format(video_id))
        youtube.update_video(video_id, desc_fn, tags_fn)

def ytdesc(yt_secrets, meta, dry_run=False):
    logger = logging.getLogger('ytdesc')
    youtube = YouTube(yt_secrets, dry_run)

    for (url, urlmeta) in meta.urls.iteritems():
        logger.info('Processing {0}'.format(url))
        logger.debug('Playlist: {0}'.format(urlmeta.youtube.playlist))

        if urlmeta.youtube.result == 'failed':
            logger.debug('Skipping failed upload')
            continue

        if len(urlmeta.tags) != 0:
            logger.debug('Tags present - skipping')
            continue

        ytdesc_process_album(youtube, urlmeta)
        if not dry_run:
            meta.save()

if __name__ == '__main__':
    import sys, json
    from state import State
    logging.basicConfig(level=logging.DEBUG)

    youtube = YouTube('client_secrets.json')
    meta = State('ektobot.json')
    url = sys.argv[1]

    ytdesc_process_album(youtube, meta.url(url, create=False))
    meta.save()
