#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuel Price Scraper - 自动抓取柴油价格数据
配置为每天下午3点运行
维护历史价格数组，用于累计计算
"""

import json
import math
import time
import copy
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Playwright 同步 API
from playwright.sync_api import sync_playwright

# 国家列表
COUNTRIES = [
    ("China", "CNY", "中国"),
    ("Vietnam", "VND", "越南"),
    ("Indonesia", "IDR", "印尼"),
    ("Thailand", "THB", "泰国"),
    ("Malaysia", "MYR", "马来西亚"),
    ("Philippines", "PHP", "菲律宾"),
    ("Mexico", "MXN", "墨西哥"),
    ("Brazil", "BRL", "巴西"),
]

BASE_URL = "https://www.globalpetrolprices.com"


def parse_local_anchors(text: str) -> dict:
    """
    Extract the 4-row reference table from the page text:
      Current price        XX,XXX.XX  -
      One month ago        XX,XXX.XX  YY.Y %
      Three months ago     XX,XXX.XX  YY.Y %
      One year ago         XX,XXX.XX  YY.Y %

    These anchors are real source-of-truth data points exposed for free
    on every country's page (unlike the 8-week chart which is image-only).
    Captured per scrape so we can backfill / cross-validate the daily series.
    """
    import re
    anchors = {}
    lines = text.splitlines()
    in_local_table = False
    for line in lines:
        # Header signals start of the local-currency reference table
        if re.search(r'Price\s*\([A-Z]{3}/Liter\)\s*Percent change', line):
            in_local_table = True
            continue
        if not in_local_table:
            continue
        for label, key in [
            ("Current price", "current"),
            ("One month ago", "one_month_ago"),
            ("Three months ago", "three_months_ago"),
            ("One year ago", "one_year_ago"),
        ]:
            m = re.match(rf'^\s*{re.escape(label)}\s+([\d,]+\.?\d*)', line)
            if m:
                anchors[key] = float(m.group(1).replace(',', ''))
                break
        if len(anchors) >= 4:
            break
    return anchors


def scrape_country(page, country_name: str) -> dict:
    """抓取单个国家的价格数据"""
    url = f"{BASE_URL}/{country_name}/diesel_prices/"

    try:
        page.goto(url, timeout=30000, wait_until='domcontentloaded')
        page.wait_for_selector("body", timeout=15000)

        # 提取价格数据
        text = page.inner_text("body")

        # 查找 USD 价格
        import re
        usd_match = re.search(r'USD (\d+\.?\d*) per liter', text)
        usd_price = float(usd_match.group(1)) if usd_match else None

        # 查找本地货币价格
        local_match = re.search(r'(CNY|VND|IDR|THB|MYR|PHP|MXN|BRL) ([\d,]+\.?\d*) per liter', text)
        if local_match:
            currency = local_match.group(1)
            local_price = float(local_match.group(2).replace(',', ''))
        else:
            currency = None
            local_price = None

        # 抓取 4 锚点参考表（current / 1mo ago / 3mo ago / 1yr ago，本地货币）
        # 失败不影响主流程
        anchors = {}
        try:
            anchors = parse_local_anchors(text)
        except Exception as e:
            print(f"  锚点解析失败: {e}")

        return {
            "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
            "price_usd": usd_price,
            "price_local": local_price,
            "currency": currency,
            "anchors_local": anchors,  # 4 reference points in local currency
        }

    except Exception as e:
        print(f"  错误: {e}")
        return None


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def update_prices(project_dir, fetch, today=None, retry_delay=2):
    """Publish only a complete fresh batch; retries never turn old data into success."""
    now = datetime.now(timezone(timedelta(hours=8)))
    today = today or now.date().isoformat()
    output_path = project_dir / 'data/prices.json'
    existing = json.loads(output_path.read_text(encoding='utf-8'))
    output = copy.deepcopy(existing)
    failures, collected, anchors = [], {}, {}
    for name, currency, name_cn in COUNTRIES:
        error = ''
        for attempt in range(3):
            try:
                quote = fetch(name)
                if not quote or quote.get('date') != today or quote.get('currency') != currency:
                    raise ValueError('missing quote, stale date or wrong currency')
                for field in ('price_usd', 'price_local'):
                    value = quote.get(field)
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                        raise ValueError(f'invalid {field}: {value}')
                collected[name] = quote
                break
            except Exception as exc:
                error = str(exc)
                print(f'{name}: attempt {attempt + 1}/3 failed: {error}', flush=True)
                if attempt < 2:
                    time.sleep(retry_delay)
        if name not in collected:
            failures.append(name)
            continue
        quote = collected[name]
        prior = output['countries'].get(name, {})
        history = prior.get('diesel', prior.get('diesel_history', []))
        # Same-day reruns refresh the quote without duplicating or rewriting past days.
        history = [row for row in history if row['date'] != today]
        history.append({'date': today, 'price': quote['price_usd'],
                        'price_local': quote['price_local'], 'currency': currency})
        output['countries'][name] = {'diesel': sorted(history, key=lambda r: r['date']),
                                     'country_cn': name_cn, 'currency': currency}
        if quote.get('anchors_local'):
            anchors[name] = quote['anchors_local']
        print(f'{name}: OK USD {quote["price_usd"]}', flush=True)
    receipt = {'status': 'failed' if failures else 'success', 'observed_date': today,
               'finished_at': datetime.now(timezone(timedelta(hours=8))).isoformat(),
               'successful_countries': sorted(collected), 'failed_countries': failures}
    atomic_json(project_dir / 'logs/scrape-status.json', receipt)
    if failures:
        raise RuntimeError('Collection incomplete; original prices preserved: ' + ', '.join(failures))
    output['last_update'] = receipt['finished_at']
    output['source'] = 'GlobalPetrolPrices.com'
    atomic_json(output_path, output)
    if anchors:
        path = project_dir / 'data/anchors_history.json'
        history = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'scrapes': []}
        history['scrapes'] = [row for row in history['scrapes'] if row.get('scrape_date') != today]
        history['scrapes'].append({'scrape_date': today, 'scrape_iso': receipt['finished_at'],
                                   'countries': anchors})
        history['scrapes'].sort(key=lambda row: row['scrape_date'])
        history['last_update'] = receipt['finished_at']
        atomic_json(path, history)
    return receipt


def main():
    project_dir = Path(__file__).resolve().parent.parent
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            update_prices(project_dir, lambda name: scrape_country(page, name))
        finally:
            browser.close()


if __name__ == '__main__':
    main()