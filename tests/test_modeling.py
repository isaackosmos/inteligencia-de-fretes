import unittest
import numpy as np
import pandas as pd
from frete.modeling import temporal_split, metrics, features

class ModelingTests(unittest.TestCase):
    def test_temporal_split_purges_crossing_freight(self):
        df = pd.DataFrame({"Dta.liq.": ["2026-03-01", "2026-03-20", "2026-04-02"], "Nº frete": ["a", "b", "b"]})
        train, test, overlap = temporal_split(df)
        self.assertEqual(train["Nº frete"].tolist(), ["a"])
        self.assertTrue(set(train["Nº frete"]).isdisjoint(test["Nº frete"]))
        self.assertEqual(overlap, 1)

    def test_cost_bias_weights_tonnage(self):
        result = metrics([100, 200], [110, 190], [1, 9])
        self.assertAlmostEqual(result["vies_total_custo"], -80 / 1900)
        self.assertAlmostEqual(result["WAPE_custo"], 100 / 1900)

    def test_features_ignore_target_columns(self):
        df = pd.DataFrame({"peso_liquido_t": [2], "Valor líquido": [100], "frete_rs_t": [50], "flag_outlier_rs_t": [1], "Dta.liq.": ["2026-04-01"]})
        result = features(df)
        self.assertNotIn("frete_rs_t", result)
        self.assertNotIn("Valor líquido", result)
        self.assertNotIn("flag_outlier_rs_t", result)
        self.assertEqual(result["indice_tempo"].iloc[0], 15)

if __name__ == "__main__":
    unittest.main()
