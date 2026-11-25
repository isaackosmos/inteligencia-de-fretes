"""Transformações puras usadas pelo painel; sem acesso a UI ou treinamento."""
from math import isfinite
import pandas as pd


def filter_period(frame, dates):
    if not isinstance(dates, (tuple, list)) or len(dates) != 2:
        raise ValueError('Selecione a data inicial e a data final. Para analisar um único dia, selecione a mesma data nas duas posições.')
    start, end = map(pd.Timestamp, dates)
    if pd.isna(start) or pd.isna(end) or start > end:
        raise ValueError('Período inválido: a data inicial deve ser anterior ou igual à final.')
    # Incluir todo o último dia, mesmo se outra fonte passar a trazer horário.
    return frame[frame['Dta.liq.'].ge(start.normalize()) & frame['Dta.liq.'].lt(end.normalize() + pd.Timedelta(days=1))].copy()


def monthly_comparison(frame):
    """Tarifas mensais usam exatamente as mesmas toneladas e itens dos dois lados."""
    common = frame[(frame['tarifa_orcada_rs_t'] > 0) & (frame['peso_liquido_t'] > 0) & (frame['Valor líquido'] > 0)].copy()
    common['mes'] = common['Dta.liq.'].dt.to_period('M').astype(str)
    common['meta_rs'] = common['tarifa_orcada_rs_t'] * common['peso_liquido_t']
    result = common.groupby('mes').agg(realizado_rs=('Valor líquido', 'sum'), meta_rs=('meta_rs', 'sum'), peso_t=('peso_liquido_t', 'sum'), itens=('Item', 'size'))
    result['Realizado · R$/t'] = result['realizado_rs'] / result['peso_t']
    result['Meta ajustada · R$/t'] = result['meta_rs'] / result['peso_t']
    result['desvio_pct'] = (result['realizado_rs'] / result['meta_rs'] - 1) * 100
    return result


def scenario_payload(result, assumptions, source=None):
    """Contrato explícito para exportar cálculo junto com suas premissas."""
    payload = {'resultado': result, 'premissas': assumptions}
    if source is not None:
        payload['fonte'] = str(source)
    return payload


def valid_vehicle(row):
    """Campos incompletos não devem derrubar a tela ou virar custo zero."""
    try:
        capacity, consumption, toll = (float(row[key]) for key in ['capacidade_t', 'rendimento_km_l', 'pedagio_rs'])
        return all(isfinite(x) for x in [capacity, consumption, toll]) and capacity > 0 and consumption > 0 and toll >= 0
    except (ValueError, TypeError, KeyError):
        return False
