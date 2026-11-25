"""Importa série oficial já baixada; --download permite obter arquivo da ANP."""
import argparse
from pathlib import Path
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from frete.anp import SOURCE_URL, build_diesel


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--start', default='2025-01')
    parser.add_argument('--end', default='2026-08')
    args = parser.parse_args()
    source = ROOT / 'data/external/raw/anp_mensal_estados.xlsx'
    if args.download and not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(SOURCE_URL, headers={'User-Agent': 'Projeto-academico-frete/0.1'})
        with urllib.request.urlopen(request, timeout=45) as response:
            if not response.geturl().startswith('https://www.gov.br/anp/'):
                raise ValueError('Redirecionamento fora do domínio oficial')
            content = response.read(20 * 1024 * 1024 + 1)
        if len(content) > 20 * 1024 * 1024:
            raise ValueError('Arquivo excedeu limite de 20 MiB')
        from io import BytesIO
        if not zipfile.is_zipfile(BytesIO(content)):
            raise ValueError('A resposta não é um XLSX válido')
        source.write_bytes(content)
    if not source.exists():
        raise SystemExit('Fonte ausente. Execute com --download ou coloque a planilha oficial em data/external/raw/anp_mensal_estados.xlsx.')
    metadata = build_diesel(ROOT, args.start, args.end)
    print(f"Diesel importado: {metadata['rows']} referências, {metadata['states']} estados, {metadata['products']}")
