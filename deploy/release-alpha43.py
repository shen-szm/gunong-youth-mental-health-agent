"""Explicit alpha42 -> alpha43 release: full frontend dist + companion memory backend delta. Run as root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import py_compile
import re
import shutil
import sqlite3
import subprocess
import tarfile
import time
import urllib.error
import urllib.request

ROOT = Path('/opt/shengyu')
BACKEND = ROOT / 'backend'
BEFORE = '5.1.0-alpha.42'
AFTER = '5.1.0-alpha.43'

MODIFIED = {
    'api/chat.py': 'c4992d752400cc3637698b1f14aa0274da47d08d73627cba50cac651c4a24b85',
    'companion_engine.py': '418939b5ab3bd2c2d955bef28d99067323fa33cbf6d30d29ec44fb891bd12948',
    'config.py': '0ff73b5ff86a4b7779ffc95d011ef4b36fda86d0015854b5cb602c4cbd7df8f9',
    'models.py': 'b7d88d983e2690d70eeddf8d275124558990a9e777b2b33e2397b0fd05c52005',
    'student_ai_authorization.py': '706fc4e021d31e32df987e3d2c3d3a1521f9d00d149e216ab6d51c2da2b0dda6',
}
FILES = list(MODIFIED)
REQUIRED_KEYS = (
    'STUDENT_COMPANION_ENGINE',
    'DEEPSEEK_API_KEY',
    'DEEPSEEK_BASE_URL',
    'DEEPSEEK_MODEL',
    'STUDENT_SCREENING_ENABLED',
)


def run(*args):
    subprocess.run(args, check=True)


def check_environment(before):
    env = ROOT / 'backend/.env'
    assert not env.is_symlink()
    data = env.read_bytes()
    assert re.findall(rb'(?m)^RELEASE_VERSION=[^\r\n]*', data) == [('RELEASE_VERSION=' + before).encode()]
    for name in REQUIRED_KEYS:
        rows = re.findall(rb'(?m)^' + name.encode() + rb'=([^\r\n]*)', data)
        assert len(rows) == 1, 'missing or duplicated setting: ' + name
        assert rows[0].strip(), 'empty setting: ' + name
    return data


def version(before, after):
    data = check_environment(before)
    env = ROOT / 'backend/.env'
    temporary = env.with_name('.env-alpha43-version-tmp')
    assert not temporary.exists()
    text = re.sub(rb'(?m)^RELEASE_VERSION=[^\r\n]*', ('RELEASE_VERSION=' + after).encode(), data, count=1)
    try:
        with temporary.open('xb') as stream:
            os.fchmod(stream.fileno(), env.stat().st_mode & 0o777)
            os.fchown(stream.fileno(), env.stat().st_uid, env.stat().st_gid)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env)
    finally:
        if temporary.exists():
            temporary.unlink()


def healthy(expected):
    for _ in range(20):
        try:
            with urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=2) as response:
                data = json.load(response)
            if data.get('status') == 'ok' and data.get('version') == expected:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def route_status(path):
    try:
        with urllib.request.urlopen('http://127.0.0.1:9000' + path, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception:
        return None


def backup_database(backup):
    source = ROOT / 'backend/shengyu_v2.db'
    target = backup / 'shengyu_v2.db'
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    os.chmod(target, source.stat().st_mode & 0o777)
    os.chown(target, source.stat().st_uid, source.stat().st_gid)
    for suffix in ('-wal', '-shm'):
        side = source.with_name(source.name + suffix)
        if side.exists():
            shutil.copy2(side, backup / side.name)


def restore_database(backup):
    for suffix in ('-wal', '-shm'):
        side = ROOT / 'backend' / ('shengyu_v2.db' + suffix)
        if side.exists():
            side.unlink()
    if (backup / 'shengyu_v2.db').exists():
        shutil.copy2(backup / 'shengyu_v2.db', ROOT / 'backend/shengyu_v2.db')
        for suffix in ('-wal', '-shm'):
            saved = backup / ('shengyu_v2.db' + suffix)
            if saved.exists():
                shutil.copy2(saved, ROOT / 'backend' / saved.name)


def main(release, apply):
    assert re.fullmatch(r'alpha43-[a-zA-Z0-9.-]+', release)
    stage = ROOT / 'releases' / release
    backup = ROOT / 'backups' / release
    assert stage.resolve() == stage and not backup.exists()
    assert not (ROOT / 'frontend/dist').is_symlink()
    assert (ROOT / 'frontend/dist/index.html').is_file()
    assert healthy(BEFORE)
    check_environment(BEFORE)
    for name, digest in MODIFIED.items():
        path = BACKEND / name
        assert path.resolve() == path
        assert hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest, 'baseline changed: ' + name
    for name in ('index.html', 'third-party-agent.txt', 'third-party-icons.txt', 'third-party-audio.txt'):
        assert (stage / 'dist' / name).is_file()
    assert not any(path.is_symlink() for path in (stage / 'dist').rglob('*'))
    code = stage / 'code'
    code.mkdir(exist_ok=True)
    with tarfile.open(stage / 'backend.tar') as archive:
        members = archive.getmembers()
        assert len(members) == len(FILES) and {m.name for m in members} == set(FILES)
        for member in members:
            assert member.isfile(), 'nonregular archive entry'
            path = code / member.name
            assert path.resolve().is_relative_to(code.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, path.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            if member.name.endswith('.py'):
                py_compile.compile(str(path), doraise=True)
    if not apply:
        print('Preflight passed; no production code or settings changed')
        return
    backup.mkdir(parents=True)
    for name in MODIFIED:
        dest = backup / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(BACKEND / name, dest)
    shutil.copy2(ROOT / 'backend/.env', backup / '.env')
    # Keep old hashed assets for browsers that were open before this release.
    old_assets = ROOT / 'frontend/dist/assets'
    if old_assets.is_dir():
        for path in old_assets.glob('*'):
            if path.is_file() and not (stage / 'dist/assets' / path.name).exists():
                shutil.copy2(path, stage / 'dist/assets' / path.name)
    for root_dir, dirs, files in os.walk(stage / 'dist'):
        os.chmod(root_dir, 0o755)
        for name in files:
            os.chmod(os.path.join(root_dir, name), 0o644)
    switched = changed_version = stopped = False
    installed = []
    try:
        run('systemctl', 'stop', 'shengyu')
        stopped = True
        backup_database(backup)
        for name in FILES:
            installed.append(name)
            run('install', '-o', 'ubuntu', '-g', 'ubuntu', '-m', '0644', str(code / name), str(BACKEND / name))
        version(BEFORE, AFTER)
        changed_version = True
        (ROOT / 'frontend/dist').rename(backup / 'frontend-dist')
        switched = True
        (stage / 'dist').rename(ROOT / 'frontend/dist')
        run('systemctl', 'start', 'shengyu')
        assert healthy(AFTER), 'new release unhealthy'
        assert route_status('/api/screening/schema') in (200, 400, 401, 403, 422), 'screening route missing'
        assert route_status('/api/chat/memories') == 401, 'companion memory route missing'
        run('systemctl', 'is-active', '--quiet', 'shengyu')
    except BaseException:
        if stopped:
            subprocess.run(['systemctl', 'stop', 'shengyu'], check=False)
            for name in installed:
                if name in MODIFIED:
                    shutil.copy2(backup / name, BACKEND / name)
            if changed_version:
                shutil.copy2(backup / '.env', ROOT / 'backend/.env')
            if switched:
                if (ROOT / 'frontend/dist').exists():
                    (ROOT / 'frontend/dist').rename(stage / 'failed-dist')
                (backup / 'frontend-dist').rename(ROOT / 'frontend/dist')
            restore_database(backup)
            run('systemctl', 'start', 'shengyu')
            assert healthy(BEFORE), 'rollback needs operator attention'
        raise
    print('Released ' + AFTER + '; backup: ' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    main(args.release, args.apply)
