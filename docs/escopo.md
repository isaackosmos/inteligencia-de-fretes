# Projeto de inteligência aplicada ao frete

## Objetivo e público
Explicar desvios entre realizado e orçamento, prever tarifas e simular decisões logísticas para gestores de logística e planejamento orçamentário. Escopo inicial: vendas de Nutrição Animal; os dados não representam todos os fretes da cooperativa.

## Perguntas de negócio
1. Quais destinos, cargas e períodos concentram custos e desvios?
2. Quanto do desvio é mudança de volume/mix e quanto é tarifa?
3. A previsão supera a referência orçada em dados futuros?
4. Como premissas de volume, combustível e veículo afetam o custo estimado?
5. Há informação suficiente para avaliar piso mínimo por operação?

## Entregas progressivas
- Diagnóstico: inventário, auditoria, ETL reproduzível, indicadores ponderados e comparação de orçamento ajustado ao volume real.
- Previsão: referências, modelos, teste temporal, erros por segmento e explicação dos resultados.
- Decisão: painel, cenários de mix e componentes de custo, comparação veicular parametrizada.
- Entrega acadêmica obrigatória, confirmada pelo aluno: dashboard web interativa, relatório de atividades/metodologia/parâmetros e códigos utilizados. Notebooks e relatório executivo complementam a entrega; slides não foram exigidos.

## Critérios de aceite
- Fontes originais preservadas e identificadas por hash.
- Valores e pesos reconciliados por unidade de observação; tratamentos explicitados.
- Nenhum custo realizado ou variável derivada do alvo como entrada do modelo.
- Divisão temporal e ausência de fretes compartilhados entre treino e teste.
- Comparação em amostra comum com cobertura da tarifa orçada informada.
- Aprovação preditiva somente se MAE e WAPE superarem a referência no teste; caso contrário registrar a falha.
- Premissas de simulação identificadas como estimativas, sem apresentar economia simulada como economia comprovada.
- Avaliação regulatória somente com enquadramento, data, distância, eixos, contratação e coeficientes oficiais suficientes.

## Restrições conhecidas
Orçamento de 2026 é uma referência retrospectiva quando associado ao histórico de 2025. Destino derivado de representante é aproximação cadastral, não itinerário comprovado. Faltam distâncias operacionais, eixos, pedágios e contratos. A data de liquidação não é necessariamente a data de contratação/transporte. Agosto/2026 é parcial.

Prazo informado em 10/11/2026: final de novembro/2026, sem dia definido. Meta interna proposta: versão candidata em 24/11 e pacote revisado em 27/11, preservando margem para ajustes. Estas são metas de planejamento, não datas estabelecidas pelo professor.

O aluno confirmou que só dispõe dos arquivos atuais. Não depender de obter cadastro interno adicional para fechar a entrega acadêmica: delimitar conclusões observacionais aos campos existentes e apresentar engenharia de custos como cenário parametrizado. A validade jurídica de um diagnóstico histórico exige regra e coeficientes vigentes em cada operação, não a tabela atual aplicada a todo o passado.
