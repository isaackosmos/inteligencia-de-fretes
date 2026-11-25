# Auditoria e reconstrução da base

## Fontes e processamento

As planilhas originais na raiz permanecem intactas. `scripts/build_data.py` lê `Realizado.xlsx` (Data), `Orcado.xlsx` (Orçado 26 e BPC 26), reconstrói a base e grava `data/processed/base_modelagem_frete.csv` e `data/processed/auditoria.json`. O JSON registra SHA-256 das fontes, dimensões, totais, ausências e alertas. O CSV da raiz é uma referência recebida, não a saída do processamento.

Execução: `python scripts/build_data.py`. Verificação: `python -m unittest discover -s tests -p test_data.py`.

## Unidade de observação e regras

- Uma linha representa um par `Nº frete + Item`; 49.051 linhas de materiais originam 29.860 itens em 11.771 fretes.
- A primeira coluna `Valor líquido` é constante no item e entra **uma única vez**. A segunda, importada como `Valor líquido.1`, é rateio por material, usado só para conferir fechamento. Somar a primeira coluna na planilha inteira superestima o custo.
- Peso líquido da linha = `Peso líquido + Peso líq.acumul.`; o peso do item é a soma das linhas dividida por 1.000. Peso bruto segue regra equivalente.
- O valor reconstruído fecha em R$ 33.951.407,81 e o peso em 200.911,43023 t. Datas: 02/01/2025–04/08/2026; agosto está incompleto.
- Material principal é o material/denominação com maior peso **agregado**, com desempate por código. Não é necessariamente a maior linha isolada.
- Campos categóricos usam moda determinística. Há três itens com mais de um representante: a moda é uma aproximação, e esses itens merecem revisão antes de decisões por rota.
- Tipo de carga é granel quando pelo menos 50% do peso está em UM=KG; caso contrário ensacado. Destino é um mapeamento por representante via BPC 26, não uma rota física origem-destino comprovada.
- Tarifa realizada = valor do item / toneladas líquidas, sem arredondamento intermediário.

## Qualidade e cobertura

| Verificação | Resultado | Tratamento |
|---|---:|---|
| Valor igual a zero | 26 itens | Preservar; excluir do treino quando necessário, sem inventar tarifa |
| Rateio divergente do valor do item | 372 itens | Tolerância absoluta R$ 0,05; investigar peso e lançamento |
| Categoria diferente de Z101 | 358 itens | Segmentar ou justificar filtro de escopo |
| Tarifa orçada ausente/não positiva | 4.607 itens | Preservar ausência; imputar somente no treino |
| Volume orçado ausente | 1.184 itens | Não substituir por volume realizado |
| Média anual orçada ausente/não positiva | 4.383 itens | Preservar ausência |
| Nome de representante ausente | 700 itens | Não significa necessariamente ausência de operação |
| Fora de P1–P99 do alvo | 598 itens | Flag exploratória; jamais filtrar teste com limites globais |

Os extremos, inclusive pesos acima de 40 t por item, são preservados para investigação. Não há remoção automática. As três verificações automatizadas conferem unicidade, totais independentes conhecidos, identidade tarifa × peso, participação de carga e um frete com valor repetido em duas linhas.

## Diferenças em relação ao CSV recebido

As chaves, quantidades, totais, pesos e cobertura do orçamento conferem. As diferenças deliberadas são:

1. A tarifa permanece em precisão integral; o CSV recebido a arredonda para duas casas.
2. O material principal é escolhido após agregação por material: 371 códigos e 452 denominações diferem da referência.
3. `_PEL` é reconhecido também nas grafias `_PELKG` e `_PEL_KG`; 1.042 participações de peletizado diferem. Exemplo verificado na fonte: `GOLDEN BEEF DIETA TOTAL ACABAMENTO_PELKG`.
4. O corte descritivo P1–P99 aplicado à precisão integral sinaliza 598 observações, contra 597 no recebido. Isso não autoriza remover qualquer uma do teste.

## Limites de uso e prevenção de vazamento

**O orçamento disponível é de 2026.** Para manter compatibilidade com os 46 campos recebidos, a ligação por representante × mês × tipo de carga também associa essa referência a registros de 2025. Trata-se de comparação retrospectiva; não há evidência de que essa tarifa estivesse disponível em 2025. Um teste que utilize essas colunas precisa ser rotulado adequadamente, e a avaliação operacional principal deve excluir atributos orçamentários sem disponibilidade histórica demonstrada.

`flag_valor_zero`, `flag_outlier_rs_t` e qualquer transformação do valor realizado não são features. Limites de outliers, imputação e codificação devem ser estimados no treino, nunca usando o teste. Consolidar itens de um frete usa informação do embarque completo; para previsão antecipada, é necessário que esse embarque já esteja planejado.

Diesel, distância, transportadora, pedágio e eixos não são observados nestas fontes. Simulações com esses componentes devem identificar premissas e não alegar conformidade legal por operação sem dados suficientes.
