"""Explicit alpha36 -> alpha37 code release, pilot flags unchanged. Run as root."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import py_compile
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path('/opt/shengyu')
BASELINES = {
    'backend/config.py': 'bd99230a085f1c541c7d116b866b596c59105d12378954c9f14213034900eb78',
    'backend/main.py': '8dcb44d511cb1d14b4034bfbdb4421a894ca11295d63c9658c2bbe5bf38f8c03',
    'backend/api/teacher.py': 'c859fce9e23ee21db8ed08961b89ce238003d79356188ada3b0c15a594e5de1c',
}
NEW = ['backend/api/teacher_tasks.py', 'backend/teacher_task_planner.py', 'backend/teacher_task_intent.py',
       'backend/teacher_task_runtime.py', 'backend/teacher_case_workflow.py', 'backend/teacher_revision_check.py',
       'backend/teacher_task_cleanup.py']
FILES = list(BASELINES) + NEW


def run(*args):
    subprocess.run(args, check=True)


def check_environment(before):
    env = ROOT / 'backend/.env'
    assert not env.is_symlink()
    data = env.read_bytes()
    assert re.findall(rb'(?m)^RELEASE_VERSION=[^\r\n]*', data) == [('RELEASE_VERSION=' + before).encode()]
    # Do not publish against unexpected enabled experiments.
    for name in ('ENABLE_TEACHER_DURABLE_PLANS', 'ALLOW_TEACHER_TASK_PLANNER_AI'):
        rows = re.findall(rb'(?m)^' + name.encode() + rb'=([^\r\n]*)', data)
        assert len(rows) <= 1 and all(row.strip().lower() in (b'false', b'0') for row in rows)
    return data


def version(before, after):
    data = check_environment(before)
    env = ROOT / 'backend/.env'
    temporary = env.with_name('.env-alpha37-version-tmp')
    assert not temporary.exists()
    try:
        with temporary.open('xb') as stream:
            os.fchmod(stream.fileno(), env.stat().st_mode & 0o777)
            os.fchown(stream.fileno(), env.stat().st_uid, env.stat().st_gid)
            stream.write(re.sub(rb'(?m)^RELEASE_VERSION=[^\r\n]*', ('RELEASE_VERSION=' + after).encode(), data, count=1))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, env)
    finally:
        if temporary.exists():
            temporary.unlink()


def healthy(expected):
    for _ in range(15):
        try:
            with urllib.request.urlopen('http://127.0.0.1:9000/health', timeout=2) as response:
                data = json.load(response)
            if data.get('status') == 'ok' and data.get('version') == expected:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main(release, apply):
    assert re.fullmatch(r'alpha37-[a-zA-Z0-9.-]+', release)
    stage = ROOT / 'releases' / release
    backup = ROOT / 'backups' / release
    assert stage.resolve() == stage and not backup.exists()
    assert not (ROOT / 'frontend/dist').is_symlink()
    assert (ROOT / 'frontend/dist/index.html').is_file()
    assert healthy('5.1.0-alpha.36')
    check_environment('5.1.0-alpha.36')
    for name, digest in BASELINES.items():
        path = ROOT / name
        assert path.resolve() == path
        assert hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == digest, 'baseline changed: ' + name
    for name in NEW:
        assert not (ROOT / name).exists(), 'new target exists: ' + name
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
            py_compile.compile(str(path), doraise=True)
    if not apply:
        print('Preflight passed; no production code or settings changed')
        return
    backup.mkdir(parents=True)
    for name in BASELINES:
        dest = backup / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dest)
    # Keep old hashed assets for browsers that were open before this release.
    for path in (ROOT / 'frontend/dist/assets').glob('*'):
        if path.is_file() and not (stage / 'dist/assets' / path.name).exists():
            shutil.copy2(path, stage / 'dist/assets' / path.name)
    switched = changed_version = stopped = False
    installed = []
    try:
        run('systemctl', 'stop', 'shengyu')
        stopped = True
        for name in FILES:
            installed.append(name)
            run('install', '-o', 'ubuntu', '-g', 'ubuntu', '-m', '0644', str(code / name), str(ROOT / name))
        version('5.1.0-alpha.36', '5.1.0-alpha.37')
        changed_version = True
        (ROOT / 'frontend/dist').rename(backup / 'frontend-dist')
        switched = True
        (stage / 'dist').rename(ROOT / 'frontend/dist')
        run('systemctl', 'start', 'shengyu')
        assert healthy('5.1.0-alpha.37'), 'new release unhealthy'
        run('systemctl', 'is-active', '--quiet', 'shengyu')
    except BaseException:
        if stopped:
            subprocess.run(['systemctl', 'stop', 'shengyu'], check=False)
            for name in installed:
                if name in BASELINES:
                    shutil.copy2(backup / name, ROOT / name)
                elif (ROOT / name).exists():
                    (ROOT / name).unlink()
            if changed_version:
                version('5.1.0-alpha.37', '5.1.0-alpha.36')
            if switched:
                if (ROOT / 'frontend/dist').exists():
                    (ROOT / 'frontend/dist').rename(stage / 'failed-dist')
                (backup / 'frontend-dist').rename(ROOT / 'frontend/dist')
            run('systemctl', 'start', 'shengyu')
            assert healthy('5.1.0-alpha.36'), 'rollback needs operator attention'
        raise
    print('Released 5.1.0-alpha.37; backup: ' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('release')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    main(args.release, args.apply)
