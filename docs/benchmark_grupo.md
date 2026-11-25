# Comparação temporal dos modelos do grupo

O resumo apresentado pelo grupo descreve uma primeira árvore de decisão e o protótipo Gradient Boosting. O experimento reproduz os hiperparâmetros informados para Gradient Boosting (100 estimadores, taxa de aprendizado 0,1, profundidade máxima 5 e semente 42). Para a árvore simples, cujo ajuste não foi especificado no resumo, usa os parâmetros padrão do scikit-learn e semente 42. A Random Forest usa a configuração do projeto.

Os três estimadores recebem as mesmas variáveis de planejamento, com imputação e codificação ajustadas exclusivamente no treino. Cada janela usa o log do alvo e limita as tarifas de treino aos percentis 1 e 99 daquela janela. A avaliação usa as tarifas observadas na escala original. A base se restringe a itens Z101, tarifas e pesos positivos, pesos de até 40 toneladas e rateios sem divergência. Itens do mesmo frete da validação são removidos do treino da janela.

As cinco janelas cobrem abril de 2025 a março de 2026 em ordem cronológica. O teste de abril a agosto de 2026 fica fora do experimento. O protocolo substitui a divisão aleatória descrita no protótipo e permite comparar as famílias de modelos sob as mesmas condições.

```bash
.venv/bin/python scripts/benchmark_group_models.py
```

O comando gera `reports/experimentos/benchmark_grupo_janelas.csv` com os tamanhos e métricas das janelas e `reports/experimentos/benchmark_grupo_resumo.csv` com os resultados agregados. O MAE médio de treino permite comparar o ajuste aos dados que cada estimador viu. O MAE médio das janelas dá o mesmo peso a cada janela. As demais métricas do resumo usam todas as previsões de validação em conjunto. Os resultados são de desenvolvimento e o comando preserva os artefatos do painel.

## Resultado nas 18.468 observações de validação

| Modelo | MAE (R$/t) | WAPE da tarifa | WAPE do custo | R² |
| --- | ---: | ---: | ---: | ---: |
| Random Forest | 41,78 | 20,90% | 19,37% | 0,2610 |
| Gradient Boosting | 42,32 | 21,17% | 20,12% | 0,2618 |
| Árvore de decisão | 52,08 | 26,05% | 22,67% | 0,1857 |

Gradient Boosting reduziu o MAE em 18,7% em relação à árvore simples. A árvore teve MAE médio de R$ 7,13/t no treino e R$ 51,46/t na validação, diferença compatível com sobreajuste. A Random Forest teve os menores MAE e WAPE. Gradient Boosting teve RMSE ligeiramente menor, de R$ 136,34/t diante de R$ 136,41/t da Random Forest.
