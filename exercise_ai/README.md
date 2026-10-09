# exercise_ai

Pacote instalável do gerador (import name `exercise_ai`; dist name `exercise-ai`).

Documentação de operador e contrato de embed: ver [`../README.md`](../README.md).

## Install

```bash
pip install -e ".[dev]"   # from repo root
```

```python
from exercise_ai.service import generate_batch
```

**Lab dual path:** same imports after editable install or with repo on `PYTHONPATH`. Deprecated bridge: `exercise_ai.compat_shim` (SemVer MINOR — do not remove in v2.7.0 without MAJOR).

## BNCC (Phase 26) — campos do contrato

| Campo | Modelo | Notas |
|-------|--------|-------|
| `habilidade_bncc` | `GenerationRequest` | Lista global; não-vazia = curricular |
| `habilidade_bncc` | `ExerciseSpec` | Por slot (modo avançado / `--itens-json`) |
| `habilidades_bncc` | `ExerciseBatch` | Echo pós-parse; omitir se vazio |

Catálogo embutido: `data/bncc_matematica_codigos.json` (membership offline; runtime **não** lê `.planning/`).

CLI: `python -m exercise_ai.main` com `--habilidade-bncc`, `--itens-json`. Wizard `gerar`: passo BNCC opcional. Sem mudanças de UI no demo host nesta fase.
