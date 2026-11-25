# Integração do projeto de fretes

O painel Streamlit reúne a análise de orçamento e tarifa, os cenários de decisão e a demonstração de cotação e consulta. A base processada pelo projeto é a origem das tarifas históricas exibidas e usadas nas cotações.

| Contribuição do grupo | Aplicação na entrega |
| --- | --- |
| Painel web de custos e quantidade de fretes | O diagnóstico mostra custo mensal e fretes distintos no recorte ao lado da tarifa ponderada, do orçamento ajustado e das verificações de cobertura. |
| Operação com visão da empresa e do motorista | A empresa estima peso × tarifa histórica para destino e carga, registra a cotação e altera seu status. O motorista consulta o mesmo registro por código ou QR. |
| Percurso de ida, ida e volta ou retorno alternativo | As distâncias dos trechos entram no simulador de viagem, junto de consumo, pedágio, ocupação, outros custos e acréscimo. Os quilômetros são informados manualmente. |
| Gráficos de previsão e investigação de modelos | O painel exibe a comparação temporal de árvore de decisão, Gradient Boosting e floresta. O notebook 04 registra o histórico de LSTM e classificadores e executa referências locais para custo por item e classe de custo. |

## Demonstração

1. Na área **Análise e simulação**, escolha um recorte, veja o custo mensal e ajuste uma viagem ou um mix. Guarde cenários e abra **Cenários salvos** para comparar ou exportar.
2. Abra **Cotação da empresa**, escolha destino, carga e peso, calcule e cadastre. Altere o status da cotação e baixe o QR.
3. Abra **Consulta do motorista** e consulte usando o código do QR. Uma sessão nova na mesma instalação acessa o mesmo registro.
4. Em **Modelo e metodologia**, abra **Experimentos de modelagem do grupo** e compare os erros por janela.

A cotação histórica calcula a tarifa como custo realizado dividido por toneladas na combinação escolhida. O volume cotado é multiplicado pela tarifa ponderada. A simulação por componentes usa premissas explícitas de viagem. Os experimentos de tarifa em R$/t, custo em R$ por item e classificação alto/baixo usam alvos e métricas próprios.

Por padrão o QR contém o código e a consulta usa `data/cotacoes.sqlite3`. Para que o QR abra a tela diretamente, defina `FRETE_URL_CONSULTA` com a URL base acessível da mesma instalação. `FRETE_COTACOES_DB` pode apontar para outro caminho local gravável. As áreas empresa e motorista são visões de demonstração sem autenticação. Execute o painel em ambiente privado. O cadastro guarda somente dados da cotação, código, data e status. O banco local fica fora do Git e do pacote.

## Origem e reprodução

- [Site da equipe](https://gabrielribas18.github.io/analise-custos-frete/) e [revisão do código consultada](https://github.com/gabrielribas18/analise-custos-frete/tree/0a7de43d30c6417eef201effd01ae07e0b437e2f).
- [Notebook no Colab](https://colab.research.google.com/drive/1IrITaR7o22wmoCDTVV8TjNdfqDcOjxt1) e [revisão do notebook no GitHub](https://github.com/gabrielribas18/analise-custos-frete/blob/0a7de43d30c6417eef201effd01ae07e0b437e2f/analise/trabalho_agraria%20.ipynb). O link curto fornecido redireciona ao mesmo repositório.
- [Experimentos de custo por item e classificação](../notebooks/04_Experimentos_do_grupo.ipynb) usam a base gerada por `scripts/build_data.py`.
- [Protocolo e resultados da comparação de tarifas](benchmark_grupo.md) incluem o comando para gerar novamente as métricas e os dados do gráfico.
