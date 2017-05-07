#!/usr/bin/env python3

from flask import make_response, json
from flask_restful import Api, Resource
from funnel.api.v1 import bp


class ApiVersionInfo(Resource):
    # No auth required
    def get(self):
        return {'stable': False}


class FunnelResource(Resource):
    # TODO user and machine auth
    pass


api = Api(bp)
api.add_resource(ApiVersionInfo, '/')


@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp
