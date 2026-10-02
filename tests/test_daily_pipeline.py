"""Regression gates for false success, incomplete collection and stale reports."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scraper import auto_scraper as scraper
from report import build_html_report as report
from engine.cumulative_calc import report_history_drift


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'data').mkdir()
        self.old = {'last_update': '2026-10-01T15:00:00+08:00', 'countries': {
            name: {'diesel': [{'date': '2026-10-01', 'price': 1.0}]}
            for name, _, _ in scraper.COUNTRIES}}
        self.path = self.root / 'data/prices.json'
        self.path.write_text(json.dumps(self.old), encoding='utf-8')

    def quote(self, country):
        currency = dict((name, cur) for name, cur, _ in scraper.COUNTRIES)[country]
        return {'date': '2026-10-02', 'price_usd': 1.2, 'price_local': 8.0,
                'currency': currency, 'anchors_local': {}}

    def run_collection(self, fetch):
        self.assertTrue(callable(getattr(scraper, 'update_prices', None)),
                        'collector must validate a complete batch before writing')
        return scraper.update_prices(self.root, fetch, today='2026-10-02', retry_delay=0)

    def test_one_failed_country_preserves_prices_and_reports_failure(self):
        before = self.path.read_bytes()
        with self.assertRaises(RuntimeError):
            self.run_collection(lambda name: None if name == 'China' else self.quote(name))
        self.assertEqual(self.path.read_bytes(), before)
        status = json.loads((self.root / 'logs/scrape-status.json').read_text())
        self.assertEqual(status['status'], 'failed')
        self.assertEqual(status['failed_countries'], ['China'])

    def test_wrong_currency_nonfinite_or_stale_quote_cannot_publish(self):
        for field, value in [('currency', 'EUR'), ('price_usd', float('nan')),
                             ('price_local', 0), ('date', '2026-10-01')]:
            with self.subTest(field=field):
                def fetch(name):
                    quote = self.quote(name)
                    if name == 'China':
                        quote[field] = value
                    return quote
                before = self.path.read_bytes()
                with self.assertRaises(RuntimeError):
                    self.run_collection(fetch)
                self.assertEqual(self.path.read_bytes(), before)

    def test_retry_recovers_and_rerun_replaces_only_today(self):
        calls = {}
        def fetch(name):
            calls[name] = calls.get(name, 0) + 1
            return None if calls[name] == 1 else self.quote(name)
        self.run_collection(fetch)
        def revised(name):
            quote = self.quote(name)
            quote['price_usd'] = 1.3
            return quote
        self.run_collection(revised)
        prices = json.loads(self.path.read_text())
        self.assertEqual(len(prices['countries']), 8)
        for country in prices['countries'].values():
            self.assertEqual(country['diesel'], [
                {'date': '2026-10-01', 'price': 1.0},
                {'date': '2026-10-02', 'price': 1.3, 'price_local': 8.0,
                 'currency': country['currency']}])


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.payload = report.build_payload()
        self.today = self.payload['meta']['cumulative_as_of']
        # Fixture is historical on purpose; normalize observations to its as-of day.
        for country in self.payload['countries'].values():
            country['latest_date'] = self.today

    def validate(self, payload):
        self.assertTrue(callable(getattr(report, 'validate_payload', None)),
                        'reports need a publication gate')
        report.validate_payload(payload, self.today)

    def test_valid_report_passes(self):
        self.validate(self.payload)

    def test_stale_or_missing_country_blocks_publication(self):
        for mutation in ['stale', 'missing', 'nan', 'headline']:
            with self.subTest(mutation=mutation):
                payload = copy.deepcopy(self.payload)
                if mutation == 'stale':
                    payload['countries']['China']['latest_date'] = '2020-01-01'
                elif mutation == 'missing':
                    del payload['countries']['China']
                elif mutation == 'nan':
                    payload['countries']['China']['latest_price'] = float('nan')
                else:
                    payload['kpi']['cumulative_extra_total'] += 100
                with self.assertRaises(ValueError):
                    self.validate(payload)

    def test_historical_rewrite_blocks_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cumulative.json'
            path.write_text(json.dumps([{'date': '2026-10-01', 'cumulative_extra_total': 10}]))
            with self.assertRaises(ValueError):
                report_history_drift(path, [
                    {'date': '2026-10-01', 'cumulative_extra_total': 20},
                    {'date': '2026-10-02', 'cumulative_extra_total': 21}])


if __name__ == '__main__':
    unittest.main()
