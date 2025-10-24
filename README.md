## Choose-Your-Own-Adventure (Flask + SQL + AI)

### Features
- Email/password and Google OAuth login
- Start a story by entering a book title
- AI extracts 5 main characters, you pick one
- AI generates a 30+ chapter branching adventure with 3 choices per chapter
- Progress saved in SQL database

### Prerequisites
- Python 3.10+
- Create a virtual environment
- One of the AI providers:
  - Gemini API key (set `AI_PROVIDER=gemini`) - **Recommended for text and image generation**
  - Ollama with `llama3.2` pulled locally (default), or
  - OpenAI API key (set `AI_PROVIDER=openai`), or
  - Stub mode (set `AI_PROVIDER=stub`)
- Google OAuth Client (Web) with authorized redirect URI: `http://localhost:5000/auth/google/callback`

### Setup
```bash
cd /Users/l27/Documents/LIT2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env with your secrets and AI provider
```

### Using Gemini (Recommended)
1) Get a Gemini API key from Google AI Studio: `https://makersuite.google.com/app/apikey`
2) In `.env`, set:
```
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here
```

### Using Ollama (default)
1) Install Ollama: see `https://ollama.com`
2) Pull the model:
```bash
ollama pull llama3.2
```
3) Ensure Ollama is running (by default it serves at `http://127.0.0.1:11434`).
4) In `.env`, set:
```
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2
```

### Using OpenAI instead (optional)
```
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Database
This app uses SQLAlchemy. By default it points to SQLite at `instance/app.db`.

```bash
export FLASK_APP=run.py
flask db init
flask db migrate -m "init schema"
flask db upgrade
```

### Run
```bash
python run.py
# or
FLASK_APP=run.py flask run
```

Then open `http://127.0.0.1:5000`.

### Notes
- In `stub` mode, the app uses deterministic outputs so you can test the flow without an AI backend.
- For Google OAuth, ensure the client is configured for `http://localhost:5000/auth/google/callback` in Google Cloud Console.

### Integrating ComfyUI for images

The app can use a Stable Diffusion-style HTTP API to generate chapter illustrations. By default it uses `SD_BASE_URL` (see `config.py`). If you run ComfyUI with an HTTP plugin or small wrapper that exposes an Automatic1111-compatible `/sdapi/v1/txt2img` endpoint, set the `COMFYUI_BASE_URL` environment variable to point at that server. The app will try `COMFYUI_BASE_URL` first, then fall back to `SD_BASE_URL`.

Example `.env` entries:

COMFYUI_BASE_URL=http://127.0.0.1:8188
SD_BASE_URL=http://127.0.0.1:7860

Notes:
- ComfyUI does not include a standard HTTP API by default; you may need a plugin (community) or a tiny proxy that exposes an Automatic1111-compatible `/sdapi/v1/txt2img` endpoint which returns base64 images in an `images` array.
- If you want direct ComfyUI workflow support (sending a workflow graph and polling for results), I can add a dedicated endpoint that converts our simple prompt into a workflow and runs it. That requires more setup (and potentially a ComfyUI server with a workflow-runner plugin).
