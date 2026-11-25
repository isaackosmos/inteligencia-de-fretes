"""Valida reconstrução do pacote em diretório temporário, com o mesmo Python.

As fontes são ligadas por symlink somente para leitura pelo processamento.
Não instala dependências nem afirma testar outro sistema operacional.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from package_delivery import build_package
from run_pipeline import ORIGINALS
from check_project import verify_archive

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    root = Path(root)
    workspace = Path(tempfile.mkdtemp(prefix='frete-reproducao-'))
    archive_path = workspace / 'codigo.zip'
    build_package(root, archive_path)
    verify_archive(archive_path)
    extracted = workspace / 'projeto'
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP corrompido')
        archive.extractall(extracted)
    for filename in ORIGINALS:
        source = root / filename
        if not source.is_file():
            raise FileNotFoundError(source)
        (extracted / filename).symlink_to(source)
    command = [sys.executable, 'scripts/run_pipeline.py']
    print(f'Reconstrução completa em {extracted}', flush=True)
    process = subprocess.run(command, cwd=extracted, check=False)
    logfiles = sorted((extracted / 'reports/execucoes').glob('*/execucao.json'))
    pipeline = json.loads(logfiles[-1].read_text()) if logfiles else {}
    complete = process.returncode == 0 and pipeline.get('status') == 'success' and pipeline.get('complete') is True and pipeline.get('sources_unchanged') is True
    summary = {'status': 'success' if complete else 'failed',
               'returncode': process.returncode, 'workspace': str(extracted),
               'python': sys.executable, 'same_dependency_environment': True,
               'sources_symlinked': True, 'pipeline_log': str(logfiles[-1]) if logfiles else None,
               'limitation': 'Reconstrução em pasta limpa usando dependências já instaladas; não equivale a instalação em outra máquina.'}
    destination = root / 'reports/validacao_entrega.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(destination)
    return process.returncode or (0 if complete else 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raise SystemExit(verify())
