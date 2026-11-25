import pandas as pd
import pytest
from frete.anp import normalize_monthly


def source():
    return pd.DataFrame({'MÊS': pd.to_datetime(['2024-12-01', '2025-01-01', '2025-01-01', '2026-09-01']),
                         'PRODUTO': ['OLEO DIESEL S10', 'OLEO DIESEL S10', 'GASOLINA COMUM', 'OLEO DIESEL S10'],
                         'ESTADO': ['PARANA'] * 4, 'UNIDADE DE MEDIDA': ['R$/l'] * 4,
                         'PREÇO MÉDIO REVENDA': [5., 6., 7., 8.], 'NÚMERO DE POSTOS PESQUISADOS': [10] * 4})


def test_periodo_produto_e_unidade_nao_misturados():
    result = normalize_monthly(source())
    assert result[['data', 'produto', 'preco_rs_l']].to_dict('records') == [
        {'data': '2025-01-01', 'produto': 'OLEO DIESEL S10', 'preco_rs_l': 6}]


def test_duplicatas_e_preco_invalido_nao_viram_media():
    frame = source()
    with pytest.raises(ValueError, match='duplicada'):
        normalize_monthly(pd.concat([frame, frame]))
    frame.loc[1, 'PREÇO MÉDIO REVENDA'] = 0
    with pytest.raises(ValueError, match='Preço inválido'):
        normalize_monthly(frame)


def test_recusa_outro_tipo_unidade_e_periodo_invertido():
    frame = source()
    frame.loc[1, 'UNIDADE DE MEDIDA'] = 'R$/kg'
    with pytest.raises(ValueError, match='unidade'):
        normalize_monthly(frame)
    with pytest.raises(ValueError, match='posterior'):
        normalize_monthly(source(), '2026-08', '2025-01')


@pytest.mark.parametrize('price', [float('inf'), float('-inf'), float('nan')])
def test_preco_nao_finito_nao_entra_em_cenario(price):
    frame = source()
    frame.loc[1, 'PREÇO MÉDIO REVENDA'] = price
    with pytest.raises(ValueError, match='Preço inválido'):
        normalize_monthly(frame)
