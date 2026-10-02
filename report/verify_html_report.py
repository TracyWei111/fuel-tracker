"""Exercise the published HTML in Chromium and reject JS errors or empty charts."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from report.build_html_report import REPO, validate_payload


def verify(path):
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(path.resolve().as_uri())
            payload = page.evaluate('DATA')
            validate_payload(payload, datetime.now(timezone(timedelta(hours=8))).date().isoformat())
            rows = page.locator('#snapshot-table tbody tr').count()
            if rows != len(payload['country_order']):
                raise ValueError(f'Expected full country table, found {rows} rows')
            # This template draws SVG polylines, not path elements.
            for chart in page.locator('svg.chart-svg').all():
                lines = chart.locator('polyline.series-line')
                if not lines.count() or any(not line.get_attribute('points') for line in lines.all()):
                    raise ValueError('Expected populated chart lines')
            if page.locator('svg.chart-svg').count() < len(payload['country_order']):
                raise ValueError('Country charts are missing')
            if errors:
                raise ValueError('JavaScript errors: ' + '; '.join(errors))
        finally:
            browser.close()
    return {'status': 'success', 'countries': rows,
            'as_of': payload['meta']['cumulative_as_of']}


if __name__ == '__main__':
    result = verify(REPO / 'reports/latest.html')
    (REPO / 'logs').mkdir(exist_ok=True)
    (REPO / 'logs/report-validation.json').write_text(json.dumps(result), encoding='utf-8')
    print(json.dumps(result))
