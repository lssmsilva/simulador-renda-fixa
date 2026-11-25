"""Coleta diaria dos dados do dashboard -> dados.json.

Fontes: BCB SGS (Selic meta 432, CDI diario 12, IPCA mensal 433) e Tesouro Transparente (CSV).
Regras: sempre usar datas (nao /ultimos/N, limitado a 20); nunca sobrescrever dados.json
se a validacao falhar (o dashboard continua com o ultimo dado bom e mostra a data).
Uso: python src/coletar.py
"""
import io
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
URL_TESOURO = ("https://www.tesourotransparente.gov.br/ckan/dataset/"
               "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
               "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv")
SAIDA = Path(__file__).resolve().parent.parent / "data" / "dados.json"


# ---------- busca (rede) ----------
CABECALHO = {"User-Agent": "Mozilla/5.0 (compatible; simulador-renda-fixa/1.0)"}


def baixar(url, params=None, tentativas=5, pausa=3, timeout=60):
    """GET com novas tentativas e pausa crescente (3s, 6s, 12s...).

    As APIs publicas as vezes derrubam a conexao (Connection reset by peer);
    quase sempre funciona na tentativa seguinte.
    """
    ultimo_erro = None
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=CABECALHO, timeout=timeout)
            if not r.ok:
                raise RuntimeError(f"{r.status_code}: {r.text[:200]}")
            return r
        except Exception as e:  # noqa: BLE001
            ultimo_erro = e
            if i < tentativas - 1:
                time.sleep(pausa * 2 ** i)
    raise RuntimeError(f"falhou apos {tentativas} tentativas: {ultimo_erro}")


def sgs(code, inicio, fim):
    params = {"formato": "json", "dataInicial": inicio.strftime("%d/%m/%Y"),
              "dataFinal": fim.strftime("%d/%m/%Y")}
    try:
        r = baixar(BCB.format(code=code), params=params)
        df = pd.DataFrame(r.json())
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"])
        return df.set_index("data")["valor"]
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"SGS {code} falhou: {e}") from e


def tesouro_selic():
    r = baixar(URL_TESOURO, timeout=120)
    t = pd.read_csv(io.BytesIO(r.content), sep=";", decimal=",", encoding="latin1")
    t["Data Base"] = pd.to_datetime(t["Data Base"], format="%d/%m/%Y")
    s = t[t["Tipo Titulo"].str.contains("Selic")]
    dia = s["Data Base"].max()
    linha = s[s["Data Base"] == dia].sort_values("Data Vencimento").iloc[0]
    return {"data_base": dia.strftime("%Y-%m-%d"),
            "taxa_venda": float(linha["Taxa Venda Manha"]),
            "pu_venda": float(linha["PU Venda Manha"])}


# ---------- calculo (puro, testavel) ----------
def cdi_anualizado(cdi_dia_pct):
    """CDI diario (% ao dia) -> % ao ano, base 252 dias uteis."""
    return ((1 + cdi_dia_pct / 100) ** 252 - 1) * 100


def ipca_acum12(ipca_mensal):
    """Serie de IPCA mensal (%) -> acumulado dos ultimos 12 meses (%)."""
    if len(ipca_mensal) < 12:
        raise ValueError("menos de 12 meses de IPCA")
    f = 1.0
    for v in ipca_mensal.iloc[-12:]:
        f *= 1 + v / 100
    return (f - 1) * 100


def validar(d, hoje=None):
    """Devolve (erros, avisos). Erro = nao grava; aviso = grava mas mostra."""
    hoje = hoje or datetime.now()
    erros, avisos = [], []
    for chave in ("selic", "cdi", "ipca_12m"):
        if d.get(chave, {}).get("valor") is None:
            erros.append(f"{chave} ausente")
    if erros:
        return erros, avisos
    if not 0 < d["selic"]["valor"] < 50:
        erros.append("Selic fora de 0-50%")
    if abs(d["cdi"]["valor"] - d["selic"]["valor"]) > 0.5:
        erros.append("CDI anualizado diverge da Selic meta em mais de 0,5 p.p.")
    if not -2 < d["ipca_12m"]["valor"] < 30:
        erros.append("IPCA 12m fora de -2% a 30%")
    idade_cdi = (hoje - datetime.strptime(d["cdi"]["data"], "%Y-%m-%d")).days
    if idade_cdi > 5:
        avisos.append(f"CDI com {idade_cdi} dias de atraso")
    idade_ipca = (hoje - datetime.strptime(d["ipca_12m"]["data_ref"], "%Y-%m-%d")).days
    if idade_ipca > 75:
        avisos.append("IPCA mais antigo que o esperado (>75 dias)")
    return erros, avisos


def montar(selic, cdi_dia, ipca_mes, tesouro):
    return {
        "gerado_em": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "selic": {"valor": float(selic.iloc[-1]), "data": selic.index[-1].strftime("%Y-%m-%d")},
        "cdi": {"valor": round(cdi_anualizado(cdi_dia.iloc[-1]), 4),
                "data": cdi_dia.index[-1].strftime("%Y-%m-%d")},
        "ipca_12m": {"valor": round(ipca_acum12(ipca_mes), 4),
                     "data_ref": ipca_mes.index[-1].strftime("%Y-%m-%d")},
        "tesouro_selic": tesouro,
    }


def main():
    hoje = pd.Timestamp.today().normalize()
    try:
        selic = sgs(432, hoje - timedelta(days=400), hoje)
        cdi = sgs(12, hoje - timedelta(days=30), hoje)
        ipca = sgs(433, hoje - timedelta(days=550), hoje)
        dados = montar(selic, cdi, ipca, tesouro_selic())
    except Exception as e:  # noqa: BLE001
        print("ERRO na coleta, mantendo dados.json anterior:", e)
        return 1
    erros, avisos = validar(dados)
    dados["avisos"] = avisos
    if erros:
        print("VALIDACAO FALHOU, nao gravei:", erros)
        return 1
    SAIDA.parent.mkdir(exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    print("dados.json atualizado:", dados["gerado_em"], "| avisos:", avisos or "nenhum")
    return 0


if __name__ == "__main__":
    sys.exit(main())
