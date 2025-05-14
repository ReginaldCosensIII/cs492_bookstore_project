# app/__init__.py

from flask import Flask
from flask_login import LoginManager
from app.models.user import load_user  # Update path as needed
from app.auth.routes import auth_bp
from app.main.routes import main_bp

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.secret_key = 'your-secret-key'  # Required for session handling

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # User loader callback (assumes you have a function like this)
    login_manager.user_loader(load_user)

    return app
