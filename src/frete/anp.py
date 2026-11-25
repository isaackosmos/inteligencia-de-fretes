"""Referência mensal de diesel ANP, separada dos dados operacionais e do modelo."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import pandas as pd
import openpyxl

SOURCE_PAGE = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos'
SOURCE_URL = 'https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/mensal/mensal-estados-desde-jan2013.xlsx'
REQUIRED = ['MÊS', 'PRODUTO', 'ESTADO', 'UNIDADE DE MEDIDA', 'PREÇO MÉDIO REVENDA', 'NÚMERO DE POSTOS PESQUISADOS']


def normalize_monthly(frame, start='2025-01', end='2026-08'):
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ValueError('Esquema ANP incompleto: ' + ', '.join(sorted(missing)))
    if pd.Period(start, 'M') > pd.Period(end, 'M'):
        raise ValueError('Período inicial posterior ao final')
    frame = frame.copy()
    dates = pd.to_datetime(frame['MÊS'], errors='coerce')
    diesel = frame['PRODUTO'].astype(str).str.upper().str.contains('DIESEL', regex=False)
    if (diesel & dates.isna()).any():
        raise ValueError('Data inválida em referência diesel')
    month = dates.dt.to_period('M')
    selected = frame.loc[diesel & month.between(pd.Period(start, 'M'), pd.Period(end, 'M'))].copy()
    if selected.empty:
        raise ValueError('Sem dados de diesel no período solicitado')
    prices = pd.to_numeric(selected['PREÇO MÉDIO REVENDA'], errors='coerce')
    units = selected['UNIDADE DE MEDIDA'].astype(str).str.strip().str.lower()
    if prices.isna().any() or not prices.map(math.isfinite).all() or (prices <= 0).any() or (~units.eq('r$/l')).any():
        raise ValueError('Preço inválido ou unidade diferente de R$/l')
    result = pd.DataFrame({'data': pd.to_datetime(selected['MÊS']).dt.to_period('M').dt.to_timestamp().dt.strftime('%Y-%m-%d'),
                           'localidade': selected['ESTADO'].astype(str).str.strip(),
                           'produto': selected['PRODUTO'].astype(str).str.strip(),
                           'preco_rs_l': prices, 'agregacao': 'mensal_estadual_ANP',
                           'n_postos_pesquisados': pd.to_numeric(selected['NÚMERO DE POSTOS PESQUISADOS'], errors='coerce'),
                           'url_fonte': SOURCE_URL})
    if result.duplicated(['data', 'localidade', 'produto']).any():
        raise ValueError('Referência mensal duplicada; não agregar silenciosamente')
    return result.sort_values(['localidade', 'produto', 'data']).reset_index(drop=True)


def read_official_workbook(path):
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        rows = iter(sheet.values)
        for _ in range(60):
            row = next(rows)
            if all(column in row for column in REQUIRED):
                columns = list(row)
                return pd.DataFrame(rows, columns=columns).loc[:, [c for c in columns if c is not None]]
        raise ValueError('Cabeçalho ANP não localizado nas primeiras 60 linhas')
    except StopIteration as exc:
        raise ValueError('Planilha ANP sem cabeçalho') from exc
    finally:
        workbook.close()


def build_diesel(root, start='2025-01', end='2026-08'):
    root = Path(root)
    source = root / 'data/external/raw/anp_mensal_estados.xlsx'
    result = normalize_monthly(read_official_workbook(source), start, end)
    collected = datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat()
    result['data_coleta'] = collected
    output = root / 'data/external/diesel.csv'
    result.to_csv(output, index=False, encoding='utf-8-sig')
    expected = pd.period_range(start, end, freq='M').astype(str).tolist()
    coverage = []
    for (state, product), group in result.groupby(['localidade', 'produto']):
        present = set(pd.to_datetime(group.data).dt.to_period('M').astype(str))
        coverage.append({'localidade': state, 'produto': product,
                         'meses': len(present), 'meses_ausentes': sorted(set(expected) - present)})
    metadata = {'source_page': SOURCE_PAGE, 'source_url': SOURCE_URL,
                'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
                'download_file_mtime_utc': collected, 'processed_at_utc': datetime.now(timezone.utc).isoformat(),
                'period_start': start, 'period_end': end, 'rows': len(result),
                'states': int(result.localidade.nunique()), 'products': sorted(result.produto.unique()),
                'coverage': coverage,
                'use': 'Contexto retrospectivo e referência de cenários; não integrado ao treinamento.',
                'limitations': ['Preço de revenda pesquisado, não custo pago pela transportadora.',
                                'Média mensal completa não estava disponível no início do mês.',
                                'Agosto/2026 mensal completo difere da base operacional encerrada em 04/08.',
                                'Geografia é estadual; não comprova local de abastecimento.',
                                'Número de postos é campo publicado, sem reinterpretar como postos únicos.']}
    (output.parent / 'diesel_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    return metadata
