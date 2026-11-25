"""Empacota o código sem ambiente local, modelos ou dados empresariais.

O arquivo é local. Não publica nem envia dados. Notebooks perdem suas saídas
somente dentro do ZIP para evitar incluir linhas da base incidentalmente.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ('src', 'scripts', 'app', 'tests', 'docs', 'notebooks')
FILES = ('README.md', 'pyproject.toml', 'requirements-lock.txt', '.gitignore', '.streamlit/config.toml',
         'output/apresentacao_ia_data_mining.pptx')
SUFFIXES = {'.py', '.md', '.toml', '.txt', '.json', '.ipynb'}
EXTERNAL_TEMPLATES = ('rotas.csv', 'operacoes.csv', 'veiculos.csv', 'antt_coeficientes.csv', 'diesel.csv')


def build_package(root, destination):
    root, destination = Path(root), Path(destination)
    paths = [root / name for name in FILES if (root / name).is_file()]
    for folder in DIRECTORIES:
        paths.extend(p for p in (root / folder).rglob('*')
                     if p.is_file() and p.suffix in SUFFIXES
                     and '__pycache__' not in p.parts)
    paths.extend(p for p in (root / 'reports/final').glob('*.md') if p.is_file())
    for name in ('benchmark_grupo_resumo.csv', 'benchmark_grupo_janelas.csv'):
        report = root / 'reports' / 'experimentos' / name
        if report.is_file():
            paths.append(report)
    for filename in EXTERNAL_TEMPLATES:
        template = root / 'data/external' / filename
        if template.is_file():
            # Nunca incluir dados externos preenchidos incidentalmente.
            if len(template.read_text(encoding='utf-8-sig').splitlines()) == 1:
                paths.append(template)
    public_metadata = root / 'data/external/diesel_metadata.json'
    public_data = root / 'data/external/diesel.csv'
    if public_metadata.is_file() and public_data.is_file():
        provenance = json.loads(public_metadata.read_text(encoding='utf-8'))
        url = urlsplit(provenance.get('source_url', ''))
        if url.scheme != 'https' or url.hostname != 'www.gov.br' or not url.path.startswith('/anp/'):
            raise ValueError('Fonte pública de diesel não possui URL oficial ANP')
        if hashlib.sha256(public_data.read_bytes()).hexdigest() != provenance.get('output_sha256'):
            raise ValueError('Série pública de diesel diverge do hash de proveniência')
        if len(provenance.get('source_sha256', '')) != 64:
            raise ValueError('Hash da fonte pública diesel ausente')
        paths.extend([public_data, public_metadata])
    entries = {}
    for path in sorted(set(paths)):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f'Link simbólico não permitido no pacote: {relative}')
        content = path.read_bytes()
        if path.suffix == '.ipynb':
            notebook = json.loads(content)
            for cell in notebook.get('cells', []):
                if cell.get('cell_type') == 'code':
                    cell['outputs'] = []
                    cell['execution_count'] = None
            content = json.dumps(notebook, ensure_ascii=False, indent=2).encode('utf-8')
        entries[relative] = content
    if not entries:
        raise ValueError('Nenhum arquivo de código ou documentação encontrado')
    manifest = {'tipo': 'codigo_sem_bases_operacionais', 'bases_operacionais_incluidas': False,
                'documentacao_contem_resultados_agregados': True,
                'notebooks_sem_saidas': True,
                'fontes_publicas_incluidas': ['data/external/diesel.csv', 'data/external/diesel_metadata.json'] if public_metadata in paths else [],
                'instrucao': 'Para o início rápido, adicionar Realizado.xlsx e Orcado.xlsx na raiz. Para run_pipeline.py/verify_delivery.py, fornecer os seis arquivos originais descritos no inventário. Executar README para reconstruir dados e modelo.',
                'arquivos': {name: hashlib.sha256(content).hexdigest() for name, content in entries.items()}}
    entries['MANIFESTO.json'] = json.dumps(manifest, indent=2, ensure_ascii=False).encode('utf-8')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/codigo_frete.zip')
    args = parser.parse_args()
    result = build_package(ROOT, args.output)
    print(f'{args.output}: {len(result["arquivos"])} arquivos; bases operacionais e modelos não incluídos; documentação contém resultados agregados')
