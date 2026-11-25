"""Estabilidade histórica fora da amostra, sem acessar o holdout já observado."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import joblib
from frete.experiments import WINDOWS, fit_candidate
from frete.modeling import read_data, features, metrics, temporal_split, NUMERIC, CATEGORICAL

CRITERIA = {"min_items": 100, "min_volume_t": 100., "max_abs_cost_bias": .10, "max_cost_wape": .30}

def eligible_history(df):
    date = pd.to_datetime(df["Dta.liq."], errors="raise")
    keep = (df.CtgI == "Z101") & (df.frete_rs_t > 0) & (df.peso_liquido_t > 0) & (df.peso_liquido_t <= 40) & (df.flag_rateio_divergente == 0) & (date < "2026-04-01")
    return df[keep].copy()

def generate_oof(history):
    """Previsões expansivas sem embaralhamento; uma observação por modelo/item."""
    if (pd.to_datetime(history["Dta.liq."]) >= "2026-04-01").any():
        raise ValueError("OOF de estabilidade permite somente histórico até março/2026")
    predictions, folds = [], []
    for fold, (start, end) in enumerate(WINDOWS, 1):
        training, validation, purged = temporal_split(history, start)
        validation = validation[pd.to_datetime(validation["Dta.liq."]) < end]
        if training.empty or validation.empty:
            raise ValueError(f"Janela {fold} não possui treino/validação suficientes")
        if set(training["Nº frete"]) & set(validation["Nº frete"]):
            raise ValueError("Frete compartilhado entre treino e validação")
        for name in ["rf_log", "rf_original"]:
            model = fit_candidate(name, training)
            pred = np.maximum(model.predict(features(validation)), 0)
            if not np.isfinite(pred).all():
                raise ValueError("Modelo produziu previsão não finita")
            part = validation[["Nº frete", "Item", "Dta.liq.", "destino_frete", "peso_liquido_t", "frete_rs_t"]].copy()
            part["model"] = name
            part["fold"] = fold
            part["train_date_max"] = str(pd.to_datetime(training["Dta.liq."]).max().date())
            part["previsto_rs_t"] = pred
            predictions.append(part)
            folds.append({"model": name, "fold": fold, "validation_start": start, "validation_end_exclusive": end, "n_train": len(training), "n_validation": len(validation), "freights_removed": purged, **metrics(validation.frete_rs_t, pred, validation.peso_liquido_t)})
    oof = pd.concat(predictions, ignore_index=True)
    if oof.duplicated(["model", "Nº frete", "Item"]).any():
        raise ValueError("Item duplicado nas previsões OOF")
    oof["mes"] = pd.to_datetime(oof["Dta.liq."]).dt.to_period("M").astype(str)
    oof["faixa_peso"] = pd.cut(oof.peso_liquido_t, [0, 1, 3, 6, 12, 20, 40], labels=["0-1", "1-3", "3-6", "6-12", "12-20", "20-40"])
    return oof, pd.DataFrame(folds)

def segment_metrics(oof, dimensions, criteria=None):
    """Critérios de diagnóstico explícitos; amostra pequena nunca vira aprovação."""
    criteria = CRITERIA if criteria is None else criteria
    rows = []
    keys = ["model"] + list(dimensions)
    for key, part in oof.groupby(keys, observed=True, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        result = dict(zip(keys, map(str, key)))
        result.update(n=len(part), volume_t=float(part.peso_liquido_t.sum()), **metrics(part.frete_rs_t, part.previsto_rs_t, part.peso_liquido_t))
        result["supported"] = bool(result["n"] >= criteria["min_items"] and result["volume_t"] >= criteria["min_volume_t"])
        result["bias_alert"] = bool(abs(result["vies_total_custo"]) > criteria["max_abs_cost_bias"])
        result["error_alert"] = bool(result["WAPE_custo"] > criteria["max_cost_wape"])
        result["status"] = "amostra_insuficiente" if not result["supported"] else ("revisar" if result["bias_alert"] or result["error_alert"] else "sem_alerta_nestes_criterios")
        rows.append(result)
    return pd.DataFrame(rows)

def analyze_stability(data_path, root="."):
    root = Path(root)
    out = root / "reports/estabilidade"
    out.mkdir(parents=True, exist_ok=True)
    history = eligible_history(read_data(data_path))
    oof, folds = generate_oof(history)
    oof.to_csv(out / "previsoes_oof.csv", index=False)
    folds.to_csv(out / "metricas_folds.csv", index=False)
    tables = {}
    for name, dimensions in [("mes", ["mes"]), ("destino", ["destino_frete"]), ("peso", ["faixa_peso"]), ("mes_destino", ["mes", "destino_frete"]), ("mes_peso", ["mes", "faixa_peso"])]:
        table = segment_metrics(oof, dimensions)
        table.to_csv(out / f"por_{name}.csv", index=False)
        tables[name] = table
    totals = segment_metrics(oof, [])
    totals.to_csv(out / "metricas_oof_agregadas.csv", index=False)
    alerts = []
    for dimension, table in tables.items():
        for model, part in table.groupby("model"):
            supported = part[part.supported]
            alerts.append({"dimension": dimension, "model": model, "segments": len(part), "supported_segments": int(part.supported.sum()), "segments_to_review": int(part.status.eq("revisar").sum()), "insufficient_segments": int(part.status.eq("amostra_insuficiente").sum()), "max_abs_bias_supported": float(supported.vies_total_custo.abs().max()) if len(supported) else None, "max_WAPE_cost_supported": float(supported.WAPE_custo.max()) if len(supported) else None, "volume_fraction_supported": float(part.loc[part.supported, "volume_t"].sum() / part.volume_t.sum())})
    alert_summary = pd.DataFrame(alerts)
    alert_summary.to_csv(out / "resumo_alertas.csv", index=False)
    low, high = history.frete_rs_t.quantile([.01, .99])
    meta = {"stage": "experimental_candidate", "candidate": "rf_original", "training_date_max": str(pd.to_datetime(history["Dta.liq."]).max().date()), "n_train": len(history), "selection_source": "reports/experimentos/vies_resumo.json; critérios definidos em experimento anterior", "validation": "cinco folds temporais OOF; sem reavaliação do holdout abr-ago2026", "independent_future_confirmation": False, "winsor_train_only": {"p01": float(low), "p99": float(high)}, "criteria": CRITERIA, "deployment_approved": False, "scope": "categoria Z101, peso positivo até40t, rateio consistente; inferência condicionada à disponibilidade de dados de embarque"}
    model = fit_candidate("rf_original", history)
    from frete.provenance import training_provenance
    meta.update(training_provenance(data_path, __file__))
    (root / "models").mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": NUMERIC + CATEGORICAL, "metadata": meta}, root / "models/frete_candidate.joblib")
    (out / "candidate_metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = {"history_rows": len(history), "oof_items_per_model": int(len(oof) / 2), "oof_date_min": str(oof["Dta.liq."].min()), "oof_date_max": str(oof["Dta.liq."].max()), "criteria": CRITERIA, "overall": totals.to_dict("records"), "alerts": alerts, "interpretation": "Resultados agregados não demonstram estabilidade. Revisar células com suporte e alertas; células sem suporte são inconclusivas. Artefato candidato preserva o modelo anterior e exige confirmação futura independente."}
    (out / "resumo.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return summary
