# Investigação do viés de desembolso

## Motivação

O modelo inicial reduziu MAE/WAPE por item, mas subestimou o desembolso agregado no teste temporal. A combinação de alvo logarítmico, minimização de erros por item e assimetria pode favorecer tarifas baixas. Isso é uma hipótese; o experimento compara alternativas, sem atribuir causalidade a uma única escolha.

## Isolamento e integridade

`scripts/experiment_bias.py` executa `src/frete/experiments.py` e grava apenas `reports/experimentos`. Não substitui `models/frete_model.joblib`, métricas anteriores ou previsões do holdout. Somente linhas anteriores a 01/04/2026 entram nas cinco janelas crescentes. O teste abril–agosto/2026 **já foi observado** na análise inicial: qualquer futura reavaliação será exploratória, não confirmação independente. Este experimento não calcula resultados nesse teste.

## Candidatos

1. Random Forest com alvo logarítmico: referência técnica atual.
2. Random Forest com alvo na escala original.
3. HistGradientBoosting com perda quadrática e alvo original.
4. Regressão linear OLS com alvo original.

Cada candidato é avaliado sem e com calibração multiplicativa. Features, filtros e limites de treinamento são mantidos iguais para facilitar a interpretação. Percentis 1–99 são ajustados somente no treino de cada modelo, inclusive no ajuste auxiliar de calibração. Tarifas orçadas, valores realizados e flags do alvo não são atributos. Previsões negativas são limitadas a zero.

## Calibração

Em cada treino temporal externo:

1. Separar os dois últimos meses disponíveis como janela interna de calibração.
2. Treinar um modelo auxiliar somente no histórico anterior a esses meses.
3. Prever os meses internos; calcular `fator = soma(custo real) / soma(custo previsto)`.
4. Reajustar o modelo em todo o treino externo e multiplicar as previsões da validação externa por esse fator.

Fretes compartilhados são retirados do treino em ambas as separações. O fator nunca usa resultados da validação externa, nem do holdout final. Não há ajuste do fator em cima do teste visto. Ainda assim, mudança de distribuição pode tornar o fator instável; seus valores por dobra são exportados.

## Regra de seleção

Antes da execução foi definida a seguinte regra: escolher o menor WAPE de custo médio entre candidatos que mantenham MAE médio até 110% da referência RF log e média do módulo do viés agregado até 5%. As médias usam as cinco janelas com peso igual, e o desvio-padrão é exportado. A guarda de viés utiliza módulos por dobra para não mascarar cancelamento entre meses superestimados e subestimados.

Se nenhum candidato cumpre ambas as guardas, a saída identifica a reprovação de viés e recomenda apenas o menor WAPE entre os candidatos que cumprem a guarda de MAE. Isso é um candidato para investigação, não aprovação orçamentária.

## Saídas e limitações

- `vies_cv_folds.csv`: métricas e fator por dobra/configuração.
- `vies_cv_resumo.csv`: médias, dispersões e guardas.
- `vies_resumo.json`: seleção e contexto de avaliação.

As decisões foram orientadas pela falha identificada no teste anterior; logo existe influência indireta desse diagnóstico sobre o desenho experimental. Para validação operacional forte será necessário reservar dados posteriores a agosto/2026, quando disponíveis, ou executar acompanhamento prospectivo. A comparação interna pode orientar o desenvolvimento, mas não constitui nova evidência futura independente.

## Resultado executado

Foram usados 22.781 itens históricos e 40 avaliações externas (oito configurações × cinco janelas). A regra selecionou **Random Forest na escala original, sem calibração**, que cumpriu ambas as guardas.

| Candidato | MAE médio R$/t | WAPE custo médio | Média do módulo do viés |
|---|---:|---:|---:|
| RF original | 41,64 | 19,28% | **1,45%** |
| RF log | 41,70 | 19,34% | 5,38% |
| RF log calibrada | 41,65 | 19,34% | 1,73% |
| RF original calibrada | 41,79 | 19,35% | 1,67% |
| HGB original | 42,82 | 20,30% | 2,15% |
| HGB original calibrada | 43,02 | 20,37% | 2,43% |
| OLS original | 45,07 | 23,71% | 4,56% |
| OLS original calibrada | 45,42 | 23,62% | 4,72% |

A RF original apresenta viés médio assinado de −1,25%, contra −5,38% da RF log. A redução de WAPE é pequena: isso sustenta a investigação de escala do alvo para reduzir viés, mas não uma alegação de grande ganho de precisão. A calibração log também reduz o viés histórico, com fator médio de aproximadamente 1,046. A calibração não melhorou o WAPE da RF original, logo não foi escolhida.

**Recomendação:** promover RF original apenas a candidato de desenvolvimento, mantendo o modelo publicado atual intacto. Revisar resíduos e estabilidade por rota/mês e validar prospectivamente antes de substituição operacional. O experimento deliberadamente não oferece nova métrica de teste final e não resolve sozinho a deriva observada em 2026.
