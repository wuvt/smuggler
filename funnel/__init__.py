from flask import Flask
from funnel import defaults
import os

app = Flask(__name__)
app.config.from_object(defaults)

config_path = os.environ.get('APP_CONFIG_PATH', 'config.py')
if config_path.endswith('.py'):
    app.config.from_pyfile(config_path, silent=True)
else:
    app.config.from_json(config_path, silent=True)

from funnel.api import v1


def init_app():
    app.register_blueprint(v1.bp, url_prefix='/api/v1')


init_app()

if __name__ == "__main__":
    app.run()
