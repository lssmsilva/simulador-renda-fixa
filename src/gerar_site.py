"""Gera a pagina final (site/index.html) juntando template.html + data/dados.json + regras.json.
Uso: python src/gerar_site.py   (rode depois de src/coletar.py)
"""
import json
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
dados = json.loads((RAIZ / "data" / "dados.json").read_text(encoding="utf-8"))
regras = json.loads((RAIZ / "regras.json").read_text(encoding="utf-8"))
html = (RAIZ / "src" / "template.html").read_text(encoding="utf-8")

versao = datetime.now().strftime("%Y%m%d%H%M%S")
html = html.replace("/*DADOS*/", json.dumps(dados, ensure_ascii=False))
html = html.replace("/*REGRAS*/", json.dumps(regras, ensure_ascii=False))
html = html.replace("/*VERSAO*/", json.dumps(versao))

saida = RAIZ / "site"
saida.mkdir(exist_ok=True)
(saida / "index.html").write_text(html, encoding="utf-8")
(saida / "versao.json").write_text(json.dumps({"versao": versao}), encoding="utf-8")
print("site/index.html gerado")
