#!/usr/bin/env python3
"""Usage: client.py --server URI ALBUM ...

-h --help       show this
--server URI    specify server URI
ALBUM           directory to an album

This is an example client for smuggler that uploads an album and locks it
"""
from docopt import docopt
import uuid
import os
import requests
import sys
from os.path import split
from urllib.parse import urlparse, urljoin, quote

ALBUMART_FILENAMES = ['folder.jpg', 'cover.jpg', 'front.jpg']


def _put_resource(endpoint, fullpath=None, debug=True):
    if debug:
        print("PUT {}".format(endpoint))

    if fullpath:
        with open(fullpath, 'rb') as fh:
            data = fh.read()
            r = requests.put(endpoint, data=data)
    else:
        r = requests.put(endpoint)

    if r.status_code < 200 or r.status_code >= 300:
        print("ERROR: {}".format(r.status_code))


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

    for path in args['ALBUM']:
        hgid = uuid.uuid4()     # HoldingGroup UUID
        hid = uuid.uuid4()      # Holding UUID
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

#        endpoint = urljoin(server, '/api/v1/holdings/{}'.format(album_uuid))
#        r = requests.get(endpoint)
#        print("GET {}".format(endpoint))
#        pprint(r.json())
