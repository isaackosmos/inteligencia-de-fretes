"""Exporta o relatório de treinamento da IA a partir dos resultados salvos."""
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, PageBreak
from export_reports import ROOT, br, foot, header, image, load, p, pct, section, table

MODEL_NAMES = {
    'random_forest': 'Random Forest',
    'hist_gradient_boosting': 'HistGradientBoosting',
    'ridge_alpha1': 'Ridge (alpha = 1)',
    'ridge_alpha10': 'Ridge (alpha = 10)',
}


def export():
    model = load('reports/modelagem/resumo.json')
    stability = load('reports/estabilidade/resumo.json')
    test = model['test']
    common = model['common_sample_test']

    story = header('Treinamento e avaliação da IA',
                   'Relatório técnico | Previsão de tarifa de frete de Nutrição Animal')
    story += [
        section('1. Problema e dados'),
        p('O projeto usa aprendizado supervisionado por regressão para estimar a tarifa de um item de frete em reais por tonelada. O alvo histórico é o valor líquido do frete dividido pelo peso líquido em toneladas. Na aplicação, a tarifa estimada é multiplicada pelo peso para obter o custo previsto do item.'),
        p(f"As planilhas Realizado.xlsx e Orcado.xlsx foram usadas para reconstruir a base. As linhas de material foram agregadas pela chave número do frete + item, contando o valor do item uma única vez. Dos {br(model['input_rows'], 0)} itens consolidados, {br(model['eligible_rows'], 0)} atenderam aos critérios de modelagem."),
        p('Treino e teste incluem a categoria Z101, tarifa e peso positivos, peso de até 40 t por item e rateio consistente. A avaliação se aplica a esse recorte.'),
        table(['Tipo', 'Variáveis usadas'], [
            ['Peso e composição', 'Peso líquido (t), peso bruto (kg), participações no peso por unidade (kg, saco e fardo) e por forma do produto (pellet, farelado e triturado).'],
            ['Operação e tempo', 'Contagens de materiais, fornecimentos e documentos de venda. Mês e índice mensal desde janeiro de 2025, calculados a partir da data de liquidação.'],
            ['Categorias', 'Representante, destino cadastral, tipo de carga, tipo de remessa e material principal.'],
        ], [47*mm,124*mm]),
        section('Prevenção de vazamento de dados'),
        p('Valor realizado, imposto, rateio, identificadores de transação e flags derivadas do alvo ficaram fora dos preditores. O orçamento de 2026 foi usado como referência de avaliação. A série de diesel da ANP e os totais do caminhão ficaram fora do treinamento.'),
        p('A data de liquidação aproxima a data planejada do transporte. O destino vem do cadastro do representante. Para uso operacional, é preciso confirmar que os atributos estão disponíveis no momento da previsão.'),
        PageBreak(),
    ]

    story += header('Como o modelo foi treinado', 'Validação temporal e parâmetros')
    story += [
        section('2. Separação temporal e tratamento'),
        table(['Etapa', 'Período e regra'], [
            ['Validação interna', 'Cinco janelas crescentes. Validação em abr-mai/2025, jun-jul/2025, ago-set/2025, out-dez/2025 e jan-mar/2026. Em cada janela, usa-se apenas histórico anterior para ajustar o modelo.'],
            ['Treino final', f"Jan/2025 a mar/2026, {br(model['n_train'], 0)} itens."],
            ['Teste temporal', f"Abr/2026 a 04/08/2026, {br(model['n_test'], 0)} itens. Agosto é parcial."],
        ], [47*mm,124*mm]),
        p('A separação remove do treino fretes também presentes na validação ou no teste. Os valores numéricos ausentes são imputados pela mediana e padronizados. Ridge e Random Forest usam codificação one-hot com frequência mínima 20. HistGradientBoosting usa codificação ordinal.'),
        p('Os tratamentos são ajustados dentro de cada treino. O alvo de treino é limitado aos percentis 1 e 99 e transformado com log1p. As previsões voltam à escala em R$/t por expm1, com piso zero. Os valores extremos do teste foram preservados.'),
        section('3. Configurações comparadas'),
        table(['Modelo', 'MAE médio (R$/t)', 'Desvio padrão'], [
            [MODEL_NAMES[r['model']], br(r['mean']), br(r['std'])] for r in model['cv']
        ], [85*mm,45*mm,41*mm]),
        p('A Random Forest obteve o menor MAE médio nas cinco janelas. Cada árvore estima a tarifa transformada a partir de regras aprendidas nos dados. A floresta combina as estimativas das árvores e o resultado é convertido de volta para R$/t.'),
        p('<b>Parâmetros da Random Forest.</b> 100 árvores, profundidade máxima de 18, mínimo de 8 itens por folha, 80% das variáveis candidatas a cada divisão e semente 42. A seleção comparou configurações fixas.'),
        PageBreak(),
    ]

    story += header('O que o teste mostrou', 'Abril a agosto de 2026 | 6.327 itens')
    story += [
        section('4. Resultados no período reservado'),
        table(['Métrica', 'Tarifa orçada', 'Random Forest'], [
            ['MAE (R$/t)', *[br(r['MAE_rs_t']) for r in test]],
            ['RMSE (R$/t)', *[br(r['RMSE_rs_t']) for r in test]],
            ['WAPE de tarifa', *[pct(r['WAPE_tarifa']) for r in test]],
            ['WAPE de custo', *[pct(r['WAPE_custo']) for r in test]],
            ['R²', *[br(r['R2'], 3) for r in test]],
            ['Viés do custo total', *[pct(r['vies_total_custo']) for r in test]],
        ], [73*mm,49*mm,49*mm]),
        p('MAE mede o erro absoluto médio em R$/t. RMSE dá mais peso a erros grandes. WAPE relaciona a soma dos erros absolutos à soma dos valores observados. No WAPE de custo, a tonelagem converte cada erro de tarifa em reais. O viés mede a diferença percentual entre gasto previsto e observado.'),
        p(f"A referência orçada teve {br(model['baseline_missing_test'],0)} tarifas ausentes, preenchidas com a mediana calculada no treino. Nos {br(model['common_sample_n'],0)} itens com tarifa orçada observada, o MAE caiu de R$ {br(common[0]['MAE_rs_t'])}/t para R$ {br(common[1]['MAE_rs_t'])}/t, redução de {(1-common[1]['MAE_rs_t']/common[0]['MAE_rs_t'])*100:.1f}%.".replace('11.2%', '11,2%')),
        image('reports/figures/custo_mensal_teste.png', 159*mm),
        p('Figura 1. Desembolso mensal observado, previsto pela IA e estimado pela referência orçada nos itens do teste. Agosto contém dados até o dia 4.', 'ReportSmall'),
        p('A IA reduziu o erro por item, porém subestimou o gasto total em 13,39%. A tarifa orçada subestimou o total em 3,94%. O resultado sustenta o uso exploratório no painel e exige investigação antes de adoção orçamentária.'),
        PageBreak(),
    ]

    story += header('Interpretação e reprodução', 'Diagnóstico do modelo e experimento de menor viés')
    story += [
        section('5. Variáveis relevantes e erros locais'),
        p('A importância por permutação foi medida no teste, com até 1.500 itens, três repetições e semente 42. Embaralhar o código do representante elevou o MAE em cerca de R$ 36,72/t. Destino cadastral veio a seguir, com R$ 13,16/t. O ranking mede a contribuição para a previsão e pode refletir correlações entre atributos.'),
        p('A equipe investigou a subestimação comparando versões com e sem transformação do alvo e calibração. A Random Forest na escala original foi selecionada em validações internas anteriores a abril/2026. A avaliação por segmento reuniu 18.468 previsões fora da amostra por versão.'),
        table(['Métrica histórica agrupada', 'RF com alvo em log', 'RF na escala original'], [
            ['MAE (R$/t)', *[br(r['MAE_rs_t']) for r in stability['overall']]],
            ['WAPE de custo', *[pct(r['WAPE_custo']) for r in stability['overall']]],
            ['Viés do custo total', *[pct(r['vies_total_custo']) for r in stability['overall']]],
        ], [67*mm,52*mm,52*mm]),
        p('A candidata reduziu a subestimação agregada histórica, mas Guarapuava registrou WAPE de custo de 35,99% e Sorocaba teve viés de -11,28%. Essas janelas também participaram do desenvolvimento. A candidata permanece experimental e requer confirmação em dados futuros.'),
        section('6. Como reproduzir'),
        p('<b>Base.</b> python scripts/build_data.py<br/><b>Treino e teste.</b> python scripts/train.py<br/><b>Experimento de viés.</b> python scripts/experiment_bias.py<br/><b>Estabilidade por segmento.</b> python scripts/analyze_stability.py'),
        p('O pipeline do modelo inicial fica em src/frete/modeling.py e o artefato em models/frete_model.joblib. Os parâmetros de ambiente e os hashes da base e do código de treino estão em reports/modelagem/resumo.json.'),
        p('Evidências principais: reports/modelagem/resumo.json, metricas_amostra_comum.csv e importancia_permutacao.csv, além de reports/estabilidade/resumo.json. Execute os comandos com as dependências descritas no README.', 'ReportSmall'),
    ]
    destination = ROOT / 'output/pdf/relatorio_treinamento_ia.pdf'
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(destination), pagesize=A4, leftMargin=20*mm,
                                 rightMargin=19*mm, topMargin=18*mm, bottomMargin=23*mm,
                                 title='Treinamento e avaliação da IA de fretes')
    document.build(story, onFirstPage=foot, onLaterPages=foot)
    return destination


if __name__ == '__main__':
    print(export())
