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


def moss_create_albumart(hid, path):
    """
    Uploads the album art to moss for the holding's UUID. If it fails, raises
    an exception.
    """
    moss_uri = app.config['MOSS_URI']
    endpoint = urljoin(moss_uri, join(str(hid), 'albumart'))
    with open(path, 'rb') as f:
        data = f.read()
        r = requests.put(endpoint, data=data)
        if r.status_code < 200 or r.status_code >= 300:
            raise IOError("Got {} from moss".format(r.status_code))


def moss_lock_holding(hid):
    """
    Locks the holding so that music files can't be modified without manual
    intervention.
    """
    moss_uri = app.config['MOSS_URI']
    endpoint = urljoin(moss_uri, join(str(hid), 'lock'))
    r = requests.put(endpoint)
    if r.status_code < 200 or r.status_code >= 300:
        raise IOError("Got {} from moss".format(r.status_code))
