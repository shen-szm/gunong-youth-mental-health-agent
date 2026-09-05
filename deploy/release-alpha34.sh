#!/usr/bin/env bash
# Deploy the reviewed alpha.32 -> alpha.34 code delta. No environment/database writes.
set -Eeuo pipefail
release=${1:?Pass a unique alpha34-<commit>-<timestamp> release ID}
case "$release" in alpha34-*) ;; *) exit 2 ;; esac
case "$release" in *[!a-zA-Z0-9.-]*) exit 2 ;; esac
root=/opt/shengyu
stage="$root/releases/$release"
backup="$root/backups/$release"
test -d "$stage/dist"
test -f "$stage/dist/index.html"
test -f "$stage/dist/third-party-agent.txt"
test -f "$stage/backend.tar"
test ! -e "$backup"
test ! -L "$root/frontend/dist"
test -d "$root/frontend/dist"
systemctl is-active --quiet shengyu

verify_baseline() {
  local actual
  actual=$(tr -d '\r' < "$root/$1" | sha256sum | cut -d ' ' -f 1)
  test "$actual" = "$2" || { echo "Baseline changed: $1. Refusing to overwrite." >&2; exit 3; }
}
verify_baseline backend/api/chat.py 8d786061ae387fa62e25a7063f6bd2e59ac64c14236b6e26c5a73a7ac76097a9
verify_baseline backend/api/teacher.py 16dc2d4339caefc6208bdbc2d5dd31fad47dec117f862fb60f18f5d3a6a3bfbd
verify_baseline backend/config.py 3cba9a409e7dd5a0a5bfce1655412c3c37c0c400318d4a999dfdedb04c459b6e
verify_baseline backend/student_support_engine.py 8739dfa334fe19b17ebab1ecc631c3e9159c49e3e3e6088138187b7ba2178462
while IFS= read -r entry; do
  case "$entry" in
    backend/|backend/api/|backend/api/chat.py|backend/api/teacher.py|backend/config.py|backend/student_support_engine.py) ;;
    *) echo "Unexpected archive entry: $entry" >&2; exit 4 ;;
  esac
done < <(tar -tf "$stage/backend.tar")
mkdir "$stage/code"
tar -xf "$stage/backend.tar" -C "$stage/code"
files=(backend/api/chat.py backend/api/teacher.py backend/config.py backend/student_support_engine.py)
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
rollback() {
  local result=$?
  trap - ERR
  if test "$stopped" = 1; then
    systemctl stop shengyu || true
    tar -xzf "$backup/backend-code.tar.gz" -C "$root"
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
  if curl -fsS http://127.0.0.1:9000/health | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("status")=="ok" and d.get("version")=="5.1.0-alpha.34" else 1)' 2>/dev/null; then
    healthy=1
    break
  fi
  sleep 1
done
test "$healthy" = 1
systemctl is-active --quiet shengyu
trap - ERR
echo "Released 5.1.0-alpha.34; backup: $backup"
