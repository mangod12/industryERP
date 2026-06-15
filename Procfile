web: sh -c "alembic upgrade head && gunicorn -w ${WEB_CONCURRENCY:-4} -k uvicorn.workers.UvicornWorker backend_core.app.main:app --bind 0.0.0.0:$PORT"
