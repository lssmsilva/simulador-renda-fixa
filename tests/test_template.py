from pathlib import Path

TEMPLATE = (Path(__file__).resolve().parent.parent / "src" / "template.html").read_text(encoding="utf-8")


def test_placeholders_aparecem_uma_vez():
    for marca in ("/*DADOS*/", "/*REGRAS*/", "/*VERSAO*/"):
        assert TEMPLATE.count(marca) == 1, marca
