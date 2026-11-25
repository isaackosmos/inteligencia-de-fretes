"""Preparação auditável de itens de frete a partir das planilhas originais."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

KEY = ["Nº frete", "Item"]


def _mode(series):
    values = series.dropna().mode()
    return values.iloc[0] if len(values) else None


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_dataset(root):
    root = Path(root)
    raw = pd.read_excel(root / "Realizado.xlsx", sheet_name="Data")
    budget = pd.read_excel(root / "Orcado.xlsx", sheet_name="Orçado 26")
    bpc = pd.read_excel(root / "Orcado.xlsx", sheet_name="BPC 26")
    if raw.duplicated().any():
        # Não remover automaticamente: linhas idênticas podem ser lançamentos reais.
        raise ValueError("Linhas integralmente duplicadas exigem revisão antes da agregação")
    g = raw.groupby(KEY, sort=True)
    if (g["Valor líquido"].nunique(dropna=False) > 1).any():
        raise ValueError("Valor do item não é constante dentro da chave de frete")
    if (g["Dta.liq."].nunique(dropna=False) > 1).any():
        raise ValueError("Data ambígua dentro do item")
    raw["peso_liquido_kg"] = raw["Peso líquido"].fillna(0) + raw["Peso líq.acumul."].fillna(0)
    raw["peso_bruto_kg"] = raw["Peso bruto"].fillna(0) + raw["Peso brt.acumulado"].fillna(0)
    for unit in ("KG", "SAC", "FD"):
        raw[f"peso_{unit}"] = raw["peso_liquido_kg"].where(raw["UM"].eq(unit), 0)
    for suffix in ("PEL", "FAR", "TRIT"):
        raw[f"peso_{suffix}"] = raw["peso_liquido_kg"].where(raw["Denominação"].str.contains("_" + suffix, na=False), 0)
    agg = {"Dta.liq.": ("Dta.liq.", "first"), "Valor líquido": ("Valor líquido", "first"),
           "rateio_soma": ("Valor líquido.1", "sum"), "n_linhas": ("Material", "size"),
           "n_materiais": ("Material", "nunique"), "n_fornecimentos": ("Fornecimento", "nunique"),
           "n_doc_venda": ("Doc.venda", "nunique"), "qtd_tprem_distintos": ("TpRem", "nunique")}
    for c in ("Representante", "CtgI", "T", "C.1", "TpRem"):
        agg[c] = (c, _mode)
    for c in ("peso_liquido_kg", "peso_bruto_kg", "peso_KG", "peso_SAC", "peso_FD", "peso_PEL", "peso_FAR", "peso_TRIT"):
        agg[c] = (c, "sum")
    d = raw.groupby(KEY, sort=True).agg(**agg).reset_index()
    # Material principal: maior peso agregado por material, desempate por código.
    materials = raw.groupby(KEY + ["Material", "Denominação"], as_index=False)["peso_liquido_kg"].sum()
    primary = materials.sort_values(KEY + ["peso_liquido_kg", "Material"], ascending=[True, True, False, True]).drop_duplicates(KEY)
    primary = primary[KEY + ["Material", "Denominação"]].rename(columns={"Material": "material_principal", "Denominação": "denominacao_principal"})
    d = d.merge(primary, on=KEY, validate="one_to_one")
    d["peso_liquido_t"] = d["peso_liquido_kg"] / 1000
    for name, unit in (("kg", "KG"), ("sac", "SAC"), ("fd", "FD")):
        d[f"peso_kg_um_{name}"] = d[f"peso_{unit}"]
        d[f"pct_peso_um_{name}"] = d[f"peso_{unit}"] / d["peso_liquido_kg"].replace(0, np.nan)
    for suffix in ("pel", "far", "trit"):
        d[f"pct_peso_{suffix}"] = d[f"peso_{suffix.upper()}"] / d["peso_liquido_kg"].replace(0, np.nan)
    d["tipo_carga"] = np.where(d["pct_peso_um_kg"].ge(.5), "GRANEL_KG", "ENSACADO_SAC_FD")
    for col, attr in (("ano", "year"), ("mes", "month"), ("trimestre", "quarter"), ("dia_semana", "dayofweek")):
        d[col] = getattr(d["Dta.liq."].dt, attr)
    d["qtd_itens_no_frete"] = d.groupby("Nº frete")["Item"].transform("size")
    d["peso_total_frete_t"] = d.groupby("Nº frete")["peso_liquido_t"].transform("sum")
    d["share_peso_item_no_frete"] = d["peso_liquido_t"] / d["peso_total_frete_t"].replace(0, np.nan)
    # Números de parceiros não numéricos (Z...) não correspondem ao realizado.
    for frame in (budget, bpc):
        frame["Representante"] = pd.to_numeric(frame["Parceiro de Negócio"], errors="coerce")
    budget["mes"] = pd.to_numeric(budget.iloc[:, 1])
    budget["tipo_carga"] = budget["Unidade medida bás"].map({"TO": "GRANEL_KG", "SAC": "ENSACADO_SAC_FD"})
    bk = ["Representante", "mes", "tipo_carga"]
    if budget.duplicated(bk).any():
        raise ValueError("Chave de orçamento duplicada")
    d = d.merge(budget[bk + ["R$/ton", "VOLUME"]], on=bk, how="left", validate="many_to_one")
    d.rename(columns={"R$/ton": "tarifa_orcada_rs_t", "VOLUME": "volume_orcado_mes_t"}, inplace=True)
    d["tarifa_orcada_rs_t"] = d["tarifa_orcada_rs_t"].where(d["tarifa_orcada_rs_t"] > 0)
    totals = budget.groupby("Representante")[["FRETE", "VOLUME"]].sum()
    annual = (totals["FRETE"] / totals["VOLUME"].replace(0, np.nan)).where(totals["FRETE"] > 0)
    d["tarifa_orcada_media_rep_rs_t"] = d["Representante"].map(annual)
    d["nome_representante"] = d["Representante"].map(budget.groupby("Representante")["Desc3"].first())
    mapping = bpc.dropna(subset=["Representante"])
    if (mapping.groupby("Representante")["Destino Frete|Ano civil/mês cal."].nunique() > 1).any():
        raise ValueError("Mapeamento de destino ambíguo")
    d["destino_frete"] = d["Representante"].map(mapping.groupby("Representante")["Destino Frete|Ano civil/mês cal."].first())
    d["destino_frete"] = d["destino_frete"].replace([0, "0", ""], np.nan).fillna("NAO_INFORMADO")
    d["frete_rs_t"] = d["Valor líquido"] / d["peso_liquido_t"].replace(0, np.nan)
    d["flag_valor_zero"] = d["Valor líquido"].eq(0).astype(int)
    d["flag_rateio_divergente"] = (~np.isclose(d["rateio_soma"], d["Valor líquido"], rtol=0, atol=.05)).astype(int)
    d["flag_ctgi_nao_padrao"] = d["CtgI"].ne("Z101").astype(int)
    lo, hi = d["frete_rs_t"].quantile([.01, .99])
    # Flag descritiva global: proibida como feature e como corte de validação temporal.
    d["flag_outlier_rs_t"] = (~d["frete_rs_t"].between(lo, hi)).astype(int)
    columns = ["Nº frete", "Item", "Dta.liq.", "ano", "mes", "trimestre", "dia_semana", "Representante", "nome_representante", "destino_frete", "CtgI", "T", "C.1", "TpRem", "qtd_tprem_distintos", "tipo_carga", "material_principal", "denominacao_principal", "n_linhas", "n_materiais", "n_fornecimentos", "n_doc_venda", "peso_liquido_kg", "peso_bruto_kg", "peso_liquido_t", "peso_kg_um_kg", "peso_kg_um_sac", "peso_kg_um_fd", "pct_peso_um_kg", "pct_peso_um_sac", "pct_peso_um_fd", "pct_peso_pel", "pct_peso_far", "pct_peso_trit", "qtd_itens_no_frete", "peso_total_frete_t", "share_peso_item_no_frete", "tarifa_orcada_rs_t", "volume_orcado_mes_t", "tarifa_orcada_media_rep_rs_t", "Valor líquido", "frete_rs_t", "flag_valor_zero", "flag_rateio_divergente", "flag_ctgi_nao_padrao", "flag_outlier_rs_t"]
    d = d[columns].sort_values(["Dta.liq."] + KEY).reset_index(drop=True)
    audit = {"source_sha256": {p: _hash(root / p) for p in ("Realizado.xlsx", "Orcado.xlsx")},
             "raw_rows": len(raw), "processed_rows": len(d), "columns": len(d.columns),
             "unique_fretes": d["Nº frete"].nunique(), "date_min": str(d["Dta.liq."].min().date()),
             "date_max": str(d["Dta.liq."].max().date()), "total_value_brl": float(d["Valor líquido"].sum()),
             "total_weight_t": float(d["peso_liquido_t"].sum()),
             "flags": {c: int(d[c].sum()) for c in d if c.startswith("flag_")},
             "missing": {c: int(d[c].isna().sum()) for c in d if d[c].isna().any()},
             "inconsistent_representative_items": int((g["Representante"].nunique() > 1).sum()),
             "outlier_descriptive_thresholds": [float(lo), float(hi)],
             "notes": ["Orçamento 2026 aplicado por mês também em 2025: referência retrospectiva, não feature historicamente disponível.", "Destino é proxy por representante, não rota origem-destino medida.", "Flags de alvo não devem ser usadas como features ou para filtrar o teste.", "Pesos elevados e divergências de rateio preservados para investigação."]}
    return d, audit


def write_dataset(root):
    root = Path(root)
    d, audit = build_dataset(root)
    output = root / "data" / "processed"
    output.mkdir(parents=True, exist_ok=True)
    d.to_csv(output / "base_modelagem_frete.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    (output / "auditoria.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    return audit
