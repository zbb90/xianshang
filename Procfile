web: gunicorn -c gunicorn.conf.py wsgi:app
release: python -c "from app import init_db; init_db()"
