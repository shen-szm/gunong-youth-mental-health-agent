#!/usr/bin/env bash
# Deploy the reviewed alpha.35 -> alpha.36 delta; only RELEASE_VERSION changes in .env.
set -Eeuo pipefail
release=${1:?Pass a unique alpha36-<commit>-<timestamp> release ID}
case "$release" in alpha36-*) ;; *) exit 2 ;; esac
case "$release" in *[!a-zA-Z0-9.-]*) exit 2 ;; esac
root=/opt/shengyu
stage="$root/releases/$release"
backup="$root/backups/$release"
test -d "$stage/dist"
test -f "$stage/dist/index.html"
test -f "$stage/dist/third-party-agent.txt"
test -f "$stage/dist/third-party-icons.txt"
test -f "$stage/dist/third-party-audio.txt"
test -f "$stage/backend.tar"
test ! -e "$backup"
test ! -L "$root/frontend/dist"
test -d "$root/frontend/dist"
systemctl is-active --quiet shengyu

set_release_version() {
  python3 - "$1" "$2" <<'PY'
import os
import pathlib
import re
import stat
import sys
import tempfile

path = pathlib.Path('/opt/shengyu/backend/.env')
before, after = sys.argv[1:]
allowed = {'5.1.0-alpha.35', '5.1.0-alpha.36'}
if before not in allowed or after not in allowed or path.is_symlink():
    raise SystemExit('Invalid release version target')
data = path.read_bytes()
pattern = rb'(?m)^RELEASE_VERSION=[^\r\n]*'
matches = re.findall(pattern, data)
if matches != [('RELEASE_VERSION=' + before).encode()]:
    raise SystemExit('Public release version changed; refusing to overwrite')
updated = re.sub(pattern, ('RELEASE_VERSION=' + after).encode(), data)
if before == after:
    raise SystemExit(0)
metadata = path.stat()
fd, name = tempfile.mkstemp(prefix='.release-version-', dir=path.parent)
try:
    with os.fdopen(fd, 'wb') as stream:
        os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
        os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
        stream.write(updated)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(name, path)
finally:
    if os.path.exists(name):
        os.unlink(name)
PY
}
set_release_version 5.1.0-alpha.35 5.1.0-alpha.35

verify_baseline() {
  local actual
  actual=$(tr -d '\r' < "$root/$1" | sha256sum | cut -d ' ' -f 1)
  test "$actual" = "$2" || { echo "Baseline changed: $1. Refusing to overwrite." >&2; exit 3; }
}
verify_baseline backend/config.py e2b283816acbccf20662b7d133987d3e0553372266c6f10793d7e23c6d65da3c
verify_baseline backend/api/chat.py d7864300d6fdad07ffc23c552d42824fa45aad93d42f551436676f48f136f7cf
while IFS= read -r entry; do
  case "$entry" in
    backend/|backend/api/|backend/config.py|backend/api/chat.py) ;;
    *) echo "Unexpected archive entry: $entry" >&2; exit 4 ;;
  esac
done < <(tar -tf "$stage/backend.tar")
mkdir "$stage/code"
tar -xf "$stage/backend.tar" -C "$stage/code"
files=(backend/config.py backend/api/chat.py)
for file in "${files[@]}"; do
  test -f "$stage/code/$file"
  test ! -L "$stage/code/$file"
  python3 -m py_compile "$stage/code/$file"
done
mkdir -p "$backup"
tar -czf "$backup/backend-code.tar.gz" -C "$root" "${files[@]}"
# Preserve hashed chunks needed by tabs opened before the release.
if test -d "$root/frontend/dist/assets"; then
  mkdir -p "$stage/dist/assets"
  cp -an "$root/frontend/dist/assets/." "$stage/dist/assets/"
fi
chown -R ubuntu:ubuntu "$stage/dist"
switched=0
stopped=0
version_changed=0
rollback() {
  local result=$?
  trap - ERR
  if test "$stopped" = 1; then
    systemctl stop shengyu || true
    tar -xzf "$backup/backend-code.tar.gz" -C "$root"
    if test "$version_changed" = 1; then
      set_release_version 5.1.0-alpha.36 5.1.0-alpha.35
    fi
    if test "$switched" = 1; then
      mv "$root/frontend/dist" "$stage/failed-dist"
      mv "$backup/frontend-dist" "$root/frontend/dist"
    fi
    systemctl start shengyu
  fi
  echo "Release failed; previous code restored. Backup: $backup" >&2
  exit "$result"
}
trap rollback ERR
systemctl stop shengyu
stopped=1
set_release_version 5.1.0-alpha.35 5.1.0-alpha.36
version_changed=1
for file in "${files[@]}"; do
  install -o ubuntu -g ubuntu -m 0644 "$stage/code/$file" "$root/$file"
done
mv "$root/frontend/dist" "$backup/frontend-dist"
# Rollback also restores the previous directory if the next move itself fails.
if ! mv "$stage/dist" "$root/frontend/dist"; then
  mv "$backup/frontend-dist" "$root/frontend/dist"
  false
fi
switched=1
systemctl start shengyu
healthy=0
for attempt in {1..15}; do
  if curl -fsS http://127.0.0.1:9000/health | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" and d.get("version")=="5.1.0-alpha.36" else 1)' 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 1
done
test "$healthy" = 1
systemctl is-active --quiet shengyu
trap - ERR
echo "Released 5.1.0-alpha.36; backup: $backup"
