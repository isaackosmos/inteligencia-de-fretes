"""Regressões do fluxo integrado de cotação, consulta e viagem."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

from frete.quotes import QuoteStore

ROOT = Path(__file__).resolve().parents[1]


def element(elements, label):
    return next(item for item in elements if item.label == label)


def dashboard():
    return AppTest.from_file(str(ROOT / 'app/dashboard.py'), default_timeout=30)


def test_quote_is_consultable_from_a_new_session(tmp_path, monkeypatch):
    database = tmp_path / 'quotes.sqlite3'
    monkeypatch.setenv('FRETE_COTACOES_DB', str(database))
    monkeypatch.setenv('FRETE_URL_CONSULTA', 'https://example.test/frete/')
    company = dashboard().run()
    element(company.radio, 'Área de trabalho').set_value('Cotação da empresa').run()
    element(company.button, 'Calcular cotação').click().run()
    element(company.button, 'Cadastrar e gerar código').click().run()
    assert not company.exception
    code = company.code[0].value
    quote = QuoteStore(database).get(code)
    assert quote['cost'] == quote['weight_t'] * quote['tariff']
    assert quote['sample'] > 0 and quote['status'] == 'Disponível'
    assert company.get('imgs')
    assert any('O QR abre a consulta' in entry.value for entry in company.caption)

    element(company.selectbox, 'Status da cotação').set_value('Em transporte')
    element(company.button, 'Atualizar status').click().run()
    assert not company.exception
    assert QuoteStore(database).get(code)['status'] == 'Em transporte'

    driver = dashboard()
    driver.query_params['cotacao'] = code
    driver.run()
    assert not driver.exception
    assert driver.code[0].value == code
    assert any('Em transporte' in entry.value for entry in driver.markdown)
    assert element(driver.metric, 'Custo indicativo').value


def test_return_distance_changes_trip_cost_and_can_be_saved():
    app = dashboard().run()
    original = element(app.metric, 'Custo estimado da viagem').value
    element(app.selectbox, 'Percurso').set_value('Ida e volta').run()
    assert not app.exception
    outbound = element(app.number_input, 'Distância de ida (km)').value
    assert element(app.number_input, 'Distância do retorno (km)').value == outbound
    assert element(app.metric, 'Custo estimado da viagem').value != original
    element(app.button, 'Guardar cenário de viagem').click().run()
    element(app.radio, 'Área de trabalho').set_value('Cenários salvos').run()
    assert not app.exception
    assert app.dataframe[0].value.iloc[0]['Tipo'] == 'Viagem'
