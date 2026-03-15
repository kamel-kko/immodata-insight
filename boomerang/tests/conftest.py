"""
conftest.py — Configuration pytest pour BOOMERANG

Fixtures partagees pour tous les tests.
"""

import os
import sys

# S'assurer que le dossier racine est dans le PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
