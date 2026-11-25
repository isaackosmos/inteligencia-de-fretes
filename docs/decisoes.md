# Registro de decisões

## 2026-11-10 — Preservação e proveniência
Manter arquivos originais na raiz nesta primeira versão, para não quebrar referências existentes. `data/raw` é reservado para futuras fontes. Bases derivadas ficam em `data/processed`. Fontes empresariais e modelos ficam fora do Git por padrão; compartilhamento público depende de autorização sobre os dados.

## 2026-11-10 — Arquitetura
Python, pandas e scikit-learn para processamento e previsão; Streamlit para interface. Código reutilizável em `src/frete`, comandos em `scripts`, documentação em `docs`. Usar ambiente `.venv` local e dependências versionadas.

## 2026-11-10 — Integridade metodológica
Resultados calculados de dados observados e cenários parametrizados serão identificados separadamente. Peso agregado por frete representa proxy, não comprova capacidade ou eixos. Inferir custos de diesel a partir de hipóteses não constitui identificação da composição real da tarifa contratada.

## 2026-11-10 — Requisitos acadêmicos confirmados
O aluno informou prazo no final de novembro, dashboard interativa com referência web, relatório das atividades e parâmetros e entrega do código. Apenas os arquivos atuais estão disponíveis. Priorizar acabamento da interface, rastreabilidade do processo e reprodução local; hospedagem pública e slides não são requisitos confirmados. A falta de dados internos adicionais será uma limitação da conclusão, não uma dependência obrigatória para entregar o trabalho acadêmico.

## 2026-11-10 — Investigação de viés sem reutilização confirmatória do teste
Preservar modelo e métricas da primeira avaliação. Experimento posterior usa apenas janelas anteriores a abril/2026 e reconhece que foi motivado pelo teste já visto. RF na escala original é candidato por validação histórica; não promovê-lo automaticamente como solução validada no futuro. Registrar tanto ganho pequeno de WAPE quanto redução do viés interno.

## 2026-11-10 — Verificação visual e distribuição
Revisão no navegador identificou contraste insuficiente de cards no tema escuro e truncamento de métricas. Corrigidos cores dos cards e disposição responsiva, com nova conferência no navegador. Pacote de código separa bases operacionais e modelos, remove saídas dos notebooks dentro do ZIP e inclui manifesto de integridade. A documentação continua contendo resultados agregados.

## 2026-11-10 — Referência externa e estabilidade local
Importar a série mensal estadual oficial ANP, produtos separados, com lacunas preservadas e proveniência. Não usá-la como feature contemporânea nem inferir posto de abastecimento pelo destino da entrega. A candidata apresenta menor viés agregado histórico, mas erros locais relevantes: manter comparação explícita, alertas por segmento e estágio experimental. Confirmação futura condiciona adoção operacional, não o encerramento acadêmico com limitações.

## 2026-11-10 — Proveniência coletada no ajuste
Novas execuções de treino registram hash da base, código, UTC e versões. Os artefatos anteriores foram arquivados localmente antes da reexecução com mesmos parâmetros. Nas 6.327 previsões do teste, a diferença máxima da versão inicial foi 9,1e-13 R$/t, sem mudança material. Não preencher retroativamente metadados como se tivessem sido coletados antes do treino.
