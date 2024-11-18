#!/bin/sh
# wait-for-postgres.sh

set -e

host="$1"
# Shift arguments with mapping:
# - $0 => $0
# - $1 => <discarded>
# - $2 => $1
# - $3 => $2
# - ...
# This is done for `exec "$@"` below to work correctly
shift

# Login for user (`-U`) and once logged in execute quit ( `-c \q` )
# If we can not login sleep for 1 sec
>&2 echo $PG_PASS
>&2 echo $PG_USER

until PGPASSWORD=$PG_PASS psql $PG_NAME -h "$host" -U $PG_USER -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  >&2 echo $PG_PASS
  >&2 echo $PG_USER
  >&2 echo $host
  sleep 1
done

>&2 echo "Postgres is up - executing command"
# Print and execute all other arguments starting with `$1`
# So `exec "$1" "$2" "$3" ...`
exec "$@"