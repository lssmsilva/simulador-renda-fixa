"""Calculo liquido de renda fixa (v1). Funcoes puras: sem internet, faceis de testar.

Simplificacoes assumidas (mostrar ao usuario no dashboard):
- CDI e IPCA constantes no periodo (projecao = valor atual).
- Rendimento mensal = (1+CDI_aa)^(1/12)-1, multiplicado pelo % do CDI.
- Aporte no inicio de cada mes; IR calculado por aporte conforme o tempo de cada um.
- Mes = 30,4 dias para achar a faixa do IR.
"""
import json
from pathlib import Path

REGRAS = json.loads((Path(__file__).resolve().parent.parent / "regras.json").read_text(encoding="utf-8"))


def aliquota_ir(dias, regras=REGRAS):
    for faixa in regras["ir_regressivo"]:
        if dias <= faixa["ate_dias"]:
            return faixa["aliquota"]
    raise ValueError("faixa de IR nao encontrada")


def _taxa_mensal_cdi(cdi_aa, pct_cdi):
    cdi_m = (1 + cdi_aa / 100) ** (1 / 12) - 1
    return cdi_m * pct_cdi / 100


def _depositos(valor, aporte, meses):
    """Lista (mes_do_deposito, valor). Inicial no mes 0; aportes nos meses 1..meses-1."""
    deps = [(0, valor)]
    deps += [(k, aporte) for k in range(1, meses) if aporte > 0]
    return deps


def simular_pos(valor, aporte, meses, cdi_aa, pct_cdi, isento_ir=False, regras=REGRAS):
    """CDB, LCI/LCA: retorna bruto, IR e liquido finais."""
    i = _taxa_mensal_cdi(cdi_aa, pct_cdi)
    investido = bruto = ir = 0.0
    for mes, v in _depositos(valor, aporte, meses):
        n = meses - mes
        final = v * (1 + i) ** n
        rend = final - v
        dias = n * regras["dias_por_mes"]
        ir += 0.0 if isento_ir else rend * aliquota_ir(dias, regras)
        investido += v
        bruto += final
    return {"investido": investido, "bruto": bruto, "ir": ir, "liquido": bruto - ir}


def simular_tesouro_selic(valor, aporte, meses, cdi_aa, regras=REGRAS):
    """Tesouro Selic ~ 100% do CDI, com IR e taxa de custodia da B3 (0,20% a.a. sobre o que passa de R$10 mil)."""
    t = regras["tesouro_selic"]
    base = simular_pos(valor, aporte, meses, cdi_aa, 100, regras=regras)
    # custodia aproximada sobre o saldo medio entre investido e bruto final
    saldo_medio = (base["investido"] + base["bruto"]) / 2
    custodia = t["custodia_aa"] * (meses / 12) * max(0.0, saldo_medio - t["isento_ate"])
    base["custodia"] = custodia
    base["liquido"] -= custodia
    return base


def simular_poupanca(valor, aporte, meses, selic_aa, tr_mensal=0.0, regras=REGRAS):
    p = regras["poupanca"]
    if selic_aa > p["limite_selic_aa"]:
        i = p["rendimento_mensal"] + tr_mensal
    else:
        i = ((1 + selic_aa / 100) ** (1 / 12) - 1) * p["fracao_selic_abaixo_limite"] + tr_mensal
    investido = bruto = 0.0
    for mes, v in _depositos(valor, aporte, meses):
        investido += v
        bruto += v * (1 + i) ** (meses - mes)
    return {"investido": investido, "bruto": bruto, "ir": 0.0, "liquido": bruto}


def taxa_anual_liquida(investido, liquido, meses):
    """Aproximacao: retorno total liquido anualizado (ignora o momento dos aportes)."""
    return ((liquido / investido) ** (12 / meses) - 1) * 100


def veredito(liquido, poupanca_liquido, investido, meses, ipca_aa):
    """Favoravel: > inflacao e > poupanca. Atencao: > inflacao mas <= poupanca. Desfavoravel: <= inflacao."""
    inflacao = investido * (1 + ipca_aa / 100) ** (meses / 12)
    if liquido <= inflacao:
        return "desfavoravel"
    return "favoravel" if liquido > poupanca_liquido else "atencao"


def simular_tudo(valor, aporte, meses, cdi_aa, selic_aa, ipca_aa,
                 pct_cdb=100, pct_lci=90, tr_mensal=0.0, regras=REGRAS):
    produtos = {
        "poupanca": simular_poupanca(valor, aporte, meses, selic_aa, tr_mensal, regras),
        "cdb": simular_pos(valor, aporte, meses, cdi_aa, pct_cdb, regras=regras),
        "tesouro_selic": simular_tesouro_selic(valor, aporte, meses, cdi_aa, regras),
    }
    if meses >= regras["lci_lca"]["prazo_minimo_meses"]:
        produtos["lci_lca"] = simular_pos(valor, aporte, meses, cdi_aa, pct_lci, isento_ir=True, regras=regras)
    pl = produtos["poupanca"]["liquido"]
    for nome, r in produtos.items():
        r["taxa_liquida_aa"] = taxa_anual_liquida(r["investido"], r["liquido"], meses)
        r["veredito"] = veredito(r["liquido"], pl, r["investido"], meses, ipca_aa) if nome != "poupanca" \
            else ("desfavoravel" if r["liquido"] <= r["investido"] * (1 + ipca_aa / 100) ** (meses / 12) else "referencia")
    return produtos


def cdb_equivalente(pct_lci, aliquota):
    """% do CDI de um CDB que empata com a LCI/LCA isenta: pct / (1 - IR)."""
    return pct_lci / (1 - aliquota)
