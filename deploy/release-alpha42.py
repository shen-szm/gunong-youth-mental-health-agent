"""Explicit alpha37 -> alpha42 release: full frontend dist + backend delta + DeepSeek/screening settings. Run as root."""
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
BEFORE = '5.1.0-alpha.37'
AFTER = '5.1.0-alpha.42'

MODIFIED = {
    'agents/tools.py': 'adeb68ab7615b91ee472e4cb728fb0cf4b82353f2461c11c5b5f04038fed1ed2',
    'api/chat.py': '31592839dd4137bf7b6f9620024b544be0c8af8e89826f7188d3eead4664c662',
    'api/companion.py': '05021ebdf6cbb1d6e6e068e47d65e446696c93543c6708b02e04a62cebf1255a',
    'api/teacher.py': '3074d60497756cf9d40f9f48be0879710e0f535eacfecce42bdba85d9a6b552d',
    'api/teacher_tasks.py': 'b773c244c4f2e834591fc513e4466faa1d9224b0a226e39ae2ceea2fba276957',
    'config.py': 'a1339c9c0877e1dce4a12cc56b9ede0ca028d5bfca5e536fef40c96774cce108',
    'database.py': '22cf625ee81b53eca4852dcc36568226e20d38fc77b2bf5c2bdc7c567ad13624',
    'main.py': '0368fd6726ec462935d58f3c8f28601591b7babbd7420ec5a16a5fbac5b9be72',
    'models.py': '3f7254bb90f5143441c408eb5a5fbfb6c6ea9ae9ac7d4e299dd13e26c6fcc9e9',
    'requirements.txt': 'a926adc168b27abf52de76683f202f8ec56887c2914940c1f09608b20610d3ff',
    'student_ai_authorization.py': 'f28ab0262181c62dfc3928e40b6030730de184330f8924fdf20ccc750f63b733',
    'student_support_engine.py': 'dbb4edaebf5b99b2e6478c6058245517fd4fa7f81da85ab1ce4a1133f13a53a6',
    'teacher_task_intent.py': '0c06b461413b85ad3d494070cb0cc4e685a6bd71bea8bdd19f48493dff4d34ff',
}
NEW = [
    'api/screening.py',
    'companion_engine.py',
    'deepseek_client.py',
    'screening_engine.py',
    'scripts/cleanup_teacher_tasks.py',
    'scripts/evaluate_teacher_intent.py',
    'scripts/serve_teacher_task_preview.py',
    'scripts/verify_teacher_cases.py',
    'scripts/verify_teacher_planner.py',
    'teacher_clarification.py',
    'teacher_intent_benchmark.py',
    'teacher_intent_guard.py',
    'teacher_intent_validation_set.py',
]
FILES = list(MODIFIED) + NEW
MANAGED_KEYS = (
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
    for name in MANAGED_KEYS:
        rows = re.findall(rb'(?m)^' + name.encode() + rb'=[^\r\n]*', data)
        assert not rows, 'managed key already present: ' + name
    return data


def read_secret(stage):
    path = stage / 'deepseek.key'
    assert path.is_file() and not path.is_symlink()
    assert path.stat().st_mode & 0o077 == 0, 'secret file must be 0600'
    secret = path.read_text().strip()
    assert secret.startswith('sk-') and len(secret) >= 20 and '\n' not in secret
    return secret


def version(before, after, secret):
    data = check_environment(before)
    env = ROOT / 'backend/.env'
    temporary = env.with_name('.env-alpha42-version-tmp')
    assert not temporary.exists()
    text = re.sub(rb'(?m)^RELEASE_VERSION=[^\r\n]*', ('RELEASE_VERSION=' + after).encode(), data, count=1)
    text = text.rstrip(b'\r\n')
    addition = (
        b'\n\n# alpha.42: DeepSeek companion engine and PHQ-9 screening\n'
        b'STUDENT_COMPANION_ENGINE=deepseek\n'
        b'DEEPSEEK_API_KEY=' + secret.encode() + b'\n'
        b'DEEPSEEK_BASE_URL=https://api.deepseek.com\n'
        b'DEEPSEEK_MODEL=deepseek-chat\n'
        b'STUDENT_SCREENING_ENABLED=true\n'
    )
    try:
        with temporary.open('xb') as stream:
            os.fchmod(stream.fileno(), env.stat().st_mode & 0o777)
            os.fchown(stream.fileno(), env.stat().st_uid, env.stat().st_gid)
            stream.write(text + addition)
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


def screening_route_present():
    try:
        with urllib.request.urlopen('http://127.0.0.1:9000/api/screening/schema', timeout=2) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        return exc.code in (400, 401, 403, 422)
    except Exception:
        return False


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
    assert re.fullmatch(r'alpha42-[a-zA-Z0-9.-]+', release)
    stage = ROOT / 'releases' / release
    backup = ROOT / 'backups' / release
    assert stage.resolve() == stage and not backup.exists()
    assert not (ROOT / 'frontend/dist').is_symlink()
    assert (ROOT / 'frontend/dist/index.html').is_file()
    assert healthy(BEFORE)
    check_environment(BEFORE)
    secret = read_secret(stage)
    for name, digest in MODIFIED.items():
        path = BACKEND / name
        assert path.resolve() == path
        assert hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest, 'baseline changed: ' + name
    for name in NEW:
        assert not (BACKEND / name).exists(), 'new target exists: ' + name
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
        version(BEFORE, AFTER, secret)
        changed_version = True
        (ROOT / 'frontend/dist').rename(backup / 'frontend-dist')
        switched = True
        (stage / 'dist').rename(ROOT / 'frontend/dist')
        run('systemctl', 'start', 'shengyu')
        assert healthy(AFTER), 'new release unhealthy'
        assert screening_route_present(), 'screening route missing'
        run('systemctl', 'is-active', '--quiet', 'shengyu')
    except BaseException:
        if stopped:
            subprocess.run(['systemctl', 'stop', 'shengyu'], check=False)
            for name in installed:
                if name in MODIFIED:
                    shutil.copy2(backup / name, BACKEND / name)
                elif (BACKEND / name).exists():
                    (BACKEND / name).unlink()
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
    finally:
        if (stage / 'deepseek.key').exists():
            (stage / 'deepseek.key').unlink()
    print('Released ' + AFTER + '; backup: ' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    main(args.release, args.apply)
