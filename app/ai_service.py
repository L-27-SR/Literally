import os
from typing import List, Tuple

import requests
import re

try:
	from openai import OpenAI
	OPENAI_AVAILABLE = True
except Exception:
	OPENAI_AVAILABLE = False

try:
	import google.generativeai as genai
	GEMINI_AVAILABLE = True
except Exception:
	GEMINI_AVAILABLE = False

from config import Config


class AIService:
	def __init__(self, api_key: str | None):
		self.provider = (Config.AI_PROVIDER or "ollama").lower()
		self.api_key = api_key
		self.ollama_base = Config.OLLAMA_BASE_URL.rstrip("/") if Config.OLLAMA_BASE_URL else "http://127.0.0.1:11434"
		# Support comma-separated list of models for fallback, e.g. "llama3.1:70b, llama3.1:8b, llama3.2"
		ollama_models = (Config.OLLAMA_MODEL or "llama3.2").split(",")
		self.ollama_models: List[str] = [m.strip() for m in ollama_models if m.strip()]
		self.client = OpenAI(api_key=api_key) if (self.provider == "openai" and api_key and OPENAI_AVAILABLE) else None
		
		# Initialize Gemini
		if self.provider == "gemini" and api_key and GEMINI_AVAILABLE:
			genai.configure(api_key=api_key)
			# Try different model names in order of preference (using the correct model names)
			model_names = [
				'gemini-2.5-flash',
				'gemini-2.0-flash', 
				'gemini-flash-latest',
				'gemini-pro-latest'
			]
			self.gemini_model = None
			for model_name in model_names:
				try:
					self.gemini_model = genai.GenerativeModel(model_name)
					# Test the model with a simple request
					test_response = self.gemini_model.generate_content("test")
					if test_response and hasattr(test_response, 'text'):
						print(f"Successfully initialized Gemini with model: {model_name}")
						break
				except Exception as e:
					print(f"Failed to initialize model {model_name}: {e}")
					continue
		else:
			self.gemini_model = None
			
		self.sd_base = Config.SD_BASE_URL.rstrip("/")
		self.sd_negative = Config.SD_NEGATIVE_PROMPT

	def _ollama_generate(self, prompt: str) -> str:
		# Try configured models in order until one returns non-empty text
		for model_name in self.ollama_models:
			try:
				resp = requests.post(
					f"{self.ollama_base}/api/generate",
					json={
						"model": model_name,
						"prompt": prompt,
						"stream": False,
						"options": {"temperature": 0.2, "num_ctx": 8192},
					},
					timeout=120,
				)
				resp.raise_for_status()
				data = resp.json()
				text = (data.get("response", "") or "").strip()
				if text:
					return text
			except Exception:
				continue
		return ""

	def _gemini_generate(self, prompt: str) -> str:
		"""Generate text using Gemini API"""
		if not self.gemini_model:
			return ""
		try:
			response = self.gemini_model.generate_content(prompt)
			if response and hasattr(response, 'text') and response.text:
				return response.text.strip()
			else:
				print(f"Gemini response was empty or invalid: {response}")
				return ""
		except Exception as e:
			print(f"Gemini generation failed: {e}")
			return ""

	def _parse_names(self, text: str) -> List[str]:
		if not text:
			return []
		text = text.strip()
		# Try JSON-style lists
		if text.startswith("[") and text.endswith("]"):
			try:
				import json
				arr = json.loads(text)
				return [str(x).strip() for x in arr if str(x).strip()]
			except Exception:
				pass
		# Fallback: split by commas/newlines/semicolons and bullets
		seps = ["\n", ",", ";"]
		parts = [text]
		for sep in seps:
			parts = sum([p.split(sep) for p in parts], [])
		clean = []
		for p in parts:
			p = p.strip(" -•\t").strip()
			if not p:
				continue
			clean.append(p)
		return clean

	def _filter_names(self, names: List[str], book_title: str) -> List[str]:
		if not names:
			return []
		blocked_substrings = [
			"book", "characters", "character", "novel", "plot", "context", "If it's", ":", "?", "!"
		]
		result: List[str] = []
		seen = set()
		for n in names:
			raw = n.strip()
			# skip lines that look like explanations
			lower = raw.lower()
			if any(bs in lower for bs in blocked_substrings):
				continue
			# heuristics: keep shortish names (<= 5 words), no parentheses
			if raw.count("(") or raw.count(")"):
				continue
			if len(raw.split()) > 5:
				continue
			# strip leading numbering and punctuation
			raw = re.sub(r'^[\s\-\.:\)\(\]\[]+|^[0-9]+[\).\-\s]*', '', raw)
			raw = raw.strip()
			if not raw:
				continue
			if raw not in seen:
				seen.add(raw)
				result.append(raw)
		return result

	def _sd_txt2img(self, prompt: str, out_dir: str, name_hint: str) -> str | None:
		try:
			# If a ComfyUI base URL is configured, try to use it first. Many
			# ComfyUI HTTP plugins expose an Automatic1111-compatible /sdapi/v1/txt2img
			# endpoint or a similar endpoint; apps can set COMFYUI_BASE_URL to point
			# to such a server. If that fails, fall back to SD_BASE_URL.
			comfy_base = getattr(self, 'comfy_base', None) or getattr(self, 'sd_base', None)
			if getattr(Config, 'COMFYUI_BASE_URL', None):
				comfy_base = Config.COMFYUI_BASE_URL.rstrip('/')
			if comfy_base and comfy_base != self.sd_base:
				try:
					resp = requests.post(
						f"{comfy_base}/sdapi/v1/txt2img",
						json={
							"prompt": prompt,
							"negative_prompt": self.sd_negative,
							"steps": 22,
							"width": 768,
							"height": 512,
						},
						timeout=180,
					)
					resp.raise_for_status()
					data = resp.json()
					imgs = data.get("images", [])
					if imgs:
						import base64
						b64 = imgs[0]
						if "," in b64:
							b64 = b64.split(",", 1)[1]
						binary = base64.b64decode(b64)
						filename = f"{name_hint}.png".replace("/", "_")
						path = os.path.join(out_dir, filename)
						with open(path, "wb") as f:
							f.write(binary)
						return "/static/generated/" + filename
				except Exception as e:
					print(f"ComfyUI image generation failed: {e}")
					# on any failure, we'll fall back to sd_base below
					pass
			os.makedirs(out_dir, exist_ok=True)
			resp = requests.post(
				f"{self.sd_base}/sdapi/v1/txt2img",
				json={
					"prompt": prompt,
					"negative_prompt": self.sd_negative,
					"steps": 22,
					"width": 768,
					"height": 512,
				},
				timeout=180,
			)
			resp.raise_for_status()
			data = resp.json()
			imgs = data.get("images", [])
			if not imgs:
				print("No images returned from Stable Diffusion")
				return None
			# images are base64 data URLs; save the first
			import base64
			b64 = imgs[0]
			if "," in b64:
				b64 = b64.split(",", 1)[1]
			binary = base64.b64decode(b64)
			filename = f"{name_hint}.png".replace("/", "_")
			path = os.path.join(out_dir, filename)
			with open(path, "wb") as f:
				f.write(binary)
			# return web path under /static
			return "/static/generated/" + filename
		except Exception as e:
			print(f"Stable Diffusion image generation failed: {e}")
			return None

	def _gemini_generate_image(self, prompt: str, out_dir: str, name_hint: str) -> str | None:
		"""Generate image using Gemini's image generation capabilities"""
		# Note: Gemini image generation is currently not working due to API limitations
		# and quota restrictions. This will be implemented when the API becomes more stable.
		# For now, we'll return None to fall back to Stable Diffusion or show placeholder.
		print("Gemini image generation is currently disabled due to API limitations")
		return None

	def extract_main_characters(self, book_title: str) -> List[str]:
		prompt1 = (
			f"You are a literary assistant. List the five main characters from the book '{book_title}'. "
			"Return ONLY names separated by commas. No extra words."
		)
		prompt2 = (
			f"List five main characters from '{book_title}' as a JSON array of strings only."
		)
		texts: List[str] = []
		if self.provider == "ollama":
			texts.append(self._ollama_generate(prompt1))
			if not texts[-1] or len(self._filter_names(self._parse_names(texts[-1]), book_title)) < 5:
				texts.append(self._ollama_generate(prompt2))
		elif self.provider == "gemini":
			texts.append(self._gemini_generate(prompt1))
			if not texts[-1] or len(self._filter_names(self._parse_names(texts[-1]), book_title)) < 5:
				texts.append(self._gemini_generate(prompt2))
		elif self.client:
			resp = self.client.chat.completions.create(
				model="gpt-4o-mini",
				messages=[{"role": "user", "content": prompt1}],
				max_tokens=128,
			)
			texts.append(resp.choices[0].message.content.strip())
			if len(self._filter_names(self._parse_names(texts[-1]), book_title)) < 5:
				resp2 = self.client.chat.completions.create(
					model="gpt-4o-mini",
					messages=[{"role": "user", "content": prompt2}],
					max_tokens=128,
				)
				texts.append(resp2.choices[0].message.content.strip())
		names: List[str] = []
		for t in texts:
			cand = self._filter_names(self._parse_names(t), book_title)
			if len(cand) >= 5:
				names = cand
				break
			elif not names:
				names = cand
		# Ensure exactly 5
		fallback = [
			f"{book_title} Protagonist",
			"Best Friend",
			"Detective",
			"Antagonist",
			"Witness",
		]
		names = (names + [n for n in fallback if n not in names])[:5]
		return [n if n else "Character" for n in names[:5]]

	def generate_chapter(self, book_title: str, character: str, chapter_num: int, history: List[Tuple[int, str, str]]):
		history_text = "\n".join(
			f"Chapter {n}: {summary} | Choice {choice}" for n, summary, choice in history
		)
		prompt = (
			f"We're writing a branching adventure for '{book_title}'. Player is '{character}'.\n"
			f"We are at Chapter {chapter_num}. Prior chapters and choices: \n{history_text}\n"
			"Write the next chapter (150-250 words) immersive 2nd-person. Do NOT include a heading like 'Chapter N:'. End with three distinct numbered options."
		)
		if self.provider == "ollama":
			text = self._ollama_generate(prompt)
			if not text:
				content = (
					f"Chapter {chapter_num}: {character} ventures deeper into '{book_title}'. "
					f"A challenge appears based on prior choice {history[-1][2] if history else 'N/A'}."
				)
				choices = ["Go left into the mist", "Confront the guardian", "Retreat and plan"]
				return content, choices, None
		elif self.provider == "gemini":
			text = self._gemini_generate(prompt)
			if not text:
				content = (
					f"Chapter {chapter_num}: {character} ventures deeper into '{book_title}'. "
					f"A challenge appears based on prior choice {history[-1][2] if history else 'N/A'}."
				)
				choices = ["Go left into the mist", "Confront the guardian", "Retreat and plan"]
				return content, choices, None
		else:
			if self.client:
				resp = self.client.chat.completions.create(
					model="gpt-4o-mini",
					messages=[{"role": "user", "content": prompt}],
					max_tokens=600,
				)
				text = resp.choices[0].message.content.strip()
			else:
				content = (
					f"Chapter {chapter_num}: {character} ventures deeper into '{book_title}'. "
					f"A challenge appears based on prior choice {history[-1][2] if history else 'N/A'}."
				)
				choices = ["Go left into the mist", "Confront the guardian", "Retreat and plan"]
				return content, choices, None

		lines = [l.strip() for l in text.splitlines() if l.strip()]
		# remove any model-added chapter heading to avoid mismatch with our UI number
		if lines and re.match(r'^chapter\s*\d+\s*[:\-]', lines[0], re.IGNORECASE):
			lines = lines[1:]
		options = [l for l in lines if l[:2].isdigit() or l.startswith(("1.", "2.", "3."))]
		choices = []
		for opt in options:
			opt = opt.lstrip("1234567890. ")
			if opt:
				choices.append(opt)
		if len(choices) < 3:
			choices += ["Option A", "Option B", "Option C"]
			choices = choices[:3]
		content_lines = []
		for l in lines:
			if l.startswith(("1.", "2.", "3.")):
				break
			content_lines.append(l)
		content = "\n".join(content_lines).strip()

		visual_prompt = f"illustration, {book_title}, chapter {chapter_num}, protagonist {character}; atmospheric, cinematic lighting"
		static_dir = os.path.join(os.path.dirname(__file__), "static", "generated")
		
		# Try Gemini image generation first, then fall back to Stable Diffusion
		image_url = None
		if self.provider == "gemini":
			image_url = self._gemini_generate_image(visual_prompt, static_dir, f"chapter_{chapter_num}_{character.replace(' ', '_')}")
		
		# If Gemini image generation failed, try Stable Diffusion as fallback
		if not image_url:
			image_url = self._sd_txt2img(visual_prompt, static_dir, f"chapter_{chapter_num}_{character.replace(' ', '_')}")
		
		return content, choices, image_url
