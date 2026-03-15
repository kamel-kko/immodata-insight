"""
Tests pour la validation statique du code forge (forge_claude.py).

Verifie que _valider_code_forge detecte correctement les imports
et appels dangereux.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from forge_claude import _valider_code_forge


def test_code_safe_passe():
    code = '''
from fastapi import FastAPI
import requests

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}
'''
    problemes = _valider_code_forge(code)
    assert problemes == []


def test_import_subprocess_detecte():
    code = '''
import subprocess
subprocess.run(["rm", "-rf", "/"])
'''
    problemes = _valider_code_forge(code)
    assert any("subprocess" in p for p in problemes)


def test_import_shutil_detecte():
    code = '''
import shutil
shutil.rmtree("/app")
'''
    problemes = _valider_code_forge(code)
    assert any("shutil" in p for p in problemes)


def test_eval_detecte():
    code = '''
result = eval("os.system('ls')")
'''
    problemes = _valider_code_forge(code)
    assert any("eval" in p for p in problemes)


def test_exec_detecte():
    code = '''
exec("import os; os.system('whoami')")
'''
    problemes = _valider_code_forge(code)
    assert any("exec" in p for p in problemes)


def test_os_system_detecte():
    code = '''
import os
os.system("echo hacked")
'''
    problemes = _valider_code_forge(code)
    assert any("os.system" in p for p in problemes)


def test_from_import_ctypes_detecte():
    code = '''
from ctypes import cdll
'''
    problemes = _valider_code_forge(code)
    assert any("ctypes" in p for p in problemes)


def test_syntaxe_invalide():
    code = "def broken( :\n  pass"
    problemes = _valider_code_forge(code)
    assert any("syntaxe" in p.lower() or "syntax" in p.lower() for p in problemes)


def test_code_fastapi_complet_safe():
    code = '''
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import re

app = FastAPI()
TOOL_NAME = "test_tool"

class RunInput(BaseModel):
    input: dict

@app.get("/health")
def health():
    return {"status": "ok", "tool": TOOL_NAME, "requiert_internet": False}

@app.post("/run")
def run(body: RunInput) -> dict:
    query = body.input.get("query", "")
    return {"output": f"Resultat pour {query}"}
'''
    problemes = _valider_code_forge(code)
    assert problemes == []


def test_import_pickle_detecte():
    code = '''
import pickle
data = pickle.loads(b"malicious")
'''
    problemes = _valider_code_forge(code)
    assert any("pickle" in p for p in problemes)


def test_import_socket_detecte():
    code = '''
import socket
s = socket.socket()
'''
    problemes = _valider_code_forge(code)
    assert any("socket" in p for p in problemes)


def test_setattr_detecte():
    code = '''
setattr(obj, "attr", "value")
'''
    problemes = _valider_code_forge(code)
    assert any("setattr" in p for p in problemes)


def test_globals_detecte():
    code = '''
g = globals()
'''
    problemes = _valider_code_forge(code)
    assert any("globals" in p for p in problemes)


def test_os_chmod_detecte():
    code = '''
import os
os.chmod("/etc/passwd", 0o777)
'''
    problemes = _valider_code_forge(code)
    assert any("chmod" in p for p in problemes)


def test_localhost_string_detecte():
    code = '''
import requests
resp = requests.get("http://127.0.0.1:8080/admin")
'''
    problemes = _valider_code_forge(code)
    assert any("127.0.0.1" in p for p in problemes)


def test_metadata_ip_detecte():
    code = '''
import requests
resp = requests.get("http://169.254.169.254/latest/meta-data/")
'''
    problemes = _valider_code_forge(code)
    assert any("169.254" in p for p in problemes)


def test_input_detecte():
    code = '''
secret = input("Entrez votre mot de passe: ")
'''
    problemes = _valider_code_forge(code)
    assert any("input" in p for p in problemes)


def test_from_socket_detecte():
    code = '''
from socket import create_connection
'''
    problemes = _valider_code_forge(code)
    assert any("socket" in p for p in problemes)


def test_safe_requests_externe_passe():
    code = '''
import requests
resp = requests.get("https://api.georisques.gouv.fr/v1/resultats")
'''
    problemes = _valider_code_forge(code)
    assert problemes == []
