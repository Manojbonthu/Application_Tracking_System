#!/bin/bash
# AI-Powered ATS — One-command setup script

echo "======================================"
echo "  AI-Powered ATS — Setup"
echo "======================================"

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 not found. Install from https://python.org"
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# 2. Backend setup
echo ""
echo "📦 Setting up backend..."
cd backend

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# 3. Create .env if not exists
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  .env file created. Edit backend/.env with your PostgreSQL credentials:"
    echo "    DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/ats_db"
fi

echo ""
echo "======================================"
echo "  Setup complete!"
echo "======================================"
echo ""
echo "To start the backend:"
echo "  cd backend && source venv/bin/activate && uvicorn main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && python3 -m http.server 3000"
echo ""
echo "Then open: http://localhost:3000"
