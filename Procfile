web: gunicorn -c gunicorn.conf.py wsgi:app
release: python -c "from enhanced_final_app import init_db; init_db()"
