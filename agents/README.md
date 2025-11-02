# ADK Wellness Bots

A comprehensive AI-powered wellness system built with Google's Agent Development Kit (ADK) that provides specialized mental health support through two distinct agents: General Wellness and Study Stress Management.

## 🌟 Features

### General Wellness Agent
- **Emotional Analysis**: Identifies emotions, focus areas, and mental wellness patterns
- **Personalized Recommendations**: Provides tailored advice, wellness exercises, and resources
- **Safety-First Approach**: Built-in safety review and refinement system
- **Memory Integration**: Remembers previous conversations for continuity

### Study Stress Agent
- **Academic-Focused Analysis**: Specialized in student mental health and study-related challenges
- **Study Strategy Recommendations**: Time management, study techniques, and academic wellness
- **Task Prioritization**: Uses Eisenhower Priority Matrix for effective planning
- **Student-Specific Resources**: Targeted tools and techniques for academic success

## 🏗️ Architecture

The system uses a sophisticated multi-agent architecture with advanced feedback loops:

### Core Components

- **Parallel Processing**: Summary and recommendation agents work simultaneously for efficiency
- **Safety Refinement Loop**: Iterative safety review and improvement system
- **Memory Management**: Persistent conversation memory using Mem0
- **Modular Design**: Separate agents for different wellness domains

### Loop Agent System

#### Safety Refinement Loop
The system implements a sophisticated **LoopAgent** that ensures all responses meet safety standards:

1. **Safety Reviewer Agent**: 
   - Analyzes responses for harmful content
   - Checks for crisis indicators and red flags
   - Verifies professional tone and appropriateness
   - Ensures no medical diagnosis or prescription advice

2. **Safety Refiner Agent**:
   - Refines responses based on safety feedback
   - Removes harmful content and adds disclaimers
   - Improves professional tone
   - Adds crisis resource information when needed

3. **Iterative Improvement**:
   - Maximum 3 iterations to prevent infinite loops
   - Automatic escalation for serious concerns
   - Clean exit when safety criteria are met

#### Feedback Mechanisms

- **Real-time Safety Scoring**: 0.0-1.0 safety assessment
- **Concern Detection**: Identifies specific safety issues
- **Modification Tracking**: Logs required changes
- **Approval System**: Binary approval for summary and recommendations
- **Escalation Protocol**: Routes serious concerns to human review

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud Platform account
- Environment variables configured

### Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:StraightOuttaVellore-Google/adk-wellness-bots.git
   cd adk-wellness-bots
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   export MODEL_NAME="your-model-name"
   export GOOGLE_APPLICATION_CREDENTIALS="path-to-your-credentials.json"
   ```

### Usage

#### General Wellness Agent
```python
from moodboard_wellness_agents.agent import root_agent

# Process a wellness conversation
response = root_agent.run("I've been feeling really anxious lately...")
```

#### Study Stress Agent
```python
from moodboard_study_agents.agent import root_agent

# Process academic stress conversation
response = root_agent.run("I have my final exams next week and I'm having panic attacks...")
```

## 📝 Sample Inputs

### General Wellness Examples

**Anxiety & Stress:**
```
"I've been feeling really anxious lately. Work has been overwhelming with tight deadlines, and I can't seem to sleep properly. I keep worrying about everything and feel like I'm not good enough."
```

**Depression & Low Mood:**
```
"I've been feeling really down for the past few weeks. Nothing seems to bring me joy anymore, and I've been isolating myself from friends and family."
```

**Relationship Issues:**
```
"My partner and I have been fighting constantly lately. We can't seem to communicate without it turning into an argument."
```

### Study Stress Examples

**Exam Anxiety:**
```
"I have my final exams next week and I'm having panic attacks. I've been studying for 8 hours a day but I feel like I don't remember anything."
```

**Academic Perfectionism:**
```
"I'm a straight-A student but I'm completely overwhelmed. I spend 15 hours a day studying because I'm terrified of getting anything less than perfect grades."
```

**Procrastination:**
```
"I have three major assignments due this week but I keep procrastinating. I sit down to study but end up scrolling through social media for hours."
```

## 🔧 Configuration

### Environment Variables

- `MODEL_NAME`: The LLM model to use (e.g., "gemini-1.5-pro")
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to your Google Cloud credentials

### Memory Configuration

The system uses Mem0 for conversation memory. Configure your Mem0 settings as needed for your deployment.

## 🛡️ Safety Features

- **Multi-layer Safety Review**: Automated safety checking and refinement
- **Crisis Detection**: Identifies serious mental health concerns
- **Professional Boundaries**: Avoids medical diagnosis or prescription advice
- **Escalation System**: Routes serious concerns to human review

## 📊 Output Format

### Summary Agent Output
```json
{
    "summary": "detailed summary text",
    "emotions": ["list", "of", "emotions"],
    "focus_areas": ["main", "topics", "discussed"],
    "tags": ["relevant", "mental", "wellness", "tags"]
}
```

### Recommendation Agent Output
```json
{
    "recommendations": [
        {"title": "title", "description": "detailed advice", "category": "category_name"}
    ],
    "wellness_exercises": [
        {"name": "exercise name", "instructions": "step-by-step", "duration": "time needed"}
    ],
    "resources": [
        {"type": "resource type", "title": "title", "description": "how it helps"}
    ],
    "tone": "supportive/encouraging/gentle/motivating"
}
```

## 🔗 Related Projects

This project is part of the larger Sahay ecosystem. Here are the other components:

### Backend Services
- **[Backend API](https://github.com/StraightOuttaVellore-Google/google-hackathon-backend)** - FastAPI backend with RESTful APIs and WebSocket support
- **[MCP Server](https://github.com/StraightOuttaVellore-Google/sahay-mcp-server)** - Model Context Protocol server for study data management

### Frontend Applications
- **[Frontend App](https://github.com/StraightOuttaVellore-Google/google-hackathon-frontend)** - React frontend for the complete wellness platform
- **[Voice Agent](https://github.com/StraightOuttaVellore-Google/VoiceAgentGeminiLive)** - Real-time voice journaling with Google Gemini Live API

### Additional Features
- **[Discord Fullstack](https://github.com/StraightOuttaVellore-Google/discord-fullstack)** - Neumorphic Discord-style chat application
- **[Sahay Aura Glow](https://github.com/StraightOuttaVellore-Google/sahay-aura-glow)** - Complete voice journaling application with advanced features

## 🧪 Testing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest

# Run with coverage
pytest --cov=moodboard_wellness_agents --cov=moodboard_study_agents
```

### Test Coverage
- Unit tests for all agent functions
- Integration tests for safety loops
- Memory management testing
- Error handling validation

## 🚀 Deployment

### Production Setup
1. **Environment Configuration**:
   ```bash
   export MODEL_NAME="gemini-1.5-pro"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/credentials.json"
   export MEM0_API_KEY="your-mem0-api-key"
   ```

2. **Docker Deployment**:
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   CMD ["python", "-m", "moodboard_wellness_agents.agent"]
   ```

3. **Cloud Deployment**:
   - Google Cloud Run
   - AWS Lambda
   - Azure Container Instances

## 📊 Performance

### Optimization Features
- **Parallel Processing**: Summary and recommendation agents run simultaneously
- **Memory Caching**: Efficient conversation memory management
- **Safety Optimization**: Iterative safety review with early exit conditions
- **Resource Management**: Optimized for cloud deployment

### Monitoring
- **Safety Metrics**: Track safety scores and refinement iterations
- **Performance Logs**: Monitor agent response times
- **Memory Usage**: Track conversation memory growth
- **Error Tracking**: Comprehensive error logging and alerting

## 🔒 Security & Safety

### Safety Features
- **Multi-layer Safety Review**: Automated safety checking and refinement
- **Crisis Detection**: Identifies serious mental health concerns
- **Professional Boundaries**: Avoids medical diagnosis or prescription advice
- **Escalation System**: Routes serious concerns to human review
- **Content Filtering**: Advanced content moderation and safety checks

### Privacy Protection
- **Data Minimization**: Only necessary data is processed
- **Secure Communication**: All API calls use HTTPS
- **Memory Encryption**: Conversation memory is encrypted at rest
- **Audit Logging**: Comprehensive logging for compliance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes
- Ensure safety features are maintained

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Google's Agent Development Kit (ADK)
- Memory management powered by Mem0
- Designed for the Google GenAI Hackathon
- Inspired by evidence-based mental health practices
- Community feedback and contributions

## 📞 Support

For support and questions:
1. Check the [documentation](https://github.com/StraightOuttaVellore-Google/adk-mas-healthcare/wiki)
2. Open an issue in the GitHub repository
3. Contact the development team

## ⚠️ Important Disclaimer

**This system is designed for general wellness support and should not replace professional mental health care. Always consult with qualified healthcare providers for serious mental health concerns.**

### When to Seek Professional Help
- Suicidal thoughts or self-harm
- Severe depression or anxiety
- Substance abuse issues
- Psychotic symptoms
- Any mental health crisis

### Crisis Resources
- **National Suicide Prevention Lifeline**: 988
- **Crisis Text Line**: Text HOME to 741741
- **Emergency Services**: 911

---

**ADK Wellness Bots** - Empowering mental wellness through AI-powered support and guidance 🧠✨
