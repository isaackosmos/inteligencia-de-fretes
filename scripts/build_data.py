"""Execute: python scripts/build_data.py --root ."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from frete.data import write_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconstrói e audita base de itens de frete")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(write_dataset(args.root), indent=2, ensure_ascii=False))
