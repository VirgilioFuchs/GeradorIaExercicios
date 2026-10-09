"""Pontes para docs do contrato de geração.

Textos autoritativos (mesmo diretório):
- TRIAD.md — tríade validação / pensamento / resposta
- AUTHORITY.md — mapa formato / plano / conteúdo
- NEVER-DO.md — catálogo never-do

Se este módulo e os .md divergirem, corrija para bater com os .md.
"""

from __future__ import annotations

from pathlib import Path

TRIAD_DOC = Path(__file__).with_name("TRIAD.md")
AUTHORITY_DOC = Path(__file__).with_name("AUTHORITY.md")
NEVER_DO_DOC = Path(__file__).with_name("NEVER-DO.md")

# Docs: TRIAD_DOC / AUTHORITY_DOC / NEVER_DO_DOC — não duplicar catálogo aqui.

pass
