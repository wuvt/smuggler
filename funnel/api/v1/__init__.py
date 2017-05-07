from flask import Blueprint

bp = Blueprint('v1', __name__)

from funnel.api.v1 import views
