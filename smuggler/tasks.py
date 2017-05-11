from beets.library import Item
from os.path import join
import requests
from urllib.parse import urljoin
from smuggler import app


def moss_create_track(hid, tmpfname, path):
    """
    Uploads the file to moss at the path within a holding's UUID. If it
    fails, raises an exception.
    """
    moss_uri = app.config['MOSS_URI']
    endpoint = urljoin(moss_uri, join(str(hid), 'music', path))
    with open(tmpfname, 'rb') as f:
        data = f.read()
        r = requests.put(endpoint, data=data)
        if r.status_code < 200 or r.status_code >= 300:
            raise IOError("Got {} from moss".format(r.status_code))


def _create_default_objects():
    """
    Creates a format and stack in impala if it doesn't already exist
    """
    default_uuids = app.config['DEFAULT_UUIDS']
    impala_uri = app.config['IMPALA_URI']

    endpoint = urljoin(impala_uri, 'api/v1/formats')
    data = {'id': default_uuids['format'],
            'name': "digital",
            'physical': False}
    r = requests.put(endpoint, data=data)
    # We expect a 409 if the resource already exists
    if r.status_code not in [200, 201, 409]:
        err = "Got {} from impala on format creation".format(r.status_code)
        raise IOError(err)

    endpoint = urljoin(impala_uri, 'api/v1/stacks')
    data = {'id': default_uuids['stack'], 'name': "default"}

    r = requests.put(endpoint, data=data)
    # We expect a 409 if the resource already exists
    if r.status_code not in [200, 201, 409]:
        err = "Got {} from impala on stack creation".format(r.status_code)
        raise IOError(err)


def impala_create_track(hgid, hid, tmpfname, path):
    """
    Creates the data corresponding to the track in impala associated with the
    holding uuid based on metadata gleaned from beets. If it fails, raises an
    exception.
    """
    i = Item.from_path(tmpfname)

    # Create a stack and format if they don't already exist
    _create_default_objects()

    # Create the holding group if it doesn't already exist
    _create_holding_group(hgid, i)

    # Create the holding if it doesn't already exist
    _create_holding(hgid, hid, i)

    # Create the track
    _create_track(hid, path, i)


def _create_holding_group(uuid, item):
    impala_uri = app.config['IMPALA_URI']
    data = {'id': uuid,
            'album_title': item.album,
            'album_artist': item.albumartist,
            'active': True,
            'stack_id': app.config['DEFAULT_UUIDS']['stack']}

    if not data['album_artist']:
        data['album_artist'] = item.artist

    # XXX should we be trusting this data?
    if item.mb_releasegroupid:
        data['releasegroup_mbid'] = item.mb_releasegroupid

    endpoint = urljoin(impala_uri, 'api/v1/holding_groups')
    r = requests.put(endpoint, data=data)

    # We expect a 409 if the resource already exists
    if r.status_code not in [200, 201, 409]:
        err = "Got {} from impala on holding group creation".format(r.status_code)
        raise IOError(err)


def _create_holding(hgid, uuid, item):
    impala_uri = app.config['IMPALA_URI']
    data = {'id': uuid,
            'label': item.label,
            'active': True,
            'holding_group_id': hgid,
            'format_id': app.config['DEFAULT_UUIDS']['format']}

    if item.comments:
        data['description'] = item.comments

    if item.mb_albumid:
        data['release_mbid'] = item.mb_albumid

    endpoint = urljoin(impala_uri, 'api/v1/holdings')
    r = requests.put(endpoint, data=data)

    # We expect a 409 if the resource already exists
    if r.status_code not in [200, 201, 409]:
        err = "Got {} from impala on holding creation".format(r.status_code)
        raise IOError(err)


def _create_track(hid, path, item):
    impala_uri = app.config['IMPALA_URI']
    data = {'title': item.title,
            'artist': item.artist,
            'file_path': path,
            'track_num': 0,
            'disc_num': 0,
            'has_fcc': 'UNKNOWN',
            'holding_id': hid}

    if item.mb_trackid:
        data['track_mbid'] = item.mb_trackid

    try:
        data['track_num'] = int(item.track)
    except:
        pass

    try:
        data['disc_num'] = int(item.disc)
    except:
        pass

    endpoint = urljoin(impala_uri, 'api/v1/tracks')
    r = requests.put(endpoint, data=data)

    # We expect a 409 if the resource already exists
    if r.status_code not in [200, 201, 409]:
        err = "Got {} from impala on track creation".format(r.status_code)
        raise IOError(err)
