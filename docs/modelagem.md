# Metodologia de previsão de fretes

## Objetivo e unidade

Prever tarifa realizada em reais por tonelada por item (`Nº frete` + `Item`). O custo é a tarifa prevista multiplicada pelo peso líquido em toneladas. Modelos descrevem associações históricas; não demonstram efeito causal de alterar peso ou rota.

## Elegibilidade

Treino e teste mantêm categoria padrão `Z101`, tarifa/peso positivos, peso até 40 toneladas por item e rateio consistente. Essas regras delimitam o público atendido e são aplicadas antes da separação, sem utilizar percentis globais. Os demais registros continuam preservados na base de dados. Percentis 1 e 99 usados para limitar o alvo de treinamento são calculados somente dentro de cada treino; o teste mantém seus extremos.

## Variáveis e disponibilidade operacional

A lista permitida encontra-se em `NUMERIC` e `CATEGORICAL` em `src/frete/modeling.py`. Custos reais, impostos, rateios, flags derivadas do alvo e identificadores de transação não entram como atributos. O orçamento disponível é de 2026: nenhuma de suas tarifas ou volumes é usada como atributo do modelo, pois isso introduziria informação futura nas operações de 2025. A tarifa orçada continua como referência de comparação no teste de 2026.

Peso total do caminhão e número de itens do frete também foram omitidos para evitar depender de uma consolidação ainda desconhecida no planejamento. A previsão pressupõe conhecimento prévio de peso, produtos, remessa e composição da carga. No histórico, data de liquidação serve como aproximação da data operacional planejada; essa equivalência deve ser validada antes do uso em produção. Campos desconhecidos são imputados, mas a qualidade tende a diminuir quando faltam informações relevantes. Código do representante e material precisam usar os mesmos identificadores das fontes de treino.

## Validação e modelos

- Holdout: treino anterior a 01/04/2026 e teste a partir dessa data, até 04/08/2026 (mês parcial).
- Fretes presentes no teste são excluídos do treino; a mesma proteção existe em cada dobra interna.
- Cinco janelas temporais crescentes: treino antes de abril, junho, agosto e outubro/2025 e janeiro/2026. Validações seguintes terminam respectivamente em junho, agosto, outubro/2025, janeiro e abril/2026.
- Candidatos: Ridge com duas regularizações, Random Forest e HistGradientBoosting. Limites de complexidade e semente fixos. A escolha usa apenas MAE médio das cinco janelas, nunca o teste final.
- Imputação, escala, codificação e transformação logarítmica do alvo são ajustadas somente no treino. Não foi implementada busca ampla por hiperparâmetros: a comparação inicial usa quatro configurações explícitas e reproduzíveis.

## Medidas e referência

MAE e RMSE são expressos em R$/t; R² é reportado sem corte de valores negativos. WAPE de tarifa soma erros absolutos das tarifas e divide pela soma das tarifas reais. WAPE de custo pondera erros pela tonelagem e divide pelo desembolso real. O viés total é a diferença entre desembolso previsto e real dividida pelo real.

Há duas comparações: todas as linhas elegíveis (tarifa orçada ausente preenchida pela mediana calculada no treino) e amostra comum com orçamento positivo disponível, sem imputação. A mediana da referência usa a tabela orçada 2026 disponível nas linhas históricas; a comparação é retrospectiva e não prova o desempenho do processo original de orçamento em tempo real.

## Interpretação e limitações

Importância por permutação no teste mede perda de precisão ao embaralhar um atributo em amostra fixa de até 1.500 linhas, três repetições. Variáveis correlacionadas podem dividir ou ocultar importância. Gráficos e tabelas mostram resíduos por mês, destino, carga e peso, além dos 50 maiores erros. A transformação log não garante resíduos normais; o Q-Q é diagnóstico, não critério automático de aprovação.

SHAP, análises externas de diesel e conformidade legal não são inferidas pelo modelo. Simulações com categorias novas ou fora do intervalo de treino são exploratórias. Superar a referência em MAE/WAPE não basta para aprovar orçamento: viés mensal, segmentos e custo agregado precisam ser examinados. A tarefa não é considerada validada operacionalmente enquanto existir subestimação relevante de desembolso.

## Execução

```bash
.venv/bin/python scripts/build_data.py
.venv/bin/python scripts/analyze.py
.venv/bin/python scripts/train.py
```

Resultados ficam em `reports/analise`, `reports/modelagem` e `reports/figures`; artefato em `models/frete_model.joblib`. Inferência: `from frete.modeling import prever_frete`; passe um DataFrame e o caminho do modelo. Carregue somente artefatos joblib confiáveis, produzidos pelo próprio projeto.
