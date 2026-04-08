#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
燃油价格计算 - 使用真实汇率数据
数据来源：
- 本地货币价格: GlobalPetrolPrices.com
- 汇率: Yahoo Finance
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ========== 数据源 ==========
# 从 GlobalPetrolPrices 爬取的本地货币价格
local_prices = {
    'China': {
        'currency': 'CNY',
        'current_local': 8.25,
        'one_month_local': 6.72,
        'daily_orders': 56500000,
        'baseline_cost_per_order': 0.003
    },
    'Vietnam': {
        'currency': 'VND',
        'current_local': 35790,
        'one_month_local': 19460,
        'daily_orders': 6610000,
        'baseline_cost_per_order': 0.0325
    },
    'Indonesia': {
        'currency': 'IDR',
        'current_local': 14620,
        'one_month_local': 14620,
        'daily_orders': 10150000,
        'baseline_cost_per_order': 0.0325
    },
    'Thailand': {
        'currency': 'THB',
        'current_local': 39.88,
        'one_month_local': 30.56,
        'daily_orders': 6300000,
        'baseline_cost_per_order': 0.0325
    },
    'Malaysia': {
        'currency': 'MYR',
        'current_local': 5.52,
        'one_month_local': 3.04,
        'daily_orders': 2700000,
        'baseline_cost_per_order': 0.0325
    },
    'Philippines': {
        'currency': 'PHP',
        'current_local': 119.20,
        'one_month_local': 60.79,
        'daily_orders': 4920000,
        'baseline_cost_per_order': 0.0325
    },
    'Mexico': {
        'currency': 'MXN',
        'current_local': 28.54,
        'one_month_local': 26.15,
        'daily_orders': 530000,
        'baseline_cost_per_order': 0.050
    },
    'Brazil': {
        'currency': 'BRL',
        'current_local': 7.45,
        'one_month_local': 6.03,
        'daily_orders': 990000,
        'baseline_cost_per_order': 0.050
    }
}

# 从 Yahoo Finance 爬取的汇率 (1本地货币 = ?USD)
exchange_rates = {
    'China': {'feb23': 0.1448, 'mar30': 0.1447},
    'Vietnam': {'feb23': 0.00003857, 'mar30': 0.00003799},
    'Indonesia': {'feb23': 0.0001, 'mar30': 0.0001},
    'Thailand': {'feb23': 0.0322, 'mar30': 0.0303},
    'Malaysia': {'feb23': 0.2574, 'mar30': 0.2488},
    'Philippines': {'feb23': 0.0173, 'mar30': 0.0165},
    'Mexico': {'feb23': 0.0585, 'mar30': 0.0551},
    'Brazil': {'feb23': 0.1931, 'mar30': 0.1909}
}

# ========== 计算 ==========
print("=" * 100)
print("燃油价格计算 - 使用真实汇率数据")
print("数据来源: GlobalPetrolPrices.com (本地货币价格) + Yahoo Finance (汇率)")
print("=" * 100)

print(f"\n{'国家':<12} {'货币':<6} {'基准本地价':>12} {'当前本地价':>12} {'基准汇率':>12} {'当前汇率':>12} {'基准USD':>10} {'当前USD':>10} {'USD涨幅':>10}")
print("-" * 100)

results = {}
total_orders = 0
weighted_cost_sum = 0
baseline_weighted_sum = 0

for country, data in local_prices.items():
    currency = data['currency']
    current_local = data['current_local']
    one_month_local = data['one_month_local']
    daily_orders = data['daily_orders']
    baseline_cost = data['baseline_cost_per_order']

    rates = exchange_rates[country]
    feb23_rate = rates['feb23']
    mar30_rate = rates['mar30']

    # 计算USD价格
    baseline_usd = one_month_local * feb23_rate
    current_usd = current_local * mar30_rate

    # USD涨幅
    usd_change_pct = ((current_usd / baseline_usd) - 1) * 100 if baseline_usd > 0 else 0

    # 计算当前每单成本
    price_ratio = current_usd / baseline_usd if baseline_usd > 0 else 1
    current_cost = baseline_cost * price_ratio

    # 汇率变化
    fx_change_pct = ((mar30_rate / feb23_rate) - 1) * 100 if feb23_rate > 0 else 0

    results[country] = {
        'currency': currency,
        'baseline_local': one_month_local,
        'current_local': current_local,
        'baseline_usd': baseline_usd,
        'current_usd': current_usd,
        'usd_change_pct': usd_change_pct,
        'fx_change_pct': fx_change_pct,
        'baseline_cost': baseline_cost,
        'current_cost': current_cost,
        'daily_orders': daily_orders
    }

    total_orders += daily_orders
    weighted_cost_sum += current_cost * daily_orders
    baseline_weighted_sum += baseline_cost * daily_orders

    print(f"{country:<12} {currency:<6} {one_month_local:>12,.2f} {current_local:>12,.2f} "
          f"{feb23_rate:>12.6f} {mar30_rate:>12.6f} "
          f"${baseline_usd:>8.2f} ${current_usd:>8.2f} {usd_change_pct:>+9.1f}%")

print("-" * 100)

# 加权平均
weighted_cost = weighted_cost_sum / total_orders if total_orders > 0 else 0
baseline_weighted = baseline_weighted_sum / total_orders if total_orders > 0 else 0
extra_per_order = weighted_cost - baseline_weighted
daily_extra_total = extra_per_order * total_orders

print(f"\n{'汇总指标':<20} {'数值':>20}")
print("-" * 50)
print(f"{'总订单量':<20} {total_orders:>20,}")
print(f"{'加权每单成本':<20} ${weighted_cost:>19.4f}")
print(f"{'基准每单成本':<20} ${baseline_weighted:>19.4f}")
print(f"{'每单多付':<20} ${extra_per_order:>19.4f}")
print(f"{'当日多付总额':<20} ${daily_extra_total:>19,.2f}")

# 汇率变化汇总
print(f"\n{'汇率变化':<20}")
print("-" * 50)
for country, r in results.items():
    fx_change = r['fx_change_pct']
    print(f"{country:<12} {fx_change:>+10.2f}%")

print("\n" + "=" * 100)
print("Methodology:")
print("1. 本地货币价格来源: GlobalPetrolPrices.com (One month ago vs Current)")
print("2. 汇率来源: Yahoo Finance Historical Data (Feb 23 vs Mar 30)")
print("3. USD价格 = 本地货币价格 × 汇率(本地货币/USD)")
print("4. 汇率变化对USD价格有显著影响，尤其是PHP、MYR、THB、MXN")
print("=" * 100)