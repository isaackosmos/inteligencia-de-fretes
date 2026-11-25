"""Confere artefatos, coerência e pacote local sem treinar ou publicar."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from math import isfinite
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = {'rotas.csv', 'operacoes.csv', 'veiculos.csv', 'antt_coeficientes.csv', 'diesel.csv'}


METRIC_COLUMNS = ('MAE_rs_t', 'RMSE_rs_t', 'WAPE_tarifa', 'WAPE_custo', 'R2', 'vies_total_custo')
BENCHMARK_COLUMNS = {
    'reports/experimentos/benchmark_grupo_resumo.csv': (
        'modelo', 'janelas', 'n_validacao', 'MAE_treino_medio_rs_t', 'MAE_janelas_medio_rs_t',
    ) + METRIC_COLUMNS,
    'reports/experimentos/benchmark_grupo_janelas.csv': (
        'modelo', 'inicio_validacao', 'fim_exclusivo', 'n_treino', 'n_validacao',
        'fretes_em_comum_removidos_do_treino', 'MAE_treino_rs_t',
    ) + METRIC_COLUMNS,
}


def validate_group_benchmark(name, content):
    rows = csv.DictReader(content.decode('utf-8-sig').splitlines())
    expected = BENCHMARK_COLUMNS[name]
    if tuple(rows.fieldnames or ()) != expected:
        raise ValueError(f'Colunas inesperadas no resumo agregado: {name}')
    for row in rows:
        if None in row or row['modelo'] not in {'random_forest', 'gradient_boosting', 'arvore_decisao'}:
            raise ValueError(f'Linha inesperada no resumo agregado: {name}')
        for field in expected[1:]:
            value = row[field]
            if field in {'inicio_validacao', 'fim_exclusivo'}:
                datetime.strptime(value, '%Y-%m-%d')
            elif field != 'R2' or value != '':
                if value is None or not isfinite(float(value)):
                    raise ValueError(f'Métrica inválida no resumo agregado: {name}')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_archive(path):
    """Verifica conteúdo efetivo, manifesto, segurança de caminhos e notebooks."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('ZIP corrompido ou com entradas duplicadas')
        manifest = json.loads(archive.read('MANIFESTO.json'))
        declared = manifest['arquivos']
        if set(names) != set(declared) | {'MANIFESTO.json'}:
            raise ValueError('Entradas não correspondem ao manifesto')
        public_names = {'data/external/diesel.csv', 'data/external/diesel_metadata.json'}
        declared_public = set(manifest.get('fontes_publicas_incluidas', []))
        if declared_public:
            if declared_public != public_names or not public_names.issubset(names):
                raise ValueError('Declaração de série pública incompleta')
            provenance = json.loads(archive.read('data/external/diesel_metadata.json'))
            validate_public_diesel(archive.read('data/external/diesel.csv'), provenance)
        for name in names:
            part = PurePosixPath(name)
            if part.is_absolute() or '..' in part.parts or '\\' in name:
                raise ValueError(f'Caminho inseguro: {name}')
            if name == 'MANIFESTO.json':
                continue
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != declared[name]:
                raise ValueError(f'Hash divergente: {name}')
            if '.venv' in part.parts or 'models' in part.parts or '__pycache__' in part.parts or part.suffix in {'.xlsx', '.xls', '.joblib', '.pkl', '.pdf', '.parquet'}:
                raise ValueError(f'Artefato vedado no pacote: {name}')
            if name in BENCHMARK_COLUMNS:
                validate_group_benchmark(name, content)
            elif part.suffix == '.csv' or part.parts[0] == 'data':
                if name not in declared_public and (len(part.parts) != 3 or part.parts[:2] != ('data', 'external') or part.name not in TEMPLATES or len(content.decode('utf-8-sig').splitlines()) != 1):
                    raise ValueError(f'Base ou template preenchido no pacote: {name}')
            if part.suffix == '.ipynb':
                notebook = json.loads(content)
                if any(c.get('outputs') or c.get('execution_count') is not None for c in notebook.get('cells', []) if c.get('cell_type') == 'code'):
                    raise ValueError(f'Notebook contém saídas: {name}')
        return len(declared)


def validate_public_diesel(content, provenance):
    url = urlsplit(provenance.get('source_url', ''))
    if url.scheme != 'https' or url.hostname != 'www.gov.br' or not url.path.startswith('/anp/'):
        raise ValueError('Série diesel sem URL oficial ANP')
    if hashlib.sha256(content).hexdigest() != provenance.get('output_sha256'):
        raise ValueError('Série diesel não corresponde ao hash de proveniência')
    if len(provenance.get('source_sha256', '')) != 64:
        raise ValueError('Hash da fonte pública diesel ausente')


def validate_training_provenance(metadata, data_path, code_path):
    """Ausência de campo não comprova proveniência; divergências falham."""
    for field, path in [('source_sha256', data_path), ('training_code_sha256', code_path)]:
        recorded = metadata.get(field)
        if not isinstance(recorded, str) or len(recorded) != 64:
            raise ValueError(f'Proveniência não demonstrada: {field} ausente/inválido')
        if digest(path) != recorded:
            raise ValueError(f'Proveniência divergente: {field} não corresponde a {path}')
    timestamp = metadata.get('trained_at_utc')
    if not isinstance(timestamp, str):
        raise ValueError('Proveniência não demonstrada: trained_at_utc ausente')
    parsed = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError('Timestamp do treino deve registrar UTC explícito')
    packages = metadata.get('package_versions')
    if not isinstance(packages, dict) or any(not packages.get(name) for name in ('numpy', 'pandas', 'scikit-learn', 'joblib')):
        raise ValueError('Versões do ambiente de treino ausentes/incompletas')
    return f'Hashes de dados/código, timestamp UTC e versões conferidos: {code_path.name}'


def safe_local_path(base, relative):
    """Caminhos do manifesto são relativos; symlinks também não podem escapar."""
    if not isinstance(relative, str) or not relative or '\\' in relative:
        raise ValueError(f'Caminho inválido no manifesto: {relative}')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'Caminho fora da raiz no manifesto: {relative}')
    resolved = (Path(base) / path).resolve()
    if not resolved.is_relative_to(Path(base).resolve()):
        raise ValueError(f'Caminho fora da raiz no manifesto: {relative}')
    return resolved


def verify_pdf_manifest(root):
    from pypdf import PdfReader
    root = Path(root).resolve()
    folder = root / 'reports/final'
    manifest = json.loads((folder / 'pdf_manifest.json').read_text())
    outputs = manifest.get('outputs')
    if not isinstance(outputs, list) or not outputs:
        raise ValueError('Manifesto PDF sem saídas declaradas')
    names = [entry.get('file') for entry in outputs]
    if len(names) != len(set(names)):
        raise ValueError('Manifesto PDF com saídas duplicadas')
    if not {'relatorio_executivo.pdf', 'relatorio_desenvolvimento.pdf'}.issubset(names):
        raise ValueError('Manifesto PDF deve incluir executivo e desenvolvimento')
    sources = manifest.get('source_sha256')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Manifesto PDF sem hashes das evidências')
    for relative, expected in sources.items():
        source = safe_local_path(root, relative)
        if digest(source) != expected:
            raise ValueError(f'Manifesto PDF desatualizado: evidência {relative}')
    for output in outputs:
        path = safe_local_path(folder, output['file'])
        if path.suffix.lower() != '.pdf':
            raise ValueError(f'Saída declarada não é PDF: {output["file"]}')
        if digest(path) != output.get('sha256'):
            raise ValueError(f'Manifesto PDF desatualizado: saída {output["file"]}')
        pages = len(PdfReader(path).pages)
        if pages < 1 or pages != output.get('pages'):
            raise ValueError(f'Contagem de páginas PDF divergente: {output["file"]}')
        if output['file'] == 'relatorio_executivo.pdf' and pages > 5:
            raise ValueError('Relatório executivo excede cinco páginas')
    return f'{len(outputs)} PDFs com hashes, páginas e evidências atuais; revisão visual feita separadamente'


def broken_markdown_links(path, root):
    """Somente links Markdown explícitos; código inline não representa link."""
    text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
    text = re.sub(r'`[^`]*`', '', text)
    broken = []
    for target in re.findall(r'!?\[[^\]\n]*\]\(([^\n]+?)\)', text):
        target = target.strip().split(' "', 1)[0].strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        decoded = unquote(parsed.path)
        resolved = Path(decoded) if decoded.startswith('/') else path.parent / decoded
        if not resolved.exists():
            broken.append(f'{path.relative_to(root)}: {target}')
    return broken


def run_checks(root=ROOT, skip_model=False, skip_zip=False):
    root = Path(root).resolve()
    results = []

    def add(name, status, detail):
        results.append({'check': name, 'status': status, 'detail': str(detail)})

    def checked(name, function):
        try:
            add(name, 'passed', function())
        except Exception as error:
            add(name, 'failed', f'{type(error).__name__}: {error}')

    def sources():
        inventory = root / 'docs/inventario_fontes.json'
        if not inventory.exists():
            raise FileNotFoundError('Inventário ausente: executar scripts/inventory.py')
        entries = json.loads(inventory.read_text())['arquivos']
        for entry in entries:
            path = root / entry['arquivo']
            if digest(path) != entry['sha256']:
                raise ValueError(f'Fonte alterada: {entry["arquivo"]}')
        audit_path = root / 'data/processed/auditoria.json'
        if audit_path.exists():
            for name, expected in json.loads(audit_path.read_text())['source_sha256'].items():
                if digest(root / name) != expected:
                    raise ValueError(f'Auditoria não corresponde à fonte atual: {name}')
        return f'{len(entries)} fontes conferidas com inventário e auditoria disponível'
    checked('source_hashes', sources)

    expected = ['data/processed/base_modelagem_frete.csv', 'data/processed/auditoria.json',
                'reports/analise/resumo.json', 'reports/modelagem/resumo.json', 'models/frete_model.joblib',
                'reports/modelagem/metricas_teste.csv', 'reports/modelagem/previsoes_teste.csv',
                'reports/final/relatorio_desenvolvimento.md', 'notebooks/01_EDA.ipynb',
                'notebooks/02_Modelagem.ipynb', 'notebooks/03_Interpretacao.ipynb',
                'README.md', 'pyproject.toml', 'requirements-lock.txt', 'app/dashboard.py']
    missing = [p for p in expected if not (root / p).is_file()]
    add('expected_outputs', 'failed' if missing else 'passed', missing or f'{len(expected)} saídas presentes')

    def links():
        broken = []
        for path in [root / 'README.md', *(root / 'docs').glob('*.md'), *(root / 'reports/final').glob('*.md')]:
            if path.exists():
                broken.extend(broken_markdown_links(path, root))
        if broken:
            raise ValueError('; '.join(broken))
        return 'Links Markdown locais explícitos existentes; caminhos apenas em código não são tratados como links'
    checked('documentation_links', links)
    if (root / 'reports/final/pdf_manifest.json').is_file():
        checked('pdf_manifest', lambda: verify_pdf_manifest(root))
    else:
        add('pdf_manifest', 'warning', 'Manifesto PDF opcional ausente; PDFs não verificados')

    def model_consistency():
        import joblib
        import numpy as np
        import pandas as pd
        sys.path.insert(0, str(root / 'src'))
        from frete.modeling import read_data, features, NUMERIC, CATEGORICAL, metrics, temporal_split
        artifact = joblib.load(root / 'models/frete_model.joblib')
        summary = json.loads((root / 'reports/modelagem/resumo.json').read_text())
        if artifact['features'] != NUMERIC + CATEGORICAL or artifact['metadata'] != summary:
            raise ValueError('Modelo, lista de atributos e resumo não correspondem')
        data = read_data(root / 'data/processed/base_modelagem_frete.csv')
        if len(data) != summary['input_rows']:
            raise ValueError('Número de linhas da base mudou')
        eligible = data[(data.CtgI == 'Z101') & (data.frete_rs_t > 0) & (data.peso_liquido_t > 0) & (data.peso_liquido_t <= 40) & data.flag_rateio_divergente.eq(0)].sort_values('Dta.liq.')
        training, test, overlap = temporal_split(eligible)
        if (len(training), len(test), overlap) != (summary['n_train'], summary['n_test'], summary['overlapping_freights_removed_from_train']):
            raise ValueError('Divisão temporal divergente')
        pred = pd.read_csv(root / 'reports/modelagem/previsoes_teste.csv', dtype={'Nº frete': str})
        joined = test.merge(pred, on=['Nº frete', 'Item'], suffixes=('', '_saved'), validate='one_to_one')
        if len(joined) != len(test):
            raise ValueError('Chaves de teste divergentes')
        np.testing.assert_allclose(joined.frete_rs_t, joined.frete_rs_t_saved, rtol=1e-10)
        prediction = np.maximum(artifact['model'].predict(features(joined)), 0)
        np.testing.assert_allclose(prediction, joined.previsto_rs_t, rtol=1e-9, atol=1e-8)
        scores = metrics(joined.frete_rs_t, prediction, joined.peso_liquido_t)
        recorded = next(x for x in summary['test'] if x['model'] == summary['selected_model'])
        table = pd.read_csv(root / 'reports/modelagem/metricas_teste.csv').set_index('model')
        for key, value in scores.items():
            np.testing.assert_allclose(value, recorded[key], rtol=1e-9, atol=1e-9)
            np.testing.assert_allclose(value, table.loc[summary['selected_model'], key], rtol=1e-9, atol=1e-9)
        return f'{len(test)} previsões e métricas recalculadas sem treino; atributos conferidos'
    if skip_model:
        add('model_consistency', 'skipped', 'Solicitado --skip-model; coerência preditiva não verificada')
    else:
        checked('model_consistency', model_consistency)
    def model_provenance():
        import joblib
        artifact = joblib.load(root / 'models/frete_model.joblib')
        return validate_training_provenance(artifact['metadata'], root / 'data/processed/base_modelagem_frete.csv', root / 'src/frete/modeling.py')
    def candidate_provenance():
        import joblib
        artifact = joblib.load(root / 'models/frete_candidate.joblib')
        recorded = json.loads((root / 'reports/estabilidade/candidate_metadata.json').read_text())
        if recorded != artifact['metadata']:
            raise ValueError('Metadata candidato não corresponde ao artefato')
        return validate_training_provenance(recorded, root / 'data/processed/base_modelagem_frete.csv', root / 'src/frete/stability.py')
    if skip_model:
        add('model_provenance', 'skipped', 'Solicitado --skip-model; proveniência do treino não verificada')
        if (root / 'models/frete_candidate.joblib').exists():
            add('candidate_provenance', 'skipped', 'Solicitado --skip-model; proveniência candidata não verificada')
    else:
        checked('model_provenance', model_provenance)
        if (root / 'models/frete_candidate.joblib').exists():
            checked('candidate_provenance', candidate_provenance)
        else:
            add('candidate_provenance', 'warning', 'Artefato candidato opcional ausente')
    add('model_readiness', 'warning', 'Modelo experimental; melhoria em MAE não comprova adequação orçamentária ou desempenho prospectivo. Consultar viés e limites.')

    external_rows = {}
    for name in sorted(TEMPLATES):
        path = root / 'data/external' / name
        external_rows[name] = max(0, len(path.read_text(encoding='utf-8-sig').splitlines()) - 1) if path.exists() else None
    add('external_data', 'warning' if any(not n for n in external_rows.values()) else 'passed', external_rows)
    diesel_meta = root / 'data/external/diesel_metadata.json'
    if diesel_meta.exists():
        def public_diesel():
            provenance = json.loads(diesel_meta.read_text())
            validate_public_diesel((root / 'data/external/diesel.csv').read_bytes(), provenance)
            raw = root / 'data/external/raw/anp_mensal_estados.xlsx'
            if raw.is_file() and digest(raw) != provenance['source_sha256']:
                raise ValueError('Arquivo bruto ANP diverge do hash registrado')
            return f"Série pública ANP verificada: {external_rows['diesel.csv']} registros; não equivale a preço pago nem integração preditiva"
        checked('public_diesel_provenance', public_diesel)
    else:
        add('public_diesel_provenance', 'warning', 'Série pública com proveniência ainda não disponível')

    logs = sorted((root / 'reports/execucoes').glob('*/execucao.json'))
    if logs:
        last = json.loads(logs[-1].read_text())
        test_step = next((s for s in last.get('steps', []) if s['name'] == 'tests'), {})
        add('test_evidence', 'passed' if test_step.get('status') == 'success' else 'warning',
            f"Última execução registrada: {logs[-1].relative_to(root)}; testes={test_step.get('status', 'ausente')}; pipeline={last.get('status')}. Registro histórico não equivale a rodar testes agora.")
    else:
        add('test_evidence', 'skipped', 'Nenhuma execução auditada encontrada; testes não foram executados por este comando')
    if skip_zip:
        add('delivery_zip', 'skipped', 'Solicitado --skip-zip')
    else:
        checked('delivery_zip', lambda: f"{verify_archive(root / 'dist/codigo_frete.zip')} arquivos conferidos; manifesto e exclusões verificados")
        archive_path = root / 'dist/codigo_frete.zip'
        if archive_path.is_file():
            try:
                stale = []
                with zipfile.ZipFile(archive_path) as archive:
                    manifest = json.loads(archive.read('MANIFESTO.json'))
                    for name, expected_hash in manifest['arquivos'].items():
                        current = root / name
                        if not current.is_file():
                            stale.append(name)
                            continue
                        content = current.read_bytes()
                        if current.suffix == '.ipynb':
                            book = json.loads(content)
                            for cell in book.get('cells', []):
                                if cell.get('cell_type') == 'code':
                                    cell['outputs'] = []
                                    cell['execution_count'] = None
                            content = json.dumps(book, ensure_ascii=False, indent=2).encode('utf-8')
                        if hashlib.sha256(content).hexdigest() != expected_hash:
                            stale.append(name)
                add('delivery_snapshot_currentness', 'warning' if stale else 'passed',
                    'ZIP é snapshot anterior; arquivos alterados/ausentes: ' + ', '.join(stale) if stale else 'Entradas do ZIP correspondem aos arquivos locais atuais, com notebooks sem outputs')
            except Exception as error:
                add('delivery_snapshot_currentness', 'failed', f'{type(error).__name__}: {error}')

    failed = any(r['status'] == 'failed' for r in results)
    skipped = any(r['status'] == 'skipped' for r in results)
    return {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
            'status': 'failed' if failed else 'partial' if skipped else 'passed_with_warnings' if any(r['status'] == 'warning' for r in results) else 'passed',
            'all_checks_executed': not skipped, 'project_complete': False,
            'scope': 'Verificação de integridade local; não certifica entrega completa, conformidade legal ou execução dos testes atuais.',
            'checks': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--skip-model', action='store_true')
    parser.add_argument('--skip-zip', action='store_true')
    args = parser.parse_args()
    result = run_checks(args.root, args.skip_model, args.skip_zip)
    destination = args.root / 'reports/verificacao_projeto.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(1 if result['status'] == 'failed' else 2 if result['status'] == 'partial' else 0)
