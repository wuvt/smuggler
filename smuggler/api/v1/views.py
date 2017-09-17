#!/usr/bin/env python3

from flask import jsonify, request, abort
from smuggler.api.v1 import bp
from smuggler import app
from smuggler.auth import requires_auth
from smuggler.tasks import moss_create_track, moss_lock_holding
from smuggler.tasks import moss_create_albumart
from smuggler.impala_session import ImpalaSession
import tempfile
import os


@bp.route('/')
def api_version_info():
    return jsonify({'stable': True})


@bp.route('/holding_groups/<uuid:hgid>/<uuid:hid>/music/<path:path>',
          methods=['POST', 'PUT'])
@requires_auth
def upload_track(hgid, hid, path):
    tempfile.tempdir = app.config['TEMP_DIR']
    session = ImpalaSession(app.config['IMPALA_SERVER']['uri'],
                            app.config['IMPALA_SERVER']['username'],
                            app.config['IMPALA_SERVER']['password'])
    f = tempfile.NamedTemporaryFile(delete=False, mode='wb')
    tmpfname = f.name
    f.write(request.data)
    f.close()

    # These are intentionally synchronous so the client knows whether or not
    # their upload succeeded in both places. If it didn't, the client must
    # rollback the changes made or overwrite them with the same UUID
    try:
        moss_create_track(hid, tmpfname, path)
        session.create_track(hgid, hid, tmpfname, path)
        os.unlink(tmpfname)
    except:
        abort(500)

    return jsonify({'message': "ok"})


@bp.route('/holdings/<uuid:hid>/albumart', methods=['POST', 'PUT'])
@requires_auth
def upload_albumart(hid):
    tempfile.tempdir = app.config['TEMP_DIR']
    f = tempfile.NamedTemporaryFile(delete=False, mode='wb')
    tmpfname = f.name
    f.write(request.data)
    f.close()

    try:
        moss_create_albumart(hid, tmpfname)
        os.unlink(tmpfname)
    except:
        abort(500)

    return jsonify({'message': "ok"})


@bp.route('/holdings/<uuid:hid>/lock', methods=['POST', 'PUT'])
@requires_auth
def lock_holding(hid):
    moss_lock_holding(hid)
    return jsonify({'message': "ok"})


@bp.route('/holdings/<uuid:hid>/source', methods=['POST'])
@requires_auth
def set_holding_torrent_hash(hid):
    session = ImpalaSession(app.config['IMPALA_SERVER']['uri'],
                            app.config['IMPALA_SERVER']['username'],
                            app.config['IMPALA_SERVER']['password'])
    session.set_source_metadata(hid, request.form)

    return jsonify({'message': 'ok'})


@bp.route('/torrents/<infohash>', methods=['GET', 'HEAD'])
@requires_auth
def get_torrent(infohash):
    infohash = infohash.lower()
    session = ImpalaSession(app.config['IMPALA_SERVER']['uri'],
                            app.config['IMPALA_SERVER']['username'],
                            app.config['IMPALA_SERVER']['password'])

    result = session.get_holding_from_torrent(infohash)

    if result:
        return jsonify({'holding': result})
    else:
        abort(404)
