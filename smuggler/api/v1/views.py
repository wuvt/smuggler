#!/usr/bin/env python3

from flask import jsonify, request, abort
from smuggler.api.v1 import bp
from smuggler import app
from smuggler.tasks import moss_create_track, impala_create_track
import tempfile
import os


@bp.route('/')
def api_version_info():
    return jsonify({'stable': False})


@bp.route('/holdings/<uuid:id>/music/<path:path>', methods=['POST', 'PUT'])
def upload_track(id, path):
    # TODO open random file
    tempfile.tempdir = app.config['TEMP_DIR']
    f = tempfile.NamedTemporaryFile(delete=False, mode='wb')
    tmpfname = f.name
    f.write(request.data)
    f.close()

    # These are intentionally synchronous so the client knows whether or not
    # their upload succeeded in both places. If it didn't, the client must
    # rollback the changes made or overwrite them with the same UUID
    try:
        moss_create_track(id, tmpfname, path)
        impala_create_track(id, tmpfname, path)
        os.unlink(tmpfname)

    except:
        abort(500)

    return "ok"


@bp.route('/holdings/<uuid:id>/lock', methods=['POST', 'PUT'])
def lock_holding(id):
    # TODO
    return "ok"
