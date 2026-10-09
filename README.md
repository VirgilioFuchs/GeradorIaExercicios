# Gerador de Exercícios com IA

Aplicação Python que gera exercícios de matemática via LLM a partir de parâmetros simples (matéria, tópico, dificuldade, quantidade), com validação estrutural obrigatória. No sucesso, a CLI imprime texto legível no **stdout** e grava o JSON estruturado no arquivo indicado por **`--out`**.

## Setup

**Preferred (editable install):** distribution name `exercise-ai`, import name `exercise_ai`.

```bash
pip install -e ".[dev]"
```

Then import the package (no `sys.path` hacks):

```python
from exercise_ai.service import generate_batch
```

**Lab dual path:** with the repo on `PYTHONPATH` or after the same editable install, always import `exercise_ai.*` (not flat `service` / `models`). A short-lived deprecated bridge lives at `exercise_ai.compat_shim` — removing it without a SemVer **MAJOR** is out of policy for v2.7.0.

## Variáveis de ambiente

Copie `exercise_ai/.env.example` para `exercise_ai/.env` (ou `.env` na raiz do repositório) e preencha as chaves. **Nunca** cole segredos reais neste README ou no código.

| Variável | Descrição |
|----------|-----------|
| `LLM_API_KEY` | Chave da API OpenAI (formato `sk-...`) |
| `GEMINI_API_KEY` | Chave da API Google Gemini (formato `AIza...`) |
| `GROK_API_KEY` | Chave da API xAI Grok |
| `LLM_PROVIDER` | Opcional: `openai`, `gemini` ou `grok`. Se omitido, o provedor é detectado pelas chaves disponíveis |
| `LLM_REASONING_EFFORT` | Opcional: `none` \| `low` \| `medium` \| `high` (padrão `medium`). Sobrescrito por `--reasoning` |
| `RELY_MAX_RETRIES` | Regenerações após a primeira tentativa (`0`–`3`). Padrão `1` se omitido. Sobrescrito por `--max-retries` |

## Como executar

`--out` é **obrigatório** no modo argparse. Flags de geração omitidas usam os defaults da demo (Matemática / Equação do primeiro grau / facil / 3).

### Wizard interativo (`gerar`)

Em um terminal interativo (TTY):

```bash
python -m exercise_ai.main gerar
```

O fluxo pergunta (com tip sob cada campo): matéria → tipo/tópico → **fáceis / médios / difíceis** → quantidade → **habilidades BNCC (opcional)** → provedor → reasoning → nome do JSON. **Enter** aceita o default (BNCC em branco = modo não curricular); o caminho do JSON é obrigatório (re-pergunta se vazio). Reasoning padrão do Enter e do env: **`medium`**.

Misto (2+ faixas >0) monta `GenerationRequest.plano`; uniforme (1 faixa) usa `dificuldade`+`quantidade` legados — o mesmo contrato da demo e do argparse `--plano`.

Para CI/scripts, continue usando as flags argparse (não use `gerar`).

### Argparse (CI / scripts)

```bash
python -m exercise_ai.main --out exercicios.json
```

Plano compacto (Phase 15):

```bash
python -m exercise_ai.main --plano 2,3,1 --out lote-misto.json
```

`--plano F,M,D` = contagens fácil, médio, difícil. Misto → `plano`; uma só faixa → legado uniforme.

BNCC curricular (lista global):

```bash
python -m exercise_ai.main \
  --habilidade-bncc EF06MA01,EF06MA02 \
  --out lote-bncc.json
```

Modo avançado (skills por slot; XOR com `--plano`):

```bash
python -m exercise_ai.main \
  --itens-json "[{\"dificuldade\":\"facil\",\"habilidade_bncc\":[\"EF06MA01\",\"EF06MA02\"]},{\"dificuldade\":\"facil\",\"habilidade_bncc\":[\"EF06MA01\"]},{\"dificuldade\":\"facil\"}]" \
  --out lote-avancado.json
```

Com parâmetros explícitos (uniforme legado):

```bash
python -m exercise_ai.main \
  --materia Matemática \
  --topico "Equação do primeiro grau" \
  --dificuldade facil \
  --quantidade 3 \
  --provider openai \
  --reasoning medium \
  --max-retries 1 \
  --out exercicios.json
```

| Flag | Obrigatória | Descrição |
|------|-------------|-----------|
| `--out` | sim | Arquivo JSON. Relativo → `exercicios-gerados/success/<nome>`; absoluto permanece |
| `--materia` | não | Matéria (padrão: Matemática) |
| `--topico` | não | Tópico (padrão: Equação do primeiro grau) |
| `--dificuldade` | não | `facil` \| `medio` \| `dificil` (padrão: facil); ignorado no payload se `--plano` |
| `--quantidade` | não | Inteiro de 1 a 40 (padrão: 3); com `--plano`, o payload usa soma/contagem das faixas |
| `--plano` | não | `F,M,D` contagens fácil,médio,difícil (ex.: `2,3,1`) |
| `--habilidade-bncc` | não | Códigos BNCC separados por vírgula; lista não-vazia ativa modo curricular |
| `--itens-json` | não | Array JSON de slots com `dificuldade` e `habilidade_bncc` opcional (XOR com `--plano`) |
| `--provider` | não | `openai` \| `gemini` \| `grok` para esta execução |
| `--reasoning` | não | `none` \| `low` \| `medium` \| `high` \| `xhigh` \| `max` (padrão `medium`) |
| `--max-retries` | não | Regenerações após a 1ª tentativa (`0`–`3`). Se omitido: `RELY_MAX_RETRIES` ou padrão `1` |

**Demo / CLI / wizard** compartilham o mesmo `GenerationRequest` (plano misto ou uniforme legado + BNCC opcional).

**Reasoning / thinking:** Grok recebe `reasoning_effort` na API; Gemini usa `ThinkingConfig.thinking_level` (`none` → `minimal`). OpenAI só envia o param em modelos com suporte (ex. família `gpt-5` / `gpt-6` / `o*`); o default `gpt-4o-mini` **omite** o campo (não é reasoning model). `xhigh`/`max` só em modelos OpenAI com reasoning.

Ajuda em português: `python -m exercise_ai.main --help`

### Regeneração e Phase 6

Em falha de validação estrutural ou resposta LLM inválida, o gerador regenera até N vezes com o **mesmo prompt** (sem apêndice de erro). Falhas matemáticas reutilizam o mesmo caminho (`generate_validated_batch`). Auth, timeout, rate-limit e conexão **não** regeneram no mesmo provider.

### Failover OpenAI ↔ Gemini

Se o provider primário falhar com erro de API de disponibilidade (`timeout`, `rate_limit`, `connection` ou `generic`), o lab tenta **uma vez** o outro do par OpenAI ↔ Gemini, reusando `generate_validated_batch` (sem segundo loop math/RELY). Em stderr: `[FAILOVER] openai -> gemini (timeout)` (ou o par inverso) e `[FAILOVER] usado: …` no sucesso — sem secrets.

- **Sem failover** em auth, recusa do modelo, resposta inválida tipada ou falha de validação/math.
- **Grok** fica fora da cadeia (single-provider).
- `--provider openai|gemini` **não** desliga o failover; não há flag `--no-failover` nesta fase.

## Como testar

A suite usa mocks e dados estáticos — **não** chama LLMs reais:

```bash
pip install -e ".[dev]"
python -m pytest exercise_ai -q
```

Em push/PR para `master`, o workflow GitHub Actions `CI` usa o mesmo caminho (editable install + pytest).

## Observabilidade de tokens

Cada chamada LLM grava um evento em memória; no fim da run a CLI faz **append** NDJSON em:

`exercise_ai/token-usage/{YYYY-MM-DD}/{provider}.ndjson`

- **Dia** = data civil no fuso local da máquina do operator.
- **Stderr:** linhas `[USAGE]` com tokens de entrada/saída, total, `duration_ms` e USD quando calculável (`indisponível` se ausente — nunca inventa `0`).
- **USD:** Grok preferencialmente via `cost_in_usd_ticks`; OpenAI/Gemini via tabela local aproximada (atualizar manualmente; sem scrape de pricing).
- Artefatos gerados estão no `.gitignore`; a pasta permanece via `.gitkeep`.
- Testes de usage usam mocks e `TOKEN_USAGE_DIR` injetável — sem LLM e sem arquivos locais de usage commitados.

## Embed / biblioteca

Contrato para um host embutir o gerador **in-process** via pacote instalável.

**Naming:** dist name `exercise-ai` (pip/metadata) vs import name `exercise_ai`.

### Demo local (throwaway)

Há um demo stdlib em [`demo/`](demo/) para ver o fluxo embed end-to-end:
`python demo/serve.py` → abra **http://[::1]:8642/**. É throwaway — **delete at
v2.0 close**; fora do CI. Detalhes anti-accretion em [`demo/README.md`](demo/README.md).

### Como chamar (preferred)

```bash
pip install -e ".[dev]"
```

```python
from exercise_ai.models import GenerationRequest, DificuldadeEnum
from exercise_ai.service import (
    generate_batch,
    ConfigError,
    InvalidRequestError,
    GenerationFailedError,
)

batch = generate_batch(
    GenerationRequest(
        materia="Matemática",
        topico="Equação do primeiro grau",
        dificuldade=DificuldadeEnum.FACIL,
        quantidade=3,
        # habilidade_bncc=["EF06MA01"],  # opcional — lista não-vazia = modo curricular
    )
)
# Sucesso: ExerciseBatch — serializável via batch.model_dump(exclude_none=True)
data = batch.model_dump(exclude_none=True)
```

**Lab dual path / deprecated bridge:** `from exercise_ai.compat_shim import generate_batch` re-exports the same callable with a `DeprecationWarning` pointing to `exercise_ai.service`. Do not remove the shim or dual-path docs in a MINOR release (v2.7.0 policy).

Assinatura: `generate_batch(request: GenerationRequest) -> ExerciseBatch` — **somente** `request` (sem kwargs `max_retries` / `provider` / `reasoning` nesta fase).

### Contrato BNCC (Phase 26)

| Campo | Onde | Regras |
|-------|------|--------|
| `habilidade_bncc` | `GenerationRequest` | `list[str] \| None`. Ausente/`[]` = não curricular. Não-vazia → curricular. Trim+upper; máx. 10; membership no catálogo embutido `exercise_ai/data/bncc_matematica_codigos.json` (~290 códigos Matemática EF/EM). |
| `habilidade_bncc` | `ExerciseSpec` (slot) | Opcional no modo avançado (`itens` / `--itens-json`). Validação igual ao request. |
| `habilidades_bncc` | `ExerciseBatch` (echo) | Anexado **pós-parse** pelo pipeline (`attach_bncc_echo`). Simples: ecoa a lista global. Avançado: união estável dos códigos dos slots. Omitido quando vazio (`exclude_none`). |

- O LLM **não** preenche BNCC via Structured Outputs (`LlmExerciseBatch` sem campos BNCC).
- Prompts injetam **apenas códigos** no USER (sem prosa oficial BNCC).
- **Sem UI de demo** para BNCC nesta fase — só CLI, wizard e este contrato README.

### Erros (três subclasses)

O host deve ramificar por **classe** (e opcionalmente `.kind` / attrs), não por matching de mensagem PT:

| Exceção | Base | Quando | Attrs úteis |
|---------|------|--------|-------------|
| `ConfigError` | `ValueError` | Chave/config ausente ou inválida | `.kind` (ex. `missing_key`) |
| `InvalidRequestError` | `ValueError` | Pedido/lote rejeitado (incl. esgotamento de validação) | `.kind` (ex. `validation_exhausted`) |
| `GenerationFailedError` | `RuntimeError` | Falha de API/provedor após o pipeline | `.retriable`, `.api_error_kind` |

Não trate `ValueError` genérico como contrato de host para esgotamento de validação — use `InvalidRequestError`.

Diagnósticos internos ainda usam `print` em stderr; o host pode usar `contextlib.redirect_stderr` até LOG-01.

### Contrato sequencial

**Uma geração por vez por processo.** Não há suporte a concorrência nesta fase — não chame `generate_batch` em paralelo no mesmo processo.

### Nomes de módulo

Com o pacote instalado (`exercise_ai.*`), os módulos flat não entram no `sys.path` do host — o risco de colisão com `models`/`service` homônimos some. Continue importando apenas `exercise_ai.*` (ou o bridge `exercise_ai.compat_shim`).

### Timeout Gemini e pior caso

O client Gemini usa `HttpOptions.timeout=30000` (**milissegundos** ≈ 30s, alinhado ao OpenAI `timeout=30.0`). Em pior caso o host pode esperar **vários minutos**: até `(max_retries+1)` tentativas × até 5 fallbacks de modelo Gemini × um hop de failover × 30s de timeout HTTP — ordem de grandeza, não SLA.

## Stdout vs stderr

- **Sucesso (stdout):** texto legível por exercício (`### Exercício N`, `Enunciado:`, `Resposta:`, `Explicação:`).
- **Sucesso (arquivo `--out`):** JSON UTF-8 do lote (`exercicios`), indentado, `ensure_ascii=False`.
- **Stderr:** rótulos de estágio (`Gerando…`, `Validando…`, `Nª Regeneração`), duração agregada (`total_ms` + `chamadas`), eventos `[USAGE]` (tokens/custo), eventos de desenvolvimento (início, parâmetros sem segredos, sucesso/falha) e detalhes `[VALIDAÇÃO]` / `[API:openai|gemini|grok]`. O motivo de erro só aparece após esgotar regenerações.

Exemplo mínimo do JSON em `--out`:

```json
{
  "exercicios": [
    {
      "enunciado": "...",
      "resposta": "...",
      "explicacao": "..."
    }
  ]
}
```
