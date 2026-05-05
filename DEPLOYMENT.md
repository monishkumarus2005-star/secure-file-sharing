# Deployment Runbook

## Prerequisites
- Docker + Docker Compose installed
- Node.js 18+ installed
- Git installed

## Environment Setup
1. Copy .env.example to .env
2. Set these required values:
   - JWT_SECRET_KEY (min 64 chars)
   - DATABASE_URL
   - REDIS_URL
   - S3_ENABLED=true
   - S3_ENDPOINT_URL
   - S3_ACCESS_KEY
   - S3_SECRET_KEY
   - S3_BUCKET_NAME
   - BLOCKCHAIN_ENABLED=true (optional)
   - WEB3_PROVIDER_URL (if blockchain enabled)
   - CONTRACT_ADDRESS (if blockchain enabled)
   - PRIVATE_KEY (if blockchain enabled)

## Start All Services
docker compose up -d

## Run Migrations
docker compose exec api python -m alembic upgrade head

## Verify Health
curl http://localhost:8000/health

## Access Points
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173
- MinIO: http://localhost:9001 (Console) / 9000 (API)
- Ganache (dev): http://localhost:8545

## Stop All Services
docker compose down

## View Logs
docker compose logs -f api
docker compose logs -f celery

## Run Backup Manually
curl -X POST http://localhost:8000/admin/backup \
  -H "Authorization: Bearer ADMIN_TOKEN"
