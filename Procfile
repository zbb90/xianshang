web: gunicorn -c gunicorn.conf.py wsgi:app --reload
release: python -c "from app import init_db; init_db(); print('🚀 v4.2.1 DEPLOYED SUCCESSFULLY')"
