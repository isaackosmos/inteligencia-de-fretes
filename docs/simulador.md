# Painel e simulação

Execute na raiz: `.venv/bin/python -m streamlit run app/dashboard.py`.

O painel lê `data/processed/base_modelagem_frete.csv`, com fallback para o CSV original. A atualização do arquivo invalida o cache. Os filtros abrangem destino, tipo de carga, período e categoria Z101. Indicadores usam apenas valores e pesos positivos. O custo e volume são somados; R$/t é ponderado por peso.

## Abas

1. Diagnóstico: custo, volume, tarifa, evolução mensal, destinos e orçamento flexível. A referência orçada aplica as tarifas aos volumes realizados, comparando exatamente os mesmos itens; cobertura em itens e toneladas é exibida. Dois gráficos distinguem a tarifa histórica de todo o recorte da comparação realizado/meta mensal na amostra comum com orçamento. O detalhamento mensal é exportável e usa o mesmo denominador de toneladas nas duas séries.
2. Cenário de mix: repondera tarifas históricas do recorte por participações editáveis e volume total. Reajuste explícito permite simular uma hipótese; não constitui previsão de IA.
3. Custo por viagem: combustível = distância / rendimento × preço do diesel; soma pedágios, outros custos por km e fixos; aplica acréscimo sobre custo; divide pela capacidade × ocupação. Valores iniciais são ilustrativos e identificados na tela. Uma tabela compara 6, 7 e 9 eixos quando o usuário preenche capacidade e rendimento; campos inicialmente zerados sinalizam informações pendentes.
4. Modelo e metodologia: apresenta métricas reais de `reports/modelagem/resumo.json`, comparando erros e viés agregado separadamente, inferência com modelo salvo e definições dos indicadores. Inclui triagem documental ANTT com upload de operação e coeficientes em JSON; sem cadastros completos retorna não avaliável.
5. Qualidade dos dados: conta flags antes das exclusões de valores/pesos não positivos, explica a sobreposição dos alertas, mostra cobertura, pesos acima de 40 t e destinos ausentes. Exibe auditoria integral com hashes dos arquivos originais e permite exportar os resultados. A auditoria integral independe dos filtros; a tabela de qualidade responde aos filtros.

Não há dados para comprovar conformidade ANTT ou atribuir automaticamente capacidades/rendimentos a 6, 7 e 9 eixos. Não se apresenta certificação legal nem se confunde estimativa paramétrica com custo observado. Distância e pedágios precisam representar o mesmo percurso. O acréscimo é markup, não margem sobre receita.

O núcleo de cálculos está em `src/frete/simulation.py` e pode ser usado fora da interface. Testes validam reponderação do mix, efeito da ocupação, componentes e entradas inválidas.

O orçamento disponível é de 2026. Aplicações ao histórico de 2025 são retrospectivas e a interface exibe aviso. Destino é proxy do representante. A aba de modelo integra `prever_frete` quando `models/frete_model.joblib` existe: altera o peso líquido e proporcionalmente o bruto de um item histórico, preservando os demais atributos; a tela explicita limites dessa análise.

## Uso e comunicação dos resultados

O cabeçalho apresenta a sequência de uso, e o menu lateral explica o recorte e as diferenças entre diagnóstico, cenário e previsão. Nomes de indicadores, tabelas e métricas são exibidos em português. O modelo é identificado como experimental; melhoria de MAE/WAPE e subestimação agregada são mostradas simultaneamente. O seletor de referência exclui categorias diferentes de Z101 e pesos acima de 40 t, e a entrada de peso limita o cenário a 40 t antes de permitir inferência.

Quando `reports/experimentos/vies_resumo.json` existe, a aba de modelo inclui a seção expansível “Experimentos de redução de viés”. Ela lê as oito configurações já calculadas e exibe erros, dispersão, viés e critérios de seleção com rótulos em português, percentuais e MAE em R$/t. O painel não recalcula o experimento. A seção separa a validação interna anterior a abril/2026 do teste já conhecido, registra que o modelo corrente não foi substituído e não apresenta eventual reteste como confirmação independente.

Exportações disponíveis: dados filtrados, destinos, comparação mensal, cenário de mix, cenário por viagem, comparação veicular, métricas do teste, qualidade e auditoria. Cenários JSON incluem resultados e premissas para reprodução. CSVs usam UTF-8 BOM, separador ponto e vírgula e vírgula decimal para abertura em planilhas em português. Nenhum arquivo-fonte é alterado pela interface.

## Validação

`tests/test_dashboard.py` usa Streamlit AppTest para verificar inicialização das cinco abas, reatividade do filtro e do volume, inferência com o modelo salvo, limite de peso na interface, contagem do recorte antes das exclusões e retorno não avaliável na triagem incompleta. Execute `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_dashboard.py`.

Os testes inspecionam a árvore da aplicação e o resultado dos cálculos; não substituem revisão visual em um navegador.

## Casos extremos e entradas incompletas

Um intervalo com apenas a data inicial interrompe os cálculos e pede a data final, em vez de mostrar silenciosamente toda a base. Para um dia único, use a mesma data nas duas posições. Intervalos invertidos são rejeitados. O último dia é integralmente incluído, mesmo se a fonte vier a conter horário. Recortes vazios mostram uma orientação; recortes sem valores/pesos positivos permitem baixar os itens para investigação.

Sem orçamento direto, o painel exibe “Sem referência” e não interpreta ausência como custo zero. As séries comparativas usam o mesmo conjunto de itens, peso e período. O mix inteiramente zerado não produz estimativa e pede uma participação positiva. Campos veiculares incompletos ou não finitos não derrubam a tela nem viram premissas operacionais. O JSON veicular preserva as premissas de viagem e de cada configuração. O filtro de categoria fica disponível quando a opção “Somente categoria padrão Z101” é desmarcada.

Os helpers puros `src/frete/dashboard_helpers.py` cobrem período, comparação mensal, contrato de exportação e validade das premissas de veículo. AppTests verificam datas incompletas/dia único, recorte vazio, ausência real de orçamento em Francisco Beltrão, categoria Z220 fora do modelo, mix zerado e inferência.

## Referências e comparação de versões

Se `data/external/diesel.csv` existir, a aba de viagem apresenta a referência oficial ANP por estado e produto, com série mensal, tabela e exportação. A seleção não altera o preço manual do cenário. As médias completas são retrospectivas, não são o valor pago pela empresa e não entram no modelo. Agosto completo na referência difere do histórico operacional encerrado em 04/08/2026.

Se `reports/estabilidade/resumo.json` existir, a aba Modelo apresenta estabilidade por mês, destino e peso, com síntese de alertas, suficiência amostral e CSVs detalhados disponíveis. Bom resultado agregado não é apresentado como evidência de estabilidade de todos os segmentos. A seção apenas lê resultados e não treina modelos.

Se `models/frete_candidate.joblib` existir, um seletor permite comparar a inferência da versão atual (padrão) com a candidata experimental. O artefato atual não é alterado. A tabela de teste abril–agosto é explicitamente identificada como avaliação exclusiva do modelo atual; resultados históricos do candidato ficam na seção de estabilidade. O candidato exige confirmação futura para adoção operacional, uma limitação de uso que não impede a comparação acadêmica. Ambas as versões usam exemplos Z101 com peso positivo até 40 t e rateio consistente.

## Aparência e telas estreitas

O tema claro está definido apenas neste projeto em `.streamlit/config.toml`. Os cartões mantêm texto escuro explícito sobre fundo claro mesmo quando o usuário seleciona tema escuro no navegador. Os rótulos e valores podem quebrar linha; grupos de indicadores passam a duas colunas em janelas de até 1100 px e uma coluna em até 480 px. Cabeçalhos acompanham a cor de texto do tema ativo. Alterações de configuração podem exigir reiniciar o servidor Streamlit.
