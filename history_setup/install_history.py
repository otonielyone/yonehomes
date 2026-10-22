#!/usr/bin/env python3
"""Install modules and attach the history router to an existing FastAPI app."""
import argparse
import ast
import shutil
from datetime import datetime, timezone
from pathlib import Path


def patch_app(source):
    tree = ast.parse(source)
    if 'from start_files.history_archive import router as history_router' in source and '.include_router(history_router)' in source:
        return source, False
    names = []
    for node in tree.body:
        value = getattr(node, 'value', None)
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(value, ast.Call):
            function = value.func
            is_fastapi = isinstance(function, ast.Name) and function.id == 'FastAPI' or isinstance(function, ast.Attribute) and function.attr == 'FastAPI'
            if is_fastapi:
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if len(targets) == 1 and isinstance(targets[0], ast.Name):
                    names.append((targets[0].id, node.end_lineno))
    if len(names) != 1:
        raise ValueError('Expected one top-level app = FastAPI(...) assignment. Attach the history router manually after creating your app.')
    name, end_line = names[0]
    lines = source.splitlines(keepends=True)
    block = '\nfrom start_files.history_archive import router as history_router\n' + name + '.include_router(history_router)\n'
    lines.insert(end_line, block)
    patched = ''.join(lines)
    ast.parse(patched)
    return patched, True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=Path('/var/www/html/yonehomes'))
    parser.add_argument('--database', type=Path)
    args = parser.parse_args()
    root = args.app_root.resolve()
    db = (args.database or root/'brightscrape'/'brightmls.db').resolve()
    if not db.is_file():
        parser.error('Existing application database is missing: '+str(db)+'. No second database will be created.')
    appfile = root/'start_files'/'app.py'
    original = appfile.read_text()
    patched, changed = patch_app(original)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = root/'history'/'installation-backups'/stamp
    folder.mkdir(parents=True, exist_ok=False)
    shutil.copy2(appfile, folder/'app.py')
    package = Path(__file__).resolve().parent
    for name in ['history_store.py', 'history_archive.py']:
        target = root/'start_files'/name
        if target.exists():
            shutil.copy2(target, folder/name)
        shutil.copy2(package/'start_files'/name, target)
    if changed:
        appfile.write_text(patched)
    print('Installed history modules into '+str(root/'start_files'))
    print('Attached router: '+str(changed))
    print('Application/module backups: '+str(folder))
    print('Existing database: '+str(db))
    print('Run the init/import/seed commands in README.md, then restart your existing FastAPI service.')


if __name__ == '__main__':
    main()
