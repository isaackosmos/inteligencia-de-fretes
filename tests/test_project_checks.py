import importlib.util
import json
from pathlib import Path
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checks = load('check_project')
package = load('package_delivery')


def test_markdown_checks_only_explicit_local_links(tmp_path):
    (tmp_path / 'exists.md').write_text('ok')
    path = tmp_path / 'README.md'
    path.write_text('[ok](exists.md) [broken](missing.md) [web](https://example.com) `fake.md`\n```\n[code](absent.md)\n```\n`[inline](fake.md)`')
    assert checks.broken_markdown_links(path, tmp_path) == ['README.md: missing.md']


def test_manifest_and_empty_external_template_validation(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/a.py').write_text('print(1)')
    (tmp_path / 'data/external').mkdir(parents=True)
    (tmp_path / 'data/external/rotas.csv').write_text('rota_id,distancia_km\n')
    (tmp_path / 'data/external/diesel.csv').write_text('data,preco\n2026-01-01,6.5\n')
    archive = tmp_path / 'code.zip'
    package.build_package(tmp_path, archive)
    assert checks.verify_archive(archive) == 2
    with zipfile.ZipFile(archive) as z:
        assert 'data/external/rotas.csv' in z.namelist()
        assert 'data/external/diesel.csv' not in z.namelist()


def test_zip_rejects_tampered_entry(tmp_path):
    import pytest
    import hashlib
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('src/a.py', 'changed')
        z.writestr('MANIFESTO.json', json.dumps({'arquivos': {'src/a.py': hashlib.sha256(b'original').hexdigest()}}))
    with pytest.raises(ValueError, match='Hash divergente'):
        checks.verify_archive(archive)


def test_zip_rejects_notebook_output_even_with_valid_hash(tmp_path):
    import pytest
    import hashlib
    content = json.dumps({'cells': [{'cell_type': 'code', 'outputs': [{'text': 'sensitive'}], 'execution_count': 1}]}).encode()
    archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('notebooks/a.ipynb', content)
        z.writestr('MANIFESTO.json', json.dumps({'arquivos': {'notebooks/a.ipynb': hashlib.sha256(content).hexdigest()}}))
    with pytest.raises(ValueError, match='contém saídas'):
        checks.verify_archive(archive)


def test_skipped_checks_cannot_claim_general_success(tmp_path):
    result = checks.run_checks(tmp_path, skip_model=True, skip_zip=True)
    assert not result['all_checks_executed']
    assert not result['project_complete']
    assert result['status'] != 'passed'
    assert any(x['status'] == 'skipped' for x in result['checks'])


def test_public_diesel_requires_official_provenance_and_hash(tmp_path):
    import hashlib
    import pytest
    folder = tmp_path / 'data/external'
    folder.mkdir(parents=True)
    content = b'data,preco\n2026-01-01,6.5\n'
    (folder / 'diesel.csv').write_bytes(content)
    provenance = {'source_url': 'https://www.gov.br/anp/dados.xlsx', 'source_sha256': 'a' * 64,
                  'output_sha256': hashlib.sha256(content).hexdigest()}
    (folder / 'diesel_metadata.json').write_text(json.dumps(provenance))
    archive = tmp_path / 'code.zip'
    package.build_package(tmp_path, archive)
    assert checks.verify_archive(archive) == 2
    (folder / 'diesel.csv').write_text('alterado')
    with pytest.raises(ValueError, match='hash'):
        package.build_package(tmp_path, archive)


def test_training_provenance_checks_hashes_and_rejects_missing_fields(tmp_path):
    import pytest
    data, code = tmp_path / 'data.csv', tmp_path / 'modeling.py'
    data.write_text('training data')
    code.write_text('training implementation')
    metadata = {'source_sha256': checks.digest(data), 'training_code_sha256': checks.digest(code),
                'trained_at_utc': '2026-11-10T20:00:00+00:00',
                'package_versions': {name: '1.0' for name in ('numpy', 'pandas', 'scikit-learn', 'joblib')}}
    assert 'conferidos' in checks.validate_training_provenance(metadata, data, code)
    incomplete = {k: v for k, v in metadata.items() if k != 'source_sha256'}
    with pytest.raises(ValueError, match='source_sha256 ausente'):
        checks.validate_training_provenance(incomplete, data, code)
    code.write_text('changed implementation')
    with pytest.raises(ValueError, match='training_code_sha256'):
        checks.validate_training_provenance(metadata, data, code)


def pdf_fixture(root):
    from pypdf import PdfWriter
    folder = root / 'reports/final'
    folder.mkdir(parents=True)
    evidence = root / 'evidence.json'
    evidence.write_text('{"result": 1}')
    outputs = []
    for name in ('relatorio_executivo.pdf', 'relatorio_desenvolvimento.pdf'):
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        path = folder / name
        with path.open('wb') as stream:
            writer.write(stream)
        outputs.append({'file': name, 'pages': 1, 'sha256': checks.digest(path)})
    manifest = {'outputs': outputs, 'source_sha256': {'evidence.json': checks.digest(evidence)}}
    path = folder / 'pdf_manifest.json'
    path.write_text(json.dumps(manifest))
    return path, manifest


def test_pdf_manifest_checks_pages_and_current_evidence(tmp_path):
    import pytest
    pdf_fixture(tmp_path)
    assert '2 PDFs' in checks.verify_pdf_manifest(tmp_path)
    (tmp_path / 'evidence.json').write_text('changed evidence')
    with pytest.raises(ValueError, match='desatualizado: evidência'):
        checks.verify_pdf_manifest(tmp_path)


def test_pdf_manifest_rejects_path_escape(tmp_path):
    import pytest
    path, manifest = pdf_fixture(tmp_path)
    manifest['source_sha256'] = {'../outside.json': 'a' * 64}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='fora da raiz'):
        checks.verify_pdf_manifest(tmp_path)
    manifest['source_sha256'] = {'evidence.json': checks.digest(tmp_path / 'evidence.json')}
    manifest['outputs'].append({'file': '../../outside.pdf', 'pages': 1, 'sha256': 'a' * 64})
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='fora da raiz'):
        checks.verify_pdf_manifest(tmp_path)
