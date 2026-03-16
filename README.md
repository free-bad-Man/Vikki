# Vikki Platform

Fullstack monorepo with FastAPI + Next.js + PostgreSQL + Redis + MinIO + Celery + Caddy.

## 📁 Structure

```
vikki/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── models/
│   │   │   └── schemas/
│   │   ├── alembic/      # Database migrations
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── celery_app.py
│   │
│   └── web/              # Next.js frontend
│       ├── src/
│       │   └── app/
│       ├── package.json
│       ├── Dockerfile
│       └── next.config.ts
│
├── infra/
│   ├── compose/
│   │   ├── docker-compose.dev.yml
│   │   └── docker-compose.prod.yml
│   ├── caddy/
│   │   └── Caddyfile
│   └── scripts/
│       ├── deploy.sh
│       └── backup_pg.sh
│
├── .env.example
└── README.md

## 📄 License

MIT
