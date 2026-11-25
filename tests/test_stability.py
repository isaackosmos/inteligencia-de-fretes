"""Estabilidade exige diagnóstico local e previsões temporalmente honestas."""
import unittest
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
from frete.stability import eligible_history, generate_oof, segment_metrics

class StabilityTests(unittest.TestCase):
    def test_opposing_segment_bias_is_not_hidden_by_overall_average(self):
        df = pd.DataFrame({"model": ["rf_original"] * 200, "destino_frete": ["A"] * 100 + ["B"] * 100, "frete_rs_t": [100.] * 200, "previsto_rs_t": [120.] * 100 + [80.] * 100, "peso_liquido_t": [2.] * 200})
        overall = segment_metrics(df, []).iloc[0]
        local = segment_metrics(df, ["destino_frete"])
        self.assertAlmostEqual(overall.vies_total_custo, 0)
        self.assertTrue(local.bias_alert.all())
        self.assertTrue(local.status.eq("revisar").all())

    def test_small_segment_never_receives_no_alert_status(self):
        df = pd.DataFrame({"model": ["rf_original"] * 5, "frete_rs_t": [100.] * 5, "previsto_rs_t": [100.] * 5, "peso_liquido_t": [40.] * 5})
        row = segment_metrics(df, []).iloc[0]
        self.assertFalse(row.supported)
        self.assertEqual(row.status, "amostra_insuficiente")

    def test_cost_bias_respects_volume(self):
        df = pd.DataFrame({"model": ["rf_original"] * 2, "frete_rs_t": [100., 200.], "previsto_rs_t": [110., 190.], "peso_liquido_t": [1., 9.]})
        row = segment_metrics(df, []).iloc[0]
        self.assertAlmostEqual(row.vies_total_custo, -80 / 1900)
        self.assertAlmostEqual(row.WAPE_custo, 100 / 1900)

    def test_oof_models_never_see_validation_dates_or_freights(self):
        dates = pd.date_range("2025-01-01", "2026-03-01", freq="MS")
        df = pd.DataFrame({"Dta.liq.": dates.repeat(2).strftime("%Y-%m-%d"), "Nº frete": [f"f{i}" for i in range(30)], "Item": [1] * 30, "destino_frete": ["A"] * 30, "frete_rs_t": [100.] * 30, "peso_liquido_t": [2.] * 30})
        df.loc[0, "Nº frete"] = df.loc[10, "Nº frete"] = "cross"
        observed = []

        def fit(name, rows):
            def predict(x):
                val = df.loc[x.index]
                self.assertLess(pd.to_datetime(rows["Dta.liq."]).max(), pd.to_datetime(val["Dta.liq."]).min())
                self.assertTrue(set(rows["Nº frete"]).isdisjoint(val["Nº frete"]))
                self.assertNotIn("frete_rs_t", x)
                observed.append((name, len(val)))
                return np.full(len(x), 100.)
            return Mock(predict=predict)

        with patch("frete.stability.fit_candidate", side_effect=fit):
            oof, folds = generate_oof(df)
        self.assertEqual(len(observed), 10)
        self.assertEqual(len(oof), 48)
        self.assertFalse(oof.duplicated(["model", "Nº frete", "Item"]).any())
        self.assertEqual(oof.mes.min(), "2025-04")
        self.assertEqual(oof.mes.max(), "2026-03")
        self.assertEqual(folds.groupby("model").size().tolist(), [5, 5])

    def test_oof_refuses_holdout_even_if_caller_forgets_filter(self):
        df = pd.DataFrame({"Dta.liq.": ["2026-04-01"]})
        with patch("frete.stability.fit_candidate") as fit:
            with self.assertRaises(ValueError):
                generate_oof(df)
            fit.assert_not_called()

    def test_history_excludes_future_and_out_of_scope_rows(self):
        df = pd.DataFrame({"Dta.liq.": ["2026-03-01", "2026-04-01", "2026-03-01"], "CtgI": ["Z101", "Z101", "Z220"], "frete_rs_t": [100., 999999., 100.], "peso_liquido_t": [2.] * 3, "flag_rateio_divergente": [0] * 3})
        result = eligible_history(df)
        self.assertEqual(result.index.tolist(), [0])

if __name__ == "__main__":
    unittest.main()
