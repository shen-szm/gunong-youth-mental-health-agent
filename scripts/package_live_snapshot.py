"""Create a sanitized archive of the exact code/assets served by guunoo.online.

Run on the authorized server. This deliberately omits all runtime state,
credentials, logs, databases, report output, and optional local test data.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
from datetime import datetime, timezone

ROOT = Path('/opt/shengyu')
BACKEND = ROOT / 'backend'
FRONTEND = ROOT / 'frontend' / 'dist'
SUFFIXES = {'.py', '.json', '.txt', '.md', '.sh'}
PREFIX = 'shengyu-live-alpha37-20261008'
OUT = Path('/tmp/shengyu-live-alpha37-20261008.tar.gz')


def source_files():
    for path in BACKEND.rglob('*'):
        if not path.is_file():
            continue
        relative = path.relative_to(BACKEND)
        if set(relative.parts) & {'venv', '__pycache__', 'reports', '.teacher-plan-runtime', 'node_modules'}:
            continue
        if relative.suffix.lower() in SUFFIXES and not relative.name.startswith('.'):
            yield 'backend/' + relative.as_posix(), path
    for path in FRONTEND.rglob('*'):
        if path.is_file():
            yield 'frontend/dist/' + path.relative_to(FRONTEND).as_posix(), path


def add_bytes(archive, name, data):
    info = tarfile.TarInfo(PREFIX + '/' + name)
    info.size = len(data)
    info.mode = 0o644
    info.mtime = 0
    archive.addfile(info, io.BytesIO(data))


def main():
    assert sys.argv[1:] == ['--package']
    assert BACKEND.is_dir() and (FRONTEND / 'index.html').is_file()
    assert not OUT.exists()
    files = sorted(source_files())
    assert len(files) > 30
    manifest = []
    with tarfile.open(OUT, 'x:gz') as archive:
        for name, path in files:
            if path.is_symlink() or not path.resolve().is_relative_to(ROOT):
                raise RuntimeError('Unsafe path: ' + name)
            if any(part in name.lower() for part in ('.env', 'secret', 'credential', 'private', 'reports/', '.db', '.sqlite', '.log')):
                raise RuntimeError('Unexpected private path: ' + name)
            data = path.read_bytes()
            manifest.append({'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
            add_bytes(archive, name, data)
        add_bytes(archive, 'README.txt', (
            '咕哝心岛线上运行快照 / guunoo.online\n'
            '采集日期：2026-10-08；线上健康检查版本：5.1.0-alpha.37。\n'
            'backend/ 是服务器当前 Python 源码；frontend/dist/ 是服务器当前提供的编译后前端。\n'
            '服务器未保存完整前端开发源码，因此此包不是可重新构建的完整项目源码。\n'
            '已排除密钥、.env、数据库、用户数据、报告、日志、虚拟环境和缓存。\n'
            '包内文件哈希见 MANIFEST.json；此包不含线上配置和依赖安装环境。\n'
        ).encode('utf-8'))
        add_bytes(archive, 'MANIFEST.json', json.dumps({
            'site': 'guunoo.online', 'version': '5.1.0-alpha.37',
            'collected_utc': datetime.now(timezone.utc).isoformat(),
            'frontend_source_available_on_server': False,
            'files': manifest,
        }, ensure_ascii=False, indent=2).encode('utf-8'))
    with tarfile.open(OUT, 'r:gz') as archive:
        assert archive.getnames()[-1] == PREFIX + '/MANIFEST.json'
        assert all(entry.isfile() for entry in archive)
    print(json.dumps({'archive': str(OUT), 'files': len(files), 'bytes': OUT.stat().st_size,
                      'sha256': hashlib.sha256(OUT.read_bytes()).hexdigest()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
