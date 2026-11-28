#!/usr/bin/env bash
# Deploy the reviewed alpha.34 -> alpha.35 delta; only RELEASE_VERSION changes in .env.
set -Eeuo pipefail
release=${1:?Pass a unique alpha35-<commit>-<timestamp> release ID}
case "$release" in alpha35-*) ;; *) exit 2 ;; esac
case "$release" in *[!a-zA-Z0-9.-]*) exit 2 ;; esac
root=/opt/shengyu
stage="$root/releases/$release"
backup="$root/backups/$release"
test -d "$stage/dist"
test -f "$stage/dist/index.html"
test -f "$stage/dist/third-party-agent.txt"
test -f "$stage/dist/third-party-icons.txt"
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
allowed = {'5.1.0-alpha.34', '5.1.0-alpha.35'}
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
set_release_version 5.1.0-alpha.34 5.1.0-alpha.34

verify_baseline() {
  local actual
  actual=$(tr -d '\r' < "$root/$1" | sha256sum | cut -d ' ' -f 1)
  test "$actual" = "$2" || { echo "Baseline changed: $1. Refusing to overwrite." >&2; exit 3; }
}
verify_baseline backend/config.py 4a5d1bc1c6be2482ec1669e38e49316a217d51fe3d52bafd61944b25460df2e8
verify_baseline backend/teacher_review_engine.py 96c39e7ac934892abbcecfef76d73aa3fb625aacf98f83d5e3ccc3fdb921bf9c
while IFS= read -r entry; do
  case "$entry" in
    backend/|backend/config.py|backend/teacher_review_engine.py) ;;
    *) echo "Unexpected archive entry: $entry" >&2; exit 4 ;;
  esac
done < <(tar -tf "$stage/backend.tar")
mkdir "$stage/code"
tar -xf "$stage/backend.tar" -C "$stage/code"
files=(backend/config.py backend/teacher_review_engine.py)
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
      set_release_version 5.1.0-alpha.35 5.1.0-alpha.34
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
set_release_version 5.1.0-alpha.34 5.1.0-alpha.35
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
  if curl -fsS http://127.0.0.1:9000/health | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" and d.get("version")=="5.1.0-alpha.35" else 1)' 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 1
done
test "$healthy" = 1
systemctl is-active --quiet shengyu
trap - ERR
echo "Released 5.1.0-alpha.35; backup: $backup"
