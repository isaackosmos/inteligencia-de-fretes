"""Cenários permanecem exclusivamente no estado da sessão do navegador."""
import json
import pandas as pd
import streamlit as st
from frete.scenario_store import ScenarioStore, MAX_SCENARIOS, MAX_JSON_BYTES


def session_store():
    return ScenarioStore(st.session_state.get('saved_scenarios', []))


def commit(store):
    st.session_state['saved_scenarios'] = store.list()


def save_scenario(kind, parameters, scope, origin, key):
    """Mostra salvamento imediatamente junto ao cenário que o usuário calculou."""
    with st.expander('Guardar este cenário na sessão'):
        name = st.text_input('Nome do cenário', value='Cenário de mix' if kind == 'mix' else 'Cenário de viagem', key=f'{key}_name')
        if st.button('Guardar cenário de mix' if kind == 'mix' else 'Guardar cenário de viagem', key=f'{key}_save'):
            try:
                store = session_store()
                scenario = store.create(kind=kind, name=name, parameters=parameters, scope=scope, origin=origin)
                commit(store)
                st.success(f'Cenário “{scenario["name"]}” guardado nesta sessão. Abra a aba Cenários salvos para comparar ou exportar.')
            except ValueError as exc:
                st.warning(f'Não foi possível guardar o cenário: {exc}')


def render_scenario_manager(br):
    st.subheader('Cenários salvos nesta sessão')
    st.write(f'Guarde até {MAX_SCENARIOS} cenários de mix ou viagem, compare alternativas e exporte um arquivo para continuar depois. Os dados não são gravados pelo aplicativo em disco; encerrar a sessão pode apagá-los.')
    store = session_store()
    with st.expander('Importar cenários em JSON'):
        st.caption(f'Formato versionado do aplicativo; limite de {MAX_JSON_BYTES // 1000} kB. Resultados importados são recalculados a partir das premissas, sem confiar nos totais do arquivo.')
        upload = st.file_uploader('Arquivo de cenários', type=['json'], key='scenario_upload')
        pasted = st.text_area('Ou cole o JSON de cenários', key='scenario_pasted', height=100)
        if upload is not None and pasted.strip():
            st.info('O arquivo selecionado terá prioridade sobre o texto colado.')
        if st.button('Importar cenários', disabled=upload is None and not pasted.strip()):
            try:
                payload = upload.getvalue() if upload is not None else pasted.encode('utf-8')
                previous = len(store.list())
                store.import_json(payload)
                commit(store)
                st.success(f'{len(store.list()) - previous} cenários importados e recalculados.')
            except ValueError as exc:
                st.error(f'Não foi possível importar: {exc}. Nenhum cenário da sessão foi alterado.')
    scenarios = store.list()
    if not scenarios:
        st.info('Nenhum cenário guardado. Calcule um cenário nas abas de mix ou viagem e use “Guardar este cenário na sessão”. Você também pode importar um JSON exportado anteriormente.')
        return
    rows = [{'id': x['id'], 'Nome': x['name'], 'Tipo': 'Mix de destinos' if x['kind'] == 'mix' else 'Viagem',
             'Custo (R$)': x['result']['custo_rs'], 'Tarifa (R$/t)': x['result']['tarifa_rs_t'],
             'Criado em UTC': x['created_at_utc']} for x in scenarios]
    st.dataframe(pd.DataFrame(rows).drop(columns='id'), hide_index=True, width='stretch',
                 column_config={'Custo (R$)': st.column_config.NumberColumn(format='%.2f'), 'Tarifa (R$/t)': st.column_config.NumberColumn(format='%.2f')})
    st.download_button('Exportar cenários da sessão', store.export_json(), 'cenarios_frete_v1.json', 'application/json')
    by_id = {x['id']: x for x in scenarios}
    label = lambda scenario_id: f'{by_id[scenario_id]["name"]} · {"mix" if by_id[scenario_id]["kind"] == "mix" else "viagem"} · {scenario_id[:8]}'
    with st.expander('Remover cenário da sessão'):
        remove_id = st.selectbox('Cenário a remover', list(by_id), format_func=label)
        if st.button('Remover somente da sessão'):
            store.remove(remove_id)
            commit(store)
            st.rerun()
    if len(scenarios) < 2:
        st.info('Guarde pelo menos dois cenários para comparar alternativas.')
        return
    st.subheader('Comparar alternativas')
    st.caption('Comparações exigem o mesmo tipo de cenário, origem e escopo. Para volumes diferentes, ative explicitamente a normalização.')
    base_id = st.selectbox('Cenário base', list(by_id), format_func=label)
    alternative_id = st.selectbox('Cenário alternativo', [x for x in by_id if x != base_id], format_func=label)
    normalize = st.checkbox('Comparar com volume comum', value=False)
    common_volume = st.number_input('Volume comum da comparação (t)', min_value=0.001, value=100.0) if normalize else None
    try:
        comparison = store.compare(base_id, alternative_id, normalize_volume_t=common_volume)
        a, b, c = st.columns(3)
        a.metric('Custo do cenário base', f'R$ {br(comparison["base"]["custo_rs"])}')
        b.metric('Custo do cenário alternativo', f'R$ {br(comparison["alternative"]["custo_rs"])}')
        c.metric('Diferença alternativa − base', f'R$ {br(comparison["delta_custo_rs"])}')
        st.caption(f'Volume comparável: {br(comparison["volume_t"])} t · diferença de tarifa: R$ {br(comparison["delta_tarifa_rs_t"])}/t.')
        if comparison.get('decomposition'):
            decomposition = pd.DataFrame(comparison['decomposition']).rename(columns={'component': 'Componente', 'base_rs': 'Base (R$)', 'alternative_rs': 'Alternativa (R$)', 'delta_rs': 'Diferença (R$)'})
            st.dataframe(decomposition, hide_index=True, width='stretch')
        for warning in comparison.get('warnings', []):
            st.warning(warning)
        st.info(comparison['interpretation'])
        st.download_button('Baixar comparação de cenários', json.dumps(comparison, ensure_ascii=False, indent=2), 'comparacao_cenarios.json', 'application/json')
    except ValueError as exc:
        st.warning(f'Comparação indisponível: {exc}. Escolha cenários compatíveis ou revise a normalização.')
