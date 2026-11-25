# Situação da implementação — 10/11/2026

## Executado
- Estrutura de projeto, Git inicializado, ambiente isolado, dependências declaradas e lock da execução.
- Escopo, decisões metodológicas, quadro de tarefas e fontes externas documentados.
- ETL reconstruído das planilhas, CSV processado, hashes e conciliação de totais.
- Diagnósticos com tabelas e gráficos, orçamento flexível e cobertura.
- Modelos com cinco janelas temporais, teste futuro, lista explícita de atributos, comparação comum e artefato salvo.
- Painel Streamlit: filtros, diagnóstico, mix, componentes de viagem, comparação veicular parametrizada e inferência.
- Triagem documental regulatória com recusa de entradas incompletas; sem tabela de produção ou conclusão legal por rota.
- Três notebooks de exploração/leitura técnica e relatório executivo inicial em Markdown.
- Roteiro de apresentação, sem deck final ainda.

## Validação
Resultados atuais: Random Forest supera MAE/WAPE da referência, mas subestima gasto agregado em aproximadamente 13,4%. Critério preditivo parcial atendido; adequação ao orçamento ainda não demonstrada. Detalhes em `reports/modelagem/resumo.json`.

Fechamento da segunda rodada: 26 testes passaram na pasta principal. Os três notebooks foram executados e suas saídas salvas. O painel possui testes de abertura, filtros, cenários, inferência, limites de escopo, qualidade, experimentos e triagem incompleta. Revisão no navegador identificou e corrigiu contraste e truncamento dos cards no tema escuro, com conferência em largura reduzida. Isso não substitui revisão visual de todos os fluxos e validação com usuários de logística.

## Avanços da segunda rodada
- Dashboard ampliada para cinco abas, comparações mensais na mesma amostra, qualidade e exportação com premissas.
- Experimento isolado: oito configurações e cinco janelas, somente antes de abril/2026. RF original é candidata: WAPE de custo médio 19,28%, média do módulo do viés 1,45%, contra 5,38% da RF log. São métricas internas, não comparáveis diretamente ao teste final. Modelo do painel e teste anterior preservados.
- Pipeline com logs, versões, hashes e interrupção em falha. Execução `--skip-train`: êxito parcial com fontes preservadas.
- Reconstrução do pacote em pasta limpa: inventário, ETL, análise, treinamento, relatório, notebooks e testes concluídos em 61,679 s, com 25 testes nessa cópia e originais intactos. A verificação usou o mesmo ambiente instalado e fontes ligadas para leitura. O teste adicional da seção de experimentos foi executado depois na pasta principal (26 testes). Evidência: `reports/validacao_entrega.json` e logs ali referenciados.
- Gerador de ZIP com manifesto SHA-256, exclusão de ambiente/modelos/bases e remoção das saídas de notebooks somente no pacote. Documentação inclui resultados agregados.

## Fechamento da terceira rodada
- **55 testes passaram** na suíte completa atual. O pipeline posterior com treino omitido também passou, com 53 testes na fotografia anterior à inclusão das duas verificações de PDFs; registrou fontes intactas e execução parcial corretamente.
- Estabilidade: 18.468 previsões históricas fora da amostra por modelo. RF original tem viés agregado OOF de -1,22%, mas Guarapuava apresenta WAPE de custo de 35,99% e Sorocaba viés de -11,28%. Alertas por mês/destino/peso e suporte amostral estão no dashboard.
- Candidata salva separadamente e selecionável na interface como experimental. Métricas do teste do modelo inicial permanecem identificadas separadamente. A confirmação futura continua necessária para adoção operacional, sem impedir a conclusão acadêmica com limitações claras.
- Série ANP importada: 1.074 referências mensais estaduais, 27 estados, dois produtos de diesel, janeiro/2025-agosto/2026. Seis lacunas preservadas; contexto retrospectivo separado do modelo e do preço efetivamente pago.
- Corrigidos intervalo de data incompleto, veículos parcialmente apagados, orçamento ausente e exportação das premissas. Conferência no navegador confirmou série ANP e inferência da candidata, além dos testes automatizados de fluxos vazios e limites.
- Modelos reexecutados com mesmos parâmetros para coletar proveniência durante o ajuste: hash da base, código, UTC e versões. Os artefatos anteriores estão arquivados localmente fora do Git. Diferença máxima nas 6.327 previsões do modelo inicial: 9,1e-13 R$/t, sem efeito material.
- Três notebooks atualizados e executados: 11 células de código no total, incluindo ANP e estabilidade.
- PDFs executivo (4 páginas) e desenvolvimento (9 páginas) exportados e revisados visualmente. Manifesto registra hashes das evidências e saídas; exportação tem dependências opcionais documentadas.
- Auditoria atual: todas as verificações executadas, sem falhas técnicas. Fontes, modelos, métricas, PDFs e ZIP conferidos. Avisos remanescentes referem-se ao estágio experimental e à ausência dos cadastros operacionais/coeficientes regulatórios.
- ZIP de código atualizado, com série pública ANP e proveniência, sem bases operacionais, modelos, ambiente ou saídas dos notebooks. O manifesto identifica resultados agregados na documentação.
- Nova reconstrução do núcleo a partir do ZIP atualizado em pasta limpa: todas as etapas passaram em 69,865 s, fontes intactas, 53 testes aprovados e dois testes de artefatos opcionais omitidos porque a candidata não acompanha o pacote de código. Esses dois testes passaram na pasta principal, onde os artefatos ampliados foram gerados. Dependências reutilizadas do ambiente instalado; não é teste de instalação em outra máquina. Evidência atual em `reports/validacao_entrega.json`.

## Pendências para escopo completo
- Dados operacionais de rotas, distâncias, contratos, eixos, pedágios e retorno.
- Coeficientes ANTT históricos e enquadramento das operações; a referência mensal ANP já foi integrada e auditada.
- Validar candidato de menor viés prospectivamente; revisão da disponibilidade antecipada dos atributos e robustez por segmento continua necessária.
- Explicação SHAP e ampliação de modelos/tuning previstos no relatório original; versão atual usa permutação e seleção limitada.
- Concluir revisão visual dos demais fluxos, validar com usuário de negócio e avaliar simulador em casos reais.
- Revisão acadêmica pelos responsáveis e personalização de autoria/instituição, se exigidas. PDFs do processo e executivo já foram exportados; slides são complemento opcional.
- Dia exato de entrega e rubrica detalhada ainda não informados.

## Requisitos confirmados pelo aluno
Entrega no final de novembro/2026, sem dia definido: dashboard interativa (referência demonstrada pelo professor foi web), relatório das atividades e dos parâmetros usados, e códigos do desenvolvimento. Só há acesso aos arquivos existentes. O painel Streamlit atende ao formato web em execução local; hospedagem pública não foi exigida nem realizada. A entrega deverá incluir instruções para execução pelo professor.

O projeto está em versão acadêmica funcional em revisão. Dados adicionais e confirmação prospectiva são condições para ampliar conclusões e adoção operacional; não impedem a entrega acadêmica do escopo demonstrável com os arquivos disponíveis. Não declarar concluída a conformidade por rota ou comprovada eficiência veicular sem evidência.
