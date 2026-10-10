"""Package selected current worktree sources, never credentials/runtime data."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = {'SOURCE_DELIVERY.md', 'PRODUCT.md', 'CHANGELOG.md', 'THIRD_PARTY_NOTICES.md', '.gitignore', '.gitattributes', '.env.example'}
FOLDERS = {'backend', 'frontend', 'deploy', 'scripts', 'licenses', 'docs'}
EXCLUDED_PARTS = {'node_modules', 'venv', '.venv', '__pycache__', 'dist', '.git', '.teacher-plan-runtime', '.pytest_cache', 'test-results', 'playwright-report'}
EXCLUDED_EXT = {'.db', '.sqlite', '.sqlite3', '.pyc', '.log', '.zip', '.gz', '.tar', '.pem', '.key', '.pfx', '.docx', '.pdf'}


def selected(name):
    path = Path(name)
    if name not in ROOT_FILES and path.parts[0] not in FOLDERS:
        return False
    if set(path.parts) & EXCLUDED_PARTS or path.suffix.lower() in EXCLUDED_EXT:
        return False
    if any(part.startswith('.env') and part != '.env.example' for part in path.parts):
        return False
    if path.parts[0] == 'docs' and path.suffix.lower() not in {'.md', '.txt', '.json'}:
        return False
    return True


def main():
    names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
    names = sorted(set(name for name in names if name and selected(name)))
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    label = 'shengyu-web-latest-source-' + stamp
    output = ROOT / 'artifacts' / (label + '.zip')
    output.parent.mkdir(exist_ok=True)
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(),
                'git_base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'snapshot': 'current_worktree_including_uncommitted_files',
                'excluded': ['credentials', 'databases', 'runtime data', 'dependencies', 'builds', 'logs', 'old archives', 'document attachments'],
                'files': []}
    secret_pattern = re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|(?:sk-proj-|ghp_)[A-Za-z0-9_-]{20,}')
    snapshots = {}
    with zipfile.ZipFile(output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name in names:
            path = ROOT / name
            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise RuntimeError('Invalid source path: ' + name)
            data = path.read_bytes()
            if path.suffix.lower() in {'.py', '.js', '.json', '.md', '.txt', '.sh', '.ps1', '.vue', '.example'} and name != 'scripts/package_source.py':
                if secret_pattern.search(data.decode('utf-8', errors='replace')):
                    raise RuntimeError('Potential credential requires review: ' + name)
            digest = hashlib.sha256(data).hexdigest()
            snapshots[name] = digest
            manifest['files'].append({'path': name, 'bytes': len(data), 'sha256': digest})
            archive.writestr(label + '/' + name, data)
        archive.writestr(label + '/DELIVERY_MANIFEST.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for entry in manifest['files']:
            assert hashlib.sha256(archive.read(label + '/' + entry['path'])).hexdigest() == entry['sha256']
    for name, digest in snapshots.items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Source changed during packaging: ' + name)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    with output.with_suffix('.sha256').open('x', encoding='utf-8') as stream:
        stream.write(digest + '  ' + output.name + '\n')
    print(json.dumps({'archive': str(output), 'files': len(names), 'bytes': output.stat().st_size, 'sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()
