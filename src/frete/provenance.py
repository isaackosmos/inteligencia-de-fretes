"""Proveniência coletada durante o ajuste, sem reconstruí-la retrospectivamente."""
import hashlib
from importlib import metadata
from pathlib import Path
from datetime import datetime, timezone


def training_provenance(data_path, code_path):
    return {'source_sha256': hashlib.sha256(Path(data_path).read_bytes()).hexdigest(),
            'training_code_sha256': hashlib.sha256(Path(code_path).read_bytes()).hexdigest(),
            'trained_at_utc': datetime.now(timezone.utc).isoformat(),
            'package_versions': {name: metadata.version(name) for name in ['numpy', 'pandas', 'scikit-learn', 'joblib']}}
