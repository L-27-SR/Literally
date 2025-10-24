from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from flask_dance.contrib.google import google
from flask_dance.contrib.github import github
from flask_dance.contrib.discord import discord
from werkzeug.routing import BuildError
from . import db
from .models import User
from config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("login.html")


@auth_bp.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    if not email or not password:
        flash("Please provide email and password.", "warning")
        return redirect(url_for("auth.login_page"))
    user = User.query.filter_by(email=email).first()
    if not user or not user.password_hash:
        flash("Invalid credentials or account uses OAuth only.", "danger")
        return redirect(url_for("auth.login_page"))
    if not check_password_hash(user.password_hash, password):
        flash("Incorrect email or password.", "danger")
        return redirect(url_for("auth.login_page"))
    login_user(user, remember=True)
    return redirect(url_for("main.index"))


@auth_bp.get("/signup")
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    return render_template("signup.html")


@auth_bp.post("/signup")
def signup_post():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = (request.form.get("password") or "").strip()
    if not email or not password:
        flash("Email and password are required.", "warning")
        return redirect(url_for("auth.signup_page"))
    existing = User.query.filter_by(email=email).first()
    if existing and existing.password_hash:
        flash("An account with this email already exists.", "danger")
        return redirect(url_for("auth.login_page"))
    if existing and not existing.password_hash:
        # Upgrade OAuth-only account to also support local login
        existing.password_hash = generate_password_hash(password)
        if name and not existing.name:
            existing.name = name
        db.session.commit()
        login_user(existing, remember=True)
        return redirect(url_for("main.index"))
    # Create new local account
    user = User(name=name or None, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    login_user(user, remember=True)
    return redirect(url_for("main.index"))


@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login_page"))


@auth_bp.get("/login/google")
def login_google():
    try:
        return redirect(url_for("google.login"))
    except BuildError:
        flash("Google OAuth is not configured. Set GOOGLE_CLIENT_ID/SECRET.", "danger")
        return redirect(url_for("auth.login_page"))


@auth_bp.get("/login/github")
def login_github():
    try:
        return redirect(url_for("github.login"))
    except BuildError:
        flash("GitHub OAuth is not configured. Set GITHUB_CLIENT_ID/SECRET.", "danger")
        return redirect(url_for("auth.login_page"))


@auth_bp.get("/login/discord")
def login_discord():
    try:
        return redirect(url_for("discord.login"))
    except BuildError:
        flash("Discord OAuth is not configured. Set DISCORD_CLIENT_ID/SECRET.", "danger")
        return redirect(url_for("auth.login_page"))


@auth_bp.get("/oauth/google/finalize")
def oauth_finalize_google():
    if not google.authorized:
        flash("Google auth not authorized", "danger")
        return redirect(url_for("auth.login_page"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        flash("Failed to fetch Google user info", "danger")
        return redirect(url_for("auth.login_page"))
    data = resp.json()
    email = (data.get("email") or "").lower()
    sub = data.get("sub") or data.get("id")
    name = data.get("name")
    picture = data.get("picture")
    user = User.query.filter((User.google_sub == sub) | (User.email == email)).first()
    if not user:
        user = User(email=email, name=name, google_sub=sub, profile_picture_url=picture)
        db.session.add(user)
        db.session.commit()
    else:
        changed = False
        if not user.google_sub and sub:
            user.google_sub = sub
            changed = True
        if picture and user.profile_picture_url != picture:
            user.profile_picture_url = picture
            changed = True
        if changed:
            db.session.commit()
    login_user(user, remember=True)
    return redirect(url_for("main.index"))


@auth_bp.get("/oauth/github/finalize")
def oauth_finalize_github():
    if not github.authorized:
        flash("GitHub auth not authorized", "danger")
        return redirect(url_for("auth.login_page"))
    resp = github.get("/user")
    if not resp.ok:
        flash("Failed to fetch GitHub user", "danger")
        return redirect(url_for("auth.login_page"))
    data = resp.json()
    gid = str(data.get("id")) if data.get("id") is not None else None
    name = data.get("name") or data.get("login")
    avatar = data.get("avatar_url")
    # GitHub emails may require a separate call
    email = None
    emails = github.get("/user/emails")
    if emails.ok:
        for e in emails.json():
            if e.get("primary"):
                email = (e.get("email") or "").lower()
                break
        if not email and emails.json():
            email = (emails.json()[0].get("email") or "").lower()
    user = None
    if gid:
        user = User.query.filter_by(github_id=gid).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email or f"github_{gid}@users.noreply", name=name, github_id=gid, profile_picture_url=avatar)
        db.session.add(user)
        db.session.commit()
    else:
        changed = False
        if not user.github_id and gid:
            user.github_id = gid
            changed = True
        if avatar and user.profile_picture_url != avatar:
            user.profile_picture_url = avatar
            changed = True
        if changed:
            db.session.commit()
    login_user(user, remember=True)
    return redirect(url_for("main.index"))


@auth_bp.get("/oauth/discord/finalize")
def oauth_finalize_discord():
    if not discord.authorized:
        flash("Discord auth not authorized", "danger")
        return redirect(url_for("auth.login_page"))
    resp = discord.get("/users/@me")
    if not resp.ok:
        flash("Failed to fetch Discord user", "danger")
        return redirect(url_for("auth.login_page"))
    data = resp.json()
    did = str(data.get("id")) if data.get("id") is not None else None
    username = data.get("username")
    avatar = data.get("avatar")
    email = (data.get("email") or "").lower()
    avatar_url = None
    if did and avatar:
        avatar_url = f"https://cdn.discordapp.com/avatars/{did}/{avatar}.png"
    user = None
    if did:
        user = User.query.filter_by(discord_id=did).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email or f"discord_{did}@users.noreply", name=username, discord_id=did, profile_picture_url=avatar_url)
        db.session.add(user)
        db.session.commit()
    else:
        changed = False
        if not user.discord_id and did:
            user.discord_id = did
            changed = True
        if avatar_url and user.profile_picture_url != avatar_url:
            user.profile_picture_url = avatar_url
            changed = True
        if changed:
            db.session.commit()
    login_user(user, remember=True)
    return redirect(url_for("main.index"))
