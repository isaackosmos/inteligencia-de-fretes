"""Executa as etapas do projeto e registra uma trilha auditável, com interrupção em erro."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
ORIGINALS = ("Contexto do Desafio.pdf", "Manual.pdf", "Relatorio_Previsao_Custo_Frete.pdf",
             "Realizado.xlsx", "Orcado.xlsx", "base_modelagem_frete.csv")
PACKAGES = ("numpy", "pandas", "openpyxl", "scikit-learn", "scipy", "matplotlib", "joblib", "streamlit", "pytest")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def package_versions():
    versions = {}
    for package in PACKAGES:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def stages(skip_train=False, skip_tests=False):
    result = [("inventory", ["scripts/inventory.py"], False),
              ("build_data", ["scripts/build_data.py"], False),
              ("analyze", ["scripts/analyze.py"], False),
              ("train", ["scripts/train.py"], skip_train),
              ("report_development", ["scripts/report_development.py"], False),
              ("create_notebooks", ["scripts/create_notebooks.py"], False),
              ("execute_notebooks", ["scripts/execute_notebooks.py"], False),
              ("tests", ["-m", "pytest", "-q"], skip_tests)]
    return result


def run_pipeline(root=ROOT, skip_train=False, skip_tests=False):
    root = Path(root).resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex[:8]
    directory = root / "reports/execucoes" / run_id
    directory.mkdir(parents=True, exist_ok=False)
    report_path = directory / "execucao.json"
    started = time.monotonic()
    report = {"run_id": run_id, "status": "running", "complete": False,
              "started_at_utc": utc_now(), "finished_at_utc": None, "duration_seconds": None,
              "root": str(root), "python_executable": sys.executable,
              "python_version": platform.python_version(), "platform": platform.platform(),
              "package_versions": package_versions(),
              "source_sha256_before": {name: sha256(root / name) for name in ORIGINALS},
              "options": {"skip_train": skip_train, "skip_tests": skip_tests},
              "notes": (["Treino omitido: relatórios e notebooks podem reutilizar artefatos existentes; a execução é parcial e não comprova sua atualidade."] if skip_train else []),
              "steps": []}

    def save():
        temporary = report_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(report_path)

    save()
    exit_code = 0
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root / "src") + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    try:
        missing_sources = [name for name, digest in report["source_sha256_before"].items() if digest is None]
        if missing_sources:
            raise FileNotFoundError("Fontes originais ausentes: " + ", ".join(missing_sources))
        for name, args, skip in stages(skip_train, skip_tests):
            command = [sys.executable, *args]
            step = {"name": name, "command": command, "status": "skipped" if skip else "running",
                    "script_sha256": sha256(root / args[0]) if args[0].endswith(".py") else None,
                    "started_at_utc": None, "finished_at_utc": None, "duration_seconds": 0,
                    "returncode": None}
            report["steps"].append(step)
            save()
            if skip:
                continue
            step["started_at_utc"] = utc_now()
            step_started = time.monotonic()
            stdout_path, stderr_path = directory / f"{name}.stdout.log", directory / f"{name}.stderr.log"
            step["stdout_log"] = str(stdout_path.relative_to(root))
            step["stderr_log"] = str(stderr_path.relative_to(root))
            print(f"[{name}] {' '.join(command)}", flush=True)
            try:
                with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
                    process = subprocess.run(command, cwd=root, env=environment, stdout=stdout, stderr=stderr, check=False)
                step["returncode"] = process.returncode
                step["status"] = "success" if process.returncode == 0 else "failed"
            except OSError as error:
                step["status"] = "failed"
                step["error"] = str(error)
                step["returncode"] = 1
            finally:
                step["finished_at_utc"] = utc_now()
                step["duration_seconds"] = round(time.monotonic() - step_started, 3)
                save()
            if step["status"] == "failed":
                exit_code = step["returncode"] or 1
                report["status"] = "failed"
                break
        else:
            report["status"] = "partial_success" if skip_train or skip_tests else "success"
            report["complete"] = not (skip_train or skip_tests)
    except BaseException as error:
        report["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
    finally:
        report["source_sha256_after"] = {name: sha256(root / name) for name in ORIGINALS}
        report["sources_unchanged"] = report["source_sha256_before"] == report["source_sha256_after"]
        if not report["sources_unchanged"]:
            report["status"] = "failed"
            report["complete"] = False
            report["error"] = "Fontes originais foram modificadas durante a execução."
            exit_code = 1
        report["finished_at_utc"] = utc_now()
        report["duration_seconds"] = round(time.monotonic() - started, 3)
        save()
    print(f"Registro: {report_path} — {report['status']}", flush=True)
    return exit_code, report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-train", action="store_true", help="Reutiliza modelo existente e marca execução parcial")
    parser.add_argument("--skip-tests", action="store_true", help="Omite testes e marca execução parcial")
    args = parser.parse_args()
    return run_pipeline(args.root, args.skip_train, args.skip_tests)[0]


if __name__ == "__main__":
    raise SystemExit(main())
