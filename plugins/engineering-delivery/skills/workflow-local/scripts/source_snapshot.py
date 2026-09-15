#!/usr/bin/env python3
"""CIの参照元をcommitへ固定し、実行前に作業ツリーとの一致を検査する。"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys


def git(root, *args):
    return subprocess.check_output(
        ['git', '-C', str(root), *args], stderr=subprocess.PIPE
    )


def relative(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or '\\' in value:
        raise ValueError('repository-relative path is required')
    if str(path) != value or value.startswith('-'):
        raise ValueError('non-canonical path')
    return value


def digest(data):
    return hashlib.sha256(data).hexdigest()


def source(root, revision, path):
    path = relative(path)
    entry = git(root, 'ls-tree', revision, '--', path).decode().strip()
    if not entry or entry.split()[0] not in ('100644', '100755'):
        raise ValueError('tracked regular file required: ' + path)
    return git(root, 'show', revision + ':' + path)


def snapshot(root, revision, workflow, includes):
    # オプションや任意のgit構文を受け取らず、利用側で解決済みのcommitだけ扱う。
    if len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('full commit SHA required')
    if git(root, 'rev-parse', revision + '^{commit}').decode().strip() != revision:
        raise ValueError('commit mismatch')
    workflow = relative(workflow)
    if not workflow.startswith('.github/workflows/') or not workflow.endswith(('.yml', '.yaml')):
        raise ValueError('GitHub workflow path required')
    files = {}
    for path in sorted(set([workflow, *includes])):
        files[path] = digest(source(root, revision, path))
    return {'schema_version': 1, 'source_sha': revision, 'workflow': workflow, 'files': files}


def verify(root, record):
    if record.get('schema_version') != 1 or not isinstance(record.get('files'), dict):
        raise ValueError('unsupported snapshot')
    expected = snapshot(root, record['source_sha'], record['workflow'], list(record['files']))
    if expected != record:
        raise ValueError('snapshot does not match committed source')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != record['source_sha']:
        raise ValueError('HEAD changed')
    root = Path(root).resolve()
    for path, expected_hash in record['files'].items():
        target = root / path
        # 親ディレクトリのsymlinkによるcheckout外参照も拒否する。
        if target.resolve() != target or not target.is_file():
            raise ValueError('regular checkout file required: ' + path)
        if digest(target.read_bytes()) != expected_hash:
            raise ValueError('working tree changed: ' + path)
    return {'status': 'matched', 'source_sha': record['source_sha'], 'workflow': record['workflow']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['capture', 'verify'])
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--revision')
    parser.add_argument('--workflow')
    parser.add_argument('--include', action='append', default=[])
    parser.add_argument('--record', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.operation == 'capture':
            if not args.revision or not args.workflow:
                raise ValueError('revision and workflow are required')
            record = snapshot(args.root, args.revision, args.workflow, args.include)
            verify(args.root, record)
            # 上書きで以前の実行証拠を消さない。ソース本文やsecretは保存しない。
            with args.record.open('x', encoding='utf-8') as file:
                json.dump(record, file, ensure_ascii=False, indent=2)
                file.write('\n')
            print('source snapshot captured; workflow has not been executed')
        else:
            print(json.dumps(verify(args.root, json.loads(args.record.read_text()))))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print('source snapshot failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
