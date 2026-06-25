# Quick Start Guide

## Get Started in 5 Minutes

### Prerequisites
- Python 3.11 or 3.12
- Node.js 18+
- Docker Desktop
- 16 GB RAM recommended

### Step 1: Start Docker Services

```bash
# Start PostgreSQL, Redis, and Qdrant
docker compose up -d

# Verify services are healthy
docker compose ps
```

### Step 2: Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set STEM_SECRET_KEY

# Initialize database
alembic upgrade head

# Start API server
uvicorn app.main:app --reload
```

**Backend running**: http://localhost:8000

### Step 3: Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

**Frontend running**: http://localhost:3000

### Step 4: Create Your First Knowledge Base

1. **Open browser**: http://localhost:3000
2. **Register account**: Click "Get Started"
3. **Create knowledge base**: Click "+ Create Knowledge Base"
4. **Upload PDF**: Drag and drop a STEM textbook or paper
5. **Wait for processing**: Document will be indexed (~1-2 minutes)
6. **Verify claim**: Go to "Verify Claims" tab and test it!

### Example Verification

**Knowledge Base**: Upload a physics textbook  
**Claim to Verify**: "Newton's second law states that F = ma"  
**Expected Result**: ✅ Correct (confidence: ~0.90) with citations

### Next Steps

- Read [README.md](README.md) for comprehensive documentation
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Check [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) if migrating from VERA

### Troubleshooting

**Issue**: Docker services won't start  
**Fix**: `docker compose down && docker compose up -d`

**Issue**: Backend won't start  
**Fix**: Check `backend/.env` has all required variables

**Issue**: Frontend shows errors  
**Fix**: Delete `.next` folder and run `npm run dev` again

### Support

- **Documentation**: See README.md
- **Issues**: [GitHub Issues]
- **Community**: [GitHub Discussions]

---

**Ready to mitigate hallucinations!** 🚀
