# Verificação de integridade do projeto e da entrega

Executar `.venv/bin/python scripts/check_project.py` depois de gerar os artefatos e o pacote (`scripts/package_delivery.py`). O comando não treina, não altera modelos, não faz download e não publica. O resultado detalhado fica em `reports/verificacao_projeto.json`.

## Cobertura

- SHA-256 dos seis originais contra o inventário e das planilhas contra a auditoria do ETL, quando disponível.
- Presença das principais saídas, modelo e documentos executáveis.
- Lista atual de atributos versus artefato, metadata versus resumo e divisão temporal atual versus contagens salvas.
- Proveniência do modelo principal e do candidato, quando presente: SHA-256 da base e do código responsável pelo treino, timestamp UTC e versões coletados durante o ajuste. Campos ausentes ou divergentes falham; não são interpretados como aprovação.
- Previsões do modelo salvo em todo o teste atual versus previsões registradas; recálculo de métricas versus JSON e CSV. Isso não reexecuta treinamento nem seleção.
- Links Markdown locais explícitos; caminhos em código inline ou blocos de código não são links e não geram falsos alertas. URLs externas não são acessadas.
- Se `reports/final/pdf_manifest.json` estiver presente, conferir SHA-256 das saídas e evidências, contagem de páginas via pypdf e limite de cinco páginas do executivo. Caminhos absolutos, travessia de diretórios e symlinks que escapem das raízes permitidas são rejeitados. Manifesto presente e desatualizado é falha técnica; ausência é aviso opcional. A checagem não substitui QA visual.
- Última evidência registrada de testes, sem confundi-la com nova execução. Rodar `.venv/bin/python -m pytest -q` para verificar o estado atual.
- ZIP: correspondência exata de entradas e manifesto, hashes, caminhos seguros, ausência de bases operacionais, modelo, ambiente e saídas dos notebooks. Templates externos só entram vazios. Exceção explícita: série pública `diesel.csv` acompanhada de `diesel_metadata.json`, URL oficial ANP e hash conferido, classificada no manifesto como fonte pública.

## Estados e limites

Código de saída 0 significa verificações executadas sem falhas, possivelmente com avisos; não significa projeto completo. Código 1 indica falha. Código 2 indica verificação parcial. `--skip-model` e `--skip-zip` geram checagens omitidas e nunca sucesso geral. Falhas mantêm prioridade sobre omissões.

Os novos treinamentos registram hashes da base e do código, data UTC e versões no próprio metadata. A verificação compara esses registros com os arquivos atuais; artefatos anteriores sem esses campos falham na checagem de proveniência. O modelo continua experimental e possui viés agregado documentado. Templates externos vazios não comprovam integração de ANP/ANTT nem conformidade por operação.

`scripts/verify_delivery.py` confere o ZIP antes de extrair e só registra sucesso se o pipeline terminar com `status=success`, `complete=true` e fontes intactas. Ele usa as dependências já instaladas e não comprova instalação em outra máquina. A execução completa desse script inclui treino; não faz parte de `check_project.py`.

## Correções do pacote

O manifesto distingue agora o início rápido com duas planilhas do pipeline auditado, que requer seis originais. Templates externos preenchidos são omitidos do ZIP; apenas cabeçalhos são incluídos, salvo a série pública de diesel com proveniência verificada. A criação do pacote não modifica os notebooks originais, mas remove outputs e contagens no conteúdo empacotado.
