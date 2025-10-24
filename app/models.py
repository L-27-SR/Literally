from datetime import datetime
from flask_login import UserMixin
from . import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    google_sub = db.Column(db.String(255), unique=True, nullable=True)
    github_id = db.Column(db.String(255), unique=True, nullable=True)
    discord_id = db.Column(db.String(255), unique=True, nullable=True)
    profile_picture_url = db.Column(db.String(512), nullable=True)
    favorite_book = db.Column(db.String(255), nullable=True)
    genre_preferences = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    stories = db.relationship("StorySession", backref="user", lazy=True)
    adventures = db.relationship("Adventure", backref="user", lazy=True)

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class StorySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    book_title = db.Column(db.String(255), nullable=False)
    selected_character = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_complete = db.Column(db.Boolean, default=False)

    chapters = db.relationship("Chapter", backref="session", lazy=True, order_by="Chapter.number")


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("story_session.id"), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    choice_a = db.Column(db.String(255), nullable=True)
    choice_b = db.Column(db.String(255), nullable=True)
    choice_c = db.Column(db.String(255), nullable=True)
    selected_choice = db.Column(db.String(1), nullable=True)  # 'A'|'B'|'C'
    image_url = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Alias model for StorySession to satisfy "Adventure" naming without breaking existing logic
class Adventure(db.Model):
    __table__ = StorySession.__table__
