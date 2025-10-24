# Gemini Setup Guide

This guide will help you set up Gemini API for both text and image generation in your LIT2 application.

## Step 1: Get a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key

## Step 2: Configure Environment Variables

Create a `.env` file in your project root with the following content:

```env
# AI Provider Configuration
AI_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here

# Other required variables
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
OAUTH_REDIRECT_URI=http://localhost:5000/auth/google/callback
```

## Step 3: Test the Integration

Run the test script to verify everything is working:

```bash
python test_gemini.py
```

## Step 4: Run the Application

```bash
python run.py
```

## Features

- **Text Generation**: Gemini 2.5 Flash for generating story chapters and character extraction
- **Image Generation**: Currently uses Stable Diffusion (Gemini image generation has API limitations)
- **Character Extraction**: AI-powered extraction of main characters from book titles
- **Chapter Generation**: Dynamic story generation with branching choices

## Image Generation Setup (Optional)

For image generation, you need to run Stable Diffusion locally:

1. **Install Automatic1111 WebUI**:
   ```bash
   git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
   cd stable-diffusion-webui
   ./webui.sh --api
   ```

2. **Configure in your `.env`**:
   ```env
   SD_BASE_URL=http://127.0.0.1:7860
   ```

3. **Alternative: Use ComfyUI**:
   ```env
   COMFYUI_BASE_URL=http://127.0.0.1:8188
   ```

**Note**: Images are optional. The app will work perfectly without image generation - you'll just see "Image will appear here" placeholders.

## Current Limitations

- **Gemini Image Generation**: Currently disabled due to API limitations and quota restrictions
- **Stable Diffusion**: Requires local installation for image generation
- **Text Generation**: Works perfectly with Gemini 2.5 Flash

## Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not found"**
   - Make sure your `.env` file is in the project root
   - Check that the API key is correctly set in the `.env` file

2. **"Gemini model not initialized"**
   - Verify your API key is valid
   - Check your internet connection
   - Ensure the `google-generativeai` package is installed

3. **Text generation fails**
   - Check your API key permissions
   - Verify you have sufficient quota in Google AI Studio

### Getting Help

- Check the [Google AI Studio documentation](https://ai.google.dev/docs)
- Verify your API key in the [Google AI Studio console](https://makersuite.google.com/app/apikey)
- Ensure you have the latest version of the `google-generativeai` package
