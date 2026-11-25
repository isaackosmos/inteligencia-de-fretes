"""Registra integridade e papel dos seis arquivos recebidos, sem modificá-los."""
import argparse
import hashlib
import json
from pathlib import Path

SOURCES = {
    "Contexto do Desafio.pdf": ("application/pdf", "Enunciado amplo: composição de custos, conformidade, eficiência veicular e simulador."),
    "Manual.pdf": ("application/pdf", "Referência de negócio: gestão matricial, indicadores e meta relativa por mix realizado."),
    "Relatorio_Previsao_Custo_Frete.pdf": ("application/pdf", "Proposta técnica recebida: regressão, validação temporal, entregáveis e dicionário do CSV."),
    "Realizado.xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Histórico operacional bruto; aba Data contém materiais por item de frete."),
    "Orcado.xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "Referência orçamentária 2026; tarifas mensais e mapeamento de destino por representante."),
    "base_modelagem_frete.csv": ("text/csv", "Base consolidada recebida; referência para comparação, preservada sem sobrescrita."),
}


def inventory(root):
    root = Path(root)
    entries = []
    for filename, (kind, role) in SOURCES.items():
        path = root / filename
        if not path.is_file():
            raise FileNotFoundError(f"Fonte original ausente: {filename}")
        entries.append({"arquivo": filename, "tamanho_bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "tipo": kind,
                        "papel": role, "origem": "Arquivo recebido na pasta do projeto; autoria e cadeia de origem não verificadas."})
    return {"versao": 1, "arquivos": entries, "pendencias_auditaveis": [
        {"tema": "Vigência do orçamento", "estado": "aberta", "descricao": "O ETL relaciona orçamento de 2026 a todos os anos pelo mês, representante e tipo de carga. Em 2025 é referência retrospectiva, sem evidência de disponibilidade à época."},
        {"tema": "Conhecimento do orçamento", "estado": "aberta", "descricao": "Confirmar a data de aprovação/disponibilidade do orçamento 2026 antes de qualquer uso preditivo histórico."},
        {"tema": "Representante e destino", "estado": "aberta", "descricao": "A ligação BPC por representante não tem vigência histórica observada. Validar estabilidade do destino ao longo do período; não equivale a rota origem-destino."},
        {"tema": "Datas operacionais", "estado": "aberta", "descricao": "Dta.liq. é data de liquidação, não data de transporte confirmada. Obter data efetiva para vínculo temporal de diesel e regra ANTT."},
        {"tema": "Período incompleto", "estado": "documentada", "descricao": "Histórico termina em 04/08/2026; agosto não pode ser tratado como mês completo."},
        {"tema": "Insumos externos", "estado": "parcial", "descricao": "Cadastros operacionais de distância, pedágio e veículo e coeficientes ANTT continuam ausentes. A série pública mensal de diesel é auditada separadamente em data/external/diesel_metadata.json, quando presente, sem representar custo efetivo de abastecimento."}
    ]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    output = args.root / "docs/inventario_fontes.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inventory(args.root), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
