#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确计算累计多付金额
基于实际爬取的价格数据和线性插值
"""

import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


def load_config():
    """加载配置"""
    config_path = Path(__file__).parent.parent / 'config' / 'jnt_params.yaml'
    import yaml
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_prices():
    """加载价格数据"""
    prices_path = Path(__file__).parent.parent / 'data' / 'prices.json'
    with open(prices_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def interpolate_price(baseline_price, current_price, days_total, days_elapsed):
    """线性插值计算某日的价格"""
    if days_total == 0:
        return baseline_price
    ratio = days_elapsed / days_total
    return baseline_price + (current_price - baseline_price) * ratio


def calculate_cumulative_extra():
    """计算累计多付金额"""
    config = load_config()
    prices = load_prices()

    # 时间范围
    baseline_date = datetime(2026, 2, 23)
    end_date = datetime(2026, 3, 30)
    days_total = (end_date - baseline_date).days  # 36 天

    print("=" * 70)
    print("精确累计多付计算 (基于线性插值)")
    print("=" * 70)
    print(f"基准日期: {baseline_date.strftime('%Y-%m-%d')}")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")
    print(f"计算天数: {days_total} 天")
    print()

    # 每日累计
    daily_records = []
    cumulative_extra_total = 0

    for day in range(days_total + 1):
        current_date = baseline_date + timedelta(days=day)

        daily_extra = 0
        countries_detail = []

        for country_key, country_config in config['countries'].items():
            baseline_cost = country_config.get('baseline_cost_per_order', 0)
            daily_orders = country_config.get('daily_orders', 0)
            country_cn = country_config.get('name_cn', country_key)

            # 获取价格数据
            country_prices = prices.get(country_key, {}).get('diesel', [])
            if len(country_prices) >= 2:
                base_price = country_prices[0]['price']
                curr_price = country_prices[-1]['price']
            else:
                continue

            # 插值计算当日价格
            daily_price = interpolate_price(base_price, curr_price, days_total, day)

            # 计算当日每单成本
            if base_price > 0:
                price_ratio = daily_price / base_price
                current_cost = baseline_cost * price_ratio
            else:
                current_cost = baseline_cost
                price_ratio = 1.0

            # 每单多付
            extra_per_order = current_cost - baseline_cost

            # 当日多付总额
            country_daily_extra = extra_per_order * daily_orders
            daily_extra += country_daily_extra

            countries_detail.append({
                'country': country_cn,
                'price': round(daily_price, 2),
                'cost': round(current_cost, 4),
                'extra': round(country_daily_extra, 2)
            })

        cumulative_extra_total += daily_extra

        record = {
            'date': current_date.strftime('%Y-%m-%d'),
            'daily_extra': round(daily_extra, 2),
            'cumulative_extra': round(cumulative_extra_total, 2),
            'countries': countries_detail
        }
        daily_records.append(record)

    # 输出汇总
    print("-" * 70)
    print(f"{'日期':<12} {'当日多付':>15} {'累计多付':>15}")
    print("-" * 70)

    # 每5天输出一次
    for i, record in enumerate(daily_records):
        if i % 5 == 0 or i == len(daily_records) - 1:
            print(f"{record['date']:<12} ${record['daily_extra']:>14,.2f} ${record['cumulative_extra']:>14,.2f}")

    print("-" * 70)
    print(f"{'总计':<12} {'':<15} ${cumulative_extra_total:>14,.2f}")
    print("=" * 70)

    # 输出各国明细
    print("\n各国累计贡献:")
    print("-" * 70)
    final_record = daily_records[-1]
    countries_sorted = sorted(final_record['countries'], key=lambda x: x['extra'], reverse=True)
    for c in countries_sorted:
        print(f"  {c['country']}: ${c['extra']:>12,.2f}")

    print()
    print(f"累计多付总额: ${cumulative_extra_total:,.2f}")

    # 保存到 daily_records.json
    output_records = [{
        'date': r['date'],
        'daily_extra_total': r['daily_extra'],
        'cumulative_extra_total': r['cumulative_extra']
    } for r in daily_records]

    output_path = Path(__file__).parent.parent / 'data' / 'cumulative_records.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)

    print(f"\n详细记录已保存到: {output_path}")

    return cumulative_extra_total


if __name__ == "__main__":
    calculate_cumulative_extra()