import importlib.util
import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1]/'start_files'/'history_store.py'
spec = importlib.util.spec_from_file_location('history_store', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
HistoryStore, ConflictError = module.HistoryStore, module.ConflictError


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root/'brightmls.db'
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE mls_homes (mls TEXT PRIMARY KEY,address TEXT)')
            conn.execute('INSERT INTO mls_homes VALUES (?,?)', ('A1','Existing home'))
        self.folder = self.root/'history'
        self.folder.mkdir()
        self.file = self.folder/'n8n_dns_foundation_history.json'
        self.original = {'record_id':'original-record','workflow_snapshots':[{'keep':'this'}],
                         'execution_history':[{'id':'old','event':'DNS cleanup','timestamp':'2026-10-12T22:31:43+00:00','mode':'verified_clean'}]}
        self.file.write_text(json.dumps(self.original))
        self.store = HistoryStore(self.db, self.folder)
        self.store.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def test_existing_database_and_models_preserved(self):
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute('SELECT address FROM mls_homes').fetchone()[0], 'Existing home')
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'app_history_%' AND type='table'").fetchone()[0],3)
        with self.assertRaises(FileNotFoundError):
            HistoryStore(self.root/'wrong.db', self.folder)
        self.assertFalse((self.root/'wrong.db').exists())

    def test_import_original_bytes_and_no_duplicate_import(self):
        before = self.file.read_bytes()
        first = self.store.archive_file(self.file)
        again = self.store.archive_file(self.file)
        self.assertEqual(first['eventsImported'],1)
        self.assertEqual(again['eventsImported'],0)
        self.assertFalse(again['newFileVersion'])
        self.assertEqual(self.store.archive(first['archiveId'])['original_bytes'],before)
        mirror = self.store.mirror()
        self.assertTrue(mirror['historyFileSaved'])
        saved = json.loads(self.file.read_text())
        self.assertEqual(saved['record_id'],self.original['record_id'])
        self.assertEqual(saved['workflow_snapshots'],self.original['workflow_snapshots'])
        self.assertEqual(len(saved['execution_history']),1)

    def test_dual_write_and_idempotency_and_conflict(self):
        first = self.store.save_event('workflow.finished', {'domain':'yonehomes.com','ok':True}, idempotency_key='run:1')
        self.assertTrue(first['databaseSaved'] and first['historyFileSaved'])
        repeated = self.store.save_event('workflow.finished', {'domain':'yonehomes.com','ok':True}, idempotency_key='run:1')
        self.assertFalse(repeated['created'])
        self.assertEqual(first['id'],repeated['id'])
        self.assertEqual(len(json.loads(self.file.read_text())['execution_history']),2)
        with self.assertRaises(ConflictError):
            self.store.save_event('workflow.finished', {'ok':False}, idempotency_key='run:1')
        self.assertEqual(self.store.events(q='yonehomes.com')['total'],1)

    def test_file_failure_keeps_database_and_retry(self):
        corrupt=b'{invalid JSON'
        self.file.write_bytes(corrupt)
        result=self.store.save_event('retry.test',{'ok':True},idempotency_key='retry:1')
        self.assertTrue(result['databaseSaved'])
        self.assertFalse(result['historyFileSaved'])
        self.assertEqual(self.file.read_bytes(),corrupt)
        self.assertEqual(self.store.stats()['pendingFileMirror'],1)
        self.file.write_text(json.dumps(self.original))
        self.assertTrue(self.store.mirror()['historyFileSaved'])
        self.assertEqual(self.store.stats()['pendingFileMirror'],0)
        self.assertEqual(len(json.loads(self.file.read_text())['execution_history']),2)

    def test_seed_status_and_newer_fact_preserved(self):
        planned={'key':'mail.alias','value':'toni.yone@yonesolutions.com','status':'planned','source':'request','observed_at':'2026-10-12T22:00:00+00:00'}
        self.store.seed_facts([planned])
        self.assertEqual(self.store.facts()[0]['status'],'planned')
        self.store.save_fact('mail.alias','toni.yone@yonesolutions.com','verified','live API','2026-10-12T23:00:00+00:00')
        self.store.seed_facts([planned])
        self.assertEqual(self.store.facts()[0]['status'],'verified')
        self.assertEqual(json.loads(self.file.read_text())['learned_context']['mail.alias']['status'],'verified')

    def test_parallel_writes_and_import_mirror_without_recursive_events(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda i:self.store.save_event('parallel',{'i':i},idempotency_key='parallel:'+str(i)),range(12)))
        self.assertTrue(all(r['historyFileSaved'] for r in results))
        self.assertEqual(self.store.stats()['events'],12)
        self.assertEqual(len(json.loads(self.file.read_text())['execution_history']),13)
        self.store.import_directory()
        count=self.store.stats()['events']
        self.store.import_directory()
        self.assertEqual(self.store.stats()['events'],count)
        self.assertEqual(count,13)

    def test_search_quotes_and_unicode_and_binary_snapshot(self):
        self.store.save_event('unicode',{'text':"Toni's house 🏡"})
        self.assertEqual(self.store.events(q="Toni's")['total'],1)
        raw=b'\x00\xffbinary'
        binary=self.folder/'historical.bin';binary.write_bytes(raw)
        result=self.store.archive_file(binary)
        self.assertEqual(self.store.archive(result['archiveId'])['original_bytes'],raw)


if __name__=='__main__':unittest.main()
