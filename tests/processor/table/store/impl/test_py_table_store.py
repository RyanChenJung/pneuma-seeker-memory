import os
import pickle
import sys
import unittest
from tempfile import TemporaryDirectory

from pandas import DataFrame


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../src"))
)

from pneuma_seeker.table.representation.impl.df_table import DFTable
from pneuma_seeker.table.representation.metadata import TableMetadataType
from pneuma_seeker.table.store.impl.py_table_store import PyTableStore


class TestPyTableStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.db_path = self.temp_dir.name
        self.test_db_schema = "test_schema"
        self.test_table_id = "test_table"
        self.py_table_store = PyTableStore(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_checkpoint_creates_files(self):
        table_store_file = os.path.join(self.db_path, "table_store.pkl")
        metadata_store_file = os.path.join(self.db_path, "metadata_store.pkl")

        self.assertTrue(os.path.exists(table_store_file))
        self.assertTrue(os.path.exists(metadata_store_file))

        with open(table_store_file, "rb") as f:
            table_store_data = pickle.load(f)
        with open(metadata_store_file, "rb") as f:
            metadata_store_data = pickle.load(f)

        self.assertEqual(table_store_data, {})
        self.assertEqual(metadata_store_data, [])

    def test_create_db_schema(self):
        db_schema_1 = self.test_db_schema + "1"
        db_schema_2 = self.test_db_schema + "2"
        self.py_table_store.create_db_schema(db_schema_1)
        self.py_table_store.create_db_schema(db_schema_2)

        available_schema = self.py_table_store.get_all_db_schemas()
        self.assertEqual(available_schema, [db_schema_1, db_schema_2])

    def test_rename_db_schema(self):
        self.py_table_store.create_db_schema(self.test_db_schema)
        self.py_table_store.rename_db_schema(
            self.test_db_schema, self.test_db_schema + "2"
        )
        available_schema = self.py_table_store.get_all_db_schemas()
        self.assertEqual(len(available_schema), 1)
        self.assertEqual(available_schema[0], self.test_db_schema + "2")

    def test_delete_db_schema(self):
        self.py_table_store.create_db_schema(self.test_db_schema)
        schema_count = len(self.py_table_store.get_all_db_schemas())
        self.assertEqual(schema_count, 1)

        self.py_table_store.delete_db_schema(self.test_db_schema)
        schema_count = len(self.py_table_store.get_all_db_schemas())
        self.assertEqual(schema_count, 0)

    def test_add_table(self):
        self.py_table_store.create_db_schema(self.test_db_schema)

        # Add new table
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        current_tables = self.py_table_store.get_all_tables_in_db_schema(
            self.test_db_schema
        )
        self.assertEqual(current_tables[self.test_table_id], table_1)

        # Overwrite existing table
        table_2 = DFTable(data=DataFrame({"a": ["2"]}))
        self.py_table_store.add_table(
            self.test_db_schema, self.test_table_id, table_2, True
        )
        current_tables = self.py_table_store.get_all_tables_in_db_schema(
            self.test_db_schema
        )
        self.assertEqual(current_tables[self.test_table_id], table_2)

    def test_get_table(self):
        self.py_table_store.create_db_schema(self.test_db_schema)
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        retrieved_table = self.py_table_store.get_table(
            self.test_db_schema, self.test_table_id
        )
        self.assertEqual(retrieved_table, table_1)

    def test_delete_table(self):
        self.py_table_store.create_db_schema(self.test_db_schema)
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        self.py_table_store.delete_table(self.test_db_schema, self.test_table_id)
        test_schema_tables = self.py_table_store.get_all_tables_in_db_schema(
            db_schema=self.test_db_schema
        )
        self.assertEqual(len(test_schema_tables), 0)

    def test_add_table_metadata(self):
        metadata_info_1 = "This is a test table."
        metadata_info_2 = "This is a test table 2."

        # Add new metadata
        self.py_table_store.create_db_schema(self.test_db_schema)
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        self.py_table_store.add_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
            metadata_info_1,
        )
        metadata = self.py_table_store.get_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
        )
        self.assertEqual(metadata, metadata_info_1)

        # Overwrite existing metadata
        self.py_table_store.add_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
            metadata_info_2,
            True,
        )
        metadata = self.py_table_store.get_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
        )
        self.assertEqual(metadata, metadata_info_2)

    def test_get_table_metadata(self):
        metadata_info = "This is a test table."
        self.py_table_store.create_db_schema(self.test_db_schema)
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        self.py_table_store.add_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
            metadata_info,
        )
        metadata = self.py_table_store.get_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
        )
        self.assertEqual(metadata, metadata_info)

    def test_delete_table_metadata(self):
        metadata_info = "This is a test table."
        self.py_table_store.create_db_schema(self.test_db_schema)
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        self.py_table_store.add_table(self.test_db_schema, self.test_table_id, table_1)
        self.py_table_store.add_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
            metadata_info,
        )
        self.py_table_store.delete_table_metadata(
            self.test_db_schema,
            self.test_table_id,
            TableMetadataType.TABLE_DESCRIPTION,
        )
        metadata_store_file = os.path.join(self.db_path, "metadata_store.pkl")
        with open(metadata_store_file, "rb") as f:
            metadata_store_data = pickle.load(f)
        self.assertEqual(metadata_store_data, [])

    def test_get_all_db_schemas(self):
        db_schema_1 = self.test_db_schema + "1"
        db_schema_2 = self.test_db_schema + "2"
        self.py_table_store.create_db_schema(db_schema_1)
        self.py_table_store.create_db_schema(db_schema_2)
        all_db_schemas = self.py_table_store.get_all_db_schemas()
        self.assertEqual(all_db_schemas, [db_schema_1, db_schema_2])

    def test_get_table_ids_in_db_schema(self):
        table_id_1 = self.test_table_id + "1"
        table_id_2 = self.test_table_id + "2"
        self.py_table_store.create_db_schema(self.test_db_schema)
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_1,
            DFTable(data=DataFrame({"a": ["1"]})),
        )
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_2,
            DFTable(data=DataFrame({"a": ["2"]})),
        )
        all_table_ids = self.py_table_store.get_table_ids_in_db_schema(
            self.test_db_schema
        )
        self.assertEqual(all_table_ids, [table_id_1, table_id_2])

    def test_check_if_table_exists(self):
        self.py_table_store.create_db_schema(self.test_db_schema)
        self.py_table_store.add_table(
            self.test_db_schema,
            self.test_table_id,
            DFTable(data=DataFrame({"a": ["1"]})),
        )
        self.assertTrue(
            self.py_table_store.check_if_table_exists(
                self.test_db_schema, self.test_table_id
            )
        )
        self.assertFalse(
            self.py_table_store.check_if_table_exists(self.test_db_schema, "unknown")
        )

    def test_get_all_tables_in_db_schema(self):
        table_id_1 = self.test_table_id + "1"
        table_id_2 = self.test_table_id + "2"
        table_1 = DFTable(data=DataFrame({"a": ["1"]}))
        table_2 = DFTable(data=DataFrame({"a": ["2"]}))

        self.py_table_store.create_db_schema(self.test_db_schema)
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_1,
            table_1,
        )
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_2,
            table_2,
        )

        table_mapping = self.py_table_store.get_all_tables_in_db_schema(
            self.test_db_schema
        )
        expected_table_mapping = {
            table_id_1: table_1,
            table_id_2: table_2,
        }
        self.assertEqual(table_mapping, expected_table_mapping)

    def test_execute_sql_query(self):
        table_id_1 = self.test_table_id + "1"
        table_id_2 = self.test_table_id + "2"
        table_1 = DFTable(data=DataFrame({"a": ["1"], "b": ["test"]}))
        table_2 = DFTable(data=DataFrame({"a": ["2"], "b": ["test"]}))

        self.py_table_store.create_db_schema(self.test_db_schema)
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_1,
            table_1,
        )
        self.py_table_store.add_table(
            self.test_db_schema,
            table_id_2,
            table_2,
        )

        sql_query = "SELECT table_1.a, table_1.b FROM table_1 JOIN table_2 WHERE table_1.b = table_2.b;"
        result = self.py_table_store.execute_sql_query(
            sql_query,
            {
                "table_1": table_1,
                "table_2": table_2,
            },
        )
        self.assertTrue(isinstance(result.get_data(), DataFrame))
        self.assertTrue(result.get_data().equals(table_1.get_data()))


if __name__ == "__main__":
    unittest.main()
