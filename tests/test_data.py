"""Verificações de integridade do conjunto reconstruído (após build_data)."""
import unittest
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


class DatasetIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = pd.read_csv(ROOT / "data/processed/base_modelagem_frete.csv", sep=";", decimal=",")

    def test_unique_observation_and_reconciled_financial_total(self):
        d = self.data
        self.assertFalse(d.duplicated(["Nº frete", "Item"]).any())
        self.assertEqual(len(d), 29860)
        self.assertAlmostEqual(d["Valor líquido"].sum(), 33951407.81, places=2)
        self.assertAlmostEqual(d["peso_liquido_t"].sum(), 200911.43023, places=5)

    def test_price_identity_and_consolidation(self):
        d = self.data
        positive = d["peso_liquido_t"].gt(0)
        np.testing.assert_allclose(d.loc[positive, "frete_rs_t"] * d.loc[positive, "peso_liquido_t"], d.loc[positive, "Valor líquido"], rtol=1e-10)
        np.testing.assert_allclose(d.groupby("Nº frete")["share_peso_item_no_frete"].sum(), 1, atol=1e-10)
        np.testing.assert_allclose(d[["pct_peso_um_kg", "pct_peso_um_sac", "pct_peso_um_fd"]].sum(axis=1), 1, atol=1e-10)

    def test_known_item_does_not_sum_repeated_freight_value(self):
        row = self.data.set_index(["Nº frete", "Item"]).loc[(436681, 2)]
        self.assertAlmostEqual(row["Valor líquido"], 1184.30, places=2)
        self.assertAlmostEqual(row["peso_liquido_t"], 12.06, places=2)


if __name__ == "__main__":
    unittest.main()
