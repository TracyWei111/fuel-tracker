#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuel Price Scraper - 通过 Playwright MCP 抓取数据
使用方法: 由 Claude 通过 Playwright MCP 调用，而非独立运行
"""

import json
import os
from datetime import datetime
from pathlib import Path

# 国家配置
COUNTRIES = {
    "China": {"url_name": "China", "name_cn": "中国"},
    "Vietnam": {"url_name": "Vietnam", "name_cn": "越南"},
    "Indonesia": {"url_name": "Indonesia", "name_cn": "印尼"},
    "Thailand": {"url_name": "Thailand", "name_cn": "泰国"},
    "Malaysia": {"url_name": "Malaysia", "name_cn": "马来西亚"},
    "Philippines": {"url_name": "Philippines", "name_cn": "菲律宾"},
    "Mexico": {"url_name": "Mexico", "name_cn": "墨西哥"},
    "Brazil": {"url_name": "Brazil", "name_cn": "巴西"},
    "South_Korea": {"url_name": "South-Korea", "name_cn": "韩国"},
    "USA": {"url_name": "USA", "name_cn": "美国"},
}

FUEL_TYPES = ["diesel", "gasoline"]

BASE_URL = "https://www.globalpetrolprices.com"


def get_country_url(country_key: str, fuel_type: str) -> str:
    """获取国家燃料价格页面 URL"""
    url_name = COUNTRIES[country_key]["url_name"]
    return f"{BASE_URL}/{url_name}/{fuel_type}_prices/"


def save_scraped_data(scraped_data: dict, output_path: str):
    """
    保存抓取的数据到 prices.json

    scraped_data 格式:
    {
        "China": {
            "diesel": {"price": 1.20, "date": "2026-03-30"},
            "gasoline": {"price": 1.35, "date": "2026-03-30"}
        },
        ...
    }
    """
    # 读取现有数据
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            try:
                existing = json.load(f)
            except:
                existing = {}

    # 合并数据
    for country_key, country_data in scraped_data.items():
        if country_key not in existing:
            existing[country_key] = {"diesel": [], "gasoline": []}

        for fuel_type in FUEL_TYPES:
            fuel_data = country_data.get(fuel_type, {})
            price = fuel_data.get("price")
            date = fuel_data.get("date")

            if price is not None and date:
                # 检查是否已有该日期的数据
                dates = [d["date"] for d in existing[country_key][fuel_type]]
                if date not in dates:
                    existing[country_key][fuel_type].append({
                        "date": date,
                        "price": price,
                        "country_cn": COUNTRIES[country_key]["name_cn"]
                    })

    # 按日期排序
    for country_key in existing:
        for fuel_type in FUEL_TYPES:
            existing[country_key][fuel_type].sort(key=lambda x: x["date"])

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"数据已保存到: {output_path}")


def print_scraping_instructions():
    """打印抓取指令供 Claude 执行"""
    print("=" * 60)
    print("Fuel Price Scraping URLs")
    print("=" * 60)

    for country_key, info in COUNTRIES.items():
        for fuel_type in FUEL_TYPES:
            url = get_country_url(country_key, fuel_type)
            print(f"{info['name_cn']} {fuel_type}: {url}")

    print("=" * 60)
    print("请使用 Playwright MCP 依次访问上述 URL 并提取价格数据")


if __name__ == "__main__":
    # 获取项目路径
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    output_path = project_dir / "data" / "prices.json"

    # 打印 URL 列表
    print_scraping_instructions()

    # 示例：手动输入抓取的数据进行测试
    print("\n请通过 Claude 使用 Playwright MCP 抓取数据后，调用 save_scraped_data() 保存")