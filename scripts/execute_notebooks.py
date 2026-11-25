"""Executa células Python dos notebooks locais gerados, guardando saídas textuais.

Não requer Jupyter para a verificação. Executar somente notebooks confiáveis.
"""
import contextlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in sorted((ROOT / 'notebooks').glob('*.ipynb')):
    notebook = json.loads(path.read_text())
    namespace = {}
    count = 0
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        count += 1
        stream = io.StringIO()
        def display(value):
            print(value.to_string() if hasattr(value, 'to_string') else str(value))
        namespace['display'] = display
        with contextlib.redirect_stdout(stream):
            exec(compile(''.join(cell['source']), str(path), 'exec'), namespace)
        cell['execution_count'] = count
        text = stream.getvalue()
        cell['outputs'] = [{'output_type': 'stream', 'name': 'stdout', 'text': text.splitlines(True)}] if text else []
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{path.name}: {count} células executadas')
