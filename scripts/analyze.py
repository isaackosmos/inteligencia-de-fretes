import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from frete.analysis import analyze
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(ROOT / "data/processed/base_modelagem_frete.csv"))
    args = parser.parse_args()
    print(analyze(args.data, ROOT))
