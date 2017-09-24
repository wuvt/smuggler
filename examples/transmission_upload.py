#!/usr/bin/env python3
"""
Usage: transmission_smuggler.py -u USER -p PASSWORD -P PORT --server URI DIRECTORY ...

-h --help       show this
--server URI    specify server URI
DIRECTORY       transmission download directories
-u USER         transmission username
-p PASSWORD     transmission password
-P PORT         transmission port (must be on localhost)

This is an example client for smuggler that uploads all completed torrents in a
transmission download directory on localhost and locks them. Local files are
not modified.
"""
import os
from os.path import split
import requests
import uuid
import sys
from urllib.parse import urlparse, urljoin, quote

from docopt import docopt
import transmissionrpc

ALBUMART_FILENAMES = ['folder.jpg', 'cover.jpg', 'front.jpg']

# TODO this should be a CLI arg
SMUGGLER_AUTH = ('user', 'hunter2')

def _put_resource(endpoint, fullpath=None, debug=True):
    if debug:
        print("PUT {}".format(endpoint))

    if fullpath:
        with open(fullpath, 'rb') as fh:
            data = fh.read()
            r = requests.put(endpoint, data=data, auth=SMUGGLER_AUTH)
    else:
        r = requests.put(endpoint, auth=SMUGGLER_AUTH)

    if r.status_code < 200 or r.status_code >= 300:
        print("ERROR: {}".format(r.status_code))


def torrent_hash_exists(server, torrent_hash):
    endpoint = urljoin(server, '/api/v1/torrents/{}'.format(torrent_hash))
    r = requests.get(endpoint, auth=SMUGGLER_AUTH)
    if r.status_code == 404:
        return False
    elif r.status_code >= 200 and r.status_code < 300:
        return True
    else:
        raise IOError("ERROR: {}".format(r.status_code))


def upload_albumart(server, hid, fullpath, debug=True):
    """
    Upload the album art to the server for the specified holding ID.
    """
    endpoint = urljoin(server, '/api/v1/holdings/{}/albumart'.format(hid))
    return _put_resource(endpoint, fullpath=fullpath, debug=debug)


def upload_track(server, hgid, hid, relpath, fullpath, debug=True):
    """
    Upload the track at fullpath to the smuggler server for the specified hgid,
    hid, and relative path.
    """
    relpath = quote(relpath)
    endpoint = urljoin(server, '/api/v1/holding_groups/{}/{}/music/{}'.format(hgid, hid, relpath))
    return _put_resource(endpoint, fullpath=fullpath, debug=debug)


def upload_source_metadata(server, hid, metadata):
    endpoint = urljoin(server, '/api/v1/holdings/{}/source'.format(hid))
    r = requests.post(endpoint, data=metadata, auth=SMUGGLER_AUTH)
    if r.status_code < 200 or r.status_code >= 300:
        print("ERROR: {}".format(r.status_code))


def lock_album(server, hid, debug=True):
    """
    Lock the album so that tracks cannot be modified.
    """
    endpoint = urljoin(server, '/api/v1/holdings/{}/lock'.format(hid))
    return _put_resource(endpoint, fullpath=None, debug=debug)


if __name__ == "__main__":
    args = docopt(__doc__)

    try:
        u = urlparse(args['--server'])
        server = args['--server']
    except:
        raise ValueError("Server must be a URL")
        sys.exit(1)

    tc = transmissionrpc.Client(address='localhost',
                                port=args['-P'],
                                user=args['-u'],
                                password=args['-p'])
    torrents = tc.get_torrents()

    to_upload = {}

    for t in torrents:
        f = t._fields

        if f['downloadDir'].value not in args['DIRECTORY']:
            continue
        if t.status not in ['seeding', 'stopped']:
            continue
        
        hash = f['hashString'].value
        to_upload[hash] = {
            'torrentFile': f['torrentFile'].value,
            'downloadDir': f['downloadDir'].value,
            'name': f['name'].value,
            'path': os.path.join(f['downloadDir'].value, f['name'].value),
            'trackers': f['trackers'],
        }

    for hash, dict in to_upload.items():
        path = dict['path']
        
        metadata = {}
        if dict['trackers'].value:
            url = urlparse(dict['trackers'].value[0]['announce'])
            # Sanitize URL to remove torrent key
            metadata['source_url'] = url.scheme + '://' + url.netloc
        metadata['torrent_hash'] = hash
        print(metadata)

        hgid = uuid.uuid4()     # HoldingGroup UUID
        hid = uuid.uuid4()      # Holding UUID

        if torrent_hash_exists(server, hash):
            print('Skipping ' + path + ': already exists in impala')
            continue

        if os.path.isdir(path):
            print('Found directory: ' + path)

            for root, dirs, files in os.walk(path):
                for name in files:
                    fullpath = os.path.join(root, name)
                    relpath = fullpath[len(path):]
                    if relpath[0] == '/':
                        relpath = relpath[1:]

                    upload_track(server, hgid, hid, relpath, fullpath)

                    if split(relpath)[1].lower() in ALBUMART_FILENAMES:
                        upload_albumart(server, hid, fullpath)

            lock_album(server, hid)

        elif os.path.isfile(path):
            print('Found file: ' + path)

            upload_track(server, hgid, hid, dict['name'], dict['path'])
            lock_album(server, hid)

        else:
            print('NOT A FILE: ' + path)
            continue
        
        upload_source_metadata(server, hid, metadata)
