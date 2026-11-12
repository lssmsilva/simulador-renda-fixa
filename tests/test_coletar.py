import pandas as pd
import pytest
from datetime import datetime
from coletar import cdi_anualizado, ipca_acum12, validar

HOJE = datetime(2026, 11, 12)

def bom():
    return {"selic": {"valor": 14.5, "data": "2026-10-29"},
            "cdi": {"valor": 14.4, "data": "2026-11-11"},
            "ipca_12m": {"valor": 4.5, "data_ref": "2026-10-01"}}

def test_cdi_anualizado():
    # 10% a.a. em base 252 -> fator diario ~ 0,0378%
    d = (1.10 ** (1 / 252) - 1) * 100
    assert cdi_anualizado(d) == pytest.approx(10.0, rel=1e-9)

def test_ipca_12m():
    s = pd.Series([0.5] * 12)
    assert ipca_acum12(s) == pytest.approx((1.005 ** 12 - 1) * 100)

def test_ipca_poucos_meses():
    with pytest.raises(ValueError):
        ipca_acum12(pd.Series([0.5] * 5))

def test_dados_bons():
    assert validar(bom(), HOJE) == ([], [])

def test_cdi_diverge_da_selic():
    d = bom(); d["cdi"]["valor"] = 9.0
    erros, _ = validar(d, HOJE)
    assert erros

def test_dado_ausente():
    d = bom(); d["cdi"]["valor"] = None
    assert validar(d, HOJE)[0]

def test_cdi_antigo_gera_aviso_nao_erro():
    d = bom(); d["cdi"]["data"] = "2026-11-01"
    erros, avisos = validar(d, HOJE)
    assert not erros and avisos

def test_ipca_absurdo():
    d = bom(); d["ipca_12m"]["valor"] = 80
    assert validar(d, HOJE)[0]
