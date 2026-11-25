"""Treino temporal, avaliação e inferência de tarifas de frete."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

NUMERIC = ["peso_liquido_t", "peso_bruto_kg", "n_materiais", "n_fornecimentos", "n_doc_venda", "pct_peso_um_kg", "pct_peso_um_sac", "pct_peso_um_fd", "pct_peso_pel", "pct_peso_far", "pct_peso_trit", "mes", "indice_tempo"]
CATEGORICAL = ["Representante", "destino_frete", "tipo_carga", "TpRem", "material_principal"]

def read_data(path):
    return pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig", dtype={"Representante": str, "material_principal": str, "Nº frete": str})

def features(df):
    """Usa lista explícita: custos realizados e flags jamais entram no modelo.

    Peso total consolidado foi omitido: pode não estar disponível no planejamento.
    A data de liquidação histórica é proxy da data planejada (limitação documentada).
    """
    out = df.reindex(columns=NUMERIC + CATEGORICAL).copy()
    if "Dta.liq." in df:
        date = pd.to_datetime(df["Dta.liq."], errors="coerce")
        out["mes"] = date.dt.month
        out["indice_tempo"] = (date.dt.year - 2025) * 12 + date.dt.month - 1
    for col in NUMERIC:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in CATEGORICAL:
        out[col] = out[col].fillna("NAO_INFORMADO").astype(str)
    return out

def temporal_split(df, cutoff="2026-04-01"):
    date = pd.to_datetime(df["Dta.liq."])
    train, test = df[date < cutoff].copy(), df[date >= cutoff].copy()
    # Excluir do treino qualquer frete que também apareça no teste.
    overlap = set(train["Nº frete"]) & set(test["Nº frete"])
    train = train[~train["Nº frete"].isin(overlap)]
    return train, test, len(overlap)

def metrics(y, pred, weights):
    y, pred, weights = map(lambda x: np.asarray(x, dtype=float), (y, pred, weights))
    residual = y - pred
    total = np.sum(y * weights)
    return {"MAE_rs_t": float(np.mean(np.abs(residual))), "RMSE_rs_t": float(np.sqrt(np.mean(residual ** 2))), "WAPE_tarifa": float(np.abs(residual).sum() / np.abs(y).sum()), "WAPE_custo": float(np.sum(np.abs(residual) * weights) / total), "R2": float(1 - np.sum(residual ** 2) / np.sum((y - y.mean()) ** 2)) if len(y) > 1 and y.var() > 0 else None, "vies_total_custo": float(np.sum((pred - y) * weights) / total)}

def make_model(kind, alpha=10):
    from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import OneHotEncoder, StandardScaler, OrdinalEncoder
    from sklearn.linear_model import Ridge
    from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
    numeric = Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)), ("scale", StandardScaler())])
    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1) if kind == "hist_gradient_boosting" else OneHotEncoder(handle_unknown="ignore", min_frequency=20)
    prep = ColumnTransformer([("num", numeric, NUMERIC), ("cat", encoder, CATEGORICAL)])
    if kind == "ridge":
        model = Ridge(alpha=alpha, solver="lsqr")
    elif kind == "random_forest":
        model = RandomForestRegressor(n_estimators=100, max_depth=18, min_samples_leaf=8, max_features=.8, n_jobs=2, random_state=42)
    else:
        model = HistGradientBoostingRegressor(max_iter=160, max_leaf_nodes=23, l2_regularization=10, learning_rate=.08, random_state=42)
    pipeline = Pipeline([("preprocess", prep), ("regressor", model)])
    return TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)

def prever_frete(df, model_path="models/frete_model.joblib"):
    """Retorna tarifa (R$/t) e custo estimado (R$), mesma ordem da entrada."""
    import joblib
    artifact = joblib.load(model_path)
    x = features(df)
    if x["peso_liquido_t"].isna().any() or (x["peso_liquido_t"] <= 0).any():
        raise ValueError("Informe peso_liquido_t positivo em todas as linhas.")
    if (x["peso_liquido_t"] > 40).any():
        raise ValueError("O modelo foi validado somente para itens com até 40 toneladas.")
    if "CtgI" in df and df["CtgI"].ne("Z101").any():
        raise ValueError("O modelo foi validado somente para categoria Z101.")
    prediction = np.maximum(artifact["model"].predict(x), 0)
    return pd.DataFrame({"tarifa_prevista_rs_t": prediction, "custo_previsto_rs": prediction * x["peso_liquido_t"].to_numpy()}, index=df.index)

def train(data_path, root="."):
    import joblib
    from sklearn.inspection import permutation_importance
    root = Path(root)
    output = root / "reports" / "modelagem"
    output.mkdir(parents=True, exist_ok=True)
    (root / "models").mkdir(exist_ok=True)
    df = read_data(data_path)
    usable = (df["CtgI"] == "Z101") & (df["frete_rs_t"] > 0) & (df["peso_liquido_t"] > 0) & (df["peso_liquido_t"] <= 40)
    if "flag_rateio_divergente" in df:
        usable &= df["flag_rateio_divergente"].eq(0)
    clean = df[usable].copy().sort_values("Dta.liq.")
    training, test, overlap = temporal_split(clean)
    candidates = [("ridge_alpha1", "ridge", 1), ("ridge_alpha10", "ridge", 10), ("random_forest", "random_forest", 10), ("hist_gradient_boosting", "hist_gradient_boosting", 10)]
    cv_rows = []
    # Janelas crescentes por mês; todos os tratamentos ajustados dentro da dobra.
    for cutoff, end in [("2025-04-01", "2025-06-01"), ("2025-06-01", "2025-08-01"), ("2025-08-01", "2025-10-01"), ("2025-10-01", "2026-01-01"), ("2026-01-01", "2026-04-01")]:
        fold_train, fold_val, _ = temporal_split(training, cutoff)
        fold_val = fold_val[pd.to_datetime(fold_val["Dta.liq."]) < end]
        if fold_train.empty or fold_val.empty:
            continue
        low, high = fold_train["frete_rs_t"].quantile([.01, .99])
        y = fold_train["frete_rs_t"].clip(low, high)
        for name, kind, alpha in candidates:
            model = make_model(kind, alpha)
            model.fit(features(fold_train), y)
            scores = metrics(fold_val["frete_rs_t"], np.maximum(model.predict(features(fold_val)), 0), fold_val["peso_liquido_t"])
            cv_rows.append({"model": name, "validation_start": cutoff, "n_train": len(fold_train), "n_validation": len(fold_val), **scores})
    cv = pd.DataFrame(cv_rows)
    cv.to_csv(output / "validacao_cruzada.csv", index=False)
    ranking = cv.groupby("model")["MAE_rs_t"].agg(["mean", "std"]).sort_values("mean")
    winner = ranking.index[0]
    final_name, kind, alpha = next(c for c in candidates if c[0] == winner)
    low, high = training["frete_rs_t"].quantile([.01, .99])
    final = make_model(kind, alpha)
    final.fit(features(training), training["frete_rs_t"].clip(low, high))
    prediction = np.maximum(final.predict(features(test)), 0)
    # Mesma imputação da referência, obtida exclusivamente no treino.
    baseline_fill = training["tarifa_orcada_rs_t"].replace(0, np.nan).median()
    baseline = test["tarifa_orcada_rs_t"].replace(0, np.nan).fillna(baseline_fill).to_numpy()
    scores = [{"model": "tarifa_orcada", **metrics(test["frete_rs_t"], baseline, test["peso_liquido_t"])}, {"model": winner, **metrics(test["frete_rs_t"], prediction, test["peso_liquido_t"])}]
    pd.DataFrame(scores).to_csv(output / "metricas_teste.csv", index=False)
    coverage = test["tarifa_orcada_rs_t"].notna() & (test["tarifa_orcada_rs_t"] > 0)
    common_scores = [{"model": "tarifa_orcada", **metrics(test.loc[coverage, "frete_rs_t"], baseline[coverage], test.loc[coverage, "peso_liquido_t"])}, {"model": winner, **metrics(test.loc[coverage, "frete_rs_t"], prediction[coverage], test.loc[coverage, "peso_liquido_t"])}]
    pd.DataFrame(common_scores).to_csv(output / "metricas_amostra_comum.csv", index=False)
    predictions = test[["Nº frete", "Item", "Dta.liq.", "destino_frete", "tipo_carga", "peso_liquido_t", "frete_rs_t", "Valor líquido"]].copy()
    predictions["previsto_rs_t"] = prediction
    predictions["baseline_rs_t"] = baseline
    predictions["residuo_rs_t"] = predictions["frete_rs_t"] - prediction
    predictions["periodo"] = pd.to_datetime(predictions["Dta.liq."]).dt.to_period("M").astype(str)
    predictions["faixa_peso"] = pd.cut(predictions.peso_liquido_t, [0, 1, 3, 6, 12, 20, 40], labels=["0-1", "1-3", "3-6", "6-12", "12-20", "20-40"])
    predictions.to_csv(output / "previsoes_teste.csv", index=False)
    predictions.assign(erro_absoluto=lambda d: d.residuo_rs_t.abs()).nlargest(50, "erro_absoluto").to_csv(output / "maiores_erros.csv", index=False)
    for group in ["destino_frete", "tipo_carga", "faixa_peso", "periodo"]:
        rows = []
        for key, part in predictions.groupby(group, observed=True):
            rows.append({group: str(key), "n": len(part), "residuo_medio_rs_t": float(part.residuo_rs_t.mean()), **metrics(part.frete_rs_t, part.previsto_rs_t, part.peso_liquido_t)})
        pd.DataFrame(rows).to_csv(output / f"residuos_por_{group}.csv", index=False)
    plot_diagnostics(predictions, root / "reports/figures")
    sample = test.sample(min(len(test), 1500), random_state=42)
    importance = permutation_importance(final, features(sample), sample["frete_rs_t"], scoring="neg_mean_absolute_error", n_repeats=3, random_state=42, n_jobs=1)
    pd.DataFrame({"variavel": NUMERIC + CATEGORICAL, "aumento_MAE_rs_t": importance.importances_mean, "std": importance.importances_std}).sort_values("aumento_MAE_rs_t", ascending=False).to_csv(output / "importancia_permutacao.csv", index=False)
    summary = {"source": str(data_path), "input_rows": len(df), "eligible_rows": len(clean), "n_train": len(training), "n_test": len(test), "overlapping_freights_removed_from_train": overlap, "selected_by": "menor MAE médio em 5 janelas temporais internas; teste não usado na seleção", "selected_model": winner, "cv": ranking.reset_index().to_dict("records"), "winsor_train_only": {"p01": low, "p99": high}, "test": scores, "common_sample_test": common_scores, "common_sample_n": int(coverage.sum()), "improves_MAE_and_WAPE": bool(scores[1]["MAE_rs_t"] < scores[0]["MAE_rs_t"] and scores[1]["WAPE_tarifa"] < scores[0]["WAPE_tarifa"]), "baseline_missing_test": int(test["tarifa_orcada_rs_t"].replace(0, np.nan).isna().sum())}
    from frete.provenance import training_provenance
    summary.update(training_provenance(data_path, __file__))
    (output / "resumo.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    joblib.dump({"model": final, "features": NUMERIC + CATEGORICAL, "metadata": summary}, root / "models" / "frete_model.joblib")
    return summary

def plot_diagnostics(predictions, output):
    import os
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/frete-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy import stats
    output.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    axes[0].scatter(predictions.previsto_rs_t, predictions.residuo_rs_t, s=3, alpha=.25)
    axes[0].axhline(0, color="black", lw=.8)
    axes[0].set(xlabel="Previsão (R$/t)", ylabel="Real − previsto (R$/t)", title="Resíduos no teste temporal")
    axes[1].hist(predictions.residuo_rs_t, bins=70, color="#197785")
    axes[1].set(title="Distribuição dos resíduos", xlabel="Resíduo (R$/t)")
    stats.probplot(predictions.residuo_rs_t, dist="norm", plot=axes[2])
    axes[2].set_title("Q-Q: resíduos versus normal")
    fig.tight_layout()
    fig.savefig(output / "diagnostico_residuos.png", dpi=150)
    plt.close(fig)
    temp = predictions.assign(real=predictions.frete_rs_t * predictions.peso_liquido_t, pred=predictions.previsto_rs_t * predictions.peso_liquido_t, baseline=predictions.baseline_rs_t * predictions.peso_liquido_t)
    monthly = temp.groupby("periodo")[["real", "pred", "baseline"]].sum()
    fig, ax = plt.subplots(figsize=(9, 4))
    monthly.plot(ax=ax, marker="o")
    ax.set(ylabel="Custo agregado (R$)", xlabel="Mês (agosto parcial)", title="Teste temporal: realizado, modelo e referência")
    fig.tight_layout()
    fig.savefig(output / "custo_mensal_teste.png", dpi=150)
    plt.close(fig)
