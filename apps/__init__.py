from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config')  # Import configuration

    db.init_app(app)

    # Import and register blueprints (routes)
    from app.routes import main
    app.register_blueprint(main)

    return app
