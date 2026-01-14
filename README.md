# BabelFish Baby 🍼

AI-powered baby cry detection and analysis web application.

## Overview

BabelFish Baby helps parents understand why their baby is crying using AI and machine learning. The app records baby cries, analyzes them using audio embeddings and historical patterns, and provides personalized advice on how to soothe the baby.

## Features

- **Audio Recording**: Record baby cries directly in the browser (up to 60 seconds)
- **AI Prediction**: ML-powered cry reason prediction based on historical patterns
- **Manual Labeling**: Label your first recordings to train personalized predictions
- **Audio Playback**: Play back previous recordings
- **Chat Assistant**: Get personalized advice from an AI chatbot
- **User Accounts**: Secure authentication with per-user data isolation

## Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 templates + vanilla JavaScript
- **Database**: SQLite + SQLAlchemy ORM
- **Vector Database**: Chroma (for embedding storage and KNN search)
- **AI/ML**:
  - MERT-v1-95M (Hugging Face) for audio embeddings
  - OpenAI GPT for predictions and chat

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- OpenAI API key
- Hugging Face API token

### Installation

1. **Clone the repository**:
   ```bash
   cd babelfish_baby
   ```

2. **Create a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   ```
   OPENAI_API_KEY=sk-your-key-here
   HUGGINGFACE_API_KEY=hf_your-token-here
   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

5. **Initialize the database**:
   ```bash
   python scripts/init_db.py
   ```

### Running the Application

**Development server**:
```bash
uvicorn main:app --reload
```

The application will be available at: http://localhost:8000

**Production server**:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Usage

1. **Register an account**: Navigate to http://localhost:8000 and create an account
2. **Record your first cries**: Click "Record New Cry" and record a baby cry (or any sound for testing)
3. **Label manually**: For your first 3 recordings, you'll need to manually label the cry reason
4. **AI predictions**: After 3+ labeled recordings, the AI will start predicting reasons
5. **Get advice**: Click "Get Advice" on any cry to chat with the AI assistant
6. **Play back**: Click play buttons to listen to previous recordings

## Project Structure

See [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for detailed file organization.

```
babelfish_baby/
├── app/                    # Main application code
│   ├── routers/            # API endpoints
│   ├── ai/                 # AI/ML integrations
│   └── utils/              # Utility functions
├── templates/              # HTML templates
├── static/                 # CSS, JavaScript, images
├── scripts/                # Setup and utility scripts
└── tests/                  # Test suite
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

Or see [API_REFERENCE.md](API_REFERENCE.md) for complete API documentation.

## Development

### Running Tests

```bash
pytest
```

### Database Inspection

```bash
sqlite3 app.db
.tables
SELECT * FROM users;
```

### Checking Logs

Server logs will appear in the terminal where you ran `uvicorn`.

## Troubleshooting

### Common Issues

**Issue: ModuleNotFoundError**
- Solution: Make sure virtual environment is activated and dependencies are installed

**Issue: OPENAI_API_KEY not found**
- Solution: Check that `.env` file exists and contains your API key

**Issue: Database locked**
- Solution: Close any SQLite browser tools and restart the server

**Issue: Microphone not working**
- Solution: Ensure browser has microphone permissions and you're using HTTPS or localhost

### Getting API Keys

**OpenAI API Key**:
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy and paste into `.env`

**Hugging Face Token**:
1. Go to https://huggingface.co/settings/tokens
2. Create a new token with "Read" permissions
3. Copy and paste into `.env`

## Deployment

See [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for deployment instructions.

Basic deployment steps:
1. Set up a VPS (Ubuntu recommended)
2. Install dependencies
3. Configure systemd service
4. Set up nginx as reverse proxy
5. Get SSL certificate with Let's Encrypt

## Contributing

This is an MVP/prototype project. Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - feel free to use this project for personal or educational purposes.

## Support

For issues or questions:
- Check [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) for development guidance
- Check [API_REFERENCE.md](API_REFERENCE.md) for API details
- Open an issue on GitHub

## Roadmap

See [TECHNICAL_SPEC_REVISED.md](TECHNICAL_SPEC_REVISED.md) for the complete feature roadmap.

Current status: **Phase 1 - MVP Development**

Next features:
- [ ] Complete audio recording and upload
- [ ] MERT audio embedding integration
- [ ] KNN search and prediction pipeline
- [ ] Chat assistant
- [ ] Mobile responsive design

## Acknowledgments

- MERT model: https://huggingface.co/m-a-p/MERT-v1-95M
- OpenAI API: https://platform.openai.com/
- Chroma DB: https://www.trychroma.com/

---

Built with ❤️ for parents and babies
