# finproj - tests for customizable asset classes
# Copyright (C) 2025-2026 Alex Scherer
#
# Run from project root with: python3 -m unittest discover -s tests -v

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'code'))

from asset_classes import default_asset_catalog


class AssetCatalogTest(unittest.TestCase):
    def test_default_catalog_has_required_assets(self):
        catalog = default_asset_catalog()
        self.assertEqual(catalog.required_ids(), {'cash', 'money_market', 'bonds', 'stocks'})
        self.assertEqual(catalog.liquidity_id(), 'cash')
        self.assertEqual(catalog.shortfall_id(), 'bonds')

    def test_rename_asset(self):
        catalog = default_asset_catalog()
        catalog.rename('stocks', 'Equities')
        self.assertEqual(catalog.name('stocks'), 'Equities')

    def test_add_and_remove_optional_asset(self):
        catalog = default_asset_catalog()
        added = catalog.add('Commodities')
        self.assertIn(added.id, catalog.ids)
        catalog.remove(added.id)
        self.assertNotIn(added.id, catalog.ids)

    def test_cannot_remove_required_asset(self):
        catalog = default_asset_catalog()
        with self.assertRaises(ValueError):
            catalog.remove('bonds')

    def test_duplicate_name_rejected(self):
        catalog = default_asset_catalog()
        catalog.rename('crypto', 'Bonds')
        with self.assertRaises(ValueError):
            catalog.validate()


if __name__ == '__main__':
    unittest.main()
