#!/bin/sh

echo "Waiting for postgres..."
# export DB_HOST=127.0.0.1
# determine IPAddress of PG docker container
#export DB_HOST=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' db)
export DB_HOST=db
export DB_PORT=5432
echo "waiting for PostgreSQL on $DB_HOST:$DB_PORT"

set -x
# for debugging startup:
set -e
sleep 5.0
while ! nc -z db $DB_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"
#PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $POSTGRES_USER -l
## psql: FATAL:  the database system is starting up

yarn install
yarn list

cd ./mybookdb
pwd -P

echo "django flush"
python manage.py flush --no-input

echo "django migrate"
python manage.py migrate

#PGPASSWORD=$POSTGRES_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $POSTGRES_USER -l


echo "django collectstatic"
#python manage.py collectstatic --no-input --clear
python manage.py collectstatic --no-input 

pwd -P
ls -la /app/mybookdb/staticfiles/
ls -la /app/mybookdb/templates/static/

#python manage.py loaddata books_samples
#python manage.py update_docs
#python manage.py update_index

echo "django run"
exec "$@"