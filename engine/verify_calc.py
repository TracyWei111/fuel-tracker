#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证累计多付计算
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# 配置数据
config = {
    'China': {'baseline_cost': 0.003, 'daily_orders': 56500000, 'name_cn': '中国'},
    'Vietnam': {'baseline_cost': 0.0325, 'daily_orders': 6610000, 'name_cn': '越南'},
    'Indonesia': {'baseline_cost': 0.0325, 'daily_orders': 10150000, 'name_cn': '印尼'},
    'Thailand': {'baseline_cost': 0.0325, 'daily_orders': 6300000, 'name_cn': '泰国'},
    'Malaysia': {'baseline_cost': 0.0325, 'daily_orders': 2700000, 'name_cn': '马来西亚'},
    'Philippines': {'baseline_cost': 0.0325, 'daily_orders': 4920000, 'name_cn': '菲律宾'},
    'Mexico': {'baseline_cost': 0.050, 'daily_orders': 530000, 'name_cn': '墨西哥'},
    'Brazil': {'baseline_cost': 0.050, 'daily_orders': 990000, 'name_cn': '巴西'},
}

# 实际爬取的价格数据
prices = {
    'China': {'baseline': 0.98, 'current': 1.20},      # 涨幅 22.4%
    'Vietnam': {'baseline': 0.74, 'current': 1.36},    # 涨幅 83.8%
    'Indonesia': {'baseline': 0.86, 'current': 0.86},  # 涨幅 0%
    'Thailand': {'baseline': 0.94, 'current': 1.22},   # 涨幅 29.8%
    'Malaysia': {'baseline': 0.75, 'current': 1.36},   # 涨幅 81.3%
    'Philippines': {'baseline': 1.01, 'current': 1.97}, # 涨幅 95.0%
    'Mexico': {'baseline': 1.46, 'current': 1.59},     # 涨幅 8.9%
    'Brazil': {'baseline': 1.13, 'current': 1.40},     # 涨幅 23.9%
}

print("=" * 80)
print("验证计算 - 2026-03-30 最终日多付金额")
print("=" * 80)
print(f"{'国家':<10} {'基准价格':>8} {'当前价格':>8} {'涨幅':>8} {'基准成本':>10} {'当前成本':>10} {'每单多付':>10} {'当日多付':>15}")
print("-" * 80)

total_daily_extra = 0
total_orders = 0

for country, cfg in config.items():
    p = prices[country]
    price_ratio = p['current'] / p['baseline']
    pct_change = (price_ratio - 1) * 100

    baseline_cost = cfg['baseline_cost']
    current_cost = baseline_cost * price_ratio
    extra_per_order = current_cost - baseline_cost
    daily_extra = extra_per_order * cfg['daily_orders']

    total_daily_extra += daily_extra
    total_orders += cfg['daily_orders']

    print(f"{cfg['name_cn']:<10} ${p['baseline']:>6.2f} ${p['current']:>6.2f} {pct_change:>6.1f}% "
          f"${baseline_cost:>8.4f} ${current_cost:>8.4f} ${extra_per_order:>8.4f} ${daily_extra:>13,.2f}")

print("-" * 80)
print(f"{'总计':<10} {'':<8} {'':<8} {'':<8} {'':<10} {'':<10} {'':<10} ${total_daily_extra:>13,.2f}")
print(f"\n总订单量: {total_orders:,}")
print(f"当日多付总额: ${total_daily_extra:,.2f}")

# 计算累计多付 (线性插值，从基准日到当前日)
print("\n" + "=" * 80)
print("累计多付计算 (线性插值)")
print("=" * 80)

from datetime import datetime, timedelta

baseline_date = datetime(2026, 2, 23)
end_date = datetime(2026, 3, 30)
days_total = (end_date - baseline_date).days  # 35 天

print(f"基准日期: {baseline_date.strftime('%Y-%m-%d')}")
print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")
print(f"天数: {days_total} 天")

# 线性插值累计
cumulative = 0
print(f"\n{'日期':<12} {'当日多付':>15} {'累计多付':>18}")
print("-" * 50)

for day in range(days_total + 1):
    date = baseline_date + timedelta(days=day)

    # 当日多付 = 最终日多付 * (day / days_total)
    # 使用梯形积分
    daily_extra = total_daily_extra * day / days_total
    cumulative += daily_extra if day == 0 else total_daily_extra * (day / days_total)

    if day % 7 == 0 or day == days_total:
        print(f"{date.strftime('%Y-%m-%d'):<12} ${daily_extra:>13,.2f} ${cumulative:>16,.2f}")

# 正确的梯形积分
print("\n正确计算 (梯形积分):")
total_cumulative = 0
for day in range(1, days_total + 1):
    # 当日的多付金额 = 最终日多付 * (day / days_total)
    daily_extra = total_daily_extra * day / days_total
    total_cumulative += daily_extra

print(f"累计多付总额 (逐日累加): ${total_cumulative:,.2f}")

# 简化公式: 累计 = 最终日多付 * days / 2
simplified = total_daily_extra * days_total / 2
print(f"累计多付总额 (简化公式): ${simplified:,.2f}")