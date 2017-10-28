#!/usr/bin/env python3
"""
This is an example client for smuggler that uploads all completed torrents in a
transmission download directory on localhost and locks them. Local files are
not modified.
"""
import argparse
import os
from os.path import split
import requests
import uuid
from urllib.parse import urlparse, urljoin, quote

import transmissionrpc

ALBUMART_FILENAMES = ['folder.jpg', 'cover.jpg', 'front.jpg']


def _put_resource(endpoint, auth, fullpath=None, debug=True):
    if debug:
        print("PUT {}".format(endpoint))

    if fullpath:
        with open(fullpath, 'rb') as fh:
            r = requests.put(endpoint, auth=auth, data=fh)
    else:
        r = requests.put(endpoint, auth=auth)

    if r.status_code < 200 or r.status_code >= 300:
        print("ERROR: {}".format(r.status_code))


def torrent_hash_exists(server, auth, torrent_hash):
    endpoint = urljoin(server, '/api/v1/torrents/{}'.format(torrent_hash))
    r = requests.get(endpoint, auth=auth)
    if r.status_code == 404:
        return False
    elif r.status_code >= 200 and r.status_code < 300:
        return True
    else:
        raise IOError("ERROR: {}".format(r.status_code))


def upload_albumart(server, auth, hid, fullpath, debug=True):
    """
    Upload the album art to the server for the specified holding ID.
    """
    endpoint = urljoin(server, '/api/v1/holdings/{}/albumart'.format(hid))
    return _put_resource(endpoint, auth, fullpath=fullpath, debug=debug)


def upload_track(server, auth, hgid, hid, relpath, fullpath, debug=True):
    """
    Upload the track at fullpath to the smuggler server for the specified hgid,
    hid, and relative path.
    """
    relpath = quote(relpath)
    endpoint = urljoin(server, '/api/v1/holding_groups/{}/{}/music/{}'.format(
        hgid, hid, relpath))
    return _put_resource(endpoint, auth, fullpath=fullpath, debug=debug)


def upload_source_metadata(server, auth, hid, metadata):
    endpoint = urljoin(server, '/api/v1/holdings/{}/source'.format(hid))
    r = requests.post(endpoint, auth=auth, data=metadata)
    if r.status_code < 200 or r.status_code >= 300:
        print("ERROR: {}".format(r.status_code))


def lock_album(server, auth, hid, debug=True):
    """
    Lock the album so that tracks cannot be modified.
    """
    endpoint = urljoin(server, '/api/v1/holdings/{}/lock'.format(hid))
    return _put_resource(endpoint, auth, fullpath=None, debug=debug)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smuggler-url', required=True,
                        help="URL to Smuggler server")
    parser.add_argument('--smuggler-user', required=True, help="Smuggler user")
    parser.add_argument('--smuggler-password', required=True,
                        help="Smuggler password")
    parser.add_argument('--transmission-port', type=int, default=9091,
                        help="Transmission RPC port (default 9091, must be on "
                             "localhost)")
    parser.add_argument('--transmission-user', required=True,
                        help="Transmission user")
    parser.add_argument('--transmission-password', required=True,
                        help="Transmission password")
    parser.add_argument('--limit-tracker', required=False,
                        help="Limit torrents to those on a specific tracker")
    parser.add_argument('directory', help="Transmission download directory")
    args = parser.parse_args()

    u = urlparse(args.smuggler_url)
    if len(u.scheme) <= 0 or len(u.netloc) <= 0:
        raise ValueError("Smuggler URL must be valid")

    server = args.smuggler_url
    auth = (args.smuggler_user, args.smuggler_password)

    tc = transmissionrpc.Client(address='localhost',
                                port=args.transmission_port,
                                user=args.transmission_user,
                                password=args.transmission_password)
    torrents = tc.get_torrents()

    to_upload = {}

    for t in torrents:
        f = t._fields

        if f['downloadDir'].value not in args.directory:
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

    for hash, data in to_upload.items():
        path = data['path']

        metadata = {}
        if data['trackers'].value:
            url = urlparse(data['trackers'].value[0]['announce'])
            # Sanitize URL to remove torrent key
            metadata['source_url'] = url.scheme + '://' + url.netloc
            # If we're limited by tracker, skip torrents that don't match
            if args.limit_tracker is not None and \
                    metadata['source_url'] != args.limit_tracker:
                continue
        elif args.limit_tracker is not None and \
                len(data['trackers'].value) <= 0:
            continue
        metadata['torrent_hash'] = hash
        print(metadata)

        hgid = uuid.uuid4()     # HoldingGroup UUID
        hid = uuid.uuid4()      # Holding UUID

        if torrent_hash_exists(server, auth, hash):
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

                    upload_track(server, auth, hgid, hid, relpath, fullpath)

                    if split(relpath)[1].lower() in ALBUMART_FILENAMES:
                        upload_albumart(server, auth, hid, fullpath)

            lock_album(server, auth, hid)

        elif os.path.isfile(path):
            print('Found file: ' + path)

            upload_track(server, auth, hgid, hid, data['name'], data['path'])
            lock_album(server, auth, hid)

        else:
            print('NOT A FILE: ' + path)
            continue

        upload_source_metadata(server, auth, hid, metadata)
