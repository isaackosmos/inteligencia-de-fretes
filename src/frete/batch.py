"""Previsão CSV em memória, com validação independente por linha.

Somente artefatos joblib locais confiáveis podem ser usados pelo servidor.
Uploads nunca são interpretados como modelo ou persistidos neste módulo.
"""
import csv
import io
import re
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from frete.modeling import NUMERIC, CATEGORICAL, features

MAX_ROWS = 5000
MAX_BYTES = 5 * 1024 * 1024
ESSENTIAL = ["Dta.liq.", "peso_liquido_t", "destino_frete", "tipo_carga", "CtgI"]
DERIVED = ["mes", "indice_tempo"]
OPTIONAL_NUMERIC = [name for name in NUMERIC if name not in DERIVED + ["peso_liquido_t"]]
OPTIONAL_CATEGORY = [name for name in CATEGORICAL if name not in ["destino_frete", "tipo_carga"]]
TEMPLATE_COLUMNS = ESSENTIAL + OPTIONAL_NUMERIC + OPTIONAL_CATEGORY
ALLOWED_COLUMNS = set(TEMPLATE_COLUMNS + DERIVED)
PACKAGE_SHARES = ["pct_peso_um_kg", "pct_peso_um_sac", "pct_peso_um_fd"]
PRODUCT_SHARES = ["pct_peso_pel", "pct_peso_far", "pct_peso_trit"]
COUNT_COLUMNS = ["n_materiais", "n_fornecimentos", "n_doc_venda"]
KINDS = {"GRANEL_KG", "ENSACADO_SAC_FD"}

def dialect(sep, decimal):
    if sep not in [";", ","] or decimal not in [",", "."] or sep == decimal:
        raise ValueError("Selecione separador ; ou , e decimal distinto do separador. Ex.: ; com decimal , ou , com decimal .")

def template_csv(sep=";"):
    if sep not in [";", ","]:
        raise ValueError("Separador deve ser ; ou ,")
    stream = io.StringIO(newline="")
    csv.writer(stream, delimiter=sep, lineterminator="\n").writerow(TEMPLATE_COLUMNS)
    return stream.getvalue().encode("utf-8-sig")

def data_dictionary():
    rows = []
    for name in TEMPLATE_COLUMNS + DERIVED:
        if name == "Dta.liq.":
            rule = "Data planejada AAAA-MM-DD; nome preserva esquema histórico. Data fora jan/2025-mar/2026 gera alerta de extrapolação."
        elif name == "peso_liquido_t":
            rule = "Toneladas líquidas, finito, maior que0 e até40."
        elif name == "CtgI":
            rule = "Categoria obrigatória exatamente Z101."
        elif name == "tipo_carga":
            rule = "GRANEL_KG ou ENSACADO_SAC_FD; não inferido de campos ausentes."
        elif name == "destino_frete":
            rule = "Praça cadastral textual; desconhecida gera alerta, não associação geográfica."
        elif name == "peso_bruto_kg":
            rule = "Kg brutos positivos e pelo menos peso líquido em kg. Ausente: mediana aprendida, com alerta."
        elif name in COUNT_COLUMNS:
            rule = "Contagem inteira positiva. Ausente: mediana aprendida, com alerta."
        elif name.startswith("pct_"):
            rule = "Proporção0..1. Embalagens completas somam1; formas físicas somam até1. Ausente: mediana aprendida, com alerta; consistência imputada não é garantida."
        elif name in DERIVED:
            rule = "Derivado da data, não precisa enviar. Se informado, deve concordar com a data; indice_tempo conta meses desde jan/2025."
        else:
            rule = "Identificador/categoria textual, preservando zeros. Ausente: NAO_INFORMADO, com alerta; categoria desconhecida sinalizada."
        rows.append({"campo": name, "obrigatorio": name in ESSENTIAL, "tipo": "numero" if name in NUMERIC else ("data" if name == "Dta.liq." else "texto"), "regra": rule})
    return pd.DataFrame(rows)

def parse_csv(data, sep=";", decimal=",", max_rows=MAX_ROWS, max_bytes=MAX_BYTES):
    dialect(sep, decimal)
    if not isinstance(data, bytes):
        raise ValueError("Envie o conteúdo CSV como bytes UTF-8")
    if len(data) > max_bytes:
        raise ValueError(f"Arquivo excede limite de {max_bytes} bytes")
    if max_rows < 1 or max_rows > MAX_ROWS or max_bytes < 1 or max_bytes > MAX_BYTES:
        raise ValueError("Limites devem ser positivos e não podem exceder5000 linhas/5MiB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV deve usar codificação UTF-8") from exc
    if "\x00" in text:
        raise ValueError("CSV contém caractere nulo")
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=sep, strict=True)
    try:
        headers = next(reader, None)
        if not headers:
            raise ValueError("CSV sem cabeçalhos")
        headers = [name.strip() for name in headers]
        if len(headers) != len(set(headers)) or any(not name for name in headers):
            raise ValueError("Cabeçalhos vazios ou duplicados")
        extra = sorted(set(headers) - ALLOWED_COLUMNS)
        if extra:
            raise ValueError("Colunas não permitidas (incluindo alvos, custos ou IDs de transação): " + ", ".join(extra))
        missing = sorted(set(ESSENTIAL) - set(headers))
        if missing:
            raise ValueError("Cabeçalhos obrigatórios ausentes: " + ", ".join(missing))
        records = []
        for row in reader:
            if not row:
                continue
            if len(row) != len(headers):
                raise ValueError("Quantidade de campos incompatível com cabeçalho; confira separador e aspas")
            records.append(row)
            if len(records) > max_rows:
                raise ValueError(f"CSV excede limite de {max_rows} registros")
    except csv.Error as exc:
        raise ValueError("CSV malformado; confira aspas e tamanho dos campos") from exc
    return pd.DataFrame(records, columns=headers)

def number(raw, decimal):
    text = str(raw).strip()
    mark = re.escape(decimal)
    if not re.fullmatch(r"[+-]?(?:\d+(?:" + mark + r"\d*)?|" + mark + r"\d+)(?:[eE][+-]?\d+)?", text):
        raise ValueError("valor numérico inválido ou decimal incompatível; não use separador de milhar")
    value = float(text.replace(decimal, "."))
    if not np.isfinite(value):
        raise ValueError("número não finito")
    return value

class BatchPredictor:
    """Carrega um modelo uma vez e processa vários CSVs em memória."""
    def __init__(self, model_path="models/frete_model.joblib", artifact=None):
        self.artifact = joblib.load(model_path) if artifact is None else artifact
        if not isinstance(self.artifact, dict) or "model" not in self.artifact:
            raise ValueError("Artefato local não contém modelo")
        self.model = self.artifact["model"]
        self.metadata = dict(self.artifact.get("metadata", {}))
        self.metadata.update({"batch_model_file": Path(model_path).name, "batch_usage": "experimental; não substitui orçamento e não constitui validação futura", "batch_training_reference_start": "2025-01-02", "batch_training_reference_end": self.metadata.get("training_date_max", "2026-03-31")})
        # Apenas API pública do sklearn: categorias efetivamente ajustadas.
        pipeline = getattr(self.model, "regressor_", self.model)
        try:
            encoder = pipeline.named_steps["preprocess"].named_transformers_["cat"]
            self.known_categories = {name: set(map(str, values)) for name, values in zip(CATEGORICAL, encoder.categories_)}
        except (AttributeError, KeyError):
            self.known_categories = {}

    def validate_row(self, raw, decimal):
        row, errors, warnings = {}, [], []
        for name in ESSENTIAL:
            if not str(raw.get(name, "")).strip():
                errors.append(f"{name}: obrigatório")
        for name in TEMPLATE_COLUMNS:
            value = str(raw.get(name, "")).strip()
            if name in NUMERIC:
                if not value:
                    row[name] = np.nan
                    if name in OPTIONAL_NUMERIC:
                        warnings.append(f"{name}: ausente; mediana aprendida no treino")
                else:
                    try:
                        row[name] = number(value, decimal)
                    except ValueError as exc:
                        errors.append(f"{name}: {exc}")
                        row[name] = np.nan
            else:
                if any(ord(char) < 32 for char in value):
                    errors.append(f"{name}: caracteres de controle não permitidos")
                row[name] = value
                if not value and name in OPTIONAL_CATEGORY:
                    row[name] = "NAO_INFORMADO"
                    warnings.append(f"{name}: ausente; categoria NAO_INFORMADO")
        date = None
        try:
            value = row["Dta.liq."]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError()
            date = pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
            if date < pd.Timestamp(self.metadata["batch_training_reference_start"]) or date > pd.Timestamp(self.metadata["batch_training_reference_end"]):
                warnings.append("data_fora_suporte: extrapolação temporal; não há confirmação futura independente")
        except (ValueError, TypeError, OverflowError):
            errors.append("Dta.liq.: data válida obrigatória no formato AAAA-MM-DD")
        if date is not None:
            expected = {"mes": date.month, "indice_tempo": (date.year - 2025) * 12 + date.month - 1}
            for name, derived in expected.items():
                if str(raw.get(name, "")).strip():
                    try:
                        if number(raw[name], decimal) != derived:
                            errors.append(f"{name}: inconsistente com a data; campo é derivado")
                    except ValueError as exc:
                        errors.append(f"{name}: {exc}")
        weight = row.get("peso_liquido_t", np.nan)
        gross = row.get("peso_bruto_kg", np.nan)
        if np.isfinite(weight) and not 0 < weight <= 40:
            errors.append("peso_liquido_t: escopo exige maior que0 e até40t")
        if np.isfinite(gross) and (gross <= 0 or (np.isfinite(weight) and gross + 1e-6 < weight * 1000)):
            errors.append("peso_bruto_kg: deve ser positivo e não inferior ao peso líquido em kg")
        for name in COUNT_COLUMNS:
            value = row.get(name, np.nan)
            if np.isfinite(value) and (value < 1 or value != int(value)):
                errors.append(f"{name}: contagem inteira positiva obrigatória quando informada")
        for group in [PACKAGE_SHARES, PRODUCT_SHARES]:
            supplied = [name for name in group if np.isfinite(row.get(name, np.nan))]
            for name in supplied:
                if not 0 <= row[name] <= 1:
                    errors.append(f"{name}: proporção deve estar entre0 e1")
            total = sum(row[name] for name in supplied)
            if total > 1.000001 or (group == PACKAGE_SHARES and len(supplied) == 3 and not np.isclose(total, 1, atol=1e-6, rtol=0)):
                errors.append("participacoes_inconsistentes: " + ",".join(group))
            if 0 < len(supplied) < 3:
                warnings.append("participacoes_parciais: imputação de campos ausentes não garante composição física consistente")
        if row["CtgI"] != "Z101":
            errors.append("CtgI: somente Z101 está no escopo")
        if row["tipo_carga"] not in KINDS:
            errors.append("tipo_carga: use GRANEL_KG ou ENSACADO_SAC_FD")
        for name in CATEGORICAL:
            known = self.known_categories.get(name)
            if known is not None and row[name] not in known:
                warnings.append(f"categoria_desconhecida: {name}={row[name]}; comportamento fora do suporte cadastral")
        if not self.known_categories:
            warnings.append("suporte_categorico_indisponivel: não foi possível conferir categorias do artefato")
        return row, errors, warnings

    def predict_csv(self, data, sep=";", decimal=",", max_rows=MAX_ROWS, max_bytes=MAX_BYTES):
        original = parse_csv(data, sep, decimal, max_rows, max_bytes)
        result = original.copy()
        result.insert(0, "linha_entrada", range(2, len(result) + 2))
        result["status"] = "invalido"
        result["mensagens"] = ""
        result["tarifa_prevista_rs_t"] = np.nan
        result["custo_previsto_rs"] = np.nan
        validated, indices, notices = [], [], {}
        for index, raw in original.iterrows():
            row, errors, warnings = self.validate_row(raw, decimal)
            notices[index] = warnings
            if errors:
                result.at[index, "mensagens"] = " | ".join(errors + warnings)
            else:
                validated.append(row)
                indices.append(index)
        if not indices:
            return result
        frame = pd.DataFrame(validated, index=indices)
        x = features(frame)
        # Mesmas features e inversão embutida usadas por prever_frete; carregar só1vez.
        try:
            predictions = np.asarray(self.model.predict(x), dtype=float)
            if predictions.shape != (len(indices),):
                raise ValueError("dimensão inesperada da previsão")
        except Exception as exc:
            for index in indices:
                result.at[index, "status"] = "erro_modelo"
                result.at[index, "mensagens"] = "Falha de inferência no lote válido; nenhum valor criado. " + type(exc).__name__
            return result
        for position, index in enumerate(indices):
            pred = predictions[position]
            if not np.isfinite(pred):
                result.at[index, "status"] = "erro_modelo"
                result.at[index, "mensagens"] = "Modelo retornou previsão não finita; nenhum valor criado"
                continue
            pred = max(float(pred), 0.)
            warnings = notices[index]
            if predictions[position] < 0:
                warnings.append("previsao_negativa_limitada_zero: regra igual à inferência individual")
            result.at[index, "tarifa_prevista_rs_t"] = pred
            result.at[index, "custo_previsto_rs"] = pred * frame.at[index, "peso_liquido_t"]
            result.at[index, "status"] = "previsto_com_alertas" if warnings else "previsto"
            result.at[index, "mensagens"] = " | ".join(warnings) or "Entrada consistente com critérios do lote; uso experimental, sem aprovação operacional"
        return result

def predict_batch(data, model_path="models/frete_model.joblib", sep=";", decimal=",", **limits):
    return BatchPredictor(model_path).predict_csv(data, sep=sep, decimal=decimal, **limits)
