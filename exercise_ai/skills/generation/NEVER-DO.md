# Never-do — contrato de geração

> Texto autoritativo do catálogo never-do neste pacote API (`skills.generation`).
> Se comentários em `rules.py` divergirem deste arquivo, corrija para bater com `NEVER-DO.md`.

Escopo: anti-padrões do **contrato de geração** (formato / plano / conteúdo / validação). Não cobre ops genéricas (logging de secrets, packaging, etc.).

## Lista

1. **Nunca** pedir auto-checagem / self-validate da LLM (“valide o JSON”, “confira a quantidade”, “revise antes de retornar”) como substituto de validação determinística (`validator` / `validate_exercise_batch`, `math_check` / `check_math_batch`, `verify_plan_echo`, RELY / `reliability.py`).
2. **Nunca** tratar schema-in-prompt, dump de JSON Schema, exemplo fenced de `ExerciseBatch`, ou lista “obrigatório: enunciado, resposta…” como **contrato de formato**. Formato = `models.py` + Structured Outputs + validadores (ver `AUTHORITY.md`).
3. **Nunca** misturar regras pedagógicas / persona em `prompts.py` como se fossem schema ou API de campos — wiring de persona/pedagogia é **Phase 19+** (PROMPT-02); até lá, não expandir “prompt theater”.
4. **Nunca** confundir `reasoning_effort` (knob de API no nível da run, `reasoning.py`) com pedagógica `tipo_raciocinio` (fora do escopo de produto v2.2).
5. **Nunca** inventar pastas de agent skill (`.cursor/skills`, `.claude/skills`, …) como casa do contrato — o pacote autoritativo é `exercise-ai/skills/generation/`.
6. **Nunca** enfraquecer ou pular RELY / testes de validator “porque o prompt já valida”.
7. **Nunca** endurecer só o prompt quando a garantia nova deveria entrar em Pydantic / validator / plan-echo primeiro (LLM não é fonte de verdade — `AGENTS.md`).

Mapa de autoridade (quem manda em cada eixo): `AUTHORITY.md`. Tríade: `TRIAD.md`.
