import pytest
from calc import *

def test_faixas_ir():
    assert aliquota_ir(180) == 0.225
    assert aliquota_ir(181) == 0.20
    assert aliquota_ir(360) == 0.20
    assert aliquota_ir(361) == 0.175
    assert aliquota_ir(720) == 0.175
    assert aliquota_ir(721) == 0.15

def test_cdb_12_meses_sem_aporte():
    # CDI 10% a.a., 100%: bruto = 10000*1.10 = 11000; 12 meses = 364,8 dias -> 17,5%
    r = simular_pos(10000, 0, 12, 10.0, 100)
    assert r["bruto"] == pytest.approx(11000, rel=1e-9)
    assert r["ir"] == pytest.approx(1000 * 0.175, rel=1e-9)
    assert r["liquido"] == pytest.approx(10825, rel=1e-9)

def test_lci_isenta():
    r = simular_pos(10000, 0, 12, 10.0, 90, isento_ir=True)
    assert r["ir"] == 0
    assert r["bruto"] == pytest.approx(10000 * (1 + 0.9 * ((1.10) ** (1/12) - 1)) ** 12)

def test_aporte_mensal_ir_por_aporte():
    r = simular_pos(0, 1000, 13, 10.0, 100)  # aportes nos meses 1..12
    assert r["investido"] == 12000
    assert r["ir"] > 0 and r["ir"] < (r["bruto"] - 12000) * 0.225

def test_poupanca_regra_atual():
    r = simular_poupanca(10000, 0, 12, selic_aa=14.5)
    assert r["bruto"] == pytest.approx(10000 * 1.005 ** 12)

def test_poupanca_selic_baixa_usa_70pct():
    r = simular_poupanca(10000, 0, 12, selic_aa=6.0)
    assert r["bruto"] == pytest.approx(10000 * (1 + 0.7 * (1.06 ** (1/12) - 1)) ** 12)

def test_tesouro_custodia_isenta_ate_10k():
    r = simular_tesouro_selic(5000, 0, 12, 10.0)
    assert r["custodia"] == 0

def test_tesouro_custodia_acima_de_10k():
    r = simular_tesouro_selic(50000, 0, 12, 10.0)
    assert r["custodia"] > 0

def test_equivalencia():
    assert cdb_equivalente(90, 0.15) == pytest.approx(105.882, rel=1e-4)
    assert cdb_equivalente(90, 0.225) == pytest.approx(116.129, rel=1e-4)

def test_lci_so_a_partir_de_6_meses():
    assert "lci_lca" not in simular_tudo(10000, 0, 5, 14, 14.5, 4.5)
    assert "lci_lca" in simular_tudo(10000, 0, 6, 14, 14.5, 4.5)

def test_veredito_cenario_atual():
    r = simular_tudo(10000, 0, 12, 14.65, 14.5, 4.5)
    assert r["cdb"]["veredito"] == "favoravel"
    assert r["lci_lca"]["liquido"] > r["cdb"]["liquido"]  # 90% isento vence 100% tributado em 12m

def test_veredito_atencao_e_desfavoravel():
    # CDI muito baixo e inflacao alta: nada ganha
    r = simular_tudo(10000, 0, 12, 3.0, 3.0, 8.0)
    assert r["cdb"]["veredito"] == "desfavoravel"
