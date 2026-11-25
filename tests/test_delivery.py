import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

spec = importlib.util.spec_from_file_location('package_delivery', Path(__file__).resolve().parents[1] / 'scripts/package_delivery.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_pacote_exclui_dados_e_saidas_e_confere_hashes(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/a.py').write_text('print(1)')
    (tmp_path / '.venv').mkdir()
    (tmp_path / '.venv/segredo.txt').write_text('não empacotar')
    (tmp_path / 'Realizado.xlsx').write_bytes(b'dados internos')
    (tmp_path / 'notebooks').mkdir()
    notebook = {'cells': [{'cell_type': 'code', 'execution_count': 1,
                           'source': ['print(1)'], 'outputs': [{'text': 'dado interno'}]}]}
    (tmp_path / 'notebooks/a.ipynb').write_text(json.dumps(notebook))
    destination = tmp_path / 'pacote.zip'
    module.build_package(tmp_path, destination)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'src/a.py', 'notebooks/a.ipynb', 'MANIFESTO.json'}
        copied = json.loads(archive.read('notebooks/a.ipynb'))
        assert copied['cells'][0]['outputs'] == []
        manifest = json.loads(archive.read('MANIFESTO.json'))
        for name, digest in manifest['arquivos'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    assert json.loads((tmp_path / 'notebooks/a.ipynb').read_text())['cells'][0]['outputs']
