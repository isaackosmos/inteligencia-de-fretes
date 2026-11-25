"""Experimento de viés: seleção exclusivamente em janelas anteriores ao holdout."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.linear_model import LinearRegression
from frete.modeling import read_data, features, make_model, metrics, temporal_split

WINDOWS = [("2025-04-01", "2025-06-01"), ("2025-06-01", "2025-08-01"), ("2025-08-01", "2025-10-01"), ("2025-10-01", "2026-01-01"), ("2026-01-01", "2026-04-01")]

def candidate(name):
    if name == "rf_log":
        return make_model("random_forest")
    if name == "rf_original":
        return clone(make_model("random_forest").regressor)
    if name == "hgb_original":
        return clone(make_model("hist_gradient_boosting").regressor)
    model = clone(make_model("ridge").regressor)
    model.set_params(regressor=LinearRegression())
    return model

def fit_candidate(name, df):
    low, high = df.frete_rs_t.quantile([.01, .99])
    model = candidate(name)
    model.fit(features(df), df.frete_rs_t.clip(low, high))
    return model

def calibration_factor(name, fold_train):
    """Fator estimado em previsão temporal fora da amostra, dentro do treino.

    Últimos dois meses completos disponíveis são calibração; o restante ajusta
    o modelo auxiliar. O modelo principal depois é reajustado em todo o treino.
    """
    date = pd.to_datetime(fold_train["Dta.liq."])
    last_month = date.max().to_period("M")
    cutoff = (last_month - 1).start_time
    earlier, calibration, overlap = temporal_split(fold_train, cutoff)
    if len(earlier) < 100 or len(calibration) < 100:
        raise ValueError("Janela insuficiente para calibração temporal interna")
    model = fit_candidate(name, earlier)
    prediction = np.asarray(model.predict(features(calibration)), dtype=float)
    weights = calibration.peso_liquido_t.to_numpy(dtype=float)
    actual = calibration.frete_rs_t.to_numpy(dtype=float)
    if prediction.shape != actual.shape or not all(np.isfinite(v).all() for v in (prediction, weights, actual)):
        raise ValueError("Calibração exige previsões, pesos e tarifas finitos e alinhados")
    if (weights <= 0).any() or (actual <= 0).any():
        raise ValueError("Calibração exige pesos e tarifas reais positivos")
    pred = np.maximum(prediction, 0)
    denominator = float(np.sum(pred * weights))
    numerator = float(np.sum(actual * weights))
    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError("Custo previsto de calibração deve ser finito e maior que zero")
    if not np.isfinite(numerator) or numerator <= 0:
        raise ValueError("Custo realizado de calibração deve ser finito e maior que zero")
    factor = numerator / denominator
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError("Fator de calibração deve ser finito e maior que zero")
    return factor, {"calibration_start": str(cutoff.date()), "n_calibration": len(calibration), "n_fit_calibration": len(earlier), "calibration_overlap_removed": overlap}

def run_bias_experiment(data_path, root="."):
    root = Path(root)
    out = root / "reports/experimentos"
    out.mkdir(parents=True, exist_ok=True)
    df = read_data(data_path)
    eligible = (df.CtgI == "Z101") & (df.frete_rs_t > 0) & (df.peso_liquido_t > 0) & (df.peso_liquido_t <= 40) & (df.flag_rateio_divergente == 0)
    # Holdout nem sequer é carregado no conjunto experimental.
    history = df[eligible & (pd.to_datetime(df["Dta.liq."]) < "2026-04-01")].copy()
    rows = []
    for start, end in WINDOWS:
        fold_train, validation, overlap = temporal_split(history, start)
        validation = validation[pd.to_datetime(validation["Dta.liq."]) < end]
        for name in ["rf_log", "rf_original", "hgb_original", "ols_original"]:
            factor, calibration_info = calibration_factor(name, fold_train)
            model = fit_candidate(name, fold_train)
            raw = np.maximum(model.predict(features(validation)), 0)
            for calibrated in [False, True]:
                pred = raw * factor if calibrated else raw
                rows.append({"candidate": name + ("_calibrated" if calibrated else ""), "validation_start": start, "validation_end_exclusive": end, "n_train": len(fold_train), "n_validation": len(validation), "overlap_removed": overlap, "calibration_factor": factor if calibrated else 1.0, **calibration_info, **metrics(validation.frete_rs_t, pred, validation.peso_liquido_t)})
    results = pd.DataFrame(rows)
    results["abs_vies_total_custo"] = results.vies_total_custo.abs()
    results.to_csv(out / "vies_cv_folds.csv", index=False)
    aggregate = results.groupby("candidate").agg(MAE_mean=("MAE_rs_t", "mean"), MAE_std=("MAE_rs_t", "std"), WAPE_custo_mean=("WAPE_custo", "mean"), WAPE_custo_std=("WAPE_custo", "std"), WAPE_tarifa_mean=("WAPE_tarifa", "mean"), abs_vies_mean=("abs_vies_total_custo", "mean"), vies_mean=("vies_total_custo", "mean"), factor_mean=("calibration_factor", "mean")).reset_index()
    # Critério declarado antes da avaliação: custo WAPE, guardas MAE e viés.
    reference_mae = aggregate.loc[aggregate.candidate.eq("rf_log"), "MAE_mean"].iloc[0]
    aggregate["passes_MAE_guard"] = aggregate.MAE_mean <= 1.10 * reference_mae
    aggregate["passes_bias_guard"] = aggregate.abs_vies_mean <= .05
    qualified = aggregate[aggregate.passes_MAE_guard & aggregate.passes_bias_guard]
    fully_qualified = not qualified.empty
    if qualified.empty:
        qualified = aggregate[aggregate.passes_MAE_guard]
    selected = qualified.sort_values("WAPE_custo_mean").iloc[0].candidate
    aggregate = aggregate.sort_values("WAPE_custo_mean")
    aggregate.to_csv(out / "vies_cv_resumo.csv", index=False)
    summary = {"source": str(data_path), "history_rows": len(history), "last_date_allowed": "2026-03-31", "folds": 5, "selected_candidate": selected, "passes_both_guards": fully_qualified, "selection_rule": "Menor WAPE de custo médio entre candidatos com MAE <=110% do RF log e média do módulo do viés <=5%; se nenhum cumpre ambos, menor WAPE entre os que cumprem MAE, explicitando reprovação da guarda de viés.", "calibration": "Fator custo real/custo previsto nos últimos dois meses internos do treino, previstos por modelo ajustado somente antes desses meses. Reajuste final da dobra em todo o treino. Teste final não acessado.", "holdout_status": "O teste abr-ago2026 já foi observado na modelagem anterior. Qualquer futura reavaliação nele será exploratória; não foi avaliado por este experimento.", "existing_model_overwritten": False, "candidate_summary": aggregate.to_dict("records")}
    (out / "vies_resumo.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary
