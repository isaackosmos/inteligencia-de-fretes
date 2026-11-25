# Inteligência de custos de frete — Agrária

Projeto acadêmico aplicado: diagnóstico de orçamento, previsão de tarifas e simulador de cenários para vendas de Nutrição Animal. Dados observados, previsões e premissas de engenharia possuem significados distintos e são apresentados separadamente.

## Projeto integrado do grupo

Abra o painel e escolha uma área na barra lateral. **Análise e simulação** reúne orçamento, histórico, cenários e desempenho dos modelos. **Cotação da empresa** calcula uma referência por peso, destino e carga e registra a cotação. **Consulta do motorista** recupera o cadastro por código ou QR. **Cenários salvos** permite comparar e transferir cenários de mix e viagem por JSON.

A [integração do grupo](docs/integracao_grupo.md) documenta a origem das contribuições, o fluxo de demonstração e a configuração do QR. Em [Experimentos do grupo](notebooks/04_Experimentos_do_grupo.ipynb) estão custo por item e classificação. A [comparação de tarifa](docs/benchmark_grupo.md) reúne árvore, Gradient Boosting e floresta em janelas temporais comuns e pode ser refeita com `.venv/bin/python scripts/benchmark_group_models.py`.

A [apresentação da disciplina Inteligência Artificial e Data Mining](output/apresentacao_ia_data_mining.pptx) inclui notas de fala, espaços editáveis para seis integrantes e roteiro de demonstração.

## Início rápido

Python 3.9 ou superior. Os arquivos `Realizado.xlsx` e `Orcado.xlsx` devem permanecer na raiz. O CSV original serve para conferência, não substitui o ETL.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python scripts/build_data.py
.venv/bin/python scripts/analyze.py
.venv/bin/python scripts/train.py
.venv/bin/python -m pytest -q
.venv/bin/python -m streamlit run app/dashboard.py
```

Para executar as etapas com registro de comandos, versões, duração e integridade das fontes, use `.venv/bin/python scripts/run_pipeline.py`. Esse fluxo de auditoria exige os seis arquivos originais na raiz. `--skip-train` reutiliza o modelo existente e identifica a execução como parcial; não comprova um novo treinamento.

Experimento complementar de viés: `.venv/bin/python scripts/experiment_bias.py`. Ele não substitui o modelo do painel nem reavalia o teste já observado. Método em `docs/experimento_vies.md`.

Estabilidade histórica e artefato candidato: `.venv/bin/python scripts/analyze_stability.py`. Gera previsões fora da amostra e diagnósticos por mês/destino/peso, sem substituir o artefato inicial. Na interface, a seleção de versão é explícita e as avaliações não são misturadas.

Referência pública de diesel: `.venv/bin/python scripts/import_diesel.py --download`. Reutiliza a fonte bruta se já existir; grava série mensal, cobertura e hashes. O pacote inclui a série pública tratada e seus metadados. A série é contexto retrospectivo, não atributo de previsão nem preço efetivamente pago pela empresa. Detalhes em `docs/diesel_anp.md`.

Auditoria da entrega: `.venv/bin/python scripts/check_project.py`. Verifica fontes, artefatos, proveniência dos modelos, métricas e manifesto do pacote. Avisos de limitação metodológica não equivalem a falhas técnicas; verificações omitidas são identificadas.

Para reconstruir os relatórios ampliados e os PDFs após o pipeline principal:

```bash
.venv/bin/python -m pip install '.[dev,docs,render]'
.venv/bin/python scripts/experiment_bias.py
.venv/bin/python scripts/analyze_stability.py
.venv/bin/python scripts/report_development.py
.venv/bin/python scripts/export_reports.py --render
```

A exportação PDF requer os extras `docs`; `--render` também requer `render`. A série ANP tratada já acompanha o pacote; o download bruto é necessário somente para reconstruir essa fonte. Os PDFs exigem as análises ampliadas e o metadado ANP presentes. São complementos ao pipeline principal e não são recriados por `run_pipeline.py`. O executivo possui até cinco páginas; o técnico registra atividades e parâmetros. Revise os textos interpretativos ao mudar os resultados.

Pacote local de código: `.venv/bin/python scripts/package_delivery.py`. Gera `dist/codigo_frete.zip`, com manifesto SHA-256, sem bases operacionais, ambiente ou modelos. A documentação inclui resultados agregados. As saídas dos notebooks são removidas apenas dentro do ZIP. Forneça os dados separadamente ao professor pelo canal autorizado e siga os comandos acima para reconstrução.

Validação do pacote em pasta temporária: `.venv/bin/python scripts/verify_delivery.py`. Reconstrói dados, modelo, relatórios e testes usando o mesmo ambiente Python, com fontes originais ligadas para leitura. Registra `reports/validacao_entrega.json` e mantém os logs na pasta temporária. Não testa instalação em outro computador.

No Windows, use `.venv\Scripts\python.exe` em lugar de `.venv/bin/python`. O lock registra o ambiente desta execução (macOS/Python 3.9); em outra versão de Python, instale a partir de `pyproject.toml` com `python -m pip install '.[dev]'` e registre novo ambiente. A instalação comum não exige suporte a modo editável do instalador.

Para testar uma instalação nova na mesma máquina, execute `.venv/bin/python scripts/verify_environment.py`. O comando cria outro venv temporário, instala dependências e o pacote, verifica conflitos, importa o pacote fora do repositório e roda a suíte. Precisa de rede e registra logs e resultado em `reports/validacao_ambiente.json`; não altera `.venv`.

## Organização

- `docs/escopo.md`: problema, perguntas e critérios de aceite.
- `docs/plano_entrega.md`: dashboard, relatório do processo e códigos, com metas internas para novembro.
- `reports/final/relatorio_desenvolvimento.md`: atividades, tratamentos, parâmetros efetivos e resultados; regenerar com `python scripts/report_development.py` após treinar.
- `docs/tarefas.md` e `docs/status.md`: planejamento e progresso verificável.
- `docs/auditoria_dados.md`: qualidade, conciliações e decisões sobre fontes.
- `docs/modelagem.md`: método e resultados preditivos.
- `docs/fontes_externas.md`: fontes oficiais e campos necessários para ampliar o escopo.
- `src/frete`: processamento, análises, modelos, simulações e triagem documental.
- `scripts`: comandos de reconstrução.
- `app/dashboard.py`: painel local.
- `notebooks`: exploração e leitura técnica reproduzíveis.
- `reports`: tabelas e figuras calculadas; `models`: artefato de previsão.

## Dados e limitações

Não há dados operacionais suficientes para afirmar conformidade por rota, comprovar custos por componente ou recomendar configuração veicular real. O simulador permite avaliar premissas explícitas. O módulo `compliance.py` só calcula uma referência com cadastro completo e coeficientes com vigência e proveniência, fornecidos externamente; não contém tabela ANTT de produção.

O orçamento 2026 aplicado a 2025 é referência retrospectiva. Destino é aproximado pelo cadastro do representante. Data de liquidação não garante disponibilidade das variáveis no momento da contratação. O modelo deve ser avaliado no escopo filtrado e em teste temporal, sem prometer desempenho em rotas desconhecidas.

Arquivos originais e modelos não são incluídos no Git por padrão. Não publicar dados empresariais sem autorização. Nunca carregar modelos joblib de origem desconhecida.
