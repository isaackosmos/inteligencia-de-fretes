"""Gera notebooks de leitura e reprodução a partir do código versionado."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def markdown(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(True)}


setup = """from pathlib import Path
import sys, json
import pandas as pd
ROOT = Path.cwd() if (Path.cwd() / 'src').exists() else Path.cwd().parent
sys.path.insert(0, str(ROOT / 'src'))
"""

books = {
    "01_EDA": [
        markdown("# Diagnóstico dos fretes\nExecute previamente `python scripts/build_data.py` e `python scripts/analyze.py`. Valores agregados usam peso como ponderador. Agosto/2026 é parcial."),
        code(setup),
        code("from frete.modeling import read_data\ndf = read_data(ROOT / 'data/processed/base_modelagem_frete.csv')\ndisplay(df.head())\ndisplay(df[['frete_rs_t', 'peso_liquido_t', 'Valor líquido']].describe(percentiles=[.01,.5,.99]))"),
        code("display(df.filter(like='flag_').sum().to_frame('ocorrencias'))\nby = df.groupby('destino_frete').agg(valor=('Valor líquido','sum'), peso=('peso_liquido_t','sum'), itens=('Item','size'))\nby['tarifa_ponderada_rs_t'] = by.valor / by.peso\ndisplay(by.sort_values('valor', ascending=False))"),
        markdown("## Reprodução\nO processamento e as regras estão em `src/frete/data.py`; as análises e gráficos são reconstruídos por `scripts/analyze.py`. Conferir a auditoria antes de interpretar valores extremos. Destino cadastrado pelo representante não comprova o itinerário real."),
        markdown("## Referência pública de diesel\nA série mensal ANP é contexto retrospectivo, não preço pago pela transportadora nem atributo do modelo. Agosto completo difere do histórico operacional encerrado em 04/08."),
        code("diesel_path = ROOT / 'data/external/diesel.csv'\nif diesel_path.exists():\n    diesel = pd.read_csv(diesel_path)\n    display(diesel.head())\n    if not diesel.empty:\n        display(diesel.groupby(['localidade', 'produto']).agg(meses=('data','nunique'), preco_min=('preco_rs_l','min'), preco_max=('preco_rs_l','max')))"),
    ],
    "02_Modelagem": [
        markdown("# Previsão e validação temporal\nTreino até março/2026; teste de abril a agosto/2026. O orçamento 2026 não entra nas features. Selecione o modelo apenas na validação interna, antes de consultar o teste."),
        code(setup),
        code("display(pd.read_csv(ROOT / 'reports/modelagem/validacao_cruzada.csv'))\ndisplay(pd.read_csv(ROOT / 'reports/modelagem/metricas_teste.csv'))"),
        code("summary = json.loads((ROOT / 'reports/modelagem/resumo.json').read_text())\nprint(json.dumps(summary, ensure_ascii=False, indent=2))"),
        markdown("## Reprodução do treinamento\nExecutar `python scripts/train.py` na raiz. O script reconstrói modelos e relatórios; seus parâmetros e transformações estão em `src/frete/modeling.py`. Instale as dependências do projeto no kernel escolhido. Verifique cobertura da referência e resultados em amostra comum."),
    ],
    "03_Interpretacao": [
        markdown("# Interpretação e limites\nImportância por permutação mede perda preditiva ao embaralhar uma variável. Não identifica efeito causal; variáveis correlacionadas podem dividir importância."),
        code(setup),
        code("display(pd.read_csv(ROOT / 'reports/modelagem/importancia_permutacao.csv'))\npred = pd.read_csv(ROOT / 'reports/modelagem/previsoes_teste.csv')\ndisplay(pred.head())"),
        code("pred['erro_abs'] = pred.residuo_rs_t.abs()\ndisplay(pred.groupby('destino_frete').agg(itens=('erro_abs','size'), MAE_rs_t=('erro_abs','mean'), vies_rs_t=('residuo_rs_t','mean')))\ndisplay(pred.nlargest(20, 'erro_abs'))"),
        markdown("## Uso responsável\nResultados descrevem itens elegíveis após filtros, não toda a operação. A data de liquidação aproxima a data planejada. Simulações não demonstram economia efetivamente capturável. SHAP e explicações adicionais permanecem extensões documentadas se ainda não executados."),
        markdown("## Estabilidade histórica da candidata\nEstes folds também participaram do desenvolvimento. Não são confirmação futura independente nem métricas do teste abril-agosto/2026. Células sem suporte são inconclusivas."),
        code("stability_path = ROOT / 'reports/estabilidade/resumo.json'\nif stability_path.exists():\n    stability = json.loads(stability_path.read_text())\n    display(pd.DataFrame(stability['overall']))\n    display(pd.DataFrame(stability['alerts']).query(\"model == 'rf_original'\"))\nelse:\n    print('Execute scripts/analyze_stability.py para gerar esta análise opcional.')"),
    ],
}

for name, cells in books.items():
    book = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}, "nbformat": 4, "nbformat_minor": 5}
    for i, cell in enumerate(cells):
        cell["id"] = f"{name.lower()}-{i}"
    (ROOT / 'notebooks' / f'{name}.ipynb').write_text(json.dumps(book, ensure_ascii=False, indent=2), encoding='utf-8')
