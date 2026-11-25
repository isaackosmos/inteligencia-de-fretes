"""Treina e avalia os modelos sem usar o teste na seleção."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frete.modeling import train

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(ROOT / "data/processed/base_modelagem_frete.csv"))
    args = parser.parse_args()
    print(train(args.data, ROOT))
