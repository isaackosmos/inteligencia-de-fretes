# Referência histórica de diesel - ANP

## Fonte e reprodução
Foi obtida a planilha oficial de preços médios mensais por estado, disponível na [série histórica da ANP](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos). Endereço direto e SHA-256 ficam em `data/external/diesel_metadata.json`.

```bash
python scripts/import_diesel.py --download
```

Se a fonte bruta já existe, o comando a reutiliza, sem atualizar silenciosamente a fotografia recebida. Sem rede, execute `python scripts/import_diesel.py` após colocar a planilha no caminho indicado pela mensagem. O arquivo bruto permanece fora do Git. O importador limita o download a 20 MiB, confere domínio oficial após redirecionamento e valida formato XLSX, esquema, unidades, preços e unicidade.

## Recorte importado
Janeiro/2025 a agosto/2026: 1.074 referências mensais de revenda, 27 estados, produtos `OLEO DIESEL` e `OLEO DIESEL S10`, preservados separadamente. Não recalculamos as médias estaduais publicadas pela ANP nem misturamos os produtos.

Cobertura ausente na fotografia consultada: óleo diesel em Amapá, abril-agosto/2026 (cinco meses), e Sergipe, agosto/2025 (um mês). As lacunas permanecem ausentes; não houve preenchimento de preços. A cobertura de cada combinação consta no metadado.

## Uso permitido nesta análise
- Contexto histórico e referência editável para cenário de custo por viagem.
- Produto, estado, período, unidade e proveniência visíveis na interface.
- Nenhuma associação automática entre destino da entrega e local de abastecimento.
- Nenhum uso como atributo do modelo atual ou da candidata. A média completa do mês não estava disponível no início daquele mês; um uso preditivo futuro precisará de defasagem e comprovação da publicação.
- Não tratar preço pesquisado de revenda como preço efetivamente pago pela transportadora.
- Agosto/2026 da ANP corresponde ao mês completo; os fretes fornecidos terminam em 04/08. Não comparar os dois como períodos operacionais idênticos.

## Auditoria
`diesel.csv` é derivado público, não um cadastro interno da Agrária. `diesel_metadata.json` registra hash da fonte bruta, hash do CSV, processamento UTC, mtime do arquivo baixado, produtos, abrangência e cobertura. O mtime documenta a fotografia local; não é a data de publicação original de cada observação.

Testes em `tests/test_anp.py` verificam recorte temporal, produto/unidade, recusa de duplicatas e preços inválidos. A atualização da fonte exige nova auditoria e regeneração dos relatórios dependentes.
