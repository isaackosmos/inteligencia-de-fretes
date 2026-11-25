"""Compara os modelos dos dois trabalhos com a mesma validação temporal."""
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from frete.experiments import WINDOWS
from frete.modeling import features, make_model, metrics, read_data, temporal_split


def models():
    tree = make_model("random_forest").set_params(
        regressor__regressor=DecisionTreeRegressor(random_state=42),
    )
    boosting = make_model("random_forest").set_params(
        regressor__regressor=GradientBoostingRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=5, random_state=42,
        ),
    )
    return {
        "arvore_decisao": tree,
        "gradient_boosting": boosting,
        "random_forest": make_model("random_forest"),
    }


def benchmark(data_path, output):
    data = read_data(data_path)
    date = pd.to_datetime(data["Dta.liq."])
    eligible = (
        data["CtgI"].eq("Z101")
        & data["frete_rs_t"].gt(0)
        & data["peso_liquido_t"].gt(0)
        & data["peso_liquido_t"].le(40)
        & data["flag_rateio_divergente"].eq(0)
    )
    history = data.loc[eligible & (date < WINDOWS[-1][1])]
    history_dates = date.loc[history.index]
    fold_rows = []
    predictions = []
    for start, end in WINDOWS:
        through_window = history.loc[history_dates < end]
        training, validation, overlap = temporal_split(through_window, start)
        if training.empty or validation.empty:
            raise ValueError(f"A janela de {start} a {end} precisa de dados de treino e validação.")
        x_training = features(training)
        x_validation = features(validation)
        actual = validation["frete_rs_t"]
        weight = validation["peso_liquido_t"]
        lower, upper = training["frete_rs_t"].quantile([.01, .99])
        target = training["frete_rs_t"].clip(lower, upper)
        for name, estimator in models().items():
            estimator.fit(x_training, target)
            predicted = np.maximum(estimator.predict(x_validation), 0)
            train_predicted = np.maximum(estimator.predict(x_training), 0)
            fold_rows.append({
                "modelo": name,
                "inicio_validacao": start,
                "fim_exclusivo": end,
                "n_treino": len(training),
                "n_validacao": len(validation),
                "fretes_em_comum_removidos_do_treino": overlap,
                "MAE_treino_rs_t": np.abs(training["frete_rs_t"] - train_predicted).mean(),
                **metrics(actual, predicted, weight),
            })
            predictions.append(pd.DataFrame({
                "modelo": name, "real": actual, "previsto": predicted, "peso": weight,
            }))

    folds = pd.DataFrame(fold_rows)
    oof = pd.concat(predictions, ignore_index=True)
    summary_rows = []
    folds_by_model = folds.groupby("modelo")
    for name, group in oof.groupby("modelo"):
        fold_metrics = folds_by_model.get_group(name)
        summary_rows.append({
            "modelo": name,
            "janelas": len(fold_metrics),
            "n_validacao": len(group),
            "MAE_treino_medio_rs_t": fold_metrics["MAE_treino_rs_t"].mean(),
            "MAE_janelas_medio_rs_t": fold_metrics["MAE_rs_t"].mean(),
            **metrics(group["real"], group["previsto"], group["peso"]),
        })
    summary = pd.DataFrame(summary_rows).sort_values("MAE_janelas_medio_rs_t")
    output.mkdir(parents=True, exist_ok=True)
    folds.to_csv(output / "benchmark_grupo_janelas.csv", index=False, float_format="%.8f")
    summary.to_csv(output / "benchmark_grupo_resumo.csv", index=False, float_format="%.8f")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/processed/base_modelagem_frete.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/experimentos")
    args = parser.parse_args()
    print(benchmark(args.data, args.output).to_string(index=False))
