# Relatório de atividades e parâmetros — versão inicial

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
Numéricos: peso_liquido_t, peso_bruto_kg, n_materiais, n_fornecimentos, n_doc_venda, pct_peso_um_kg, pct_peso_um_sac, pct_peso_um_fd, pct_peso_pel, pct_peso_far, pct_peso_trit, mes, indice_tempo.

Categóricos: Representante, destino_frete, tipo_carga, TpRem, material_principal.

Ano/mês são derivados da data de liquidação, uma aproximação da data planejada. Excluídos do modelo: valores realizados, impostos, rateios, flags do alvo, identificadores de transação, tarifas/volumes orçados de 2026 e totais de caminhão cuja disponibilidade antecipada não foi demonstrada.

## 5. Pré-processamento, candidatos e seleção
Imputação numérica por mediana e StandardScaler ajustados em cada treino. Ridge e Random Forest usam OneHotEncoder com categorias desconhecidas ignoradas e frequência mínima 20. HistGradientBoosting usa OrdinalEncoder para desconhecidos com valor −1; os códigos são uma representação numérica, não uma escala de negócio. Alvo transformado com log1p e previsão invertida com expm1; valores previstos são limitados inferiormente a zero.

Candidatos implementados: Ridge alpha 1 e 10 (solver lsqr), Random Forest e HistGradientBoosting. Random Forest: 100 árvores, profundidade máxima 18, mínimo 8 observações por folha, max_features 0,8, n_jobs 2 e semente 42. Boosting: 160 iterações, 23 folhas, regularização L2 10, learning_rate 0,08 e semente 42. Esses parâmetros são uma comparação inicial limitada, não busca exaustiva nem otimização global.

Cinco janelas temporais internas crescentes orientam a seleção pelo menor MAE médio. Treino final anterior a abril/2026 e teste a partir de abril até 04/08/2026. Fretes compartilhados são removidos do treino em cada divisão. Houve 22781 itens de treino e 6327 de teste; fretes compartilhados removidos: 0.

Modelo selecionado: **random_forest**. Parâmetros efetivos extraídos do estimador salvo:

```json
{
  "bootstrap": true,
  "ccp_alpha": 0.0,
  "criterion": "squared_error",
  "max_depth": 18,
  "max_features": 0.8,
  "max_leaf_nodes": null,
  "max_samples": null,
  "min_impurity_decrease": 0.0,
  "min_samples_leaf": 8,
  "min_samples_split": 2,
  "min_weight_fraction_leaf": 0.0,
  "monotonic_cst": null,
  "n_estimators": 100,
  "n_jobs": 2,
  "oob_score": false,
  "random_state": 42,
  "verbose": 0,
  "warm_start": false
}
```

## 6. Resultados e interpretação
Medidas no teste completo (referência com ausências preenchidas pela mediana do treino):

| model | MAE_rs_t | RMSE_rs_t | WAPE_tarifa | WAPE_custo | R2 | vies_total_custo |
| --- | --- | --- | --- | --- | --- | --- |
| tarifa_orcada | 63.49767663992862 | 105.549984391216 | 0.28738046544938367 | 0.2759535567692619 | 0.33561700456076127 | -0.0393643399065603 |
| random_forest | 48.36491400479264 | 94.48462902493108 | 0.2188919694957259 | 0.2094590042209435 | 0.4676166238768803 | -0.13391214003248544 |

Amostra comum com orçamento válido (5294 itens), sem imputação:

| model | MAE_rs_t | RMSE_rs_t | WAPE_tarifa | WAPE_custo | R2 | vies_total_custo |
| --- | --- | --- | --- | --- | --- | --- |
| tarifa_orcada | 58.73750224253901 | 104.40734568715298 | 0.2599316879615281 | 0.25808934065340366 | 0.37732131604988683 | -0.045879574903479034 |
| random_forest | 52.142715163834275 | 99.22538641985038 | 0.23074770717125986 | 0.21939374214323493 | 0.43759718388519486 | -0.14050153180986047 |

A previsão melhora MAE e WAPE, porém subestima o gasto agregado. Não foi calibrada usando o teste. O diagnóstico deve investigar tendência temporal e segmentos antes de uso orçamentário. Importância por permutação usa até 1.500 itens do teste, três repetições e semente 42; não demonstra causalidade.

## 7. Dashboard e regras dos cenários
Filtros por destino, tipo de carga, período e categoria. Indicadores usam soma de valor/soma de peso. Orçamento flexível usa tarifa orçada × peso realizado somente nos itens com referência. O painel informa cobertura e o caráter retrospectivo do orçamento 2026 aplicado a 2025.

Mix: reponderação de tarifas históricas por distribuição e volume escolhidos. Viagem: combustível calculado como distância/rendimento × preço; somam-se pedágios, outros custos e acréscimo declarado. Capacidade e ocupação determinam toneladas para a tarifa simulada. Esses valores não comprovam a composição do frete contratado. Comparação de eixos depende de capacidades e rendimentos informados; não deduz características técnicas apenas pelo número de eixos.

## 8. Verificação e reprodução
Executar comandos do README. Versões de dependências estão em requirements-lock.txt; pacotes e faixas em pyproject.toml. Testes cobrem dupla contagem, reconciliação, vazamento de atributos, separação de fretes, métricas ponderadas, cenários, interface e triagem incompleta. A quantidade de testes e situação mais recente ficam em docs/status.md. Os notebooks são executados pelo script próprio, com saídas textuais salvas; revisão visual completa e validação com logística continuam pendentes.

## 9. Limitações e trabalho restante
Sem itinerários comprovados, eixos, contratos e pedágios não é possível concluir conformidade regulatória por rota. A situação das fontes externas é detalhada nas seções complementares abaixo quando disponíveis. SHAP, Lasso e busca ampla de hiperparâmetros não foram executados. OLS foi incluída no experimento complementar descrito abaixo. Hospedagem pública e slides não são requisitos confirmados. Concluir revisão visual, aprofundar segmentos de maior erro e preparar pacote de códigos e relatório para entrega. Confirmação futura é condição de eventual adoção operacional, não impede concluir o trabalho acadêmico com limitações explícitas. Documento gerado a partir do artefato atual; executar novamente após alterar o treinamento.


## 10. Investigação complementar do viés
Após o teste inicial, foram avaliadas oito configurações em cinco janelas anteriores a abril/2026. O diagnóstico do teste motivou o experimento; logo seus resultados internos não constituem nova confirmação independente. O modelo anterior e suas métricas foram preservados. Candidato recomendado: **rf_original**.

| candidate | MAE_mean | MAE_std | WAPE_custo_mean | WAPE_custo_std | WAPE_tarifa_mean | abs_vies_mean | vies_mean | factor_mean | passes_MAE_guard | passes_bias_guard |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rf_original | 41.63594409994442 | 4.49168636454495 | 0.19284168963196935 | 0.007793753038757212 | 0.20796942258828763 | 0.014514255177792774 | -0.012520353640753898 | 1.0 | True | True |
| rf_log | 41.69926106310119 | 4.984198350423432 | 0.19335600054956661 | 0.008183363496936737 | 0.20825367918035279 | 0.05381863755941875 | -0.05381863755941875 | 1.0 | True | False |
| rf_log_calibrated | 41.6452525116863 | 4.105363307597258 | 0.19342485374750387 | 0.004641028378275447 | 0.2080282178818821 | 0.01733073679297712 | -0.01055146516928878 | 1.0457049875556774 | True | True |
| rf_original_calibrated | 41.7850925336826 | 4.384643285297762 | 0.19353902995546118 | 0.007397354019554146 | 0.20871569593007705 | 0.016711681714574936 | -0.007333895817183 | 1.005219992294713 | True | True |
| hgb_original | 42.81595363058763 | 6.29118405645715 | 0.20297959023546513 | 0.010449126908705558 | 0.2136476885753978 | 0.021488308377019573 | -0.015930713677809887 | 1.0 | True | True |
| hgb_original_calibrated | 43.01917067742038 | 6.334771053039773 | 0.20371745146055803 | 0.010729709722181966 | 0.21465471252528207 | 0.02429919497859947 | -0.01372875345036513 | 1.0021296695547413 | True | True |
| ols_original_calibrated | 45.420481034917614 | 5.615693637839952 | 0.23618261271549135 | 0.010596666654393844 | 0.22678440287221963 | 0.04724950175477055 | 0.00035498483195306186 | 0.966291104454138 | True | True |
| ols_original | 45.072142018449014 | 4.142081974726476 | 0.23713418189268087 | 0.012725308118439922 | 0.2252089785548316 | 0.04556982998349231 | 0.03481341655580649 | 1.0 | True | True |

A regra prioriza WAPE de custo com guardas de MAE e viés, usando somente validações históricas. Método e calibração em docs/experimento_vies.md; código em scripts/experiment_bias.py e src/frete/experiments.py. O artefato anterior permanece preservado, com aviso de subestimação. Não houve promoção operacional automática do candidato.


## 11. Estabilidade por período e segmento
Foram reunidas 18468 previsões fora da amostra por modelo, de 2025-04-01 a 2026-03-31. Os mesmos folds participaram do desenvolvimento; os resultados não são confirmação independente. Métricas agregadas OOF reúnem todos os itens, enquanto o experimento anterior usa média de cinco janelas.

| model | n | MAE_rs_t | WAPE_custo | vies_total_custo |
| --- | --- | --- | --- | --- |
| rf_log | 18468 | 41.77770587750974 | 0.19373260579758805 | -0.054560067029810776 |
| rf_original | 18468 | 41.73860685763444 | 0.19334521799644877 | -0.01223201586430374 |

Critérios de triagem explícitos: {"min_items": 100, "min_volume_t": 100.0, "max_abs_cost_bias": 0.1, "max_cost_wape": 0.3}.

| dimension | supported_segments | segments_to_review | insufficient_segments |
| --- | --- | --- | --- |
| mes | 12 | 0 | 0 |
| destino | 10 | 2 | 1 |
| peso | 6 | 0 | 0 |
| mes_destino | 51 | 13 | 81 |
| mes_peso | 59 | 6 | 13 |

A melhora agregada não elimina falhas por destino e mês. Guarapuava apresenta WAPE de custo de 35,99%; Sorocaba, viés de −11,28%. Células pequenas permanecem inconclusivas. Detalhamento e critérios em docs/estabilidade_modelo.md, código em src/frete/stability.py. Artefato separado models/frete_candidate.joblib permanece marcado experimental.


## 12. Integração de referência pública de diesel
Importadas 1074 referências mensais estaduais da ANP, 27 estados e produtos OLEO DIESEL, OLEO DIESEL S10, de 2025-01 a 2026-08. Preço de revenda pesquisado, não preço efetivamente pago pela transportadora. A série não entra no modelo: médias completas do mês não estavam disponíveis no início dele. Agosto completo da ANP não equivale ao histórico operacional encerrado em 04/08. Lacunas não foram imputadas; fonte, unidades, cobertura e hashes estão em data/external/diesel_metadata.json. Código: src/frete/anp.py e scripts/import_diesel.py. Método: docs/diesel_anp.md.

Fonte oficial: https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos
