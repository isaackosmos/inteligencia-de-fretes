"""Execute: streamlit run app/dashboard.py."""
import os
import sys
from pathlib import Path
import json
from math import ceil
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from app.components.quotes import render_lookup, render_quotes
from app.components.saved_scenarios import render_scenario_manager, save_scenario
from frete.quotes import QuoteStore
from frete.simulation import component_scenario, volume_scenario
from frete.dashboard_helpers import filter_period, monthly_comparison, scenario_payload, valid_vehicle

st.set_page_config(page_title='Fretes | Agrária', page_icon='🚚', layout='wide')
st.markdown('''<style>
.block-container{padding-top:2rem;max-width:1450px}
[data-testid="stMetric"]{background:#f1f5f4;border:1px solid #dce7e2;border-radius:12px;padding:16px;height:100%}
[data-testid="stMetric"] *{color:#183c36!important}
[data-testid="stMetricValue"]{font-size:clamp(1.25rem,2.4vw,1.9rem);white-space:normal;overflow:visible;overflow-wrap:anywhere}
[data-testid="stMetricValue"] > div{font-size:inherit;white-space:normal;overflow:visible;text-overflow:clip}
[data-testid="stMetricLabel"] p{white-space:normal;overflow:visible;text-overflow:clip;font-size:.9rem;line-height:1.4}
h1,h2,h3{color:var(--text-color,#183c36)}
@media(max-width:1100px){
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]){flex-wrap:wrap;gap:1rem}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"]{flex:1 1 calc(50% - 1rem);min-width:calc(50% - 1rem);width:calc(50% - 1rem)}
}
@media(max-width:480px){
  .block-container{padding-left:1rem;padding-right:1rem}
  [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] [data-testid="stMetric"]) > [data-testid="stColumn"]{flex-basis:100%;min-width:100%;width:100%}
}
</style>''', unsafe_allow_html=True)


def br(value, decimals=2):
    return f'{value:,.{decimals}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def csv_bytes(frame):
    return frame.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')


@st.cache_data
def load(path, modified):
    df = pd.read_csv(path, sep=';', decimal=',', encoding='utf-8-sig',
                     dtype={'Representante': str, 'material_principal': str, 'Nº frete': str})
    df['Dta.liq.'] = pd.to_datetime(df['Dta.liq.'], errors='coerce')
    for column in ['peso_liquido_t', 'Valor líquido', 'tarifa_orcada_rs_t']:
        df[column] = pd.to_numeric(df[column], errors='coerce')
    df['destino_frete'] = df['destino_frete'].fillna('NAO_INFORMADO')
    return df


quote_store = QuoteStore(os.environ.get('FRETE_COTACOES_DB') or ROOT / 'data/cotacoes.sqlite3')
mode = st.sidebar.radio('Área de trabalho', ['Análise e simulação', 'Cotação da empresa',
                                            'Consulta do motorista', 'Cenários salvos'])
quote_code = st.query_params.get('cotacao', '')
if quote_code or mode == 'Consulta do motorista':
    if quote_code and st.sidebar.button('Fechar consulta do QR'):
        del st.query_params['cotacao']
        st.rerun()
    render_lookup(quote_store, br, quote_code[:36])
    st.stop()
if mode == 'Cenários salvos':
    render_scenario_manager(br)
    st.stop()

st.title('Inteligência de fretes')
st.caption('Diagnóstico do realizado, orçamento comparável e cenários de decisão · Nutrição Animal')
st.markdown('**Explore o histórico → compare o orçamento → simule decisões → confira as evidências.**')
path = ROOT / 'data/processed/base_modelagem_frete.csv'
if not path.exists():
    path = ROOT / 'base_modelagem_frete.csv'
if not path.exists():
    st.error('Base não encontrada. Execute python scripts/build_data.py.')
    st.stop()
df = load(str(path), path.stat().st_mtime_ns)
with st.sidebar:
    st.header('Recorte da análise')
    st.caption(f'Fonte: {path.relative_to(ROOT)}')
    destinations = st.multiselect('Destinos', sorted(df['destino_frete'].unique()), placeholder='Todos os destinos')
    cargo = st.multiselect('Tipos de carga', sorted(df['tipo_carga'].dropna().unique()), placeholder='Todos os tipos de carga')
    dates = st.date_input('Período', (df['Dta.liq.'].min().date(), df['Dta.liq.'].max().date()))
    only_standard = st.checkbox('Somente categoria padrão Z101', value=True)
    categories = [] if only_standard else st.multiselect('Categorias de item', sorted(df['CtgI'].dropna().unique()), placeholder='Todas as categorias')
    st.caption('Valores positivos e pesos positivos são usados nos indicadores. Agosto/2026 é parcial.')
    with st.expander('Guia de leitura'):
        st.write('Diagnóstico mostra fatos observados. Cenários usam premissas editáveis. Modelo apresenta previsões experimentais. Qualidade explica os limites da base. Todos os filtros afetam as abas.')
filtered = df.copy()
if destinations:
    filtered = filtered[filtered['destino_frete'].isin(destinations)]
if cargo:
    filtered = filtered[filtered['tipo_carga'].isin(cargo)]
try:
    filtered = filter_period(filtered, dates)
except ValueError as exc:
    st.info(str(exc))
    st.stop()
if only_standard:
    filtered = filtered[filtered['CtgI'] == 'Z101']
elif categories:
    filtered = filtered[filtered['CtgI'].isin(categories)]
scope = filtered.copy()
filtered = filtered[(filtered['peso_liquido_t'] > 0) & (filtered['Valor líquido'] > 0)].copy()
if filtered.empty:
    if scope.empty:
        st.info('Nenhum registro no recorte selecionado. Ajuste o período, destino, tipo de carga ou categoria.')
    else:
        st.info(f'Os {len(scope)} itens do recorte têm custo ou peso não positivo e não permitem calcular tarifa. Ajuste os filtros ou investigue esses registros.')
        st.download_button('Baixar itens sem tarifa calculável', csv_bytes(scope), 'itens_sem_tarifa.csv', 'text/csv')
    st.stop()
if mode == 'Cotação da empresa':
    render_quotes(filtered, quote_store, br)
    st.stop()

weight = filtered['peso_liquido_t'].sum()
cost = filtered['Valor líquido'].sum()
coverage = filtered['tarifa_orcada_rs_t'].notna() & (filtered['tarifa_orcada_rs_t'] > 0)
matched = filtered.loc[coverage]
budget = (matched['tarifa_orcada_rs_t'] * matched['peso_liquido_t']).sum()
matched_cost = matched['Valor líquido'].sum()
c1, c2, c3, c4 = st.columns(4)
c1.metric('Custo realizado', f'R$ {br(cost, 0)}')
c2.metric('Volume transportado', f'{br(weight, 0)} t')
c3.metric('Tarifa ponderada', f'R$ {br(cost / weight)}/t')
c4.metric('Itens no recorte', br(len(filtered), 0))
tab1, tab2, tab3, tab4, tab5 = st.tabs(['Diagnóstico', 'Cenário de mix', 'Custo por viagem', 'Modelo e metodologia', 'Qualidade dos dados'])
with tab1:
    st.subheader('Realizado versus orçamento ajustado ao volume')
    st.write('A comparação usa o mesmo conjunto de itens e o volume realizado em cada um. Assim, mudanças de volume não são confundidas com mudanças de tarifa.')
    if (filtered['Dta.liq.'].dt.year < 2026).any():
        st.warning('O recorte inclui 2025, mas a referência disponível é o orçamento de 2026. Para 2025, a comparação é retrospectiva e não representa o orçamento original daquele ano.')
    a, b, c = st.columns(3)
    a.metric('Meta ajustada · itens com tarifa', f'R$ {br(budget, 0)}' if not matched.empty else 'Sem referência')
    b.metric('Realizado · mesmos itens', f'R$ {br(matched_cost, 0)}' if not matched.empty else 'Sem amostra')
    c.metric('Desvio contra a meta', f'{br((matched_cost / budget - 1) * 100)}%' if budget else 'Sem referência')
    st.caption(f'Cobertura da tarifa orçada: {br(100 * len(matched) / len(filtered), 1)}% dos itens e {br(100 * matched["peso_liquido_t"].sum() / weight, 1)}% do volume. Itens sem tarifa são excluídos somente desta comparação.')
    monthly = filtered.assign(mes=filtered['Dta.liq.'].dt.to_period('M').astype(str)).groupby('mes').agg(custo_rs=('Valor líquido', 'sum'), peso_t=('peso_liquido_t', 'sum'))
    monthly['Realizado · R$/t'] = monthly['custo_rs'] / monthly['peso_t']
    with st.expander('Custo mensal e quantidade de fretes'):
        monthly_cost = monthly[['custo_rs']].rename(columns={'custo_rs': 'Custo (R$)'})
        st.bar_chart(monthly_cost, y_label='Reais', x_label='Mês')
        st.caption(f'{br(filtered["Nº frete"].nunique(), 0)} fretes distintos no recorte. O custo soma os itens elegíveis.')
    st.subheader('Evolução da tarifa ponderada')
    st.line_chart(monthly[['Realizado · R$/t']], y_label='Reais por tonelada', x_label='Mês')
    st.caption('Histórico completo do recorte. A média é ponderada pelo peso; meses parciais podem apresentar outro mix de embarques.')
    st.subheader('Comparação mensal na mesma amostra')
    if not matched.empty:
        monthly_common = monthly_comparison(filtered)
        st.line_chart(monthly_common[['Realizado · R$/t', 'Meta ajustada · R$/t']], y_label='Reais por tonelada', x_label='Mês')
        with st.expander('Detalhamento mensal e exportação'):
            monthly_display = monthly_common.reset_index().rename(columns={'mes': 'Mês', 'realizado_rs': 'Realizado (R$)', 'meta_rs': 'Meta ajustada (R$)', 'peso_t': 'Volume (t)', 'itens': 'Itens', 'desvio_pct': 'Desvio (%)'})
            st.dataframe(monthly_display, hide_index=True, width='stretch')
            st.download_button('Baixar comparação mensal', csv_bytes(monthly_display), 'comparacao_mensal.csv', 'text/csv')
    else:
        st.info('Nenhum item com tarifa orçada no recorte; comparação mensal indisponível.')
    routes = filtered.groupby('destino_frete').agg(custo_rs=('Valor líquido', 'sum'), peso_t=('peso_liquido_t', 'sum'), itens=('Item', 'size')).reset_index()
    routes['tarifa_rs_t'] = routes['custo_rs'] / routes['peso_t']
    st.subheader('Destinos do recorte')
    route_display = routes.sort_values('custo_rs', ascending=False).rename(columns={'destino_frete': 'Destino', 'custo_rs': 'Custo realizado (R$)', 'peso_t': 'Volume (t)', 'itens': 'Itens', 'tarifa_rs_t': 'Tarifa ponderada (R$/t)'})
    st.dataframe(route_display, width='stretch', hide_index=True,
                 column_config={'Custo realizado (R$)': st.column_config.NumberColumn(format='%.2f'), 'Volume (t)': st.column_config.NumberColumn(format='%.2f'), 'Tarifa ponderada (R$/t)': st.column_config.NumberColumn(format='%.2f')})
    st.download_button('Baixar resumo por destino', csv_bytes(route_display), 'resumo_destinos.csv', 'text/csv')
    st.download_button('Baixar dados filtrados', csv_bytes(filtered), 'fretes_filtrados.csv', 'text/csv')
with tab2:
    st.subheader('Como o mix de destinos altera o orçamento?')
    st.write('Mantenha as tarifas históricas do recorte e altere a distribuição do volume. Os pesos do mix são normalizados automaticamente; não precisam somar 100.')
    volume = st.number_input('Volume do cenário (t)', min_value=0.0, value=float(round(weight, 2)))
    adjustment = st.number_input('Reajuste sobre as tarifas históricas (%)', min_value=-100.0, value=0.0, step=1.0)
    segments = routes.rename(columns={'destino_frete': 'destino'})[['destino', 'peso_t', 'tarifa_rs_t']].copy()
    segments['participacao'] = segments['peso_t'] / segments['peso_t'].sum() * 100
    editable = st.data_editor(segments[['destino', 'tarifa_rs_t', 'participacao']], disabled=['destino', 'tarifa_rs_t'], hide_index=True, width='stretch', key='mix',
                              column_config={'participacao': st.column_config.NumberColumn('Peso no mix', min_value=0.0), 'tarifa_rs_t': st.column_config.NumberColumn('Tarifa histórica R$/t', format='%.2f')})
    mix_parameters = {'segments': segments.to_dict('records'), 'volume_t': volume,
                      'mix': dict(zip(editable['destino'], editable['participacao'])),
                      'adjustment_pct': adjustment}
    try:
        scenario = volume_scenario(**mix_parameters)
        a, b = st.columns(2)
        a.metric('Custo estimado do cenário', f'R$ {br(scenario["custo_rs"])}')
        b.metric('Tarifa ponderada do cenário', f'R$ {br(scenario["tarifa_rs_t"])}/t')
        st.info(scenario['metodo'])
        scenario_export = scenario_payload(scenario, {'volume_t': volume, 'reajuste_pct': adjustment,
                           'mix': editable.to_dict('records'), 'periodo': [str(x) for x in dates],
                           'destinos_filtrados': destinations, 'tipos_carga_filtrados': cargo, 'somente_Z101': only_standard,
                           'categorias_filtradas': categories}, path.relative_to(ROOT))
        st.download_button('Baixar cenário', json.dumps(scenario_export, ensure_ascii=False, indent=2), 'cenario_mix.json', 'application/json')
        save_scenario('mix', mix_parameters, {
            'periodo': [str(x) for x in dates], 'destinos': destinations, 'cargas': cargo,
            'somente_Z101': only_standard, 'categorias': categories,
        }, str(path.relative_to(ROOT)), 'mix_scenario')
    except ValueError as exc:
        st.warning(str(exc))
with tab3:
    st.subheader('Composição estimada por viagem')
    st.info('Premissas ilustrativas e editáveis. Os valores abaixo não foram extraídos do histórico. A comparação de 6, 7 ou 9 eixos exige capacidades legais, consumo e custos verificados de cada configuração. Não há diagnóstico de conformidade ANTT neste simulador.')
    anp_path = ROOT / 'data/external/diesel.csv'
    if anp_path.exists():
        with st.expander('Referência histórica de diesel · ANP'):
            try:
                anp = pd.read_csv(anp_path, parse_dates=['data'])
                anp_state = st.selectbox('Estado da referência ANP', sorted(anp['localidade'].dropna().unique()))
                anp_product = st.selectbox('Produto da referência ANP', sorted(anp['produto'].dropna().unique()))
                anp_selected = anp[(anp['localidade'] == anp_state) & (anp['produto'] == anp_product)].sort_values('data')
                st.write('Série oficial de preço médio mensal por estado. Use-a como contexto histórico; o campo de diesel do cenário permanece editável e não é alterado automaticamente.')
                st.warning('Média mensal completa é retrospectiva: não representa o preço pago pela empresa nem uma variável do modelo. Agosto/2026 na ANP cobre o mês completo; o histórico operacional termina em 04/08/2026.')
                if not anp_selected.empty:
                    st.line_chart(anp_selected.set_index('data')[['preco_rs_l']].rename(columns={'preco_rs_l': 'Preço médio (R$/l)'}), y_label='Reais por litro', x_label='Mês')
                    st.dataframe(anp_selected.rename(columns={'data': 'Mês', 'localidade': 'Estado', 'produto': 'Produto', 'preco_rs_l': 'Preço médio (R$/l)', 'agregacao': 'Agregação', 'n_postos_pesquisados': 'Postos pesquisados', 'url_fonte': 'Fonte', 'data_coleta': 'Coleta'}), hide_index=True, width='stretch')
                    st.download_button('Baixar referência ANP selecionada', csv_bytes(anp_selected), 'referencia_diesel_anp.csv', 'text/csv')
                else:
                    st.info('Não há preços para a combinação de estado e produto selecionada.')
            except (ValueError, KeyError, pd.errors.ParserError) as exc:
                st.warning(f'Referência ANP indisponível ou incompleta: {exc}. O cenário manual continua disponível.')
    a, b, c = st.columns(3)
    with a:
        route = st.selectbox('Percurso', ['Somente ida', 'Ida e volta', 'Retorno para outro destino'])
        outbound = st.number_input('Distância de ida (km)', min_value=0.0, value=500.0)
        returning = 0.0
        if route != 'Somente ida':
            returning = st.number_input('Distância do retorno (km)', min_value=0.0,
                                        value=outbound if route == 'Ida e volta' else 0.0,
                                        key=f'return_distance_{route}')
        distance = outbound + returning
        st.caption(f'Distância total considerada: {br(distance)} km.')
        diesel = st.number_input('Diesel (R$/litro)', min_value=0.0, value=6.0)
        consumption = st.number_input('Rendimento (km/litro)', min_value=0.1, value=2.5)
    with b:
        capacity = st.number_input('Capacidade útil (t)', min_value=0.1, value=30.0)
        occupancy = st.number_input('Ocupação da capacidade (%)', min_value=0.1, max_value=100.0, value=85.0)
        toll = st.number_input('Pedágios da viagem (R$)', min_value=0.0, value=200.0)
    with c:
        other = st.number_input('Outros custos variáveis (R$/km)', min_value=0.0, value=1.0)
        fixed = st.number_input('Custos fixos alocados à viagem (R$)', min_value=0.0, value=300.0)
        margin = st.number_input('Acréscimo sobre o custo (%)', min_value=0.0, value=10.0)
    trip_parameters = {'distance_km': distance, 'diesel_rs_l': diesel, 'consumption_km_l': consumption,
                       'toll_rs': toll, 'capacity_t': capacity, 'utilization_pct': occupancy,
                       'other_rs_km': other, 'fixed_rs': fixed, 'margin_pct': margin}
    trip = component_scenario(**trip_parameters)
    a, b, c = st.columns(3)
    a.metric('Custo estimado da viagem', f'R$ {br(trip["custo_rs"])}')
    b.metric('Carga considerada', f'{br(trip["peso_t"])} t')
    c.metric('Tarifa estimada', f'R$ {br(trip["tarifa_rs_t"])}/t')
    st.bar_chart(pd.Series({k.replace('_rs', '').capitalize(): trip[k] for k in ['diesel_rs', 'pedagio_rs', 'outros_rs', 'acrescimo_rs']}, name='R$'))
    st.caption('Distância e pedágios devem cobrir o mesmo percurso, incluindo retorno quando aplicável. Outros custos podem incluir manutenção, pneus, depreciação e motorista. Acréscimo é markup sobre custo, não margem sobre receita.')
    trip_export = {'resultado': trip, 'premissas': {'distancia_km': distance, 'diesel_rs_l': diesel,
                   'rendimento_km_l': consumption, 'capacidade_t': capacity, 'ocupacao_pct': occupancy,
                   'pedagio_rs': toll, 'outros_rs_km': other, 'fixo_rs': fixed, 'acrescimo_pct': margin,
                   'percurso': route, 'ida_km': outbound, 'retorno_km': returning},
                   'observacao': 'Premissas fornecidas pelo usuário; não comprova conformidade legal.'}
    st.download_button('Baixar cenário por viagem', json.dumps(trip_export, ensure_ascii=False, indent=2), 'cenario_viagem.json', 'application/json')
    save_scenario('viagem', trip_parameters, {}, 'Premissas manuais de viagem', 'trip_scenario')
    st.subheader('Comparar configurações veiculares')
    st.write('Preencha capacidade útil, rendimento e pedágio de cada configuração com dados verificados. Zeros iniciais indicam informação pendente; não são premissas operacionais. Distância, diesel, ocupação, outros custos e acréscimo são os informados acima.')
    vehicles = st.data_editor(pd.DataFrame({'eixos': [6, 7, 9], 'capacidade_t': [0.0] * 3, 'rendimento_km_l': [0.0] * 3, 'pedagio_rs': [0.0] * 3}),
                             disabled=['eixos'], hide_index=True, width='stretch', key='vehicles',
                             column_config={'eixos': 'Eixos', 'capacidade_t': st.column_config.NumberColumn('Capacidade útil (t)', min_value=0.0),
                                            'rendimento_km_l': st.column_config.NumberColumn('Rendimento (km/l)', min_value=0.0),
                                            'pedagio_rs': st.column_config.NumberColumn('Pedágio (R$)', min_value=0.0)})
    comparisons = []
    for vehicle in vehicles.to_dict('records'):
        if valid_vehicle(vehicle):
            estimate = component_scenario(distance, diesel, vehicle['rendimento_km_l'], vehicle['pedagio_rs'], vehicle['capacidade_t'], occupancy, other, fixed, margin)
            comparisons.append({'eixos': vehicle['eixos'], 'carga_t': estimate['peso_t'], 'custo_viagem_rs': estimate['custo_rs'], 'tarifa_rs_t': estimate['tarifa_rs_t']})
    if comparisons:
        comparisons_frame = pd.DataFrame(comparisons).rename(columns={'eixos': 'Eixos', 'carga_t': 'Carga (t)', 'custo_viagem_rs': 'Custo por viagem (R$)', 'tarifa_rs_t': 'Tarifa estimada (R$/t)'})
        st.dataframe(comparisons_frame, hide_index=True, width='stretch')
        st.download_button('Baixar comparação veicular', csv_bytes(comparisons_frame), 'comparacao_veiculos.csv', 'text/csv')
        vehicle_export = scenario_payload(comparisons, {'viagem': trip_export['premissas'], 'veiculos': vehicles.astype(object).where(pd.notna(vehicles), None).to_dict('records')})
        st.download_button('Baixar premissas da comparação veicular', json.dumps(vehicle_export, ensure_ascii=False, indent=2), 'premissas_veiculos.json', 'application/json')
        st.caption('Comparação paramétrica; outros custos podem variar entre veículos e precisam ser refinados. Não verifica capacidade legal nem disponibilidade da rota.')
        incomplete_axles = [str(int(row['eixos'])) for row in vehicles.to_dict('records') if not valid_vehicle(row)]
        if incomplete_axles:
            st.caption(f'Configurações não calculadas por premissas incompletas ou inválidas: {", ".join(incomplete_axles)} eixos. Preencha capacidade e rendimento positivos e pedágio não negativo.')
    else:
        st.caption('Comparação pendente de premissas de pelo menos uma configuração.')
with tab4:
    st.subheader('Modelo preditivo e evidências')
    current_label = 'Atual · floresta com alvo em log · teste abril–agosto/2026'
    candidate_label = 'Candidata · floresta com alvo original · validação histórica'
    versions = {current_label: ROOT / 'models/frete_model.joblib'}
    candidate_path = ROOT / 'models/frete_candidate.joblib'
    if candidate_path.exists():
        versions[candidate_label] = candidate_path
        selected_version = st.radio('Versão da previsão', list(versions), index=0,
                                    help='A escolha altera somente a inferência nesta tela. Nenhum arquivo de modelo é substituído.')
    else:
        selected_version = current_label
    model_path = versions[selected_version]
    if selected_version == candidate_label:
        st.warning('Versão candidata experimental: avaliada em validação histórica até março/2026, sem confirmação futura independente. Sua seleção nesta tela não substitui o modelo atual e não autoriza adoção operacional. O teste abril–agosto/2026 já conhecido não seria confirmação independente.')
    else:
        st.warning('Previsão experimental: o modelo atual reduz o erro por item, mas subestima o custo agregado no teste. Ainda não deve substituir o orçamento sem revisão e calibração.')
    candidates = filtered[(filtered['CtgI'] == 'Z101') & (filtered['peso_liquido_t'] <= 40)]
    if 'flag_rateio_divergente' in candidates:
        candidates = candidates[pd.to_numeric(candidates['flag_rateio_divergente'], errors='coerce').eq(0)]
    if model_path.exists() and not candidates.empty:
        st.write('Use um item histórico como referência e altere seu peso. Escopo: categoria Z101, até 40 toneladas e rateio consistente.')
        search = st.text_input('Buscar item de referência', placeholder='Número do frete, destino ou nome do material')
        searched = candidates
        if search.strip():
            search_columns = [column for column in ['Nº frete', 'destino_frete', 'denominacao_principal'] if column in candidates]
            search_text = candidates[search_columns].fillna('').astype(str).agg(' '.join, axis=1)
            searched = candidates[search_text.str.contains(search.strip(), case=False, regex=False)]
        pages = max(1, ceil(len(searched) / 200))
        page = st.number_input('Página de exemplos', min_value=1, max_value=pages, value=1, step=1,
                               help='A paginação mantém todos os itens acessíveis sem carregar milhares de opções de uma só vez.')
        page_indices = list(searched.index[(page - 1) * 200:page * 200])
        st.caption(f'{br(len(searched), 0)} itens encontrados · página {page} de {pages}. Todos os itens podem ser acessados por busca ou paginação.')
        index = st.selectbox('Item de referência', page_indices,
                             format_func=lambda i: f'{filtered.loc[i, "destino_frete"]} · {filtered.loc[i, "tipo_carga"]} · {br(filtered.loc[i, "peso_liquido_t"])} t · frete {filtered.loc[i, "Nº frete"]}')
        if index is None:
            st.info('Nenhum item corresponde à busca. Ajuste o texto ou os filtros para usar o exemplo individual.')
        new_weight = st.number_input('Peso do item a prever (t)', min_value=0.001, max_value=40.0, value=float(filtered.loc[index, 'peso_liquido_t']) if index is not None else 1.0,
                                     help='Limite do escopo validado. Para outra categoria ou peso maior, é necessário novo estudo.')
        if st.button('Calcular previsão do modelo', disabled=index is None):
            try:
                from frete.modeling import prever_frete
                item = filtered.loc[[index]].copy()
                weight_ratio = new_weight / float(item.iloc[0]['peso_liquido_t'])
                item['peso_liquido_t'] = new_weight
                if 'peso_liquido_kg' in item:
                    item['peso_liquido_kg'] = new_weight * 1000
                if 'peso_bruto_kg' in item:
                    item['peso_bruto_kg'] = item['peso_bruto_kg'] * weight_ratio
                prediction = prever_frete(item, model_path=str(model_path))
                a, b = st.columns(2)
                a.metric('Tarifa prevista', f'R$ {br(float(prediction.iloc[0]["tarifa_prevista_rs_t"]))}/t')
                b.metric('Custo previsto', f'R$ {br(float(prediction.iloc[0]["custo_previsto_rs"]))}')
                st.caption(f'Previsão produzida pela versão selecionada: {selected_version}.')
                st.caption('O peso bruto acompanha proporcionalmente o peso líquido; demais características permanecem as do item selecionado. É uma análise exploratória e pode criar combinações pouco representadas no treino.')
            except (ValueError, ImportError, FileNotFoundError, KeyError) as exc:
                st.error(f'Não foi possível prever: {exc}')
    elif model_path.exists():
        st.info('Não há itens elegíveis para o modelo neste recorte. Selecione categoria Z101 com peso positivo de até 40 toneladas e rateio consistente.')
    else:
        st.caption('Modelo salvo ainda não disponível. O simulador histórico e paramétrico funciona independentemente dele.')
    with st.expander('Experimentos de modelagem do grupo'):
        st.caption('O resumo do grupo propôs árvore de decisão e Gradient Boosting para tarifa. A comparação usa cinco janelas até março de 2026 com as mesmas variáveis e itens da referência local.')
        benchmark = ROOT / 'reports/experimentos/benchmark_grupo_resumo.csv'
        folds = ROOT / 'reports/experimentos/benchmark_grupo_janelas.csv'
        if benchmark.exists() and folds.exists():
            model_labels = {'random_forest': 'Floresta aleatória', 'gradient_boosting': 'Gradient Boosting',
                            'arvore_decisao': 'Árvore de decisão'}
            scores = pd.read_csv(benchmark).assign(modelo=lambda frame: frame['modelo'].replace(model_labels))
            scores = scores.rename(columns={'modelo': 'Modelo', 'MAE_rs_t': 'MAE (R$/t)', 'RMSE_rs_t': 'RMSE (R$/t)',
                                             'WAPE_custo': 'WAPE de custo', 'R2': 'R²'})
            st.dataframe(scores[['Modelo', 'MAE (R$/t)', 'RMSE (R$/t)', 'WAPE de custo', 'R²']], hide_index=True,
                         column_config={'WAPE de custo': st.column_config.NumberColumn(format='percent')})
            windows = pd.read_csv(folds).assign(modelo=lambda frame: frame['modelo'].replace(model_labels))
            curves = windows.pivot(index='inicio_validacao', columns='modelo', values='MAE_rs_t').sort_index()
            st.line_chart(curves, x_label='Início da janela', y_label='MAE (R$/t)')
            st.download_button('Baixar métricas por janela', csv_bytes(windows), 'benchmark_grupo_janelas.csv', 'text/csv')
        else:
            st.info('Para gerar as métricas, execute python scripts/benchmark_group_models.py.')
        st.caption('O notebook 04_Experimentos_do_grupo reúne a trilha de custo em R$ por item e de classificação, com métricas próprias para cada tarefa.')
    summary_path = ROOT / 'reports/modelagem/resumo.json'
    if summary_path.exists():
        st.subheader('Avaliação do modelo atual · teste abril–agosto/2026')
        st.caption('As métricas desta tabela pertencem exclusivamente ao modelo atual com alvo em log, independentemente da versão escolhida para inferência acima. Não são métricas do candidato.')
        summary = json.loads(summary_path.read_text())
        scores = pd.DataFrame(summary['test'])
        scores = scores.rename(columns={'model': 'Modelo', 'MAE_rs_t': 'Erro médio absoluto (R$/t)', 'RMSE_rs_t': 'Raiz do erro quadrático (R$/t)', 'WAPE_tarifa': 'Erro relativo de tarifa (%)', 'WAPE_custo': 'Erro relativo de custo (%)', 'R2': 'R²', 'vies_total_custo': 'Viés do custo total (%)'})
        for column in ['Erro relativo de tarifa (%)', 'Erro relativo de custo (%)', 'Viés do custo total (%)']:
            scores[column] = scores[column] * 100
        scores['Modelo'] = scores['Modelo'].replace({'tarifa_orcada': 'Referência: tarifa orçada', 'random_forest': 'Floresta aleatória', 'hist_gradient_boosting': 'Árvores por gradiente', 'ridge_alpha1': 'Regressão Ridge (α=1)', 'ridge_alpha10': 'Regressão Ridge (α=10)'})
        st.caption(f'Modelo: {summary["selected_model"]} · treino: {summary["n_train"]:,} itens · teste: {summary["n_test"]:,} itens')
        st.dataframe(scores, hide_index=True, width='stretch',
                     column_config={column: st.column_config.NumberColumn(format='%.2f') for column in scores if column != 'Modelo'})
        st.download_button('Baixar métricas do teste', csv_bytes(scores), 'metricas_teste.csv', 'text/csv')
        baseline = next(x for x in summary['test'] if x['model'] == 'tarifa_orcada')
        winner = next(x for x in summary['test'] if x['model'] == summary['selected_model'])
        if summary.get('improves_MAE_and_WAPE'):
            st.success('O modelo supera a referência de tarifa orçada em MAE e WAPE no teste temporal.')
        else:
            st.warning('O modelo ainda não supera a referência em todos os critérios principais.')
        st.warning(f'Viés do custo total no teste: modelo {br(winner["vies_total_custo"] * 100)}%; referência {br(baseline["vies_total_custo"] * 100)}%. Valores negativos significam subestimação. Melhor erro por item não garante melhor total orçamentário.')
        st.caption(f'Itens do teste sem tarifa orçada direta: {summary.get("baseline_missing_test", "não informado")}. Consulte a metodologia sobre a imputação e a comparação retrospectiva.')
    else:
        st.write('Métricas ainda não geradas. Execute o treinamento para disponibilizar os resultados.')
    experiment_path = ROOT / 'reports/experimentos/vies_resumo.json'
    if experiment_path.exists():
        with st.expander('Experimentos de redução de viés'):
            experiment = json.loads(experiment_path.read_text())
            candidate_names = {
                'rf_original': 'Floresta aleatória · alvo original',
                'rf_log': 'Floresta aleatória · alvo em log',
                'rf_log_calibrated': 'Floresta aleatória · log + calibração',
                'rf_original_calibrated': 'Floresta aleatória · original + calibração',
                'hgb_original': 'Árvores por gradiente · alvo original',
                'hgb_original_calibrated': 'Árvores por gradiente · original + calibração',
                'ols_original': 'Regressão linear · alvo original',
                'ols_original_calibrated': 'Regressão linear · original + calibração',
            }
            st.write(f'Comparação interna de {len(experiment["candidate_summary"])} configurações em {experiment["folds"]} janelas temporais, usando somente histórico até {pd.Timestamp(experiment["last_date_allowed"]).strftime("%d/%m/%Y")} — anterior a abril/2026.')
            st.warning('Estes resultados são de validação interna. O modelo atual não foi substituído. O teste de abril a agosto/2026 já foi conhecido na modelagem anterior; uma nova avaliação nesse período será exploratória e não servirá como confirmação independente.')
            experiment_scores = pd.DataFrame(experiment['candidate_summary'])
            percentage_columns = ['WAPE_custo_mean', 'WAPE_custo_std', 'WAPE_tarifa_mean', 'abs_vies_mean', 'vies_mean']
            experiment_scores[percentage_columns] = experiment_scores[percentage_columns] * 100
            experiment_scores['candidate'] = experiment_scores['candidate'].map(lambda x: candidate_names.get(x, x))
            for guard in ['passes_MAE_guard', 'passes_bias_guard']:
                experiment_scores[guard] = experiment_scores[guard].map({True: 'Sim', False: 'Não'})
            experiment_scores = experiment_scores.rename(columns={
                'candidate': 'Configuração', 'MAE_mean': 'MAE médio (R$/t)', 'MAE_std': 'Desvio do MAE (R$/t)',
                'WAPE_custo_mean': 'Erro de custo médio (%)', 'WAPE_custo_std': 'Desvio do erro de custo (p.p.)',
                'WAPE_tarifa_mean': 'Erro de tarifa médio (%)', 'abs_vies_mean': 'Média do módulo do viés (%)',
                'vies_mean': 'Viés médio (%)', 'factor_mean': 'Fator de calibração médio',
                'passes_MAE_guard': 'Atende critério de MAE', 'passes_bias_guard': 'Atende critério de viés',
            })
            numeric_columns = [name for name in experiment_scores if name not in ['Configuração', 'Atende critério de MAE', 'Atende critério de viés']]
            st.dataframe(experiment_scores, hide_index=True, width='stretch',
                         column_config={name: st.column_config.NumberColumn(format='%.2f') for name in numeric_columns})
            selected_name = candidate_names.get(experiment['selected_candidate'], experiment['selected_candidate'])
            st.info(f'Candidato selecionado internamente: {selected_name}. Seleção pelo menor erro relativo de custo, respeitando os critérios de erro por item e viés.')
            st.caption('Critérios: MAE médio de até 110% da floresta com alvo em log e média do módulo do viés de até 5%. A média do módulo do viés não permite que sinais opostos se anulem. Calibração estima um fator nos dois últimos meses internos do treino, previstos sem acesso a esses meses no ajuste inicial.')
            st.caption('O painel apenas lê resultados já calculados; abrir esta seção não executa treinamento nem recalcula o experimento.')
            st.download_button('Baixar comparação de redução de viés', csv_bytes(experiment_scores), 'experimentos_reducao_vies.csv', 'text/csv')
    stability_path = ROOT / 'reports/estabilidade/resumo.json'
    if stability_path.exists():
        with st.expander('Estabilidade por período e segmento'):
            try:
                stability = json.loads(stability_path.read_text())
                st.write('Avaliação de estabilidade com previsões temporais fora da amostra de ajuste, dentro do histórico de desenvolvimento. Compara erros por mês, destino e faixa de peso.')
                st.warning('Resultados de desenvolvimento não são confirmação independente. O candidato continua experimental e não substitui o modelo atual do simulador.')
                model_names = {'rf_original': 'Floresta · alvo original', 'rf_log': 'Floresta · alvo em log', 'random_forest': 'Floresta · modelo atual'}
                labels = {'model': 'Modelo', 'n': 'Itens', 'volume_t': 'Volume (t)', 'MAE_rs_t': 'MAE (R$/t)',
                          'RMSE_rs_t': 'RMSE (R$/t)', 'WAPE_custo': 'Erro relativo de custo (%)',
                          'WAPE_tarifa': 'Erro relativo de tarifa (%)', 'vies_total_custo': 'Viés do custo (%)',
                          'supported': 'Amostra suficiente', 'bias_alert': 'Alerta de viés', 'error_alert': 'Alerta de erro', 'status': 'Situação'}
                def stability_table(records):
                    frame = pd.DataFrame(records)
                    for column in ['WAPE_custo', 'WAPE_tarifa', 'vies_total_custo']:
                        if column in frame:
                            frame[column] = frame[column] * 100
                    if 'model' in frame:
                        frame['model'] = frame['model'].map(lambda x: model_names.get(x, x))
                    for column in ['supported', 'bias_alert', 'error_alert']:
                        if column in frame:
                            frame[column] = frame[column].map({True: 'Sim', False: 'Não'})
                    if 'status' in frame:
                        frame['status'] = frame['status'].replace({'sem_alerta_nestes_criterios': 'Sem alerta nestes critérios', 'revisar': 'Revisar', 'amostra_insuficiente': 'Amostra insuficiente', 'insuficiente': 'Amostra insuficiente'})
                    return frame.rename(columns=labels)
                overall = stability_table(stability.get('overall', []))
                st.dataframe(overall, hide_index=True, width='stretch')
                st.caption(f'Período das previsões de desenvolvimento: {stability.get("oof_date_min", "não informado")} a {stability.get("oof_date_max", "não informado")}. Alertas requerem interpretação junto ao tamanho da amostra.')
                if stability.get('alerts'):
                    alert_summary = pd.DataFrame(stability['alerts'])
                    st.warning('Bom resultado agregado não demonstra estabilidade. Há segmentos com erros ou viés relevantes; segmentos com amostra insuficiente continuam inconclusivos.')
                    alert_summary = alert_summary[['dimension', 'model', 'supported_segments', 'segments_to_review', 'insufficient_segments', 'volume_fraction_supported']]
                    alert_summary['model'] = alert_summary['model'].map(lambda x: model_names.get(x, x))
                    alert_summary['dimension'] = alert_summary['dimension'].replace({'mes': 'Mês', 'destino': 'Destino', 'peso': 'Peso', 'mes_destino': 'Mês × destino', 'mes_peso': 'Mês × peso'})
                    alert_summary['volume_fraction_supported'] *= 100
                    alert_summary = alert_summary.rename(columns={'dimension': 'Recorte', 'model': 'Modelo', 'supported_segments': 'Segmentos com amostra suficiente', 'segments_to_review': 'Segmentos a revisar', 'insufficient_segments': 'Segmentos inconclusivos', 'volume_fraction_supported': 'Volume com amostra suficiente (%)'})
                    st.dataframe(alert_summary, hide_index=True, width='stretch')
                dimensions = {'por_mes': 'Mês', 'por_destino': 'Destino', 'por_peso': 'Faixa de peso',
                              'por_mes_destino': 'Mês e destino', 'por_mes_peso': 'Mês e faixa de peso'}
                available = {label: stability_path.parent / f'{stem}.csv' for stem, label in dimensions.items() if (stability_path.parent / f'{stem}.csv').exists()}
                if available:
                    dimension = st.selectbox('Detalhamento da estabilidade', list(available))
                    detail = pd.read_csv(available[dimension])
                    detail = stability_table(detail.to_dict('records')).rename(columns={'mes': 'Mês', 'destino_frete': 'Destino', 'faixa_peso': 'Faixa de peso'})
                    st.dataframe(detail, hide_index=True, width='stretch')
                    st.download_button('Baixar estabilidade do segmento', csv_bytes(detail), 'estabilidade_segmento.csv', 'text/csv')
                st.download_button('Baixar resumo de estabilidade', stability_path.read_bytes(), 'estabilidade_resumo.json', 'application/json')
                with st.expander('Critérios dos alertas de estabilidade'):
                    st.json(stability.get('criteria', {}))
            except (ValueError, TypeError, KeyError, pd.errors.ParserError) as exc:
                st.warning(f'Relatório de estabilidade indisponível ou incompleto: {exc}. Os demais recursos continuam disponíveis.')
    st.markdown('**Como o modelo foi avaliado**')
    st.write('Treino: janeiro/2025 a março/2026. Teste: abril a agosto/2026, preservado na escolha do modelo. A seleção usa janelas temporais dentro do treino, sem compartilhar o mesmo frete entre treino e teste. Custos realizados, impostos e flags derivados do alvo não entram como preditores. A data de liquidação é uma aproximação da data operacional.')
    st.caption('Erro médio absoluto informa o erro típico em R$/t; erro relativo de custo considera o peso de cada item; viés mostra a direção do erro no total. Melhorar a primeira medida não assegura melhorar a terceira.')
    st.markdown('''**Como ler os resultados**

- Tarifa ponderada = soma dos valores / soma das toneladas; não é a média simples das tarifas.
- O orçamento ajustado usa tarifa orçada × volume realizado, somente onde existe tarifa.
- A referência orçada é de 2026; aplicada a 2025, serve apenas como comparação retrospectiva. Destino é uma aproximação pelo representante.
- O cenário de mix repondera o histórico e não representa uma previsão causal.
- O cenário por viagem é uma estimativa com premissas editáveis, separada do modelo estatístico.
- Dados históricos terminam em 04/08/2026; períodos incompletos exigem cuidado.
- Nenhuma tela comprova conformidade com o piso ANTT sem as informações da operação e a norma aplicável.
''')
    with st.expander('Triagem documental do piso mínimo ANTT'):
        st.write('Esta triagem recebe cadastros previamente validados. Sem as informações completas e coeficientes com vigência e proveniência, o resultado é “não avaliável”. Não há coeficientes oficiais preenchidos automaticamente.')
        operation_file = st.file_uploader('Operação em JSON', type=['json'], key='operation')
        coefficient_file = st.file_uploader('Lista de coeficientes em JSON', type=['json'], key='coefficients')
        if st.button('Executar triagem documental'):
            try:
                from frete.compliance import avaliar_piso
                operation = json.load(operation_file) if operation_file else {}
                coefficients = json.load(coefficient_file) if coefficient_file else []
                if not isinstance(operation, dict) or not isinstance(coefficients, list):
                    raise ValueError('Operação deve ser objeto e coeficientes devem ser lista JSON.')
                st.json(avaliar_piso(operation, coefficients))
            except (ValueError, TypeError, ImportError, AttributeError) as exc:
                st.error(f'Cadastro inválido: {exc}')
with tab5:
    st.subheader('Qualidade e cobertura do recorte')
    st.write('As ocorrências abaixo usam o recorte dos filtros antes de excluir custos ou pesos não positivos. Flags podem coexistir: somá-las não representa a quantidade de itens problemáticos.')
    a, b, c = st.columns(3)
    a.metric('Itens antes das exclusões analíticas', br(len(scope), 0))
    b.metric('Itens excluídos dos indicadores', br(len(scope) - len(filtered), 0))
    c.metric('Sem tarifa orçada direta', br(int((scope['tarifa_orcada_rs_t'].isna() | (scope['tarifa_orcada_rs_t'] <= 0)).sum()), 0))
    flag_names = {'flag_valor_zero': 'Valor de frete zerado', 'flag_rateio_divergente': 'Divergência no rateio', 'flag_ctgi_nao_padrao': 'Categoria diferente de Z101', 'flag_outlier_rs_t': 'Tarifa fora dos percentis descritivos 1–99'}
    quality = []
    for key, label in flag_names.items():
        count = int(pd.to_numeric(scope[key], errors='coerce').fillna(0).sum()) if key in scope else 0
        quality.append({'Verificação': label, 'Itens': count, 'Participação (%)': 100 * count / len(scope)})
    quality.extend([
        {'Verificação': 'Destino não informado', 'Itens': int(scope['destino_frete'].eq('NAO_INFORMADO').sum()), 'Participação (%)': 100 * scope['destino_frete'].eq('NAO_INFORMADO').mean()},
        {'Verificação': 'Peso do item acima de 40 t', 'Itens': int(scope['peso_liquido_t'].gt(40).sum()), 'Participação (%)': 100 * scope['peso_liquido_t'].gt(40).mean()},
    ])
    quality = pd.DataFrame(quality)
    st.dataframe(quality, hide_index=True, width='stretch', column_config={'Participação (%)': st.column_config.NumberColumn(format='%.2f')})
    st.download_button('Baixar diagnóstico de qualidade', csv_bytes(quality), 'qualidade_recorte.csv', 'text/csv')
    st.info('As flags são alertas para investigação. A análise mantém divergências e tarifas extremas; não há exclusão silenciosa por esses alertas. O modelo tem escopo próprio: Z101, valor/peso positivos, até 40 t e rateio consistente.')
    st.subheader('O que os dados permitem concluir')
    st.markdown('''- **Observado:** valores de frete, pesos, materiais e datas de liquidação.
- **Referência:** tarifas e volumes do orçamento de 2026.
- **Aproximação:** destino obtido do cadastro do representante; não é rota origem–destino medida.
- **Ausente:** distância operacional, configuração veicular, consumo, pedágio e enquadramento ANTT por viagem.
- **Cenários:** componentes faltantes são premissas declaradas pelo usuário, separadas dos fatos históricos.
''')
    audit_path = ROOT / 'data/processed/auditoria.json'
    if audit_path.exists():
        with st.expander('Auditoria completa da base e rastreabilidade'):
            audit = json.loads(audit_path.read_text())
            st.caption('Resumo da base completa, independente dos filtros; hashes identificam os arquivos-fonte usados no processamento.')
            st.json(audit)
            st.download_button('Baixar auditoria completa', audit_path.read_bytes(), 'auditoria.json', 'application/json')
