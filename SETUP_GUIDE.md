# BabelFish Baby - Setup Guide

Complete guide to set up and run the BabelFish Baby application.

## Prerequisites

### System Requirements
- **Python**: 3.10 or higher
- **Operating System**: macOS, Linux, or Windows
- **RAM**: 2GB minimum
- **Storage**: 10GB available (for audio files and dependencies)

### Required API Keys
- **OpenAI API Key**: Get from https://platform.openai.com/api-keys
- **Hugging Face Token**: Get from https://huggingface.co/settings/tokens

### Required Software
- **ffmpeg**: Required for audio file conversion

## Step-by-Step Setup

### 1. Install ffmpeg

**macOS** (using Homebrew):
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows** (using Chocolatey):
```bash
choco install ffmpeg
```

Or download from: https://ffmpeg.org/download.html

**Verify installation**:
```bash
ffmpeg -version
```

### 2. Set Up Python Environment

Navigate to the project directory:
```bash
cd babelfish_baby
```

Create virtual environment:
```bash
python3 -m venv venv
```

Activate virtual environment:
- **macOS/Linux**: `source venv/bin/activate`
- **Windows**: `venv\Scripts\activate`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages including:
- FastAPI and Uvicorn (web framework)
- SQLAlchemy (database)
- OpenAI (AI predictions)
- Chroma (vector database)
- pydub (audio processing)
- And more...

### 4. Configure Environment Variables

The `.env` file has already been created with a random secret key. Now you need to add your API keys:

Edit the `.env` file:
```bash
nano .env  # or use your preferred editor
```

Add your API keys:
```
OPENAI_API_KEY=sk-your-actual-openai-key-here
HUGGINGFACE_API_KEY=hf_your-actual-huggingface-token-here
```

**Getting API Keys:**

**OpenAI**:
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-`)
4. Paste into `.env` file

**Hugging Face**:
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Select "Read" permissions
4. Copy the token (starts with `hf_`)
5. Paste into `.env` file

### 5. Initialize Database

The database has already been initialized with:
- All tables created
- 7 cry categories seeded
- Directories created

If you need to reinitialize:
```bash
rm app.db  # Remove existing database
rm -rf audio_files chroma_db  # Remove existing data
python scripts/init_db.py
```

### 6. Start the Server

```bash
./venv/bin/uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or on Windows:
```bash
venv\Scripts\uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The `--reload` flag enables auto-reload when code changes.

### 7. Access the Application

Open your browser and navigate to:
- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## First Time Usage

### Register an Account
1. Go to http://localhost:8000
2. Fill in the registration form
3. Create a username and strong password
4. Click "Register"

### Record Your First Cry
1. After logging in, click "Record New Cry"
2. Allow microphone permissions when prompted
3. Click "Start Recording"
4. Record a sound (can be any sound for testing)
5. Click "Stop Recording"
6. Wait for processing

### Label Your First Recordings
**Important**: The AI needs at least 3 labeled recordings before it can make predictions.

1. Go back to history page
2. You'll see a banner: "Please label your first few recordings"
3. Click "Label" on each recording
4. Select a category (hungry, tired, etc.)
5. Optionally add notes
6. Click "Save"

### Test AI Predictions
After labeling 3 recordings:
1. Record a 4th cry
2. The AI will automatically analyze it
3. You'll see an AI prediction
4. Validate if it's correct or wrong
5. Continue recording and labeling to improve accuracy

### Get Advice
1. Click "Get Advice" on any recording
2. Ask questions like:
   - "How do I get them to sleep?"
   - "Should I swaddle them?"
   - "When should I call the doctor?"
3. The AI chatbot will provide personalized advice

## Troubleshooting

### Issue: ModuleNotFoundError

**Symptom**: `ModuleNotFoundError: No module named 'fastapi'`

**Solution**:
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: ffmpeg not found

**Symptom**: `RuntimeWarning: Couldn't find ffmpeg or avconv`

**Solution**:
- Install ffmpeg (see step 1)
- Verify with `ffmpeg -version`
- Restart the server after installing

### Issue: OPENAI_API_KEY not set

**Symptom**: Audio uploads fail with "OpenAI client not initialized"

**Solution**:
- Check `.env` file exists
- Verify API key is correctly set
- Restart the server after adding keys

### Issue: Microphone not working

**Symptom**: Browser doesn't request microphone permission

**Solution**:
- Use **https** or **localhost** (microphone requires secure context)
- Check browser permissions settings
- Try a different browser (Chrome/Firefox recommended)

### Issue: Database locked

**Symptom**: `database is locked` error

**Solution**:
```bash
# Close any SQLite browser tools
# Stop all running servers
pkill -f uvicorn

# Restart server
./venv/bin/uvicorn main:app --reload
```

### Issue: Port already in use

**Symptom**: `Address already in use` error

**Solution**:
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9

# Or use a different port
./venv/bin/uvicorn main:app --reload --port 8001
```

### Issue: Hugging Face API is slow

**Symptom**: Recording processing takes 30+ seconds

**Explanation**: The MERT model may need to "warm up" on Hugging Face servers. First request can take 30-60 seconds.

**Solution**:
- Be patient for first recording
- Subsequent recordings will be faster
- Or upgrade to Hugging Face Pro for faster inference

### Issue: OpenAI rate limits

**Symptom**: "Rate limit exceeded" error

**Solution**:
- Wait a few minutes before trying again
- Check your OpenAI usage: https://platform.openai.com/usage
- Upgrade your OpenAI plan if needed

## Development Tips

### Running Tests
```bash
pytest
```

### Viewing Database
```bash
sqlite3 app.db
.tables
SELECT * FROM users;
SELECT * FROM cry_instances;
.quit
```

### Checking Logs
Server logs appear in the terminal where you ran uvicorn.

### Accessing API Documentation
Go to http://localhost:8000/docs to:
- See all endpoints
- Test API calls
- View request/response schemas

### Stopping the Server
Press `Ctrl+C` in the terminal where the server is running.

## Project Structure Quick Reference

```
babelfish_baby/
├── app/
│   ├── routers/          # API endpoints
│   │   ├── auth.py       # Login/register
│   │   ├── cries.py      # Cry management
│   │   └── chat.py       # Chat interface
│   ├── ai/               # AI integrations
│   │   ├── embeddings.py # MERT model
│   │   ├── predictions.py # Prediction pipeline
│   │   └── chatbot.py    # OpenAI chat
│   ├── models.py         # Database models
│   ├── database.py       # Database connection
│   └── vector_db.py      # Chroma integration
├── templates/            # HTML pages
├── static/               # CSS and JavaScript
├── scripts/              # Utility scripts
└── tests/                # Test suite
```

## Next Steps

After successful setup:
1. Read [API_REFERENCE.md](API_REFERENCE.md) for API details
2. Read [TECHNICAL_SPEC_REVISED.md](TECHNICAL_SPEC_REVISED.md) for system architecture
3. Check [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for development roadmap

## Known Limitations (MVP)

- No concurrent recording support
- No offline mode
- WAV audio format only
- English language only
- Single baby per user
- No mobile native app

## Getting Help

If you encounter issues not covered here:
1. Check the API documentation: http://localhost:8000/docs
2. Review error messages in terminal logs
3. Check `.env` file is properly configured
4. Ensure all dependencies are installed
5. Verify ffmpeg is accessible

## Security Notes (for Production)

This MVP setup is for development only. Before deploying to production:
- Use HTTPS (required for microphone access)
- Set strong SECRET_KEY
- Enable `secure=True` for cookies (in app/auth.py)
- Set up proper database backups
- Configure firewall rules
- Use environment-specific settings
- Add rate limiting
- Review CORS settings if using separate frontend

---

Ready to start? Run:
```bash
./venv/bin/uvicorn main:app --reload
```

Then open http://localhost:8000 in your browser!
