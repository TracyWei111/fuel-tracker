#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确计算累计多付金额
基于实际爬取的价格数据和线性插值
动态计算到当天
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


def get_baseline_and_current_prices(prices_data, country_key, baseline_date_str):
    """从历史数组中获取基准和当前价格"""
    country_data = prices_data.get('countries', {}).get(country_key, {})
    diesel_list = country_data.get('diesel', country_data.get('diesel_history', []))

    if not diesel_list:
        return None, None

    # 找基准价格（baseline_date 或最接近的早期记录）
    baseline_price = None
    for record in diesel_list:
        if record['date'] >= baseline_date_str:
            baseline_price = record.get('price', record.get('price_usd'))
            break

    if baseline_price is None:
        # 使用最早记录作为基准
        first_record = diesel_list[0]
        baseline_price = first_record.get('price', first_record.get('price_usd'))

    # 当前价格（最后一条记录）
    last_record = diesel_list[-1]
    current_price = last_record.get('price', last_record.get('price_usd'))

    return baseline_price, current_price


def calculate_cumulative_extra():
    """计算累计多付金额"""
    config = load_config()
    prices = load_prices()

    # 时间范围 - 动态计算到今天
    baseline_date = datetime.strptime(config['baseline_date'], '%Y-%m-%d')
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_total = (end_date - baseline_date).days

    if days_total < 0:
        print("基准日期未到，无需计算")
        return 0

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
            base_price, curr_price = get_baseline_and_current_prices(
                prices, country_key, config['baseline_date']
            )

            if base_price is None or curr_price is None:
                continue

            # 插值计算当日价格（线性）
            if days_total > 0:
                ratio = day / days_total
                daily_price = base_price + (curr_price - base_price) * ratio
            else:
                daily_price = base_price

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

    for i, record in enumerate(daily_records):
        if i % 5 == 0 or i == len(daily_records) - 1:
            print(f"{record['date']:<12} ${record['daily_extra']:>14,.2f} ${record['cumulative_extra']:>14,.2f}")

    print("-" * 70)
    print(f"{'总计':<12} {'':<15} ${cumulative_extra_total:>14,.2f}")
    print("=" * 70)

    # 保存到 cumulative_records.json
    output_records = [{
        'date': r['date'],
        'daily_extra_total': r['daily_extra'],
        'cumulative_extra_total': r['cumulative_extra']
    } for r in daily_records]

    output_path = Path(__file__).parent.parent / 'data' / 'cumulative_records.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)

    print(f"详细记录已保存到: {output_path}")

    return cumulative_extra_total


if __name__ == "__main__":
    calculate_cumulative_extra()