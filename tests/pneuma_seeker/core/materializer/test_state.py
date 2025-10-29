# tests/pneuma_seeker/core/materializer/test_state.py
import os
import sys
import unittest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../src"))
)

import pandas as pd

from pneuma_seeker.core.ir_system.data_model import RetrieverType, Table
from pneuma_seeker.core.materializer.state import MaterializerState


class MaterializerStateTests(unittest.TestCase):
    def setUp(self):
        self.state = MaterializerState()

    def test_initial_state(self):
        self.assertEqual(self.state.retrieved_tables, [])
        self.assertEqual(self.state.intermediate_tables, set())
        self.assertIsNone(self.state.web_search_result)

    def test_add_intermediate_table(self):
        df = pd.DataFrame({"a": [1]})
        table = Table("tbl1", RetrieverType.USER, df, {}, path="dummy")
        self.state.add_intermediate_table(table)
        self.assertIn(table, self.state.intermediate_tables)

        # Adding the same table again should replace (set ensures no duplicates)
        self.state.add_intermediate_table(table)
        self.assertEqual(len(self.state.intermediate_tables), 1)

    def test_reset(self):
        df = pd.DataFrame({"a": [1]})
        table = Table("tbl1", RetrieverType.USER, df, {}, path="dummy")
        self.state.retrieved_tables.append(table)
        self.state.add_intermediate_table(table)
        self.state.web_search_result = table

        self.state.reset()
        self.assertEqual(self.state.retrieved_tables, [])
        self.assertEqual(self.state.intermediate_tables, set())
        self.assertIsNone(self.state.web_search_result)


if __name__ == "__main__":
    unittest.main()
