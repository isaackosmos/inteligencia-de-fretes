"""Diagnóstico de tarifas com agregações ponderadas pelo volume."""
from pathlib import Path
import json
import os
import pandas as pd
from frete.modeling import read_data

def summarize(df, group):
    temp = df.assign(custo_referencia=df["tarifa_orcada_rs_t"] * df["peso_liquido_t"])
    out = temp.groupby(group, dropna=False, observed=True).agg(itens=("Item", "size"), volume_t=("peso_liquido_t", "sum"), realizado_rs=("Valor líquido", "sum"), itens_com_orcamento=("tarifa_orcada_rs_t", "count"))
    out["tarifa_ponderada_rs_t"] = out.realizado_rs / out.volume_t
    # Meta flexível somente nos registros com referência: não comparar universos diferentes.
    covered = temp[temp.tarifa_orcada_rs_t.notna() & (temp.tarifa_orcada_rs_t > 0)]
    comparable = covered.groupby(group, dropna=False, observed=True).agg(realizado_comparavel_rs=("Valor líquido", "sum"), meta_flexivel_rs=("custo_referencia", "sum"), volume_comparavel_t=("peso_liquido_t", "sum"))
    out = out.join(comparable)
    out["desvio_tarifa_rs"] = out.realizado_comparavel_rs - out.meta_flexivel_rs
    out["desvio_tarifa_pct"] = out.desvio_tarifa_rs / out.meta_flexivel_rs
    return out.reset_index()

def analyze(data_path, root="."):
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/frete-matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    root = Path(root)
    output, figures = root / "reports" / "analise", root / "reports" / "figures"
    output.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    df = read_data(data_path)
    df = df[(df["peso_liquido_t"] > 0) & (df["Valor líquido"] > 0)].copy()
    df["periodo"] = pd.to_datetime(df["Dta.liq."]).dt.to_period("M").astype(str)
    df["faixa_peso"] = pd.cut(df.peso_liquido_t, [0, 1, 3, 6, 12, 20, 40, float("inf")], labels=["0–1", "1–3", "3–6", "6–12", "12–20", "20–40", ">40"])
    for group in ["destino_frete", "periodo", "tipo_carga", "faixa_peso"]:
        table = summarize(df, group)
        table.to_csv(output / f"por_{group}.csv", index=False)
        fig, ax = plt.subplots(figsize=(10, 4.5))
        ax.bar(table[group].astype(str), table.tarifa_ponderada_rs_t, color="#197785")
        ax.set_ylabel("Tarifa ponderada (R$/t)")
        ax.set_title(f"Custo realizado por {group} — jan/2025 a ago/2026 parcial")
        ax.tick_params(axis="x", rotation=45)
        fig.tight_layout()
        fig.savefig(figures / f"tarifa_{group}.png", dpi=150)
        plt.close(fig)
    # Comparação financeira apenas em 2026: orçamento 2026 não era informação de 2025.
    comparable = df[pd.to_datetime(df["Dta.liq."]).dt.year == 2026]
    summarize(comparable, "destino_frete").to_csv(output / "orcamento_2026_por_destino.csv", index=False)
    stats = {"rows_positive": len(df), "custo_total_rs": float(df["Valor líquido"].sum()), "volume_total_t": float(df.peso_liquido_t.sum()), "tarifa_ponderada_rs_t": float(df["Valor líquido"].sum() / df.peso_liquido_t.sum()), "date_min": str(df["Dta.liq."].min()), "date_max": str(df["Dta.liq."].max()), "nota": "Agosto/2026 parcial. Tabelas históricas com orçamento 2026 são referências retrospectivas; comparação orçamentária decisória restrita a 2026."}
    (output / "resumo.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats
