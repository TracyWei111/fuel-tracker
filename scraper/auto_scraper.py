#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuel Price Scraper - 自动抓取柴油价格数据
配置为每天下午3点运行
维护历史价格数组，用于累计计算
"""

import json
import asyncio
from datetime import datetime
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


def scrape_country(page, country_name: str) -> dict:
    """抓取单个国家的价格数据"""
    url = f"{BASE_URL}/{country_name}/diesel_prices/"

    try:
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)

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

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price_usd": usd_price,
            "price_local": local_price,
            "currency": currency
        }

    except Exception as e:
        print(f"  错误: {e}")
        return None


def main():
    """主函数"""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    data_dir = project_dir / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "prices.json"

    # 日志目录
    log_dir = project_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / "scraper.log"

    print(f"[{datetime.now().isoformat()}] 开始抓取柴油价格数据")

    # 读取现有历史数据
    existing_data = {"last_update": None, "source": "GlobalPetrolPrices.com", "countries": {}}
    if output_path.exists():
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except:
            pass

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for country_name, currency, country_cn in COUNTRIES:
            print(f"  抓取: {country_cn}...", end=" ")
            data = scrape_country(page, country_name)

            if data and data.get("price_usd"):
                # 获取现有历史记录
                country_existing = existing_data.get("countries", {}).get(country_name, {})
                diesel_history = country_existing.get("diesel_history", [])

                # 添加新记录（避免重复日期）
                today = data["date"]
                existing_dates = [r["date"] for r in diesel_history]
                if today not in existing_dates:
                    diesel_history.append({
                        "date": today,
                        "price_usd": data["price_usd"],
                        "price_local": data["price_local"]
                    })

                # 按日期排序
                diesel_history.sort(key=lambda x: x["date"])

                results[country_name] = {
                    "currency": currency,
                    "country_cn": country_cn,
                    "diesel_history": diesel_history
                }
                print(f"OK USD {data['price_usd']}")
            else:
                # 保持现有数据
                if country_name in existing_data.get("countries", {}):
                    results[country_name] = existing_data["countries"][country_name]
                print("SKIP 失败")

            page.wait_for_timeout(500)

        browser.close()

    # 保存结果
    if results:
        output = {
            "last_update": datetime.now().isoformat(),
            "source": "GlobalPetrolPrices.com",
            "countries": results
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"数据已保存: {output_path}")
        print(f"共 {len(results)} 个国家")

    # 写入日志
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] 完成，{len(results)} 个国家\n")


if __name__ == "__main__":
    main()