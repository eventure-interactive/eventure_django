#!/usr/bin/env bash

# Deploys the current directory to /var/local/eventure-api
# updates the virtual environment and celery workers

# will restart uwsgi, but doesn't touch uwsgi or nginx configurations

set -e

DEPLOY_DIR="/var/local/eventure-api"
APP_DIR="$DEPLOY_DIR/app"
VENV_DIR="$DEPLOY_DIR/api-venv"


rm -rf $APP_DIR/core
rm -rf $APP_DIR/evtidj
rm -rf $DEPLOY_DIR/static/*

cp -a core $APP_DIR
cp -a evtidj $APP_DIR

if [ ! -d $APP_DIR/logs ]; then
	mkdir $APP_DIR/logs
fi

chown --recursive www-data:www-data $APP_DIR

## Set up our virtualenv
source $VENV_DIR/bin/activate
$VENV_DIR/bin/pip3 install --upgrade -r ./requirements.txt

# Do migrations
python manage.py migrate

# Copy static files
python manage.py collectstatic --noinput
deactivate

# reload uwsgi
service uwsgi restart
service celeryd restart

echo Done.
