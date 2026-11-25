"""Smoke tests da interface e reatividade dos cenários."""
import unittest
from pathlib import Path
from datetime import date
import json
import pandas as pd
from streamlit.testing.v1 import AppTest
from frete.dashboard_helpers import filter_period, monthly_comparison, scenario_payload, valid_vehicle


class DashboardTests(unittest.TestCase):
    def test_filters_and_volume_scenario(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app/dashboard.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.tabs), 5)
        original = next(x.value for x in app.metric if x.label == 'Custo estimado do cenário')
        volume = next(x for x in app.number_input if x.label == 'Volume do cenário (t)')
        volume.set_value(0).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x.value for x in app.metric if x.label == 'Custo estimado do cenário'), 'R$ 0,00')
        self.assertNotEqual(original, 'R$ 0,00')
        app.multiselect[0].set_value(['Guarapuava']).run()
        self.assertFalse(app.exception)
        self.assertLess(int(next(x.value for x in app.metric if x.label == 'Itens no recorte').replace('.', '')), 29477)

    def test_saved_model_and_incomplete_compliance(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        if (root / 'models/frete_model.joblib').exists():
            next(x for x in app.button if x.label == 'Calcular previsão do modelo').click().run()
            self.assertFalse(app.exception)
            self.assertTrue(any(x.label == 'Tarifa prevista' for x in app.metric))
        next(x for x in app.button if x.label == 'Executar triagem documental').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any('nao_avaliavel' in x.value for x in app.json))

    def test_prediction_scope_and_quality(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        weight_input = next((x for x in app.number_input if x.label == 'Peso do item a prever (t)'), None)
        if weight_input is not None:
            self.assertEqual(weight_input.max, 40.0)
            weight_input.set_value(40.0).run()
            next(x for x in app.button if x.label == 'Calcular previsão do modelo').click().run()
            self.assertFalse(app.exception)
        self.assertTrue(any(x.label == 'Itens excluídos dos indicadores' for x in app.metric))
        app.checkbox[0].set_value(False).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x.value for x in app.metric if x.label == 'Itens antes das exclusões analíticas'), '29.860')

    def test_bias_experiments_are_internal_evidence(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / 'reports/experimentos/vies_resumo.json').exists():
            self.skipTest('Resultados opcionais do experimento ainda não gerados.')
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label == 'Experimentos de redução de viés' for x in app.expander))
        table = next(x.value for x in app.dataframe if 'Configuração' in x.value.columns)
        self.assertEqual(len(table), 8)
        self.assertTrue(table['Erro de custo médio (%)'].between(0, 100).all())
        self.assertGreater(table['Erro de custo médio (%)'].min(), 1)
        self.assertTrue(any('modelo atual não foi substituído' in x.value for x in app.warning))
        self.assertTrue(any('não servirá como confirmação independente' in x.value for x in app.warning))

    def test_empty_and_incomplete_period(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        app.date_input[0].set_value((date(2025, 1, 2),)).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Selecione a data inicial e a data final' in x.value for x in app.info))
        self.assertEqual(len(app.metric), 0)
        app.date_input[0].set_value((date(2025, 1, 1), date(2025, 1, 1))).run()
        self.assertFalse(app.exception)
        self.assertTrue(any('Nenhum registro' in x.value for x in app.info))
        app.date_input[0].set_value((date(2025, 1, 2), date(2025, 1, 2))).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label == 'Itens no recorte' for x in app.metric))

    def test_without_budget_and_out_of_model_category(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        app.multiselect[0].set_value(['Francisco Beltrao']).run()
        self.assertFalse(app.exception)
        self.assertEqual(next(x.value for x in app.metric if x.label == 'Desvio contra a meta'), 'Sem referência')
        self.assertTrue(any('comparação mensal indisponível' in x.value for x in app.info))
        app.multiselect[0].set_value([]).run()
        app.checkbox[0].set_value(False).run()
        next(x for x in app.multiselect if x.label == 'Categorias de item').set_value(['Z220']).run()
        self.assertFalse(app.exception)
        self.assertFalse(any(x.label == 'Calcular previsão do modelo' for x in app.button))
        self.assertTrue(any('Não há itens elegíveis' in x.value for x in app.info))

    def test_zero_mix_shows_error_and_no_cost(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        mix_frame = next(x.value for x in app.dataframe if 'participacao' in x.value.columns)
        app.session_state['mix'] = {'edited_rows': {i: {'participacao': 0.0} for i in range(len(mix_frame))}, 'added_rows': [], 'deleted_rows': []}
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any('ao menos uma participação positiva' in x.value for x in app.warning))
        self.assertFalse(any(x.label == 'Custo estimado do cenário' for x in app.metric))

    def test_optional_anp_and_stability_do_not_retrain_or_change_diesel(self):
        root = Path(__file__).resolve().parents[1]
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        self.assertFalse(app.exception)
        diesel_before = next(x.value for x in app.number_input if x.label == 'Diesel (R$/litro)')
        if (root / 'data/external/diesel.csv').exists():
            states = next(x for x in app.selectbox if x.label == 'Estado da referência ANP')
            states.set_value(states.options[-1]).run()
            self.assertFalse(app.exception)
            self.assertEqual(next(x.value for x in app.number_input if x.label == 'Diesel (R$/litro)'), diesel_before)
            self.assertTrue(any('mês completo' in x.value for x in app.warning))
        if (root / 'reports/estabilidade/resumo.json').exists():
            self.assertTrue(any(x.label == 'Estabilidade por período e segmento' for x in app.expander))
            self.assertTrue(any('candidato continua experimental' in x.value for x in app.warning))

    def test_candidate_version_is_explicit_and_separate_from_test_metrics(self):
        root = Path(__file__).resolve().parents[1]
        if not (root / 'models/frete_candidate.joblib').exists():
            self.skipTest('Artefato candidato opcional ainda não gerado.')
        app = AppTest.from_file(str(root / 'app/dashboard.py'), default_timeout=30).run()
        version = next(x for x in app.radio if x.label == 'Versão da previsão')
        self.assertIn('Atual', version.value)
        version.set_value(version.options[1]).run()
        next(x for x in app.button if x.label == 'Calcular previsão do modelo').click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label == 'Tarifa prevista' for x in app.metric))
        self.assertTrue(any('candidata experimental' in x.value for x in app.warning))
        self.assertTrue(any('Não são métricas do candidato' in x.value for x in app.caption))
        self.assertTrue(any('Candidata' in x.value and 'Previsão produzida' in x.value for x in app.caption))


class DashboardCalculationTests(unittest.TestCase):
    def test_period_validation_and_complete_last_day(self):
        frame = pd.DataFrame({'Dta.liq.': pd.to_datetime(['2025-01-02 15:00', '2025-01-03 00:00'])})
        self.assertEqual(len(filter_period(frame, (date(2025, 1, 2), date(2025, 1, 2)))), 1)
        for dates in [(date(2025, 1, 3), date(2025, 1, 2)), (), (date(2025, 1, 2),)]:
            with self.assertRaises(ValueError):
                filter_period(frame, dates)

    def test_monthly_common_sample_excludes_missing_budget(self):
        frame = pd.DataFrame({'Dta.liq.': pd.to_datetime(['2026-01-02'] * 3), 'Item': [1, 2, 3],
                              'peso_liquido_t': [1, 9, 100], 'Valor líquido': [100, 1800, 90000],
                              'tarifa_orcada_rs_t': [110, 210, float('nan')]})
        result = monthly_comparison(frame).iloc[0]
        self.assertEqual(result['itens'], 2)
        self.assertEqual(result['peso_t'], 10)
        self.assertEqual(result['Realizado · R$/t'], 190)
        self.assertEqual(result['Meta ajustada · R$/t'], 200)
        self.assertAlmostEqual(result['desvio_pct'], -5)

    def test_incomplete_vehicle_and_export_contract(self):
        self.assertFalse(valid_vehicle({'capacidade_t': 30, 'rendimento_km_l': 3, 'pedagio_rs': float('nan')}))
        self.assertFalse(valid_vehicle({'capacidade_t': None, 'rendimento_km_l': 3, 'pedagio_rs': 0}))
        self.assertTrue(valid_vehicle({'capacidade_t': 30, 'rendimento_km_l': 3, 'pedagio_rs': 0}))
        payload = scenario_payload({'custo_rs': 123}, {'volume_t': 2, 'mix': [{'destino': 'A', 'participacao': 1}], 'periodo': ['2026-01-01', '2026-01-31']}, 'data/test.csv')
        self.assertEqual(json.loads(json.dumps(payload))['premissas']['volume_t'], 2)
        self.assertEqual(payload['fonte'], 'data/test.csv')


if __name__ == '__main__':
    unittest.main()
