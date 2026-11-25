# Diagnóstico e previsão de custos de frete

Versão inicial executada em 10/11/2026. Escopo: Nutrição Animal, dados de janeiro/2025 a 04/08/2026. Relatório de trabalho; não constitui parecer regulatório ou modelo aprovado para contratação.

## Problema e solução implementada

O orçamento precisa distinguir variações de tarifa das mudanças de volume e mix. Foi implementado um processamento reproduzível das planilhas, diagnóstico ponderado, comparação com orçamento ajustado ao volume, previsão estatística e painel com simulações. O painel permite avaliar destinos, períodos e cargas e explorar cenários de volume, mix e componentes de custo.

## Base e confiabilidade

As 49.051 linhas de materiais foram consolidadas em 29.860 itens de frete, pertencentes a 11.771 fretes. O custo total reconciliado é R$ 33.951.407,81, para 200.911,43023 toneladas. A unidade de modelagem é o item de frete, e não a linha de material. Repetir o valor total do item para cada material causaria dupla contagem.

Foram identificados 372 itens com divergência de rateio, 26 itens de valor zero e 358 itens de categorias diferentes de Z101. O ETL preserva as ocorrências e registra regras e hashes das fontes. O modelo utiliza um escopo filtrado: categoria padrão, valor e peso positivos, até 40 t por item e sem divergência de rateio. Seus resultados não devem ser generalizados a toda a operação sem nova avaliação.

O orçamento é de 2026. Sua associação a 2025 é retrospectiva, sem comprovação de disponibilidade histórica. Destino cadastrado por representante aproxima a praça, sem comprovar a rota física. Agosto/2026 é parcial.

## Previsão e avaliação

Foram avaliados modelos Ridge, Random Forest e HistGradientBoosting. A seleção utilizou cinco janelas temporais internas; o teste contém abril a agosto/2026. Fretes compartilhados entre treino e teste são removidos do treino. O orçamento e os custos realizados não entram nos atributos preditivos. A referência orçada com ausências é preenchida com mediana estimada no treino e reportada separadamente da amostra com cobertura real.

O modelo selecionado foi Random Forest, com 22.781 itens de treino e 6.327 de teste.

| Avaliação no teste completo | Referência orçada com imputação | Modelo |
|---|---:|---:|
| MAE (R$/t) | 63,50 | 48,36 |
| WAPE de tarifa | 28,74% | 21,89% |
| WAPE de custo | 27,60% | 20,95% |
| Viés do gasto total | −3,94% | −13,39% |

Em 5.294 itens com tarifa orçada observada, sem imputação, o MAE foi R$ 58,74/t para a referência e R$ 52,14/t para o modelo; WAPE de tarifa de 25,99% e 23,07%, respectivamente. A melhora permanece, mas é menor nessa comparação. Outros 1.033 itens do teste não possuem tarifa orçada válida.

**Conclusão:** o modelo melhora os erros por item e o erro absoluto de custo, mas apresenta subestimação agregada relevante, pior que a referência nesse critério. Ainda não deve substituir o orçamento. Ganho preditivo não representa economia financeira obtida.

## Uso do simulador

- Diagnóstico: tarifa ponderada e orçamento flexível em universos comparáveis, com cobertura informada.
- Mix: estima o custo ao redistribuir o volume entre destinos, mantendo tarifas históricas e reajuste declarado.
- Viagem: calcula custos com distância, diesel, consumo, pedágio, capacidade, ocupação, outros custos e acréscimo editáveis.
- Veículos: compara configurações 6/7/9 eixos quando o usuário fornece premissas de capacidade, consumo e pedágio; não possui cadastro técnico validado.
- Modelo: permite explorar a previsão de um item com alteração de peso, sujeita ao suporte do treinamento.

Custos por componente são cenários, não decomposição comprovada do preço contratado. O simulador não estima causalmente o efeito de trocar o veículo ou alterar uma operação.

## Recomendações e próximos passos

1. Revisar itens com rateio divergente e pesos extremos antes de decisões individuais.
2. Usar orçamento ajustado ao volume para separar mudança de tarifa e composição de destinos.
3. Investigar viés temporal, segmentos e custos subestimados antes de adoção orçamentária; qualquer calibração deve ser escolhida no treino, com novo período de teste preservado.
4. Obter origem/destino efetivos, distância, configuração veicular, modalidade da operação, pedágios, datas e contratos para viabilizar eficiência e conformidade reais.
5. Integrar diesel e coeficientes oficiais por vigência e documentar cobertura; não aplicar uma tabela atual indistintamente ao histórico.
6. Validar premissas e utilidade do painel com responsável de logística e adequar os entregáveis ao prazo e à rubrica acadêmica.

## Evidências e reprodução

Fontes: planilhas originais preservadas na raiz; auditoria em `data/processed/auditoria.json`; método em `docs/auditoria_dados.md` e `docs/modelagem.md`; métricas em `reports/modelagem/resumo.json`; previsões e resíduos no mesmo diretório. Comandos completos no README. Os valores deste relatório correspondem à execução com base reconstruída e cinco janelas internas; novas execuções exigem revisão deste documento.

## Atualização: investigação complementar

Em oito configurações e cinco janelas históricas anteriores a abril/2026, RF na escala original reduziu a média do módulo do viés agregado para 1,45%, contra 5,38% da versão log, com MAE médio semelhante (R$ 41,64/t contra R$ 41,70/t). O WAPE de custo médio passou de 19,34% para 19,28%. A candidata não substituiu o modelo do painel e não foi reavaliada como confirmação no teste já conhecido. Método completo em `docs/experimento_vies.md`.
