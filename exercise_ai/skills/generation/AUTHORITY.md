# Mapa de autoridade: formato / plano / conteúdo

> Texto autoritativo de CONTRACT-03 neste pacote API (`skills.generation`).
> Se outra prosa divergir deste arquivo, corrija o outro lado para bater com `AUTHORITY.md`.

| Eixo | Autoridade | Pointers |
|------|------------|----------|
| **Formato** | `models.py` + Structured Outputs / Pydantic (`Exercise` / `ExerciseBatch`) — **não** o prompt | `models.py`; schema via `.parse()` / `response_format` |
| **Plano** | `verify_plan_echo` + `itens_ordenados` | `models.py` → `verify_plan_echo`; orquestração em `reliability.py` (RELY) |
| **Conteúdo** | Prompts (`prompts.py`) — pedagogia / persona (wiring: Phase 19+) | `prompts.py`; persona stub em `skills.generation.persona` |

Relacionados: tríade validação/pensamento/resposta → `TRIAD.md`; never-do → `NEVER-DO.md`.
