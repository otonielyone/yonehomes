#!/usr/bin/env python3
"""Repair history installation for the server layout supplied by the owner."""
import argparse
import ast
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

MARKER = '# YONE_HISTORY_ROUTER_INTEGRATION'


def attach_router(source):
    if MARKER in source:
        return source, 0
    tree = ast.parse(source)
    aliases, modules = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('fastapi'):
            for name in node.names:
                if name.name == 'FastAPI':
                    aliases.add(name.asname or name.name)
        if isinstance(node, ast.Import):
            for name in node.names:
                if name.name == 'fastapi':
                    modules.add(name.asname or name.name)
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        matched = isinstance(f, ast.Name) and f.id in aliases
        matched = matched or (isinstance(f, ast.Attribute) and f.attr == 'FastAPI' and isinstance(f.value, ast.Name) and f.value.id in modules)
        if matched:
            calls.append(node)
    if not calls:
        return source, 0
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def position(line, column):
        # AST column offsets are UTF-8 bytes, not character offsets.
        prefix = lines[line-1].encode('utf-8')[:column].decode('utf-8')
        return offsets[line-1] + len(prefix)

    edits = []
    for call in calls:
        start = position(call.lineno, call.col_offset)
        end = position(call.end_lineno, call.end_col_offset)
        edits.append((start, end, '_yone_attach_history(' + source[start:end] + ')'))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    # Preserve module docstrings and required __future__ import positioning.
    insert_line = 0
    for index, node in enumerate(tree.body):
        if index == 0 and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            insert_line = node.end_lineno
        elif isinstance(node, ast.ImportFrom) and node.module == '__future__':
            insert_line = node.end_lineno
        else:
            break
    lines = source.splitlines(keepends=True)
    block = '\n' + MARKER + '\nfrom start_files.history_archive import router as _yone_history_router\n\ndef _yone_attach_history(application):\n    application.include_router(_yone_history_router)\n    return application\n\n'
    lines.insert(insert_line, block)
    result = ''.join(lines)
    ast.parse(result)
    return result, len(calls)


def atomic_write(path, text, mode=0o600):
    fd, temporary = tempfile.mkstemp(prefix='.history-install-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


EXCLUDED_DIRS = {'venv', '.venv', 'history', 'history_setup', '__pycache__', '.git',
                 '.history-install-backups', 'logs', 'certs', 'node_modules'}
DATABASE_NAMES = {'brightmls.db', 'brightscrape.db'}


def source_files(root, extensions):
    for directory, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith('.') and not (Path(directory)/d).is_symlink()]
        for name in names:
            path = Path(directory)/name
            if path.is_symlink() or path.suffix.lower() not in extensions:
                continue
            if name == 'fix_history_install.py':
                continue
            yield path


def audit_database_paths(root, target):
    references, dynamic_calls, parse_errors = [], [], []
    sqlite_prefixes = ('sqlite:///', 'sqlite+pysqlite:///')
    def resolve(value):
        for prefix in sqlite_prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):].split('?',1)[0]
                break
        if not any(value.endswith(name) for name in DATABASE_NAMES):
            return None
        path = Path(value)
        return str((path if path.is_absolute() else root/path).resolve())
    for path in source_files(root, {'.py'}):
        # New archive adapter gets its path from APP_DATABASE_PATH and is
        # checked independently below, rather than treating config as a literal.
        if path in {root/'start_files/history_store.py', root/'start_files/history_archive.py'}:
            continue
        try:
            tree = ast.parse(path.read_text())
        except (SyntaxError,UnicodeDecodeError,OSError) as exc:
            parse_errors.append({'file':str(path.relative_to(root)), 'error':type(exc).__name__})
            continue
        assignments = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value,str):
                for binding in node.targets:
                    if isinstance(binding,ast.Name):assignments.setdefault(binding.id,set()).add(node.value.value)
            if isinstance(node,ast.Constant) and isinstance(node.value,str):
                value=node.value
                resolved=resolve(value)
                if resolved:
                    references.append({'file':str(path.relative_to(root)), 'line':node.lineno,
                                       'databaseName':Path(value).name, 'resolvedPath':resolved,
                                       'usesTarget':resolved==str(target)})
        for node in ast.walk(tree):
            if not isinstance(node,ast.Call) or not node.args:
                continue
            f=node.func
            engine=isinstance(f,ast.Name) and f.id=='create_engine'
            sqlite_call=isinstance(f,ast.Attribute) and f.attr=='connect' and isinstance(f.value,ast.Name) and f.value.id=='sqlite3'
            if not (engine or sqlite_call):continue
            arg=node.args[0]
            values={arg.value} if isinstance(arg,ast.Constant) and isinstance(arg.value,str) else assignments.get(arg.id,set()) if isinstance(arg,ast.Name) else set()
            if values and all(resolve(v)==str(target) for v in values):continue
            dynamic_calls.append({'file':str(path.relative_to(root)),'line':node.lineno,
                                  'operation':'create_engine' if engine else 'sqlite3.connect',
                                  'reason':'Database argument could not be statically confirmed against the target; inspect this call'})
    with sqlite3.connect(target.as_uri()+'?mode=ro',uri=True,timeout=30) as conn:
        tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    history_adapter = None
    if (root/'start_files/history_archive.py').is_file():
        configured = None
        envfile=root/'.env'
        if envfile.is_file():
            for line in envfile.read_text().splitlines():
                match=re.match(r'^\s*(?:export\s+)?APP_DATABASE_PATH\s*=\s*(.*?)\s*$',line)
                if match:
                    configured=match.group(1).strip().strip("\"'")
        history_adapter={'configuredDatabasePath':configured,'usesTarget':configured==str(target)}
    non_target=[r for r in references if not r['usesTarget']]
    return {'targetDatabase':str(target),'targetExists':target.is_file(),'tables':tables,
            'references':references,'nonTargetReferences':non_target,
            'unresolvedDatabaseCalls':dynamic_calls,'parseErrors':parse_errors,
            'historyAdapter':history_adapter,
            'allStaticReferencesUseTarget':not non_target and not dynamic_calls and not parse_errors and (history_adapter is None or history_adapter['usesTarget']),
            'note':'Read-only static source audit. It does not execute application requests or prove dynamic runtime connections.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--app-root', type=Path, default=Path('/var/www/html/yonehomes'))
    parser.add_argument('--audit-only', action='store_true', help='Read-only scan of application database references')
    args = parser.parse_args()
    root = args.app_root.resolve()
    target_database = root / 'databases' / 'brightmls.db'
    if args.audit_only:
        if not target_database.is_file():parser.error('Existing target database is missing: '+str(target_database))
        print(json.dumps(audit_database_paths(root,target_database),indent=2))
        return
    package = root / 'history_setup'
    for name in ['history_store.py', 'history_archive.py']:
        module = package / 'start_files' / name
        if not module.is_file():
            parser.error('Extracted module missing: ' + str(module))
        ast.parse(module.read_text())
    candidates = [root / 'start_files' / 'app.py', root / 'main.py']
    selected = []
    already = []
    for candidate in candidates:
        if not candidate.is_file():
            continue
        original = candidate.read_text()
        if MARKER in original:
            already.append(candidate)
            continue
        patched, count = attach_router(original)
        if count:
            selected.append((candidate, patched, count))
    if not selected and not already:
        parser.error('No FastAPI constructor found in start_files/app.py or main.py. No files were changed. Provide those two source files so the actual app factory can be attached correctly.')
    if len(selected) + len(already) > 1:
        parser.error('Multiple app-construction modules found. No files were changed; provide app.py and main.py to select the production entrypoint.')
    original_db = root / 'databases' / 'brightmls.db'
    if not original_db.is_file():
        parser.error('Existing database is missing at '+str(original_db)+'. Put your existing brightmls.db there first. No files were changed and no database will be created.')
    # Update only exact old database literals, keeping unrelated app code intact.
    db_literals = {'sqlite:///brightscrape/brightmls.db', 'sqlite:///brightscape/brightmls.db',
                   'sqlite:///brightmls.db', 'sqlite:///databases/brightmls.db',
                   'brightscrape/brightmls.db', 'brightscape/brightmls.db',
                   'databases/brightmls.db', 'brightmls.db'}
    path_updates = []
    python_files = list(source_files(root,{'.py'}))
    for code_path in python_files:
        if code_path.name in {'fix_history_install.py', 'history_store.py', 'history_archive.py'}:
            continue
        original = code_path.read_text()
        source = next((patched for target, patched, _ in selected if target == code_path), original)
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        def offset(line, col):
            return offsets[line-1] + len(lines[line-1].encode('utf-8')[:col].decode('utf-8'))
        edits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in db_literals:
                replacement = 'sqlite:///' + str(original_db) if node.value.startswith('sqlite:///') else str(original_db)
                edits.append((offset(node.lineno,node.col_offset),offset(node.end_lineno,node.end_col_offset),repr(replacement)))
        for start, end, replacement in sorted(edits, reverse=True):
            source = source[:start] + replacement + source[end:]
        if edits:
            ast.parse(source)
            path_updates.append((code_path,source,len(edits)))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = root / '.history-install-backups' / stamp
    backup.mkdir(mode=0o700, parents=True, exist_ok=False)
    database_to_backup = original_db
    # A SQLite-aware backup includes committed data rather than copying an open file.
    source_uri = database_to_backup.resolve().as_uri() + '?mode=ro'
    with sqlite3.connect(source_uri, uri=True, timeout=30) as source:
        with sqlite3.connect(backup / 'brightmls.db') as target:
            source.backup(target)
    env_path = root / '.env'
    old_env = env_path.read_text() if env_path.exists() else ''
    if env_path.exists():
        shutil.copy2(env_path, backup / '.env')
        os.chmod(backup / '.env', 0o600)
    configured_line = 'APP_DATABASE_PATH=' + str(original_db)
    env_lines = old_env.splitlines()
    configured, found = [], False
    for line in env_lines:
        if re.match(r'^\s*(?:export\s+)?APP_DATABASE_PATH\s*=', line):
            if not found:
                configured.append(configured_line)
                found = True
        else:
            configured.append(line)
    if not found:
        configured.append(configured_line)
    atomic_write(env_path, '\n'.join(configured) + '\n', 0o600)
    for name in ['history_store.py', 'history_archive.py']:
        target = root / 'start_files' / name
        if target.exists():
            shutil.copy2(target, backup / name)
        module_text=(package/'start_files'/name).read_text()
        if name=='history_archive.py':
            module_text=module_text.replace('return APP_ROOT / "brightscrape" / "brightmls.db"','return APP_ROOT / "databases" / "brightmls.db"')
        atomic_write(target,module_text,0o644)
    for target, patched, count in selected:
        shutil.copy2(target, backup / target.name)
        atomic_write(target, patched, target.stat().st_mode & 0o777)
        print('Attached history router in ' + str(target) + ' (' + str(count) + ' constructor call(s), including factory support)')
    for target, patched, count in path_updates:
        relative = target.relative_to(root)
        saved = backup / 'app-source' / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        # For files also receiving router integration, original bytes are already
        # backed up above; this extra backup remains a valid installed-stage copy.
        shutil.copy2(target, saved)
        atomic_write(target, patched, target.stat().st_mode & 0o777)
        print('Updated database path literals in ' + str(target) + ' (' + str(count) + ')')
    if already:
        print('History router was already attached in ' + str(already[0]))
    seed_path = package / 'domain_context_seed.json'
    if seed_path.is_file():
        shutil.copy2(seed_path, backup / 'domain_context_seed.json')
        seed = json.loads(seed_path.read_text())
        for fact in seed.get('facts', []):
            if fact.get('key') == 'database.application':
                value = fact['value']
                value['uploaded_configured_url'] = value.pop('configured_url', 'sqlite:///brightscrape/brightmls.db')
                value['expected_absolute_path'] = str(original_db)
                value['history_database_path'] = str(original_db)
                value['app_database_url_after_repair'] = 'sqlite:///' + str(original_db)
                fact['status'] = 'reported'
                fact['source'] = 'Owner selected databases folder; repair sets the same absolute SQLite path in the app and archive configuration'
                fact['observed_at'] = datetime.now(timezone.utc).isoformat()
        atomic_write(seed_path, json.dumps(seed, indent=2) + '\n', seed_path.stat().st_mode & 0o777)
    print('Existing database: ' + str(original_db))
    print('APP_DATABASE_PATH updated in existing .env; secrets were not printed')
    print('Backup: ' + str(backup))
    print('Next: run init, import and seed from the application root, then restart your existing service.')
    print(json.dumps({'databaseReferenceAudit':audit_database_paths(root,original_db)},indent=2))


if __name__ == '__main__':
    main()
