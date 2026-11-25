# Fontes externas e dados necessários

Levantamento inicial: 10/11/2026. Série mensal estadual de diesel ANP importada e auditada em `diesel_anp.md`; coeficientes ANTT ainda não importados. Não há tabela regulatória certificada nesta versão.

| Tema | Fonte | Uso e cuidado |
|---|---|---|
| Diesel | [ANP — série histórica](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis) | Preços pesquisados, não necessariamente preço pago pela transportadora. Selecionar produto, local, período e agregação. |
| Piso mínimo | [ANTT — política nacional](https://www.gov.br/antt/pt-br/assuntos/cargas/politica-nacional-de-pisos-minimos-de-frete) | Obter enquadramento e coeficientes por vigência histórica. |
| Método | [ANTT — como calcular](https://www.gov.br/antt/pt-br/assuntos/cargas/politica-nacional-de-pisos-minimos-de-frete/como-calcular) | Exemplos são ilustrativos. Não substituem confirmação dos coeficientes aplicáveis. |
| Referência oficial | [Calculadora ANTT](https://calculadorafrete.antt.gov.br/) | Conferência de casos completos, sem automatizar conclusões com entradas desconhecidas. |

## Contrato mínimo de dados para próxima integração

`rotas.csv`: rota_id, origem, destino, distancia_km, fonte_distancia, data_consulta, pedágio_por_viagem, fonte_pedagio, vigencia_inicio, vigencia_fim.

`operacoes.csv`: numero_frete, data_transporte, rota_id, eixos, categoria_carga, modalidade_contratacao, lotacao_ou_fracionada, peso_t, valor_contratado, pedagio_incluso, retorno_vazio, fonte.

`veiculos.csv`: configuracao, eixos, capacidade_util_t, consumo_km_l, custo_outros_por_km, custo_fixo_viagem, fonte, vigencia. Capacidade e consumo não são determinados somente pelo número de eixos.

`antt_coeficientes.csv`: vigencia_inicio, vigencia_fim, tabela, categoria_carga, eixos, coeficiente_deslocamento, coeficiente_carga_descarga, ato_normativo, url_fonte.

`diesel.csv`: data, localidade, produto, preco_rs_l, agregacao, url_fonte, data_coleta.

## Regras de uso
- Não preencher dados desconhecidos com números apresentados como observados.
- Não usar média municipal como preço efetivamente pago sem identificar a aproximação.
- Não aplicar automaticamente regra de lotação a itens de carga fracionada.
- Não comparar tarifa de um item com piso de uma viagem inteira.
- Registrar insumos ausentes e emitir resultado “não avaliável” quando necessário.
