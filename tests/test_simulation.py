import unittest
from frete.simulation import component_scenario, volume_scenario


class SimulationTests(unittest.TestCase):
    def test_mix_changes_cost_without_mean_of_means(self):
        segments = [{'destino': 'A', 'peso_t': 90, 'tarifa_rs_t': 100},
                    {'destino': 'B', 'peso_t': 10, 'tarifa_rs_t': 300}]
        self.assertEqual(volume_scenario(segments, 100)['custo_rs'], 12000)
        self.assertEqual(volume_scenario(segments, 100, {'A': 1, 'B': 1})['custo_rs'], 20000)

    def test_trip_components_and_occupancy(self):
        result = component_scenario(600, 6, 3, 200, 30, 100, 1, 100, 10)
        self.assertAlmostEqual(result['custo_rs'], 2310)
        half = component_scenario(600, 6, 3, 200, 30, 50, 1, 100, 10)
        self.assertAlmostEqual(half['tarifa_rs_t'], result['tarifa_rs_t'] * 2)

    def test_invalid_inputs(self):
        for consumption in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                component_scenario(1, 1, consumption, 0, 1, 100)
        with self.assertRaises(ValueError):
            volume_scenario([{'destino': 'A', 'peso_t': 1, 'tarifa_rs_t': 1}], 1, {'B': 1})


if __name__ == '__main__':
    unittest.main()
