from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db
from .models import StorySession, Chapter
from .ai_service import AIService
from config import Config
import os
from werkzeug.utils import secure_filename
import bleach

main_bp = Blueprint("main", __name__)

ai_service = AIService(api_key=Config.GEMINI_API_KEY)


@main_bp.get("/")
def marketing():
	return render_template("marketing.html")


@main_bp.get("/app")
@login_required
def index():
	sessions = StorySession.query.filter_by(user_id=current_user.id).order_by(StorySession.created_at.desc()).all()
	return render_template("index.html", sessions=sessions)


@main_bp.post("/start")
@login_required
def start():
    raw_title = request.form.get("book_title", "")
    book_title = bleach.clean(raw_title, strip=True)[:255].strip()
    if not book_title:
        flash("Please enter a book title", "warning")
        return redirect(url_for("main.index"))
    session = StorySession(user_id=current_user.id, book_title=book_title)
    db.session.add(session)
    db.session.commit()
    return redirect(url_for("main.choose_character", session_id=session.id))


@main_bp.post("/session/<int:session_id>/delete")
@login_required
def delete_session(session_id: int):
	session_obj = StorySession.query.get_or_404(session_id)
	if session_obj.user_id != current_user.id:
		flash("Not authorized", "danger")
		return redirect(url_for("main.index"))
	# delete chapters first to satisfy FK
	Chapter.query.filter_by(session_id=session_id).delete()
	db.session.delete(session_obj)
	db.session.commit()
	flash("Story deleted", "success")
	return redirect(url_for("main.index"))


@main_bp.get("/session/<int:session_id>/characters")
@login_required
def choose_character(session_id: int):
	session_obj = StorySession.query.get_or_404(session_id)
	if session_obj.user_id != current_user.id:
		flash("Not authorized", "danger")
		return redirect(url_for("main.index"))
	characters = ai_service.extract_main_characters(session_obj.book_title)
	return render_template("choose_character.html", session=session_obj, characters=characters)


@main_bp.post("/session/<int:session_id>/characters")
@login_required
def select_character(session_id: int):
    session_obj = StorySession.query.get_or_404(session_id)
    if session_obj.user_id != current_user.id:
        flash("Not authorized", "danger")
        return redirect(url_for("main.index"))
    character = bleach.clean(request.form.get("character", ""), strip=True)[:255]
    if not character:
        flash("Please select a character", "warning")
        return redirect(url_for("main.choose_character", session_id=session_id))
    session_obj.selected_character = character
    db.session.commit()
    return redirect(url_for("main.chapter", session_id=session_id, number=1))


@main_bp.get("/session/<int:session_id>/chapter/<int:number>")
@login_required
def chapter(session_id: int, number: int):
	session_obj = StorySession.query.get_or_404(session_id)
	if session_obj.user_id != current_user.id:
		flash("Not authorized", "danger")
		return redirect(url_for("main.index"))
	chapter = Chapter.query.filter_by(session_id=session_id, number=number).first()
	if not chapter:
		# generate new chapter
		history = []
		prev_chapters = Chapter.query.filter_by(session_id=session_id).order_by(Chapter.number.asc()).all()
		for ch in prev_chapters:
			history.append((ch.number, ch.content[:120].replace("\n", " ") + ("..." if len(ch.content) > 120 else ""), ch.selected_choice or ""))
		content, choices, image_url = ai_service.generate_chapter(
			book_title=session_obj.book_title,
			character=session_obj.selected_character or "Protagonist",
			chapter_num=number,
			history=history,
		)
		chapter = Chapter(
			session_id=session_id,
			number=number,
			content=content,
			choice_a=choices[0] if len(choices) > 0 else None,
			choice_b=choices[1] if len(choices) > 1 else None,
			choice_c=choices[2] if len(choices) > 2 else None,
			image_url=image_url,
		)
		db.session.add(chapter)
		db.session.commit()
	return render_template("chapter.html", session=session_obj, chapter=chapter)


@main_bp.post("/session/<int:session_id>/chapter/<int:number>/back")
@login_required
def back_chapter(session_id: int, number: int):
	session_obj = StorySession.query.get_or_404(session_id)
	if session_obj.user_id != current_user.id:
		flash("Not authorized", "danger")
		return redirect(url_for("main.index"))
	if number <= 1:
		return redirect(url_for("main.chapter", session_id=session_id, number=1))
	# delete current chapter if exists, or delete the last chapter if user hit back on non-existent
	current = Chapter.query.filter_by(session_id=session_id, number=number).first()
	if current:
		db.session.delete(current)
		db.session.commit()
	return redirect(url_for("main.chapter", session_id=session_id, number=number - 1))


@main_bp.post("/session/<int:session_id>/chapter/<int:number>")
@login_required
def choose_option(session_id: int, number: int):
    choice = (request.form.get("choice") or "").strip().upper()
    chapter = Chapter.query.filter_by(session_id=session_id, number=number).first_or_404()
    if choice not in {"A", "B", "C"}:
        flash("Please choose a valid option", "warning")
        return redirect(url_for("main.chapter", session_id=session_id, number=number))
    chapter.selected_choice = choice
    db.session.commit()

    # If final chapter, complete and show session
    if number >= 30:
        session_obj = StorySession.query.get(session_id)
        session_obj.is_complete = True
        db.session.commit()
        return redirect(url_for("main.view_session", session_id=session_id))
    # Synchronously generate next chapter so it appears immediately after click
    next_number = number + 1
    # Only generate if it doesn't exist yet
    existing = Chapter.query.filter_by(session_id=session_id, number=next_number).first()
    if not existing:
        session_obj = StorySession.query.get_or_404(session_id)
        prev_chapters = Chapter.query.filter_by(session_id=session_id).order_by(Chapter.number.asc()).all()
        history = []
        for ch in prev_chapters:
            history.append((ch.number, ch.content[:120].replace("\n", " ") + ("..." if len(ch.content) > 120 else ""), ch.selected_choice or ""))
        content, choices, image_url = ai_service.generate_chapter(
            book_title=session_obj.book_title,
            character=session_obj.selected_character or "Protagonist",
            chapter_num=next_number,
            history=history,
        )
        next_chapter = Chapter(
            session_id=session_id,
            number=next_number,
            content=content,
            choice_a=choices[0] if len(choices) > 0 else None,
            choice_b=choices[1] if len(choices) > 1 else None,
            choice_c=choices[2] if len(choices) > 2 else None,
            image_url=image_url,
        )
        db.session.add(next_chapter)
        db.session.commit()
    return redirect(url_for("main.chapter", session_id=session_id, number=next_number))


@main_bp.get("/session/<int:session_id>")
@login_required
def view_session(session_id: int):
    session_obj = StorySession.query.get_or_404(session_id)
    if session_obj.user_id != current_user.id:
        flash("Not authorized", "danger")
        return redirect(url_for("main.index"))
    return render_template("session.html", session=session_obj)


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "GET":
        return render_template("profile.html", user=current_user)
    # POST: update profile fields
    name = bleach.clean(request.form.get("name", ""), strip=True)[:255]
    favorite_book = bleach.clean(request.form.get("favorite_book", ""), strip=True)[:255]
    genre_preferences = bleach.clean(request.form.get("genre_preferences", ""), strip=True)
    picture_url = request.form.get("profile_picture_url")
    if picture_url:
        picture_url = bleach.clean(picture_url, strip=True)[:512]
    # Optional upload handling
    file = request.files.get("profile_picture")
    if file and file.filename:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
        os.makedirs(upload_dir, exist_ok=True)
        path = os.path.join(upload_dir, filename)
        file.save(path)
        picture_url = "/static/generated/" + filename
    # Apply updates
    changed = False
    if name and name != current_user.name:
        current_user.name = name
        changed = True
    if picture_url and picture_url != current_user.profile_picture_url:
        current_user.profile_picture_url = picture_url
        changed = True
    if favorite_book != (current_user.favorite_book or ""):
        current_user.favorite_book = favorite_book
        changed = True
    if genre_preferences != (current_user.genre_preferences or ""):
        current_user.genre_preferences = genre_preferences
        changed = True
    if changed:
        db.session.commit()
        flash("Profile updated", "success")
    else:
        flash("No changes detected", "info")
    return redirect(url_for("main.profile"))
