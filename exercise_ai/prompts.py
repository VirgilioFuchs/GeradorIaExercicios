"""Prompt templates and builders for math exercise generation."""

import re

from exercise_ai.models import DificuldadeEnum, GenerationRequest, resolve_bncc_codes
from exercise_ai.skills.generation import get_persona_system

# Alias de descoberta: fonte única = get_persona_system() (PROMPT-02).
SYSTEM_PROMPT = get_persona_system()

_HYBRID_LABELS: dict[DificuldadeEnum, str] = {
    DificuldadeEnum.FACIL: "fácil (facil)",
    DificuldadeEnum.MEDIO: "médio (medio)",
    DificuldadeEnum.DIFICIL: "difícil (dificil)",
}

# ASCII controls \x00-\x1f and DEL \x7f (D-01).
_ASCII_CONTROLS = re.compile(r"[\x00-\x1f\x7f]")
_MAX_FIELD_LEN = 200

USER_PROMPT_TEMPLATE = (
    "Gere exercícios de matemática com base nos seguintes parâmetros:\n"
    "- Matéria: {materia}\n"
    "- Tópico: {topico}\n"
    "- Quantidade: {quantidade}\n\n"
    "Plano de dificuldade por exercício (slot → faixa):\n"
    "{slot_list}\n\n"
    "Requisitos obrigatórios:\n"
    "1. Gere exatamente {quantidade} exercício(s), um por slot acima, "
    "respeitando a dificuldade indicada em cada linha.\n"
    "2. Todos os exercícios devem pertencer estritamente ao tópico '{topico}'.\n"
    "3. Utilize português brasileiro formal e didático.\n"
    "4. No lote, o campo dificuldades é o resumo das faixas distintas usadas "
    "(ordem fácil→médio→difícil), não um valor por exercício."
)


def hygiene_prompt_field(value: str, field_name: str) -> str:
    """Strip ASCII controls + whitespace; reject empty or overlong (D-01..D-05)."""
    cleaned = _ASCII_CONTROLS.sub("", value).strip()
    if not cleaned:
        raise ValueError(f"{field_name} não pode ser vazio após higienização")
    if len(cleaned) > _MAX_FIELD_LEN:
        raise ValueError(
            f"{field_name} excede o limite de {_MAX_FIELD_LEN} caracteres "
            f"(recebido: {len(cleaned)})"
        )
    return cleaned


def _format_slot_list(request: GenerationRequest) -> str:
    """Numbered 1-based hybrid labels from itens_ordenados (D-01..D-04)."""
    lines = [
        f"{i}. {_HYBRID_LABELS[spec.dificuldade]}"
        for i, spec in enumerate(request.itens_ordenados, start=1)
    ]
    return "\n".join(lines)


def _format_bncc_section(codes: list[str]) -> str:
    """USER section listing BNCC codes only (D-05) — no official skill prose."""
    listed = ", ".join(codes)
    return (
        "\n\nHabilidades BNCC (códigos):\n"
        f"- {listed}\n"
        "Alinhe o conteúdo dos exercícios a esses códigos; "
        "não invente outros códigos BNCC."
    )


def build_prompts(request: GenerationRequest) -> tuple[str, str]:
    """Constrói a tupla (system_prompt, user_prompt) formatada a partir de uma requisição."""
    materia = hygiene_prompt_field(request.materia, "materia")
    topico = hygiene_prompt_field(request.topico, "topico")
    user_prompt = USER_PROMPT_TEMPLATE.format(
        materia=materia,
        topico=topico,
        quantidade=request.quantidade,
        slot_list=_format_slot_list(request),
    )
    bncc_codes = resolve_bncc_codes(request)
    if bncc_codes:
        user_prompt += _format_bncc_section(bncc_codes)
    return get_persona_system(), user_prompt
