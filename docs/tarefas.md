# Quadro de trabalho

Estados: a fazer, pronta, em andamento, revisão, concluída, bloqueada por dados. Cada conclusão exige um arquivo, execução ou verificação observável.

| ID | Tarefa | Prioridade | Dependência | Aceite | Estado atual |
|---|---|---|---|---|---|
| G01 | Estruturar projeto e escopo | Alta | — | Diretórios, escopo, Git e execução documentados | Concluída (versão inicial) |
| D01 | Auditar fontes e esquema | Alta | — | Inventário, hashes, chaves e ausências | Concluída (versão inicial) |
| D02 | Reconstruir ETL | Alta | D01 | Base gerada sem duplicação de valores e reconciliação | Concluída (versão inicial) |
| A01 | Diagnóstico orçamento versus realizado | Alta | D02 | Análises ponderadas por mês, destino e carga | Concluída (versão inicial) |
| M01 | Referências e modelos temporais | Alta | D02 | Métricas, previsões e modelo salvo | Concluída (versão inicial) |
| M02 | Validação cruzada e interpretação | Alta | M01 | Dispersão, erros por segmento e importância | Concluída (permutação e resíduos; SHAP pendente) |
| M03 | Investigar viés agregado | Alta | M02 | Experimento isolado, critérios e janelas internas documentados | Concluída (candidato ainda não promovido) |
| M04 | Estabilidade por segmento | Alta | M03 | OOF por mês/destino/peso, suporte e alertas, artefato candidato separado | Concluída (limitações operacionais documentadas) |
| S01 | Painel e simulações | Alta | A01/M01 | Filtros, premissas e cenários funcionais | Em revisão (funcional e revisão visual inicial) |
| E01 | Cadastro de fontes externas | Alta | — | Fontes oficiais e contratos de dados | Concluída (versão inicial) |
| E02 | Diesel histórico ANP | Média | E01 | Série tratada, fonte, cobertura temporal/local | Concluída (referência retrospectiva, fora das features) |
| E03 | Rotas, pedágios e veículos | Alta | Cadastro operacional | Distância e configuração verificadas | Bloqueada por dados |
| E04 | Diagnóstico ANTT histórico | Alta | E03 + regras por vigência | Elegibilidade e cálculo por operação | Bloqueada por dados |
| Q01 | Testes e reprodução integral | Alta | D02/M01/S01 | Testes e execução do zero | Concluída (pasta limpa, ambiente existente; instalação nova pendente) |
| Q02 | Auditoria de integridade e proveniência | Alta | Q01 | Hashes, métricas, modelos, PDFs e ZIP conferidos; omissões explícitas | Concluída (avisos metodológicos preservados) |
| F01 | Notebooks e relatórios | Alta | A01/M02 | Resultados reais, parâmetros e limitações coerentes | Em revisão (PDF executivo4p e desenvolvimento9p revisados visualmente) |
| F02 | Demonstração e apresentação opcional | Média | F01/S01 | Roteiro revisado; slides se necessários | Roteiro inicial concluído |
| F03 | Pacote de código | Alta | Q01/F01 | ZIP com manifesto, sem ambiente/bases e notebooks sem saídas | Concluída (versão de revisão) |

O estado atualizado de cada entrega executada fica em `docs/status.md`. Bloqueio por dados não impede avançar nas demais frentes. Não marcar o escopo completo como concluído com campos operacionais desconhecidos.
