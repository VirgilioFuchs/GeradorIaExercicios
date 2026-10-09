"""Check the public setup paths and local demonstration limits."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_README = REPO_ROOT / "demo" / "README.md"
ROOT_README = REPO_ROOT / "README.md"


def test_demo_readme_setup_and_local_limits() -> None:
    text = DEMO_README.read_text(encoding="utf-8")
    for needle in (
        "python -m pip install -e .",
        "python demo/serve.py",
        "http://[::1]:8642/",
        "IPv6",
        "HTTP 409",
        "servidor de produção",
        "../README.md",
    ):
        assert needle in text, f"missing instruction in demo/README.md: {needle!r}"


def test_root_readme_demo_and_offline_example() -> None:
    text = ROOT_README.read_text(encoding="utf-8")
    assert "(demo/README.md)" in text
    assert "http://[::1]:8642/" in text
    assert "--habilidade-bncc EF07MA18 --quantidade 1 --out exemplo.json" in text
    assert "[licença MIT](LICENSE)" in text
    assert (REPO_ROOT / "LICENSE").is_file()
