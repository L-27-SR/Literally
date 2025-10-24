import os
from dotenv import load_dotenv

load_dotenv()


# Resolve absolute instance directory and ensure it exists
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_PATH = os.path.join(BASE_DIR, "instance")
try:
	os.makedirs(INSTANCE_PATH, exist_ok=True)
except Exception:
	pass


class Config:
	SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
	SQLALCHEMY_DATABASE_URI = os.getenv(
		"DATABASE_URL",
		f"sqlite:///{os.path.join(INSTANCE_PATH, 'app.db')}"
	)
	SQLALCHEMY_TRACK_MODIFICATIONS = False

	# AI provider selection
	AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
	OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
	GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
	OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
	OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

	# Local Stable Diffusion (AUTOMATIC1111 API)
	SD_BASE_URL = os.getenv("SD_BASE_URL", "http://127.0.0.1:7860")
	SD_NEGATIVE_PROMPT = os.getenv("SD_NEGATIVE_PROMPT", "lowres, blurry, deformed, watermark, text, nsfw")

	# Optional: ComfyUI HTTP server base URL. If set, AIService will try to use
	# an Automatic1111-compatible txt2img endpoint hosted by ComfyUI or a
	# ComfyUI API plugin. Example: "http://127.0.0.1:8188"
	COMFYUI_BASE_URL = os.getenv("COMFYUI_BASE_URL")

	# Google OAuth
	GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
	GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
	OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "http://localhost:5000/auth/google/callback")

	SESSION_COOKIE_SECURE = False
	REMEMBER_COOKIE_SECURE = False
