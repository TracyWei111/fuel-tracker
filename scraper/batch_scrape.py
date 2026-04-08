#!/usr/bin/env python3
"""
从 GlobalPetrolPrices 批量爬取柴油价格数据
"""

import sys
import json
import time
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 国家列表
COUNTRIES = [
    'China',
    'Vietnam',
    'Indonesia',
    'Thailand',
    'Malaysia',
    'Philippines',
    'Mexico',
    'Brazil'
]

def main():
    """输出爬取任务"""
    print("=" * 60)
    print("Diesel Price Scraping Task")
    print("=" * 60)

    print("\n需要爬取以下国家的柴油价格数据:")
    for country in COUNTRIES:
        url = f"https://www.globalpetrolprices.com/{country}/diesel_prices/"
        print(f"  {country}: {url}")

    print("\n每个页面需要提取:")
    print("  - Current price (USD/L)")
    print("  - One month ago price (USD/L)")
    print("  - 确认 Last update 日期")

    print("\n数据频率: Weekly (每周更新)")
    print("基准日期: 2026-02-23 (One month ago)")
    print("当前日期: 2026-03-30")

if __name__ == "__main__":
    main()