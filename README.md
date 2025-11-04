# 🎙️ Voice Agent Backend API

A comprehensive FastAPI backend for an AI-powered wellness and voice journaling platform. Built with Google's Agent Development Kit (ADK), Firebase Firestore, and Gemini Live API integration.

## 🌟 Features

### 🎯 Core Functionality
- **Voice Journaling**: Real-time voice transcription and analysis using Google Gemini Live API
- **Wellness Analysis**: AI-powered emotional and mental wellness analysis with specialized agents
- **Study Stress Management**: Academic-focused wellness support and study recommendations
- **Priority Matrix**: Eisenhower Matrix task management system
- **Daily Journaling**: Track daily emotions, activities, and wellness metrics
- **Moodboard**: Visual mood tracking and analysis
- **Chat System**: Real-time chat with AI agents
- **Wearable Integration**: Health data from wearable devices
- **Statistics & Analytics**: Comprehensive user statistics and insights
- **Reddit Communities**: Community features for wellness support

### 🤖 AI Agents
- **General Wellness Agent**: Emotional analysis and personalized wellness recommendations
- **Study Stress Agent**: Academic-focused mental health support
- **MCP Server Integration**: Model Context Protocol server for study data management
- **Hybrid RAG System**: Retrieval-Augmented Generation for context-aware responses

### 🔥 Firebase Integration
- **Unified Database**: All features use Firebase Firestore for real-time sync
- **Authentication**: Firebase-based user authentication
- **Real-time Updates**: Live data synchronization across the Sahay ecosystem

## 🛠️ Tech Stack

- **Framework**: FastAPI 0.120.4
- **Database**: Firebase Firestore (unified)
- **AI/ML**: 
  - Google Gemini Live API
  - Google ADK (Agent Development Kit)
  - Mem0 for conversation memory
- **WebSockets**: Real-time bidirectional communication
- **Authentication**: JWT, Firebase Auth
- **Cloud Services**: Google Cloud Speech-to-Text, Cloud Storage, Secret Manager

## 📋 Prerequisites

- Python 3.8+
- Firebase project with Firestore enabled
- Google Cloud project with necessary APIs enabled
- Firebase service account key (JSON file)

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/StraightOuttaVellore-Google/google-hackathon-backend.git
cd google-hackathon-backend
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Setup

Create a `.env` file in the root directory (never commit this file):

```env
# Firebase Configuration
GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json
FIREBASE_PROJECT_ID=your-firebase-project-id

# Google Cloud Services
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=./firebase-service-account.json

# Speech-to-Text
GOOGLE_SPEECH_API_KEY=your-speech-api-key
VOICE_AGENT_STT_KEY_PATH=./voice-agent-stt-key.json

# Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Server Configuration
PORT=8000
ENVIRONMENT=development

# CORS (for frontend)
FRONTEND_URL=http://localhost:5173
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 4. Firebase Setup

1. Download your Firebase service account key from [Firebase Console](https://console.firebase.google.com)
2. Place it in the root directory as `firebase-service-account.json`
3. Ensure Firestore is enabled in your Firebase project

### 5. Run the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 6. API Documentation

Once the server is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 📁 Project Structure

```
.
├── main.py                 # FastAPI application entry point
├── firebase_db.py          # Firebase Firestore client initialization
├── firebase_models.py      # Firebase data models
├── routers/                # API route handlers
│   ├── auth.py            # Authentication endpoints
│   ├── voice_agent.py     # Voice agent WebSocket endpoints
│   ├── voice_journal.py   # Voice journaling endpoints
│   ├── wellness_analysis.py # Wellness analysis endpoints
│   ├── moodboard.py       # Moodboard features
│   ├── daily_journal.py   # Daily journal entries
│   ├── priority_matrix.py # Eisenhower Matrix tasks
│   ├── chat.py            # Chat endpoints
│   ├── stats.py           # Statistics endpoints
│   ├── wearable.py        # Wearable device data
│   └── reddit.py          # Reddit community features
├── agents/                 # AI agent implementations
│   ├── orchestrator.py    # Agent orchestration logic
│   ├── moodboard_wellness_agents/ # Wellness agents
│   ├── moodboard_study_agents/    # Study stress agents
│   └── mcp_server/        # MCP server for study data
├── hybrid_rag_manager.py  # RAG system for context-aware responses
├── utils.py               # Utility functions
└── requirements.txt       # Python dependencies
```

## 🔌 Key API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh JWT token

### Voice Journaling
- `POST /voice-journal/analyze` - Analyze voice journal entry
- `GET /voice-journal/sessions` - Get user's journal sessions
- `GET /voice-journal/sessions/{session_id}` - Get specific session

### Wellness Analysis
- `POST /wellness/analyze` - Run wellness analysis
- `GET /wellness/pathways` - Get wellness pathways
- `GET /wellness/recommendations` - Get AI recommendations

### Priority Matrix
- `GET /priority-matrix/tasks` - Get all tasks
- `POST /priority-matrix/tasks` - Create new task
- `PUT /priority-matrix/tasks/{task_id}` - Update task

### Voice Agent (WebSocket)
- `WS /voice-agent/ws/{client_id}` - Real-time voice agent connection

## 🐳 Docker Deployment

### Build Docker Image
```bash
docker build -t voice-agent-backend .
```

### Run Container
```bash
docker run -p 8000:8000 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/firebase-service-account.json \
  -v $(pwd)/firebase-service-account.json:/app/firebase-service-account.json:ro \
  voice-agent-backend
```

## ☁️ Google Cloud Deployment

### Using Cloud Run

1. **Build and push to Container Registry**:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/voice-agent-backend
```

2. **Deploy to Cloud Run**:
```bash
gcloud run deploy voice-agent-backend \
  --image gcr.io/PROJECT_ID/voice-agent-backend \
  --platform managed \
  --region us-central1 \
  --set-secrets="GOOGLE_APPLICATION_CREDENTIALS=firebase-service-account:latest" \
  --allow-unauthenticated
```

### Environment Variables in Cloud Run

Use Google Cloud Secret Manager for sensitive values:
- Store `firebase-service-account.json` as a secret
- Store API keys as secrets
- Reference secrets in Cloud Run deployment

See `../CI_CD_DEPLOYMENT_GUIDE.md` for detailed CI/CD setup.

## 🔒 Security Best Practices

⚠️ **Never commit sensitive files to the repository:**
- `.env` files
- `firebase-service-account.json`
- `voice-agent-stt-key.json`
- Any files containing API keys or credentials

✅ **Use Google Cloud Secret Manager** for production deployments.

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

## 📚 Documentation

- [Start Here Guide](./START_HERE.md) - Quick start guide
- [Database Architecture](./DATABASE_ARCHITECTURE.md) - Firebase schema
- [Firebase Setup](./FIREBASE_SETUP_GUIDE.md) - Firebase configuration
- [MCP Server README](./agents/mcp_server/README.md) - MCP server documentation
- [Agents README](./agents/README.md) - AI agents documentation

## 🔗 Related Projects

This backend is part of the larger **Sahay** ecosystem:

- **[Frontend](https://github.com/StraightOuttaVellore-Google/google-hackathon-frontend)** - React frontend application
- **[Discord Fullstack](https://github.com/StraightOuttaVellore-Google/discord-fullstack)** - Neumorphic chat interface
- **[ADK Wellness Bots](https://github.com/StraightOuttaVellore-Google/adk-mas-healthcare)** - AI wellness agents

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is part of the Google Hackathon submission.

## 👥 Authors

- **StraightOuttaVellore-Google** - [GitHub](https://github.com/StraightOuttaVellore-Google)

## 🙏 Acknowledgments

- Google Agent Development Kit (ADK)
- Firebase for real-time database
- Google Gemini Live API
- FastAPI community

---

**Note**: For production deployment, ensure all environment variables are set via Google Cloud Secret Manager. Never commit `.env` files or service account keys to the repository.

