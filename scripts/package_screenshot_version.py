"""Bundle exact deployed runtime and editable worktree source with clear provenance."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'artifacts/shengyu-live-alpha37-20261008.tar.gz'
SOURCE = ROOT / 'artifacts/shengyu-web-latest-source-20261008-232352.zip'
OUTPUT = ROOT / 'artifacts/shengyu-screenshot-version-alpha37-20261008.zip'
PREFIX = 'shengyu-screenshot-version-alpha37/'


def main():
    assert LIVE.is_file() and SOURCE.is_file() and not OUTPUT.exists()
    listed = []
    with tarfile.open(LIVE, 'r:gz') as live, zipfile.ZipFile(SOURCE) as source, zipfile.ZipFile(OUTPUT, 'x') as output:
        live_manifest_member = next(m for m in live if m.name.endswith('/MANIFEST.json'))
        live_manifest = json.load(live.extractfile(live_manifest_member))
        source_manifest_name = next(n for n in source.namelist() if n.endswith('/DELIVERY_MANIFEST.json'))
        source_manifest = json.loads(source.read(source_manifest_name))
        assert live_manifest['version'] == '5.1.0-alpha.37'
        assert any(x['path'] == 'frontend/dist/index.html' for x in live_manifest['files'])
        required = {'frontend/src/views/RoomHomeView.vue', 'frontend/src/App.vue',
                    'backend/teacher_intent_guard.py', 'backend/teacher_clarification.py'}
        assert required <= {x['path'] for x in source_manifest['files']}
        readme = (
            '咕哝心岛：与用户截图对应的 alpha.37 项目文件\n\n'
            '01-online-current/：2026-10-08 从 guunoo.online 服务器采集的实际运行文件。'
            '含当时后端 Python 源码与正在提供服务的 frontend/dist 编译文件。'
            '其中 frontend/dist/index.html 加载 assets/index-CsCAvp54.js。\n\n'
            '02-editable-source/：2026-10-08 当前本地工作区的前后端开发源码。'
            'RoomHomeView.vue 含截图中的首次引导、听音乐、倾诉、咕团、探索、我的等界面。'
            '本地后端还包含线上尚未发布的需求风险检查与澄清记录。'
            '因此此目录不能视作线上运行文件的逐字节源码重建。\n\n'
            '线上后端与本地开发后端分别保留，避免把两者混成同一版本。'
            '服务器未保存完整前端开发源码；已排除密钥、数据库、用户资料、日志和依赖环境。'
            '两套文件各自附有清单和逐文件 SHA256。\n'
        )
        output.writestr(PREFIX + 'README.txt', readme.encode('utf-8'))
        for entry in live_manifest['files']:
            name = entry['path']
            member = live.getmember(live_manifest_member.name.rsplit('/', 1)[0] + '/' + name)
            assert member.isfile() and '..' not in Path(name).parts
            data = live.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            target = PREFIX + '01-online-current/' + name
            output.writestr(target, data, compress_type=zipfile.ZIP_STORED)
            listed.append(target)
        output.writestr(PREFIX + '01-online-current/MANIFEST.json', json.dumps(live_manifest, ensure_ascii=False, indent=2))
        base = source_manifest_name.rsplit('/', 1)[0] + '/'
        for entry in source_manifest['files']:
            name = entry['path']
            assert '..' not in Path(name).parts
            data = source.read(base + name)
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            target = PREFIX + '02-editable-source/' + name
            output.writestr(target, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            listed.append(target)
        output.writestr(PREFIX + '02-editable-source/DELIVERY_MANIFEST.json', json.dumps(source_manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(OUTPUT) as output:
        assert output.testzip() is None
        assert len(output.namelist()) == len(listed) + 3
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    print(json.dumps({'archive': str(OUTPUT), 'files': len(listed), 'bytes': OUTPUT.stat().st_size, 'sha256': digest}, ensure_ascii=False))


if __name__ == '__main__':
    main()
