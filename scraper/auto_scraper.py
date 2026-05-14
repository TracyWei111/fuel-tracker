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

        # 抓取 4 锚点参考表（current / 1mo ago / 3mo ago / 1yr ago，本地货币）
        # 失败不影响主流程
        anchors = {}
        try:
            anchors = parse_local_anchors(text)
        except Exception as e:
            print(f"  锚点解析失败: {e}")

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "price_usd": usd_price,
            "price_local": local_price,
            "currency": currency,
            "anchors_local": anchors,  # 4 reference points in local currency
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
    anchors_path = data_dir / "anchors_history.json"

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

    # 读取 anchors 历史
    anchors_history = {"scrapes": []}
    if anchors_path.exists():
        try:
            with open(anchors_path, 'r', encoding='utf-8') as f:
                anchors_history = json.load(f)
        except:
            pass

    results = {}
    today_anchors = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        for country_name, currency, country_cn in COUNTRIES:
            print(f"  抓取: {country_cn}...", end=" ")
            data = scrape_country(page, country_name)

            if data and data.get("price_usd"):
                # 获取现有历史记录（兼容 diesel 和 diesel_history 格式）
                country_existing = existing_data.get("countries", {}).get(country_name, {})
                diesel_list = country_existing.get("diesel", country_existing.get("diesel_history", []))

                # 添加新记录（使用 calculator.py 兼容格式）
                today = data["date"]
                existing_dates = [r["date"] for r in diesel_list]
                if today not in existing_dates:
                    diesel_list.append({
                        "date": today,
                        "price": data["price_usd"],  # 字段名改为 price
                        "price_local": data["price_local"],
                        "currency": currency
                    })

                # 按日期排序
                diesel_list.sort(key=lambda x: x["date"])

                results[country_name] = {
                    "diesel": diesel_list,  # 字段名改为 diesel
                    "country_cn": country_cn,
                    "currency": currency
                }

                # 收集 4 锚点（如果解析成功）
                if data.get("anchors_local"):
                    today_anchors[country_name] = data["anchors_local"]

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

    # 保存 anchors 历史（每天一条记录）
    if today_anchors:
        today_str = datetime.now().strftime("%Y-%m-%d")
        # 同日去重
        anchors_history["scrapes"] = [
            s for s in anchors_history.get("scrapes", [])
            if s.get("scrape_date") != today_str
        ]
        anchors_history["scrapes"].append({
            "scrape_date": today_str,
            "scrape_iso": datetime.now().isoformat(),
            "countries": today_anchors,
        })
        anchors_history["scrapes"].sort(key=lambda s: s.get("scrape_date", ""))
        anchors_history["last_update"] = datetime.now().isoformat()
        with open(anchors_path, 'w', encoding='utf-8') as f:
            json.dump(anchors_history, f, ensure_ascii=False, indent=2)
        print(f"锚点历史已保存: {anchors_path} (累计 {len(anchors_history['scrapes'])} 次)")

    # 写入日志
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now().isoformat()}] 完成，{len(results)} 个国家，锚点 {len(today_anchors)} 个\n")


if __name__ == "__main__":
    main()