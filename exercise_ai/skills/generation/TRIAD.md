# Tríade de geração: validação / pensamento / resposta

> Texto autoritativo de CONTRACT-02 neste pacote API (`skills.generation`).
> Se outra prosa divergir deste arquivo, corrija o outro lado para bater com `TRIAD.md`.

## Pipeline

`prompt → LLM → validate → math_check → verify_plan_echo → RELY`

A LLM **não** é fonte de verdade: validação e adesão ao plano ficam no código (ver `AGENTS.md` / constraints do projeto).

## Validação

Validação = **código determinístico apenas**, depois da resposta do LLM — nunca uma seção de “valide o JSON” no SYSTEM prompt.

Pointers:

- Estrutura / schema: `validator.py` → `validate_exercise_batch`
- Matemática: `math_check.py` → `check_math_batch`
- Adesão ao plano: `models.py` → `verify_plan_echo` (slots / `itens_ordenados`)
- Orquestração com retries: `reliability.py` (RELY)

## Pensamento

`reasoning_effort` é knob de API **no nível da run**, resolvido em `reasoning.py` (`resolve_reasoning_effort` / `ReasoningLevel`). **Não** é campo de `Exercise`.

**Callout:** não confundir com pedagógica `tipo_raciocinio` (fora do escopo de produto v2.2).

## Resposta

Resposta = apenas campos Structured Outputs de `models.Exercise`: `enunciado`, `resposta`, `explicacao`, `dificuldade`.

Não dump de JSON Schema nem redesenho de formato em prompts — autoridade de formato: `AUTHORITY.md` (schema/Pydantic + Structured Outputs).

## Fora desta fase

- Mapa de autoridade (formato / plano / conteúdo) → `AUTHORITY.md`
- Catálogo never-do → `NEVER-DO.md`
