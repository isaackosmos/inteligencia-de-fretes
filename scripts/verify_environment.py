"""Instala e testa o projeto em um venv novo; requer acesso ao índice de pacotes.

Não altera o ambiente de desenvolvimento. Mantém diretório e logs de verificação
para auditoria. Usa o mesmo Python/OS da máquina, não valida outros sistemas.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    root = Path(root).resolve()
    workspace = Path(tempfile.mkdtemp(prefix='frete-ambiente-'))
    env_path = workspace / 'venv'
    python = env_path / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    destination = root / 'reports/validacao_ambiente.json'
    record = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
              'workspace': str(workspace), 'python_origin': sys.executable,
              'status': 'running', 'steps': [],
              'limitation': 'Venv e instalação novos na mesma máquina/versão de Python; não comprova portabilidade entre sistemas operacionais.'}
    environment = os.environ.copy()
    for name in ['PYTHONPATH', 'PYTHONHOME']:
        environment.pop(name, None)
    environment.update(PYTHONNOUSERSITE='1', PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_INPUT='1',
                       MPLCONFIGDIR=str(workspace / 'matplotlib'))

    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding='utf-8')

    def run(name, command, cwd):
        log = workspace / f'{name}.log'
        started = time.monotonic()
        print(f'[{name}]', flush=True)
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run(command, cwd=cwd, env=environment, stdout=stream,
                                    stderr=subprocess.STDOUT, check=False)
        record['steps'].append({'name': name, 'command': command, 'returncode': result.returncode,
                                'duration_seconds': round(time.monotonic() - started, 3), 'log': str(log)})
        save()
        if result.returncode:
            raise RuntimeError(f'{name} falhou; consulte {log}')

    save()
    try:
        run('create_venv', [sys.executable, '-m', 'venv', str(env_path)], workspace)
        run('installer', [str(python), '-m', 'pip', 'install', '--upgrade', 'pip'], workspace)
        run('locked_dependencies', [str(python), '-m', 'pip', 'install', '-r', str(root / 'requirements-lock.txt')], workspace)
        run('install_project', [str(python), '-m', 'pip', 'install', str(root) + '[docs,render]'], workspace)
        run('dependency_consistency', [str(python), '-m', 'pip', 'check'], workspace)
        # Executado fora da pasta do projeto, sem PYTHONPATH: comprova o wheel instalado.
        check = """from pathlib import Path
import sys, frete.simulation
from frete.simulation import component_scenario
path = Path(frete.simulation.__file__).resolve()
assert Path(sys.prefix).resolve() in path.parents, path
assert component_scenario(100, 6, 2, 0, 20, 100)['custo_rs'] == 300
print('Pacote instalado importado de:', path)
"""
        run('installed_package', [str(python), '-c', check], workspace)
        run('tests', [str(python), '-m', 'pytest', '-q'], root)
        run('freeze', [str(python), '-m', 'pip', 'freeze'], workspace)
        record['status'] = 'success'
    except (RuntimeError, OSError) as exc:
        record['status'] = 'failed'
        record['error'] = str(exc)
    finally:
        record['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        save()
    print(destination, record['status'], flush=True)
    return 0 if record['status'] == 'success' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    raise SystemExit(verify())
