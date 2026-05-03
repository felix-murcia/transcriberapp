#!/bin/bash
# migration-helper.sh - Helper script for Clean Architecture migration

set -e

echo "🔄 TranscriberApp Clean Architecture Migration Helper"
echo "=================================================="

echo ""
echo "✅ Migration Status:"
echo "  - Domain layer: COMPLETED"
echo "  - Application layer: COMPLETED"
echo "  - Presentation layer: COMPLETED"
echo "  - Infrastructure layer: COMPLETED"
echo ""

echo "📁 New Structure:"
echo "  src/"
echo "  ├── domain/           # Business entities & rules"
echo "  ├── application/      # Use cases & business logic"
echo "  ├── presentation/     # FastAPI routes & schemas"
echo "  └── infrastructure/   # External adapters & config"
echo ""

echo "🚀 Running Application:"
echo "  cd /path/to/transcriberapp"
echo "  export PYTHONPATH=\$PWD/src"
echo "  python -m src.main"
echo ""

echo "📊 API Endpoints:"
echo "  POST /api/process-audio      # Process complete audio files"
echo "  POST /api/upload-chunk       # Upload audio chunks"
echo "  POST /api/upload-complete    # Complete chunked upload"
echo "  GET  /api/job/{job_id}       # Get job status"
echo "  POST /api/summarize-text     # Summarize existing text"
echo "  GET  /health                 # Health check"
echo ""

echo "🔧 Key Improvements:"
echo "  - Clean Architecture with proper separation of concerns"
echo "  - Dependency injection with ports & adapters"
echo "  - Pydantic v2 schemas for validation"
echo "  - Async processing with background tasks"
echo "  - Comprehensive error handling"
echo "  - File-based job persistence"
echo ""

echo "⚠️  Migration Notes:"
echo "  - Old transcriber_app/ directory backed up in backup/old_structure/"
echo "  - Tests preserved for compatibility"
echo "  - Environment variables remain the same"
echo "  - API contracts maintained"
echo ""

echo "🎉 Migration Complete!"
echo "Ready to run with: python -m src.main"