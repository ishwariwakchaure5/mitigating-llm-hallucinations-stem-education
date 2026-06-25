# Migration Guide: VERA to STEM Hallucination Mitigation System

This guide helps you migrate from VERA to the new STEM Hallucination Mitigation System.

## Overview of Changes

### What's Changed
- **Project Name**: VERA → STEM Hallucination Mitigation System
- **Environment Variables**: `VERA_*` → `STEM_*`
- **Database Names**: `vera_db` → `stem_db`
- **Docker Containers**: `vera_*` → `stem_*`
- **New Features**: Citation generation, cross-referencing, benchmark evaluation
- **Enhanced**: Confidence scoring, knowledge base structure, educational UI

### What's Preserved
- All your knowledge bases and documents
- User accounts and authentication
- Verification history
- API endpoint structure (backward compatible)
- Core verification algorithms

## Pre-Migration Checklist

- [ ] Backup all data (PostgreSQL, Qdrant)
- [ ] Document current environment variables
- [ ] Stop all running services
- [ ] Update codebase to latest version
- [ ] Review ARCHITECTURE.md for detailed changes

## Step-by-Step Migration

### Step 1: Backup Your Data

```bash
# 1. Backup PostgreSQL database
docker exec vera_postgres pg_dump -U vera_user vera_db > backup_vera_$(date +%Y%m%d).sql

# 2. Backup Qdrant vector database
docker cp vera_qdrant:/qdrant/storage ./qdrant_backup_$(date +%Y%m%d)

# 3. Backup environment files
cp backend/.env backend/.env.backup
cp frontend/.env.local frontend/.env.local.backup

# 4. Verify backups
ls -lh backup_vera_*.sql
ls -lh qdrant_backup_*
```

### Step 2: Stop Existing Services

```bash
# Stop all VERA services
docker compose down

# Verify all containers are stopped
docker ps -a | grep vera

# Optional: Remove old containers (data is preserved in volumes)
docker rm vera_postgres vera_redis vera_qdrant vera_api vera_worker
```

### Step 3: Update Environment Variables

#### Backend (.env)

```bash
cd backend

# Create new .env from template
cp .env.example .env

# Migrate variables (automated script)
python3 << EOF
import re

# Read old config
with open('.env.backup', 'r') as f:
    old_config = f.read()

# Replace VERA_ with STEM_
new_config = old_config.replace('VERA_', 'STEM_')

# Update database URL
new_config = new_config.replace('vera_db', 'stem_db')
new_config = new_config.replace('vera_user', 'stem_user')
new_config = new_config.replace('vera_pass', 'stem_pass')

# Write new config
with open('.env', 'w') as f:
    f.write(new_config)

print("✅ Environment variables migrated")
EOF
```

**Manual verification** - Check these new variables are present:
```env
# New configuration options
STEM_CONFIDENCE_HIGH_THRESHOLD=0.85
STEM_CONFIDENCE_MEDIUM_THRESHOLD=0.65
STEM_CONFIDENCE_LOW_THRESHOLD=0.45

STEM_SEMANTIC_WEIGHT=0.5
STEM_SYMBOLIC_WEIGHT=0.4
STEM_VISUAL_WEIGHT=0.3

STEM_ENABLE_CROSS_REFERENCING=true
STEM_CITATION_FORMAT=APA
```

#### Frontend (.env.local)

```bash
cd frontend

# Update variables
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=STEM Hallucination Mitigation
NEXT_PUBLIC_APP_DESCRIPTION=Mitigating LLM Hallucinations in STEM Education via Cross-Referenced Knowledge Bases
NEXT_PUBLIC_ENABLE_ANALYTICS=true
EOF
```

### Step 4: Migrate Database

```bash
# Start only PostgreSQL container
docker compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Restore your data to new database
cat backup_vera_*.sql | docker exec -i stem_postgres psql -U stem_user -d stem_db

# Run new migrations
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
alembic upgrade head

# Verify migration
docker exec stem_postgres psql -U stem_user -d stem_db -c "\dt"
```

**Expected new tables**:
- `citations` - Citation generation
- `cross_references` - Cross-referencing system
- `metadata_enrichments` - Enhanced metadata

### Step 5: Migrate Qdrant Vector Database

```bash
# Start Qdrant
docker compose up -d qdrant

# Wait for Qdrant to be ready
sleep 10

# Restore vector data
docker cp ./qdrant_backup_*/. stem_qdrant:/qdrant/storage/

# Restart Qdrant to load data
docker compose restart qdrant

# Verify collections
curl http://localhost:6333/collections
```

### Step 6: Update Backend Dependencies

```bash
cd backend

# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Update dependencies (new packages added)
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
pip list | grep -E "fastapi|qdrant|sympy"
```

**New dependencies**:
- `networkx>=3.0` - For cross-referencing graphs
- `scipy>=1.10` - For enhanced confidence fusion
- Additional data processing libraries

### Step 7: Update Frontend

```bash
cd frontend

# Install updated dependencies
npm install

# Verify build
npm run build

# If build succeeds, you're ready
```

### Step 8: Start All Services

```bash
# From project root
docker compose up -d

# Check all services are healthy
docker compose ps

# Expected output:
# stem_postgres   Up (healthy)
# stem_redis      Up (healthy)
# stem_qdrant     Up (healthy)
# stem_api        Up
# stem_worker     Up
```

### Step 9: Verification

#### 1. Test API

```bash
# Health check
curl http://localhost:8000/health

# Expected: {"status": "healthy"}

# API documentation
open http://localhost:8000/docs
```

#### 2. Test Frontend

```bash
# Start frontend dev server
cd frontend
npm run dev

# Open browser
open http://localhost:3000
```

**Verification checklist**:
- [ ] Landing page loads with new branding
- [ ] Can login with existing account
- [ ] Dashboard shows existing knowledge bases
- [ ] Can create new knowledge base
- [ ] Can upload document
- [ ] Can verify claim
- [ ] Citations appear in results
- [ ] Confidence scores display correctly

#### 3. Test Data Integrity

```bash
cd backend
python << EOF
import asyncio
from app.database import get_db
from app.models.knowledge_base import KnowledgeBase

async def check_data():
    async for db in get_db():
        count = await db.query(KnowledgeBase).count()
        print(f"✅ Found {count} knowledge bases")
        break

asyncio.run(check_data())
EOF
```

### Step 10: Enable New Features

#### Enable Cross-Referencing

```bash
# In backend/.env
STEM_ENABLE_CROSS_REFERENCING=true

# Rebuild cross-references for existing data
cd backend
python -m app.scripts.rebuild_cross_references

# This may take time for large knowledge bases
```

#### Enable Citation Generation

Citations are enabled by default. Test with:

```bash
curl -X POST http://localhost:8000/api/v1/verify/{kb_id} \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"claim_text": "Test claim", "include_citations": true}'
```

### Step 11: Optional - Run Benchmarks

```bash
cd backend

# Download benchmark datasets (first time only)
python -m evaluation.datasets --download

# Run benchmarks
python -m evaluation.run_benchmarks \
  --dataset truthfulqa_stem \
  --output evaluation/results/

# View results
cat evaluation/results/benchmark_results.json
```

## Rollback Procedure

If you need to rollback:

### Quick Rollback

```bash
# 1. Stop new system
docker compose down

# 2. Restore old environment
cp backend/.env.backup backend/.env
cp frontend/.env.local.backup frontend/.env.local

# 3. Restore old database
docker compose up -d postgres
cat backup_vera_*.sql | docker exec -i stem_postgres psql -U stem_user -d stem_db

# 4. Restore Qdrant
docker cp ./qdrant_backup_*/. stem_qdrant:/qdrant/storage/

# 5. Checkout previous git version
git checkout <previous-commit>

# 6. Restart services
docker compose up -d
```

## Troubleshooting

### Issue: "Cannot connect to database"

**Solution**:
```bash
# Check PostgreSQL is running
docker compose ps postgres

# Check connection string in .env
grep STEM_DATABASE_URL backend/.env

# Should be: postgresql+asyncpg://stem_user:stem_pass@localhost:5432/stem_db
```

### Issue: "Qdrant collection not found"

**Solution**:
```bash
# Recreate collections
curl -X DELETE http://localhost:6333/collections/documents
curl -X DELETE http://localhost:6333/collections/images

# Reindex documents
python -m app.scripts.reindex_all
```

### Issue: "Frontend shows old branding"

**Solution**:
```bash
cd frontend

# Clear Next.js cache
rm -rf .next

# Rebuild
npm run build
npm run dev
```

### Issue: "Migration failed"

**Solution**:
```bash
cd backend

# Check migration status
alembic current

# If stuck, manually resolve
alembic downgrade -1
alembic upgrade head

# Check for conflicts
alembic history
```

## Post-Migration Tasks

### 1. Update Documentation

- [ ] Update internal documentation with new project name
- [ ] Update API documentation links
- [ ] Notify users of new features

### 2. Configure New Features

- [ ] Set confidence thresholds for your use case
- [ ] Configure citation format preference
- [ ] Enable cross-referencing for existing KBs
- [ ] Set up benchmark evaluation schedule

### 3. User Training

- [ ] Train educators on new citation features
- [ ] Show students improved UI
- [ ] Demonstrate confidence scoring
- [ ] Explain hallucination detection

### 4. Performance Tuning

- [ ] Monitor query performance
- [ ] Adjust confidence weights if needed
- [ ] Tune cross-reference parameters
- [ ] Review Qdrant index settings

## FAQ

**Q: Will my old API keys still work?**  
A: Yes, JWTs and authentication are fully backward compatible.

**Q: Do I need to re-upload documents?**  
A: No, existing documents are automatically migrated.

**Q: Will verification results change?**  
A: Confidence scores may be more accurate with new calibration, but core verdicts remain consistent.

**Q: Can I use both systems simultaneously?**  
A: Not recommended, but possible by running on different ports.

**Q: How long does migration take?**  
A: Typically 15-30 minutes, plus reindexing time for large databases.

## Support

If you encounter issues:

1. Check logs: `docker compose logs -f`
2. Review ARCHITECTURE.md for technical details
3. Open GitHub issue with logs
4. Contact: [support email]

---

**Migration completed?** Mark this checklist:

- [ ] Data backed up
- [ ] Environment variables updated
- [ ] Database migrated
- [ ] Services running
- [ ] Verification tests passed
- [ ] New features enabled
- [ ] Documentation updated

**Congratulations! You're now running the STEM Hallucination Mitigation System.** 🎉
