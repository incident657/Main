from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config')  # Import config settings

    db.init_app(app)

    # Import and register routes
    from app.routes import main
    app.register_blueprint(main)

    return app
