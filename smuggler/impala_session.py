import requests
from beets.library import Item
from requests.auth import HTTPBasicAuth
from urllib.parse import urljoin
from smuggler import app


class ImpalaSession:
    def __init__(self, uri, username, password):
        self.uri = uri
        self.username = username
        self.password = password
        self.session = None
        self.login()

    def login(self):
        endpoint = urljoin(self.uri, 'api/v1/login')
        r = requests.get(endpoint,
                         auth=HTTPBasicAuth(self.username, self.password))
        if r.status_code < 200 or r.status_code >= 300:
            raise IOError(str(r.status_code) + ": Login to impala failed")

        self.session = r.cookies['session']

    def logout(self):
        endpoint = urljoin(self.uri, 'api/v1/logout')
        r = requests.get(endpoint,
                         cookies={'session': self.session})
        self.session = None
        if r.status_code < 200 or r.status_code >= 300:
            raise IOError(str(r.status_code) + ": Failed to logout of impala")

    def get(self, endpoint):
        endpoint = urljoin(self.uri, endpoint)
        if not self.session:
            self.login()
        return requests.get(endpoint, cookies={'session': self.session})

    def put(self, endpoint, resource):
        endpoint = urljoin(self.uri, endpoint)
        if not self.session:
            self.login()
        return requests.put(endpoint, data=resource,
                            cookies={'session': self.session})

    def patch(self, endpoint, data):
        endpoint = urljoin(self.uri, endpoint)
        if not self.session:
            self.login()
        return requests.patch(endpoint, data=data,
                              cookies={'session': self.session})

    def set_source_metadata(self, hid, metadata):
        """
        Sets the source metadata for a Holding. Only three fields may be
        modified: torrent_hash, source_url, and source_desc.
        """
        data = {}
        hid = str(hid)
        for key in ['torrent_hash', 'source_url', 'source_desc']:
            if key in metadata:
                data[key] = metadata[key]

        if 'torrent_hash' in data:
            data['torrent_hash'] = data['torrent_hash'].lower()

        r = self.patch('api/v1/holdings/' + hid, data=data)
        if r.status_code < 200 or r.status_code >= 300:
            raise IOError(str(r.status_code) + ": Failed to set src metadata")

    def get_holding_from_torrent(self, infohash):
        """
        Return the UUID of a Holding, if it exists. Else, return null.
        """
        if not infohash.isalnum():
            raise ValueError("infohash must be alphanumeric")
        infohash = infohash.lower()

        r = self.get('api/v1/holdings/search?torrent_hash=' + infohash)
        results = r.json()['results']
        if not results:
            return None
        else:
            return results[0]['id']

    def create_track(self, hgid, hid, tmpfname, path):
        """
        Creates the data corresponding to the track in impala associated with
        the holding uuid based on metadata gleaned from beets. If it fails,
        raises an exception.
        """
        try:
            # In the event the item isn't a music track, we need to prevent it
            # from getting added to impala but keep it in moss.
            i = Item.from_path(tmpfname)
        except:
            return

        # Create a stack and format if they don't already exist
        self._create_default_objects()

        # Create the holding group if it doesn't already exist
        self._create_holding_group(hgid, i)

        # Create the holding if it doesn't already exist
        self._create_holding(hgid, hid, i)

        # Create the track
        self._create_track(hid, path, i)

    def _create_default_objects(self):
        """
        Creates a format and stack in impala if it doesn't already exist
        """
        default_uuids = app.config['DEFAULT_UUIDS']

        data = {'id': default_uuids['format'],
                'name': "digital",
                'physical': False}
        r = self.put('api/v1/formats', data)

        # We expect a 409 if the resource already exists
        if r.status_code not in [200, 201, 409]:
            err = "Got {} from impala on format creation".format(r.status_code)
            raise IOError(err)

        data = {'id': default_uuids['stack'], 'name': "default"}

        r = self.put('api/v1/stacks', data)
        # We expect a 409 if the resource already exists
        if r.status_code not in [200, 201, 409]:
            err = "Got {} from impala on stack creation".format(r.status_code)
            raise IOError(err)

    def _create_holding_group(self, uuid, item):
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

        r = self.put('api/v1/holding_groups', data)

        # We expect a 409 if the resource already exists
        if r.status_code not in [200, 201, 409]:
            err = "Got {} from impala on holding group creation".format(r.status_code)
            raise IOError(err)

    def _create_holding(self, hgid, uuid, item):
        data = {'id': uuid,
                'label': item.label,
                'active': True,
                'holding_group_id': hgid,
                'format_id': app.config['DEFAULT_UUIDS']['format']}

        if item.comments:
            data['description'] = item.comments

        if item.mb_albumid:
            data['release_mbid'] = item.mb_albumid

        r = self.put('api/v1/holdings', data)

        # We expect a 409 if the resource already exists
        if r.status_code not in [200, 201, 409]:
            err = "Got {} from impala on holding creation".format(r.status_code)
            raise IOError(err)

    def _create_track_metadata(self, track_id, path, item):
        for key in item._fields.keys():
            value = str(getattr(item, key))
            data = {'key': key,
                    'value': value,
                    'track_id': track_id}
            r = self.put('api/v1/track_metadata', data)
            if r.status_code not in [200, 201, 409]:
                err = "Got {} from impala on metadata creation".format(r.status_code)
                raise IOError(err)

    def _create_track(self, hid, path, item):
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

        r = self.put('api/v1/tracks', data)

        # We expect a 409 if the resource already exists
        if r.status_code not in [200, 201, 409]:
            err = "Got {} from impala on track creation".format(r.status_code)
            raise IOError(err)

        track_id = r.json()['id']
        self._create_track_metadata(track_id, path, item)
