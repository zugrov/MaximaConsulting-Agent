#!/bin/bash
# maxima consulting AI Agent — запуск веб-версии
# Запускать из папки consulting-agent/web/

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "Root: $ROOT"

# Backend
echo ""
echo "=== Запуск бэкенда (FastAPI) на http://localhost:8000 ==="
cd "$ROOT/web/backend"
PYTHONPATH="$ROOT/web/backend" python3 -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Frontend
echo ""
echo "=== Запуск фронтенда (Vite) на http://localhost:5173 ==="
cd "$ROOT/web/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "✓ Приложение доступно: http://localhost:5173"
echo "  Для остановки нажмите Ctrl+C"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Остановлено'" EXIT INT TERM
wait
