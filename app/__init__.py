from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

# OAuth blueprints (Flask-Dance)
try:
    from flask_dance.contrib.google import make_google_blueprint
    from flask_dance.contrib.github import make_github_blueprint
    from flask_dance.contrib.discord import make_discord_blueprint
    FLASK_DANCE_AVAILABLE = True
except Exception:
    FLASK_DANCE_AVAILABLE = False

# Extensions
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login_page"


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True, template_folder="templates", static_folder="static")
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Import parts
    from . import models  # noqa: F401
    from .auth import auth_bp
    from .routes import main_bp

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Register OAuth provider blueprints (Flask-Dance)
    if FLASK_DANCE_AVAILABLE:
        # Google -> /auth/google
        if Config.GOOGLE_CLIENT_ID and Config.GOOGLE_CLIENT_SECRET:
            google_bp = make_google_blueprint(
                client_id=Config.GOOGLE_CLIENT_ID,
                client_secret=Config.GOOGLE_CLIENT_SECRET,
                scope=["openid", "email", "profile"],
                redirect_to="auth.oauth_finalize_google",
            )
            app.register_blueprint(google_bp, url_prefix="/auth")
        # GitHub -> /auth/github
        if getattr(Config, "GITHUB_CLIENT_ID", None) and getattr(Config, "GITHUB_CLIENT_SECRET", None):
            github_bp = make_github_blueprint(
                client_id=Config.GITHUB_CLIENT_ID,
                client_secret=Config.GITHUB_CLIENT_SECRET,
                scope="read:user,user:email",
                redirect_to="auth.oauth_finalize_github",
            )
            app.register_blueprint(github_bp, url_prefix="/auth")
        # Discord -> /auth/discord
        if getattr(Config, "DISCORD_CLIENT_ID", None) and getattr(Config, "DISCORD_CLIENT_SECRET", None):
            discord_bp = make_discord_blueprint(
                client_id=Config.DISCORD_CLIENT_ID,
                client_secret=Config.DISCORD_CLIENT_SECRET,
                scope=["identify", "email"],
                redirect_to="auth.oauth_finalize_discord",
            )
            app.register_blueprint(discord_bp, url_prefix="/auth")

    # Create instance folder
    try:
        import os
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    return app
