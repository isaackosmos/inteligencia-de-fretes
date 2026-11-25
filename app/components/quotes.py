"""Fluxo demonstrativo de cotação e consulta por código ou QR."""
from io import BytesIO
import os
from urllib.parse import urlencode, urlsplit

import streamlit as st

from frete.quotes import STATUSES, estimate_quote


def show_quote(quote, br):
    st.write(f'**{quote["destination"]} · {quote["cargo"]}**')
    a, b, c = st.columns(3)
    a.metric('Peso cotado', f'{br(quote["weight_t"])} t')
    b.metric('Tarifa de referência', f'R$ {br(quote["tariff"])}/t')
    c.metric('Custo indicativo', f'R$ {br(quote["cost"])}')
    st.caption(f'Tarifa ponderada de {quote["sample"]} itens do recorte. Estimativa histórica demonstrativa.')


def render_lookup(store, br, initial_code=''):
    st.title('Consulta de fretes')
    st.caption('Visão demonstrativa do motorista. Consulte uma cotação cadastrada nesta instalação.')
    with st.form('quote_lookup'):
        code = st.text_input('Código do frete', value=initial_code, max_chars=36)
        submitted = st.form_submit_button('Consultar frete')
    if submitted or initial_code:
        quote = store.get(code)
        if quote is None:
            st.info('Código não localizado nesta instalação.')
        else:
            st.code(quote['code'])
            st.write(f'**Status** · {quote["status"]}')
            show_quote(quote, br)


def qr_payload(code):
    base = os.environ.get('FRETE_URL_CONSULTA', '').strip()
    url = urlsplit(base)
    if url.scheme in {'http', 'https'} and url.netloc and not url.query and not url.fragment:
        return f'{base}?{urlencode({"cotacao": code})}'
    return code


def render_quotes(history, store, br):
    st.subheader('Cotação rápida por destino e carga')
    st.caption('Visão demonstrativa da empresa. A referência usa os filtros da análise. Cotações cadastradas ficam no banco local e podem ser consultadas por código.')
    options = history.dropna(subset=['destino_frete', 'tipo_carga'])
    options = options[options['destino_frete'].ne('NAO_INFORMADO')]
    if not options.empty:
        destination = st.selectbox('Destino da cotação', sorted(options['destino_frete'].unique()))
        cargos = sorted(options.loc[options['destino_frete'].eq(destination), 'tipo_carga'].unique())
        cargo = st.selectbox('Carga da cotação', cargos)
        with st.form('quote_create'):
            weight = st.number_input('Peso da cotação (t)', min_value=0.001, value=15.0, format='%.3f')
            submitted = st.form_submit_button('Calcular cotação')
        if submitted:
            st.session_state.pop('quote_estimate', None)
            st.session_state.pop('quote_code', None)
            try:
                st.session_state['quote_estimate'] = estimate_quote(history, destination, cargo, weight)
            except ValueError as exc:
                st.warning(str(exc))
        estimate = st.session_state.get('quote_estimate')
        if estimate:
            st.markdown('**Última cotação calculada**')
            show_quote(estimate, br)
            if not st.session_state.get('quote_code') and st.button('Cadastrar e gerar código'):
                st.session_state['quote_code'] = store.create(estimate)
    else:
        st.info('Ajuste os filtros para encontrar um destino com tipo de carga informado.')

    with st.expander('Reabrir cotação cadastrada'):
        with st.form('quote_reopen'):
            saved_code = st.text_input('Código cadastrado', max_chars=36)
            if st.form_submit_button('Reabrir cotação'):
                saved_quote = store.get(saved_code)
                if saved_quote is None:
                    st.info('Código não localizado nesta instalação.')
                else:
                    st.session_state['quote_code'] = saved_quote['code']

    code = st.session_state.get('quote_code')
    if not code:
        return
    quote = store.get(code)
    if quote is None:
        return
    st.markdown('**Cotação cadastrada**')
    st.code(code)
    show_quote(quote, br)
    with st.form('quote_status', clear_on_submit=True):
        status = st.selectbox('Status da cotação', STATUSES, index=STATUSES.index(quote['status']))
        if st.form_submit_button('Atualizar status'):
            store.set_status(code, status)
            st.success(f'Status atualizado para {status}.')
    try:
        import qrcode
    except ImportError:
        st.info('Instale qrcode para exibir o QR. O código acima já permite consulta.')
        return
    payload = qr_payload(code)
    image = BytesIO()
    qrcode.make(payload).save(image, format='PNG')
    png = image.getvalue()
    st.image(png, caption='QR da cotação', width=200)
    st.download_button('Baixar QR', png, f'{code}.png', 'image/png')
    if payload == code:
        st.caption('O QR contém o código. Leia-o com a câmera e cole o texto na tela Consulta do motorista.')
    else:
        st.caption('O QR abre a consulta na instalação indicada.')
