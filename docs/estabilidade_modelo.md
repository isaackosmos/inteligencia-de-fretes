# Estabilidade histórica do candidato de frete

## Escopo e execução

`scripts/analyze_stability.py` usa a base preparada e executa dez ajustes temporais: RF log e RF original nas mesmas cinco janelas crescentes do experimento de viés. Os modelos auxiliares são ajustados somente antes de cada validação. A janela final termina em 31/03/2026. Fretes presentes na validação são excluídos do treino; o alvo usado para limitar extremos é ajustado dentro do respectivo treino.

Foram produzidas **18.468 previsões fora da amostra por modelo**, cobrindo abril/2025 a março/2026, com chaves de item, fold e última data de treino. Janeiro a março/2025 servem de histórico inicial e não recebem previsão OOF. Cada item aparece uma única vez por modelo. O histórico completo elegível para o artefato candidato contém 22.781 itens anteriores a abril/2026.

Esta é evidência histórica de desenvolvimento. Os mesmos folds já participaram da seleção do candidato, portanto a análise não é validação independente do processo de seleção. O teste abril–agosto/2026, já observado na análise inicial, não foi reavaliado. Um período futuro ou acompanhamento prospectivo continua necessário.

## Critérios de diagnóstico

Uma célula tem suporte mínimo se possuir **100 itens e 100 toneladas**. Abaixo disso, recebe `amostra_insuficiente`, mesmo quando o erro é zero. Nas células com suporte, há alerta se o módulo do viés agregado ultrapassar **10%** ou WAPE de custo ultrapassar **30%**.

Esses limiares são critérios explícitos de triagem do projeto, não limites contratados com a área de negócio e não testes estatísticos. `sem_alerta_nestes_criterios` não significa estabilidade garantida. O WAPE soma erros absolutos de desembolso; o viés pode cancelar erros de sinais opostos, por isso ambos são analisados.

Há tabelas por mês, destino e faixa de peso, além de cruzamentos mês×destino e mês×peso. Esses cruzamentos impedem que a média histórica de uma rota esconda um período problemático. Mês é o período da data de liquidação histórica, ainda sujeito à limitação de não representar perfeitamente a data planejada de embarque.

## Resultados

| OOF histórico agregado | RF log | RF original |
|---|---:|---:|
| MAE R$/t | 41,78 | 41,74 |
| WAPE custo | 19,37% | 19,33% |
| Viés de custo | −5,46% | **−1,22%** |

Os números agregados OOF diferem ligeiramente das médias do experimento: aqui todos os itens são reunidos antes de calcular as métricas; naquele relatório as cinco janelas têm peso igual.

**O candidato melhora o viés agregado, mas ainda apresenta instabilidade localizada.** Para RF original:

- **Meses:** 12 com suporte, sem alertas nos critérios; maior módulo de viés mensal 3,14%.
- **Destinos:** dois dos dez destinos com suporte exigem revisão, e um destino tem amostra insuficiente.
- **Mês×destino:** 13 das 51 células com suporte exigem revisão; 81 células são inconclusivas por suporte insuficiente. Células com suporte cobrem 84,62% do volume.
- **Faixas de peso agregadas:** seis com suporte, sem alertas; isso não se mantém em todos os meses.
- **Mês×peso:** seis das 59 células com suporte exigem revisão; 13 são inconclusivas. Cobertura de volume com suporte 91,22%.

### Prioridades de investigação

1. **Guarapuava:** 6.192 itens OOF, WAPE de custo 35,99%. Apresenta alertas em 11 dos 12 meses. Janeiro/2026 tem WAPE 44,35% e viés −15,91%, associado a erros de tarifa elevados. Investigar operações, qualidade e subdivisões de rota antes de recomendar uso local.
2. **Sorocaba:** 221 itens, viés −11,28%. A amostra histórica agregada tem suporte, mas a fragmentação mensal reduz a capacidade de concluir estabilidade por período.
3. **Londrina:** junho e julho/2025 têm viés de −13,64% e −21,47%, respectivamente, embora a média histórica do destino não ultrapasse o limiar.
4. **Itens leves:** em janeiro/2026, a faixa até uma tonelada tem viés −37,07% e WAPE 46,46%; entre uma e três toneladas, viés −15,83%. A média por faixa dilui esses períodos.

Esses sinais não demonstram causas. As próximas ações devem confrontar os maiores erros com as fontes, analisar alterações operacionais e verificar se a codificação de destino agrupa operações diferentes. Alterações de tratamento/modelo exigem nova avaliação temporal e registro das decisões.

## Artefato candidato e preservação

`models/frete_candidate.joblib` contém RF original treinada somente até março/2026, com a mesma estrutura `model`, `features` e `metadata` usada na inferência do projeto. Metadados identificam estágio `experimental_candidate`, `deployment_approved=false`, público de aplicação e ausência de confirmação futura independente. Não houve substituição de `models/frete_model.joblib` nem alteração dos resultados do holdout anterior.

O artefato permite integração opcional de desenvolvimento; não autoriza promoção operacional automática. Filtros mantidos: categoria Z101, peso positivo até 40t, tarifa positiva e rateio consistente. A disponibilidade prévia dos atributos da carga e o comportamento diante de categorias novas precisam ser avaliados em eventual integração.

## Arquivos e reprodução

```bash
.venv/bin/python scripts/analyze_stability.py
```

Saídas em `reports/estabilidade/`: `previsoes_oof.csv`, `metricas_folds.csv`, `metricas_oof_agregadas.csv`, `por_mes.csv`, `por_destino.csv`, `por_peso.csv`, `por_mes_destino.csv`, `por_mes_peso.csv`, `resumo_alertas.csv`, `resumo.json` e `candidate_metadata.json`. Critérios estão centralizados em `CRITERIA` no código. Testes cobrem separação temporal, fretes cruzados, bloqueio do holdout, ponderação pelo volume e o risco de cancelamento de vieses entre segmentos.
