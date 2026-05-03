# TranscriberApp v2.0 - Clean Architecture

AI-powered audio transcription and summarization service built with Clean Architecture.

## 🏗️ Architecture

This project follows **Clean Architecture** principles with strict separation of concerns:

```
src/
├── domain/                      # 🧠 Business Logic Core
│   ├── entities/               # Business entities (TranscriptionJob, AudioFile)
│   ├── value_objects/          # Value objects (Language, JobStatus, Email)
│   ├── events/                 # Domain events
│   ├── exceptions/             # Domain-specific exceptions
│   └── ports/                  # Interfaces (TranscriptionServicePort, etc.)
│
├── application/                 # ⚙️ Use Cases & Business Rules
│   ├── use_cases/              # Application use cases
│   ├── dtos/                   # Data Transfer Objects (Pydantic)
│   └── services/               # Application services
│
├── presentation/                # 🟢 HTTP API Layer
│   ├── routers/                # FastAPI route handlers
│   ├── schemas/                # Pydantic request/response schemas
│   ├── dependencies/           # FastAPI dependency injection
│   └── middleware/             # Custom middleware
│
└── infrastructure/              # 🔵 External Interfaces
    ├── persistence/            # Database adapters (SQLAlchemy)
    ├── external/               # External service adapters (Groq, FFmpeg)
    └── config.py               # Dependency injection wiring
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- FFmpeg API server running
- Groq API key
- Gemini API key (optional)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="your-groq-key"
export GEMINI_API_KEY="your-gemini-key"
export FFMPPEG_API_URL="http://ffmpeg-server:8080"

# Run application
export PYTHONPATH=$PWD/src
python -m src.main
```

### API Usage

#### Process Audio File
```bash
curl -X POST "http://localhost:8000/api/process-audio" \
  -F "file=@audio.mp3" \
  -F "mode=tecnico" \
  -F "email=user@example.com"
```

#### Upload Audio Chunks
```bash
# Upload chunk
curl -X POST "http://localhost:8000/api/upload-chunk" \
  -F "chunk=@chunk_0000.webm" \
  -F "chunkIndex=0" \
  -F "totalChunks=18" \
  -F "uploadId=upload-123" \
  -F "nombre=meeting.webm" \
  -F "mode=tecnico"

# Complete upload
curl -X POST "http://localhost:8000/api/upload-complete" \
  -d "upload_id=upload-123" \
  -d "filename=meeting.webm" \
  -d "mode=tecnico"
```

#### Check Job Status
```bash
curl "http://localhost:8000/api/job/job-123"
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_API_KEY` | Groq API key | Required |
| `GEMINI_API_KEY` | Gemini API key | Optional |
| `FFMPEG_API_URL` | FFmpeg service URL | `http://ffmpeg-api-prod:8080` |
| `JOB_STORAGE_DIR` | Job persistence directory | `/tmp/transcriber_jobs` |
| `CHUNKS_BASE_DIR` | Audio chunks directory | `/app/audios/chunks` |

### Supported Modes

- `default` - Standard summarization
- `tecnico` - Technical summary
- `refinamiento` - Refined summary
- `ejecutivo` - Executive summary
- `bullet` - Bullet point summary

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Validate architecture
./scripts/validate-standards.sh
```

## 📊 Architecture Validation

Run the validation script to ensure Clean Architecture compliance:

```bash
./scripts/validate-standards.sh
```

The script checks:
- Domain layer purity (no external imports)
- Proper use of ports and adapters
- Correct dependency direction
- Pydantic usage in appropriate layers

## 🔄 Migration from v1.x

If migrating from the old structure:

```bash
# Backup old structure
cp -r transcriber_app backup/

# Run migration helper
./scripts/migration-helper.sh

# Update your scripts to use src.main instead of main
```

## 📈 Key Features

- ✅ **Real-time chunk processing** - Process audio chunks as they arrive
- ✅ **Multiple AI providers** - Groq and Gemini support
- ✅ **Asynchronous processing** - Background job execution
- ✅ **Clean Architecture** - Maintainable and testable code
- ✅ **Comprehensive error handling** - Robust failure recovery
- ✅ **File-based persistence** - Job state survives restarts

## 🤝 Contributing

1. Follow Clean Architecture principles
2. Run `./scripts/validate-standards.sh` before committing
3. Add tests for new features
4. Update documentation

## 📝 License

[Add your license here]