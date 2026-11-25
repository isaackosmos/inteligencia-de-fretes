"""Gera relatório técnico do processo com parâmetros obtidos do modelo salvo."""
from pathlib import Path
import json
import sys
import joblib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from frete.modeling import NUMERIC, CATEGORICAL


def table(frame):
    columns = list(frame.columns)
    lines = ['| ' + ' | '.join(columns) + ' |', '| ' + ' | '.join(['---'] * len(columns)) + ' |']
    for row in frame.itertuples(index=False, name=None):
        lines.append('| ' + ' | '.join(str(v) for v in row) + ' |')
    return '\n'.join(lines)


artifact = joblib.load(ROOT / 'models/frete_model.joblib')
summary = json.loads((ROOT / 'reports/modelagem/resumo.json').read_text())
estimator = artifact['model'].regressor_.named_steps['regressor']
parameters = estimator.get_params(deep=False)
out = ROOT / 'reports/final/relatorio_desenvolvimento.md'
text = f'''# Relatório de atividades e parâmetros — versão inicial

## 1. Requisitos e escopo
O professor solicitou dashboard interativa, relatório das atividades e parâmetros e códigos do desenvolvimento. Prazo previsto para o final de novembro/2026, sem dia definido. A aplicação utiliza Streamlit e funciona como dashboard web local. Só há acesso aos seis arquivos originalmente recebidos. Este relatório registra a implementação atual, sem declarar concluídas as extensões pendentes.

## 2. Atividades realizadas e evidências
| Atividade | Código/documentação | Evidência |
|---|---|---|
| Inventário e preservação | scripts/inventory.py | docs/inventario_fontes.json, hashes dos originais |
| Reconstrução dos dados | src/frete/data.py | data/processed/base_modelagem_frete.csv e auditoria.json |
| Diagnóstico | src/frete/analysis.py | reports/analise e reports/figures |
| Treino e validação | src/frete/modeling.py | reports/modelagem e models/frete_model.joblib |
| Interpretação | permutação e resíduos no treinamento | importância, segmentos e maiores erros |
| Interface e cenários | app/dashboard.py, src/frete/simulation.py | filtros, indicadores, cenários e inferência |
| Triagem documental | src/frete/compliance.py | recusa de cadastro incompleto; sem coeficientes reais |
| Verificação | tests e scripts/execute_notebooks.py | testes automatizados e notebooks com saídas |

O desenvolvimento utilizou assistência de IA e agentes para dividir implementação de dados, modelagem e painel. As saídas foram integradas e verificadas por testes e execução. Isso não substitui a revisão acadêmica e o entendimento dos autores que apresentarão o projeto.

## 3. Fontes, limpeza e engenharia
As fontes e decisões detalhadas constam em docs/auditoria_dados.md. A primeira coluna de valor líquido entra uma vez por item, enquanto o rateio é usado para conferir consistência. Pesos líquidos e acumulados são somados e convertidos de kg para t. As ligações com orçamento usam representante, mês e tipo de carga. Destino é aproximação cadastral. Os originais permanecem preservados.

Foram reconstruídos 29.860 itens e 46 colunas. Itens não elegíveis continuam no CSV. Na modelagem, mantiveram-se Z101, tarifa/peso positivos, peso até 40 t e rateio consistente. Filtros limitam a população sobre a qual se pode concluir. Percentis 1 e 99 são calculados somente no treino de cada janela para limitar o alvo; extremos do teste são preservados.

## 4. Atributos
Numéricos: {', '.join(NUMERIC)}.

Categóricos: {', '.join(CATEGORICAL)}.

Ano/mês são derivados da data de liquidação, uma aproximação da data planejada. Excluídos do modelo: valores realizados, impostos, rateios, flags do alvo, identificadores de transação, tarifas/volumes orçados de 2026 e totais de caminhão cuja disponibilidade antecipada não foi demonstrada.

## 5. Pré-processamento, candidatos e seleção
Imputação numérica por mediana e StandardScaler ajustados em cada treino. Ridge e Random Forest usam OneHotEncoder com categorias desconhecidas ignoradas e frequência mínima 20. HistGradientBoosting usa OrdinalEncoder para desconhecidos com valor −1; os códigos são uma representação numérica, não uma escala de negócio. Alvo transformado com log1p e previsão invertida com expm1; valores previstos são limitados inferiormente a zero.

Candidatos implementados: Ridge alpha 1 e 10 (solver lsqr), Random Forest e HistGradientBoosting. Random Forest: 100 árvores, profundidade máxima 18, mínimo 8 observações por folha, max_features 0,8, n_jobs 2 e semente 42. Boosting: 160 iterações, 23 folhas, regularização L2 10, learning_rate 0,08 e semente 42. Esses parâmetros são uma comparação inicial limitada, não busca exaustiva nem otimização global.

Cinco janelas temporais internas crescentes orientam a seleção pelo menor MAE médio. Treino final anterior a abril/2026 e teste a partir de abril até 04/08/2026. Fretes compartilhados são removidos do treino em cada divisão. Houve {summary['n_train']} itens de treino e {summary['n_test']} de teste; fretes compartilhados removidos: {summary['overlapping_freights_removed_from_train']}.

Modelo selecionado: **{summary['selected_model']}**. Parâmetros efetivos extraídos do estimador salvo:

```json
{json.dumps(parameters, ensure_ascii=False, indent=2)}
```

## 6. Resultados e interpretação
Medidas no teste completo (referência com ausências preenchidas pela mediana do treino):

{table(pd.DataFrame(summary['test']))}

Amostra comum com orçamento válido ({summary['common_sample_n']} itens), sem imputação:

{table(pd.DataFrame(summary['common_sample_test']))}

A previsão melhora MAE e WAPE, porém subestima o gasto agregado. Não foi calibrada usando o teste. O diagnóstico deve investigar tendência temporal e segmentos antes de uso orçamentário. Importância por permutação usa até 1.500 itens do teste, três repetições e semente 42; não demonstra causalidade.

## 7. Dashboard e regras dos cenários
Filtros por destino, tipo de carga, período e categoria. Indicadores usam soma de valor/soma de peso. Orçamento flexível usa tarifa orçada × peso realizado somente nos itens com referência. O painel informa cobertura e o caráter retrospectivo do orçamento 2026 aplicado a 2025.

Mix: reponderação de tarifas históricas por distribuição e volume escolhidos. Viagem: combustível calculado como distância/rendimento × preço; somam-se pedágios, outros custos e acréscimo declarado. Capacidade e ocupação determinam toneladas para a tarifa simulada. Esses valores não comprovam a composição do frete contratado. Comparação de eixos depende de capacidades e rendimentos informados; não deduz características técnicas apenas pelo número de eixos.

## 8. Verificação e reprodução
Executar comandos do README. Versões de dependências estão em requirements-lock.txt; pacotes e faixas em pyproject.toml. Testes cobrem dupla contagem, reconciliação, vazamento de atributos, separação de fretes, métricas ponderadas, cenários, interface e triagem incompleta. A quantidade de testes e situação mais recente ficam em docs/status.md. Os notebooks são executados pelo script próprio, com saídas textuais salvas; revisão visual completa e validação com logística continuam pendentes.

## 9. Limitações e trabalho restante
Sem itinerários comprovados, eixos, contratos e pedágios não é possível concluir conformidade regulatória por rota. A situação das fontes externas é detalhada nas seções complementares abaixo quando disponíveis. SHAP, OLS/Lasso e busca ampla de hiperparâmetros não foram executados. Hospedagem pública e slides não são requisitos confirmados. Concluir revisão visual, aprofundar segmentos de maior erro e preparar pacote de códigos e relatório para entrega. Confirmação futura é condição de eventual adoção operacional, não impede concluir o trabalho acadêmico com limitações explícitas. Documento gerado a partir do artefato atual; executar novamente após alterar o treinamento.
'''
experiment_path = ROOT / 'reports/experimentos/vies_resumo.json'
if experiment_path.exists():
    experiment = json.loads(experiment_path.read_text())
    text = text.replace('SHAP, OLS/Lasso e busca ampla de hiperparâmetros não foram executados.',
                        'SHAP, Lasso e busca ampla de hiperparâmetros não foram executados. OLS foi incluída no experimento complementar descrito abaixo.')
    text += '\n\n## 10. Investigação complementar do viés\n'
    text += ('Após o teste inicial, foram avaliadas oito configurações em cinco janelas anteriores a abril/2026. '
             'O diagnóstico do teste motivou o experimento; logo seus resultados internos não constituem nova confirmação independente. '
             'O modelo anterior e suas métricas foram preservados. Candidato recomendado: **' + experiment['selected_candidate'] + '**.\n\n')
    text += table(pd.DataFrame(experiment['candidate_summary']))
    text += ('\n\nA regra prioriza WAPE de custo com guardas de MAE e viés, usando somente validações históricas. '
             'Método e calibração em docs/experimento_vies.md; código em scripts/experiment_bias.py e src/frete/experiments.py. '
             'O artefato anterior permanece preservado, com aviso de subestimação. Não houve promoção operacional automática do candidato.\n')
stability_path = ROOT / 'reports/estabilidade/resumo.json'
if stability_path.exists():
    stability = json.loads(stability_path.read_text())
    text += '\n\n## 11. Estabilidade por período e segmento\n'
    text += (f"Foram reunidas {stability['oof_items_per_model']} previsões fora da amostra por modelo, "
             f"de {stability['oof_date_min']} a {stability['oof_date_max']}. "
             'Os mesmos folds participaram do desenvolvimento; os resultados não são confirmação independente. '
             'Métricas agregadas OOF reúnem todos os itens, enquanto o experimento anterior usa média de cinco janelas.\n\n')
    cols = ['model', 'n', 'MAE_rs_t', 'WAPE_custo', 'vies_total_custo']
    text += table(pd.DataFrame(stability['overall'])[cols])
    text += '\n\nCritérios de triagem explícitos: ' + json.dumps(stability['criteria'], ensure_ascii=False) + '.\n\n'
    alerts = pd.DataFrame(stability['alerts'])
    text += table(alerts.loc[alerts.model.eq('rf_original'), ['dimension', 'supported_segments', 'segments_to_review', 'insufficient_segments']])
    text += ('\n\nA melhora agregada não elimina falhas por destino e mês. Guarapuava apresenta WAPE de custo de 35,99%; '
             'Sorocaba, viés de −11,28%. Células pequenas permanecem inconclusivas. '
             'Detalhamento e critérios em docs/estabilidade_modelo.md, código em src/frete/stability.py. '
             'Artefato separado models/frete_candidate.joblib permanece marcado experimental.\n')
diesel_path = ROOT / 'data/external/diesel_metadata.json'
if diesel_path.exists():
    diesel = json.loads(diesel_path.read_text())
    text += '\n\n## 12. Integração de referência pública de diesel\n'
    text += (f"Importadas {diesel['rows']} referências mensais estaduais da ANP, "
             f"{diesel['states']} estados e produtos {', '.join(diesel['products'])}, "
             f"de {diesel['period_start']} a {diesel['period_end']}. "
             'Preço de revenda pesquisado, não preço efetivamente pago pela transportadora. '
             'A série não entra no modelo: médias completas do mês não estavam disponíveis no início dele. '
             'Agosto completo da ANP não equivale ao histórico operacional encerrado em 04/08. '
             'Lacunas não foram imputadas; fonte, unidades, cobertura e hashes estão em data/external/diesel_metadata.json. '
             'Código: src/frete/anp.py e scripts/import_diesel.py. Método: docs/diesel_anp.md.\n\n')
    text += 'Fonte oficial: ' + diesel['source_page'] + '\n'
out.write_text(text, encoding='utf-8')
print(out)
