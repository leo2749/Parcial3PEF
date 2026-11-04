"""Configuración de Sphinx. Generar con:  python -m sphinx -b html docs docs/_build/html"""
import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "Motor de recomendaciones"
author = "Leonel Sposetti"
release = "2.0.0"
language = "es"

extensions = [
    "sphinx.ext.autodoc",      # extrae la documentación de los docstrings
    "sphinx.ext.napoleon",     # entiende docstrings estilo Google (Args/Returns)
    "sphinx.ext.viewcode",     # enlaza cada función con su código fuente
]
# Los ejemplos ">>>" de los docstrings los ejecuta pytest (--doctest-modules).

autodoc_default_options = {"members": True, "undoc-members": False, "show-inheritance": True}
autodoc_member_order = "bysource"
napoleon_google_docstring = True

html_theme = "alabaster"
html_static_path = ["_static"]
exclude_patterns = ["_build"]
