"""Proteções contra vazamento e calibração incompatível com desembolso."""
import unittest
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
from frete.experiments import calibration_factor


def history():
    # Um frete cruza janeiro/fevereiro e deve sair do ajuste auxiliar.
    return pd.DataFrame({
        "Dta.liq.": ["2025-01-15"] * 120 + ["2025-02-15"] * 100 + ["2025-03-15"] * 100,
        "Nº frete": ["cross"] + [f"train_{i}" for i in range(119)] + ["cross"] + [f"feb_{i}" for i in range(99)] + [f"mar_{i}" for i in range(100)],
        "peso_liquido_t": [2.] * 120 + [1.] * 100 + [9.] * 100,
        "frete_rs_t": [999.] * 120 + [100.] * 100 + [200.] * 100,
    })


class CalibrationTests(unittest.TestCase):
    def test_calibration_is_out_of_time_and_cost_weighted(self):
        df = history()
        fitted = []

        def auxiliary_fit(name, rows):
            fitted.append(rows.copy())
            self.assertLess(pd.to_datetime(rows["Dta.liq."]).max(), pd.Timestamp("2025-02-01"))
            self.assertNotIn("cross", set(rows["Nº frete"]))
            self.assertTrue(set(rows.index).isdisjoint(set(df.index[120:])))

            def predict(x):
                # Predição não recebe o alvo real usado para calcular o fator.
                self.assertNotIn("frete_rs_t", x)
                self.assertNotIn("Valor líquido", x)
                self.assertEqual(set(x.index), set(df.index[120:]))
                return np.full(len(x), 100.)

            return Mock(predict=predict)

        with patch("frete.experiments.fit_candidate", side_effect=auxiliary_fit):
            factor, info = calibration_factor("rf_log", df)
        # Desembolso real: 100*1*100 + 200*9*100 = 190.000.
        # Desembolso previsto: 100*(1*100 + 9*100) = 100.000.
        # Média simples das tarifas daria 1,5, que seria incorreto aqui.
        self.assertAlmostEqual(factor, 1.9)
        self.assertEqual(info["n_fit_calibration"], 119)
        self.assertEqual(info["calibration_overlap_removed"], 1)
        self.assertEqual(len(fitted), 1)

    def test_changing_calibration_targets_cannot_change_auxiliary_training(self):
        df = history()
        changed = df.copy()
        changed.loc[120:, "frete_rs_t"] *= 7
        model = Mock()
        model.predict.side_effect = lambda x: np.full(len(x), 100.)
        with patch("frete.experiments.fit_candidate", return_value=model) as fit:
            before, _ = calibration_factor("rf_log", df)
            first_training = fit.call_args.args[1].copy()
            after, _ = calibration_factor("rf_log", changed)
            second_training = fit.call_args.args[1].copy()
        pd.testing.assert_frame_equal(first_training, second_training)
        self.assertAlmostEqual(after, before * 7)

    def test_zero_or_nonfinite_prediction_cannot_produce_factor(self):
        for invalid in [0., -2., np.nan, np.inf]:
            with self.subTest(prediction=invalid):
                model = Mock()
                model.predict.side_effect = lambda x, v=invalid: np.full(len(x), v)
                with patch("frete.experiments.fit_candidate", return_value=model):
                    with self.assertRaises(ValueError):
                        calibration_factor("rf_log", history())

    def test_invalid_observed_inputs_are_not_silently_skipped(self):
        for column, value in [("peso_liquido_t", np.nan), ("peso_liquido_t", 0.), ("frete_rs_t", np.inf), ("frete_rs_t", np.nan)]:
            with self.subTest(column=column, value=value):
                df = history()
                df.loc[120, column] = value
                model = Mock()
                model.predict.side_effect = lambda x: np.full(len(x), 100.)
                with patch("frete.experiments.fit_candidate", return_value=model):
                    with self.assertRaises(ValueError):
                        calibration_factor("rf_log", df)

    def test_insufficient_history_never_fits_model(self):
        with patch("frete.experiments.fit_candidate") as fit:
            with self.assertRaises(ValueError):
                calibration_factor("rf_log", history().iloc[110:])
            fit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
