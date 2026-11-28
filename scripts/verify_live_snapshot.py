"""Verify the downloaded live snapshot and its internal file checksums."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile

archive_path = Path(sys.argv[1])
prefix = 'shengyu-live-alpha37-20261008/'
with tarfile.open(archive_path, 'r:gz') as archive:
    members = archive.getmembers()
    assert all(member.isfile() and member.name.startswith(prefix) and '..' not in Path(member.name).parts for member in members)
    manifest = json.load(archive.extractfile(prefix + 'MANIFEST.json'))
    assert manifest['version'] == '5.1.0-alpha.37'
    assert len(members) == len(manifest['files']) + 2
    assert any(item['path'] == 'backend/main.py' for item in manifest['files'])
    assert any(item['path'] == 'frontend/dist/index.html' for item in manifest['files'])
    for item in manifest['files']:
        data = archive.extractfile(prefix + item['path']).read()
        assert len(data) == item['bytes']
        assert hashlib.sha256(data).hexdigest() == item['sha256']
    print(json.dumps({'verified_files': len(manifest['files']), 'archive_sha256': hashlib.sha256(archive_path.read_bytes()).hexdigest()}, ensure_ascii=False))
