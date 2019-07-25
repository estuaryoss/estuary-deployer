from flask import Flask


def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object('rest.api.flask_config.Config')
    with app.app_context():
        return app
