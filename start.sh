#!/bin/sh
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn barberia.wsgi --bind 0.0.0.0:$PORT
