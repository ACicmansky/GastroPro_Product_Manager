import unittest
import os
import sys
import json
import pandas as pd
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import load_config, load_csv_data

class TestUtils(unittest.TestCase):

    def setUp(self):
        self.test_config_path = 'test_config.json'
        self.test_csv_path = 'test_data.csv'

    def tearDown(self):
        if os.path.exists(self.test_config_path):
            os.remove(self.test_config_path)
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)

    def test_load_config_success(self):
        config_data = {'key': 'value'}
        with open(self.test_config_path, 'w') as f:
            json.dump(config_data, f)
        
        self.assertEqual(load_config(self.test_config_path), config_data)

    def test_load_config_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_config('non_existent_file.json')

    def test_load_config_invalid_json(self):
        with open(self.test_config_path, 'w') as f:
            f.write('invalid json')
        
        with self.assertRaises(ValueError):
            load_config(self.test_config_path)

    def test_load_csv_data_success(self):
        csv_data = {'col1': [1, 2], 'col2': [3, 4]}
        df = pd.DataFrame(csv_data)
        df.to_csv(self.test_csv_path, index=False, sep=';', decimal=',')

        loaded_df = load_csv_data(self.test_csv_path)
        self.assertTrue(df.equals(loaded_df))

    def test_load_csv_data_file_not_found(self):
        with self.assertRaises(Exception):
            load_csv_data('non_existent_file.csv')

if __name__ == '__main__':
    unittest.main()