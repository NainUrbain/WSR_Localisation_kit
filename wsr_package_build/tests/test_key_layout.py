"""Regression checks for normalized quote keys and lossless catalog sorting."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pipeline_tools'))
import translation_csvs as catalog


class KeyLayoutTests(unittest.TestCase):
    def test_normalized_quotes_keep_template_classification(self):
        for key in ('quotes_1', 'quotes_440', 'Quotes_1', 'event_quote12'):
            with self.subTest(key=key):
                self.assertTrue(catalog.is_quote_key(key))
                self.assertEqual(catalog.classify(key, 'A plain quotation.'),
                                 'Candidate Template')
        self.assertFalse(catalog.is_quote_key('quotes_title'))

    def test_sort_includes_extras_and_locales_without_changing_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / 'source_data/WSR_translation_all.csv',
                     root / 'source_data/WSR_translation_news_templates.csv',
                     root / 'locales/ko-KR/WSR_translation_all.csv']
            header = 'Key,Source (EN),Context\r\n'
            records = ['UI-ab123456,Generated,\r\n',
                       'tutorial_1_10_body,"Line one\nLine two",Keep\r\n',
                       'tutorial_1_2_body,"A, B","Quote ""here"""\r\n',
                       'tutorial_1_1_body,First,\r\n']
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((catalog.BOM + header + ''.join(records)).encode('utf-8'))
            with patch.object(catalog, 'SCRIPT_DIR', directory), \
                    patch.object(catalog, 'TRANSLATION_CSVS', [str(paths[0])]), \
                    patch.object(catalog, 'EXTRA_CSVS', [str(paths[1])]), \
                    patch.object(catalog, 'write_manifest'):
                catalog.sort_files()
                expected = (catalog.BOM + header + ''.join(
                    records[i] for i in (3, 2, 1, 0))).encode('utf-8')
                for path in paths:
                    self.assertEqual(path.read_bytes(), expected)
                catalog.sort_files()
                for path in paths:
                    self.assertEqual(path.read_bytes(), expected, 'sort must be idempotent')


if __name__ == '__main__':
    unittest.main()
