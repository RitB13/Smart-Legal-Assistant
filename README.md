# Smart Legal Assistant 🏛️

An **AI-powered legal assistance platform** with **multilingual support** for 10+ languages. Ask legal questions in any language and get instant, accurate guidance powered by LLaMA 3.1 (via Groq API).

## 🌟 Features

- ✅ **Multilingual Support** - Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi, English
- ✅ **Auto Language Detection** - Automatically detects your query language
- ✅ **Language-Aware Responses** - LLM responds in your language
- ✅ **Fast & Reliable** - Powered by Groq API (70B LLaMA model)
- ✅ **Modern UI** - Built with React, TypeScript, Tailwind CSS
- ✅ **Document Analysis** - Upload and analyze legal documents
- ✅ **Comprehensive Logging** - Full request tracking with request IDs

## 📋 Tech Stack

### Backend
- **Framework**: FastAPI (Python)
- **LLM**: Groq API (LLaMA 3.1 70B)
- **Language Detection**: langdetect
- **Server**: Uvicorn
- **Data Validation**: Pydantic

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **UI Components**: shadcn/ui
- **Routing**: React Router v6

## 🚀 Quick Start (10 minutes)

### Prerequisites
- Python 3.8+ (backend)
- Node.js 16+ (frontend)
- Groq API Key (free at https://console.groq.com)

### Step 1: Backend Setup
```bash
# Navigate to project
cd Smart-Legal-Assistant

# Create & activate virtual environment
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and add your GROQ_API_KEY

# Start backend
uvicorn app:app --reload --port 8000
```

**Expected**: `Uvicorn running on http://127.0.0.1:8000`

### Step 2: Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

**Expected**: `Local: http://127.0.0.1:8080/`

### Step 3: Test It
- Open http://127.0.0.1:8080
- Click "Legal Assistant" 
- Send a question in any language
- Get response in your language! 🎉

---

## 📖 Documentation

- **[BACKEND_SETUP.md](BACKEND_SETUP.md)** - Detailed backend setup, troubleshooting, configuration
- **[FRONTEND_SETUP.md](FRONTEND_SETUP.md)** - Frontend setup, development guide
- **[ISSUES_FOUND.md](ISSUES_FOUND.md)** - 20+ issues found and fixes applied
- **[MULTILINGUAL_DOCUMENTATION.md](MULTILINGUAL_DOCUMENTATION.md)** - Multilingual implementation details

---

## 🌍 Supported Languages

| Code | Language | Status |
|------|----------|--------|
| en | English | ✅ |
| hi | हिंदी (Hindi) | ✅ |
| bn | বাংলা (Bengali) | ✅ |
| ta | தமிழ் (Tamil) | ✅ |
| te | తెలుగు (Telugu) | ✅ |
| mr | मराठी (Marathi) | ✅ |
| gu | ગુજરાતી (Gujarati) | ✅ |
| kn | ಕನ್ನಡ (Kannada) | ✅ |
| ml | മലയാളം (Malayalam) | ✅ |
| pa | ਪੰਜਾਬੀ (Punjabi) | ✅ |

---

## 🔌 API Example

```bash
POST /query
Content-Type: application/json

{
  "query": "What are my tenant rights?",
  "language": "en"  # Optional, auto-detected
}

# Response:
{
  "summary": "Tenants have many protections...",
  "laws": ["Residential Tenancies Act", ...],
  "suggestions": ["Document violations...", ...],
  "language": "en",
  "request_id": "uuid",
  "created_at": "2026-03-12T..."
}
```

---

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| "Unable to connect" | Verify backend running on port 8000 |
| GROQ_API_KEY error | Add key to `.env` file |
| Port 8000 in use | Use `--port 8001` for backend |
| Port 8080 in use | Vite tries 8081, 8082... |
| CORS error | Add frontend URL to `CORS_ORIGINS` in `.env` |

See [ISSUES_FOUND.md](ISSUES_FOUND.md) for comprehensive troubleshooting.

---

## 🛠️ Development

### Terminal 1: Backend
```bash
source venv/bin/activate
uvicorn app:app --reload --port 8000
```

### Terminal 2: Frontend
```bash
cd frontend
npm run dev
```

Both auto-reload on file changes.

---

## ⚙️ Configuration

### Backend `.env`
```env
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.1-70b-versatile
LLM_TIMEOUT=30
API_PORT=8000
DEBUG=False
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:8080
ENABLE_MULTILINGUAL=True
DEFAULT_LANGUAGE=en
```

### Frontend `.env.local`
```env
VITE_API_URL=http://localhost:8000
```

---

## 📂 Project Structure

```
Smart-Legal-Assistant/
├── app.py                      # FastAPI app
├── config.py                   # Configuration
├── requirements.txt            # Python dependencies
├── BACKEND_SETUP.md
├── FRONTEND_SETUP.md
├── ISSUES_FOUND.md
│
├── models/
│   └── query_model.py         # Request/Response schemas
├── routes/
│   └── query_routes.py        # API endpoints
├── services/
│   ├── llm_service.py         # Groq API integration
│   ├── language_service.py    # Language detection
│   └── parser.py              # Response parsing
│
└── frontend/                   # React app
    ├── src/pages/Chat.tsx     # Chat interface
    ├── package.json
    └── vite.config.ts
```

---

## ✨ Features in Detail

### Auto Language Detection
Queries are automatically analyzed to detect language, supporting 10 Indian + International languages.

### Language-Aware LLM
The LLM receives language-specific instructions to respond in the user's language.

### Comprehensive Logging
Every query gets a request ID for tracking through the system pipeline.

### Error Handling
Graceful handling of API timeouts, connection errors, and invalid responses with user-friendly messages.

---

## 🚀 Deployment

### Backend
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app:app
```

### Frontend
```bash
npm run build
# Deploy dist/ folder to Vercel, Netlify, AWS S3, etc.
```

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file

---

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and test
3. Commit: `git commit -m "feat: description"`
4. Push and create PR

---

## 🎯 Roadmap

- User authentication
- Chat history
- Document upload & analysis
- More languages (20+)
- Regional law databases
- Mobile app

---

**Built with ❤️ for Justice**  
**Version**: 1.0.0 (Multilingual)  
**Last Updated**: March 12, 2026
