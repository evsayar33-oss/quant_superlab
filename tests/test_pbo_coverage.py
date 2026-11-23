"""PBO partition accounting is transparent without changing trading gates."""
import unittest
import numpy as np
import pandas as pd

from lab import metrics


class PboCoverageTests(unittest.TestCase):
    def test_16_block_subsampling_matches_implementation(self):
        x = np.random.default_rng(42).normal(0, 0.01, (400, 3))
        data = pd.DataFrame(x, columns=["a", "b", "c"])
        out = metrics.pbo_coverage(data)
        self.assertEqual(out["partitions_possible"], 12870)
        self.assertEqual(out["partition_stride"], 7)
        self.assertEqual(out["partitions_evaluated"], 1839)
        self.assertEqual(out["status"], "ESTIMATED")
        self.assertFalse(out["independent_forward_evidence"])
        self.assertFalse(out["partition_level_confidence_interval_available"])
        self.assertIsNotNone(metrics.pbo(data))

    def test_insufficient_samples_not_confused_with_zero_pbo(self):
        out = metrics.pbo_coverage(pd.DataFrame({"a": [0.1] * 10, "b": [-0.1] * 10}))
        self.assertEqual(out["status"], "INSUFFICIENT_OBSERVATIONS_OR_VARIANTS")
        self.assertEqual(out["partitions_evaluated"], 0)

    def test_missing_cells_are_explicitly_reported(self):
        rng = np.random.default_rng(1)
        x = pd.DataFrame(rng.normal(size=(400, 2)), columns=["a", "b"])
        x.loc[0, "a"] = np.nan
        x.loc[1, "b"] = np.nan
        self.assertEqual(metrics.pbo_coverage(x)["partial_missing_cells_zero_filled"], 2)

    def test_invalid_partition_structure_rejected(self):
        with self.assertRaises(ValueError):
            metrics.pbo_coverage(pd.DataFrame({"a": [0.1]}), S=15)


if __name__ == "__main__":
    unittest.main()
