import ast
import importlib.util
import os
import secrets
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def test_attach_once_and_keep_routes(self):
        spec=importlib.util.spec_from_file_location('installer',ROOT/'install_history.py')
        installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
        original='from fastapi import FastAPI\napp = FastAPI()\n@app.get("/")\ndef home():\n    return {"ok": True}\n'
        first,changed=installer.patch_app(original)
        self.assertTrue(changed)
        self.assertIn('@app.get("/")',first)
        second,changed=installer.patch_app(first)
        self.assertFalse(changed)
        self.assertEqual(first,second)
        with self.assertRaises(ValueError):installer.patch_app('def build():\n    return FastAPI()\n')


class AuthTests(unittest.TestCase):
    def setUp(self):
        # Run the actual authentication function with a lightweight HTTPException
        # adapter; this tests its logic without claiming FastAPI integration ran.
        source=ast.parse((ROOT/'start_files'/'history_archive.py').read_text())
        node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='require_key')
        class HTTPError(Exception):
            def __init__(self,status_code,detail,headers=None):
                self.status_code=status_code
                super().__init__(detail)
        self.Error=HTTPError
        env={'os':os,'secrets':secrets,'Optional':Optional,'HTTPAuthorizationCredentials':object,
             'Depends':lambda _:None,'bearer':object(),'HTTPException':HTTPError}
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual_auth_function','exec'),env)
        self.require=env['require_key']
        self.envpatch=patch.dict(os.environ,{},clear=True);self.envpatch.start()
        self.addCleanup(self.envpatch.stop)

    def test_missing_key_and_url_are_configuration_errors(self):
        with self.assertRaises(self.Error) as err:self.require(None)
        self.assertEqual(err.exception.status_code,503)
        os.environ['FASTAPI_API']='https://yonehomes.com'
        with self.assertRaises(self.Error) as err:self.require(None)
        self.assertEqual(err.exception.status_code,503)

    def test_exact_secret_and_override_priority(self):
        class Credentials:
            def __init__(self,key):self.credentials=key
        os.environ['FASTAPI_API']='test-server-secret'
        self.assertIsNone(self.require(Credentials('test-server-secret')))
        with self.assertRaises(self.Error) as err:self.require(Credentials('wrong'))
        self.assertEqual(err.exception.status_code,401)
        with self.assertRaises(self.Error):self.require(None)
        os.environ['HISTORY_API_KEY']='explicit-secret'
        self.assertIsNone(self.require(Credentials('explicit-secret')))
        with self.assertRaises(self.Error):self.require(Credentials('test-server-secret'))


if __name__=='__main__':unittest.main()
