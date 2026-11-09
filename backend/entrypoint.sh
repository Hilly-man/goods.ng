#!/bin/sh
set -e

# Render (and similar platforms) mount persistent disks root-owned, which would stop the
# unprivileged app user writing uploads. When the container starts as root, fix ownership
# of the media tree (public photos + private KYC documents) and then drop privileges.
if [ "$(id -u)" = "0" ]; then
  media="${LOCAL_MEDIA_DIR:-media}"
  case "$media" in
    /*) ;;
    *) media="/app/$media" ;;
  esac
  mkdir -p "$media" "$(dirname "$media")/private"
  chown -R 10001:10001 "$media" "$(dirname "$media")/private"
  exec gosu 10001:10001 "$@"
fi

exec "$@"
