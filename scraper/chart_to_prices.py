#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 GlobalPetrolPrices.com 图表提取的柴油价格数据
数据通过分析 charts/ 目录中的图表读取
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

# 国家信息
COUNTRIES = {
    "China": {"name_cn": "中国", "currency": "CNY"},
    "Vietnam": {"name_cn": "越南", "currency": "VND"},
    "Indonesia": {"name_cn": "印尼", "currency": "IDR"},
    "Thailand": {"name_cn": "泰国", "currency": "THB"},
    "Malaysia": {"name_cn": "马来西亚", "currency": "MYR"},
    "Philippines": {"name_cn": "菲律宾", "currency": "PHP"},
    "Mexico": {"name_cn": "墨西哥", "currency": "MXN"},
    "Brazil": {"name_cn": "巴西", "currency": "BRL"},
}

def main():
    """
    从图表读取的数据生成 prices.json
    """

    # 8 周日期（截止到 2026-04-08）
    weekly_dates = []
    for i in range(8):
        week_date = datetime(2026, 2, 17) + timedelta(weeks=i)
        weekly_dates.append(week_date.strftime('%Y-%m-%d'))

    # 从图表读取的价格数据（本地货币）
    # 这些是通过分析 charts/ 目录中图表读取的实际数值
    chart_data = {
        "China": {
            # Y轴: 6.5-8.5 CNY, 数据点逐周上升
            "prices_local": [7.05, 7.15, 7.30, 7.50, 7.70, 7.90, 8.10, 8.25],
            "current_usd": 1.20,
        },
        "Vietnam": {
            # Y轴: 17000-46000 VND, 数据点稳步上升
            "prices_local": [27000, 28500, 30500, 32500, 35500, 39000, 42500, 45225],
            "current_usd": 1.72,
        },
        "Indonesia": {
            # Y轴: 13000-15000 IDR, 前几周略低后稳定
            "prices_local": [13860, 14000, 14200, 14620, 14620, 14620, 14620, 14620],
            "current_usd": 0.86,
        },
        "Thailand": {
            # Y轴: 28-50 THB, 前三周平稳后快速上升
            "prices_local": [30.14, 30.14, 30.14, 33.00, 36.50, 41.00, 45.50, 48.68],
            "current_usd": 1.50,
        },
        "Malaysia": {
            # Y轴: 2.5-6.5 MYR, 持续上升
            "prices_local": [2.95, 3.10, 3.25, 3.60, 4.20, 4.85, 5.50, 6.02],
            "current_usd": 1.49,
        },
        "Philippines": {
            # Y轴: 55-130 PHP, 大幅上升
            "prices_local": [57.00, 59.00, 61.00, 68.00, 80.00, 95.00, 115.00, 128.80],
            "current_usd": 2.15,
        },
        "Mexico": {
            # Y轴: 26-29 MXN, 缓慢上升
            "prices_local": [26.30, 26.55, 26.80, 27.10, 27.40, 27.75, 28.15, 28.54],
            "current_usd": 1.61,
        },
        "Brazil": {
            # Y轴: 5.8-7.6 BRL, 中等上升
            "prices_local": [6.05, 6.05, 6.08, 6.15, 6.35, 6.65, 7.05, 7.45],
            "current_usd": 1.44,
        },
    }

    # 生成 prices.json
    result = {}

    for country_key, data in chart_data.items():
        country_info = COUNTRIES[country_key]
        prices_local = data["prices_local"]
        current_usd = data["current_usd"]

        # 计算汇率
        usd_rate = current_usd / prices_local[-1]

        result[country_key] = {
            "diesel": [],
            "gasoline": []
        }

        for i, (date, price_local) in enumerate(zip(weekly_dates, prices_local)):
            usd_price = price_local * usd_rate

            result[country_key]["diesel"].append({
                "date": date,
                "price": round(usd_price, 2),
                "price_local": round(price_local, 2),
                "country_cn": country_info["name_cn"],
                "note": f"Weekly, {country_info['currency']} {price_local:,.2f}"
            })

    # 保存
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    output_path = project_dir / "data" / "prices.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"数据已保存: {output_path}")
    print(f"共 {len(result)} 个国家，每个国家 8 周数据")

    # 打印摘要
    print("\n价格摘要:")
    for country_key, data in result.items():
        diesel = data["diesel"]
        first = diesel[0]
        last = diesel[-1]
        change = ((last["price"] / first["price"]) - 1) * 100
        print(f"  {first['country_cn']}: {first['price']:.2f} → {last['price']:.2f} USD/L ({change:+.1f}%)")


if __name__ == "__main__":
    main()