#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
精确计算累计多付金额
每一天用「当天实际挂出的价格」（即当日或之前最近一次抓到的报价，向前填充）计算，
逐日累加到当天。已经过去的日子不会因为今天的新价格而被改写。

2026-09-29 之前用的是「从基准价线性插值到当前价」，当前价一变，整段历史跟着重算，
累计头条数字会被追溯改写（2026-09-25 实测：一周 +$5.61M 里有 $3.85M 是历史改写）。
"""

import sys
import json
from datetime import datetime, timedelta, timezone
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


def get_price_series(prices_data, country_key):
    """取某国柴油价的历史观测序列，按日期升序返回 [(date_str, price), ...]"""
    country_data = prices_data.get('countries', {}).get(country_key, {})
    diesel_list = country_data.get('diesel', country_data.get('diesel_history', []))
    series = [
        (r['date'], r.get('price', r.get('price_usd')))
        for r in diesel_list
        if r.get('price', r.get('price_usd')) is not None
    ]
    return sorted(series, key=lambda x: x[0])


def get_baseline_price(series, baseline_date_str):
    """基准价 = 基准日当天或之后第一次抓到的报价（口径与 engine/calculator.py 保持一致）"""
    for date_str, price in series:
        if date_str >= baseline_date_str:
            return price
    return series[-1][1] if series else None


def price_on(series, date_str, baseline_date_str, baseline_price):
    """当天实际挂出的价格：当日或之前最近一次抓到的报价（向前填充）。

    基准日到第一次抓到报价之间的空档用基准价填，避免用基准日之前的旧价去和
    基准价比较（那会让第一天凭空出现正负偏差）。
    """
    current = None
    for obs_date, price in series:
        if obs_date > date_str:
            break
        if obs_date >= baseline_date_str:
            current = price
    return current if current is not None else baseline_price


def calculate_cumulative_extra():
    """计算累计多付金额"""
    config = load_config()
    prices = load_prices()

    # 时间范围 - 动态计算到今天
    baseline_date = datetime.strptime(config['baseline_date'], '%Y-%m-%d')
    end_date = datetime.now(timezone(timedelta(hours=8))).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    days_total = (end_date - baseline_date).days

    if days_total < 0:
        print("基准日期未到，无需计算")
        return 0

    print("=" * 70)
    print("精确累计多付计算 (逐日实价, 历史不改写)")
    print("=" * 70)
    print(f"基准日期: {baseline_date.strftime('%Y-%m-%d')}")
    print(f"结束日期: {end_date.strftime('%Y-%m-%d')}")
    print(f"计算天数: {days_total} 天")
    print()

    # 各国价格序列与基准价只解析一次
    country_series = {}
    for country_key in config['countries']:
        series = get_price_series(prices, country_key)
        if not series:
            continue
        country_series[country_key] = (series, get_baseline_price(series, config['baseline_date']))

    # 每日累计
    daily_records = []
    cumulative_extra_total = 0

    for day in range(days_total + 1):
        current_date = baseline_date + timedelta(days=day)
        current_date_str = current_date.strftime('%Y-%m-%d')

        daily_extra = 0
        countries_detail = []

        for country_key, country_config in config['countries'].items():
            baseline_cost = country_config.get('baseline_cost_per_order', 0)
            daily_orders = country_config.get('daily_orders', 0)
            country_cn = country_config.get('name_cn', country_key)

            if country_key not in country_series:
                continue
            series, base_price = country_series[country_key]
            if base_price is None:
                continue

            # 当天实际挂出的价格（向前填充），不受之后价格变动影响
            daily_price = price_on(series, current_date_str, config['baseline_date'], base_price)

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
    report_history_drift(output_path, output_records)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_records, f, ensure_ascii=False, indent=2)

    print(f"详细记录已保存到: {output_path}")

    return cumulative_extra_total


def report_history_drift(output_path, new_records, tolerance=0.01):
    """对比即将写入的记录与已入库的记录，任何一天被改写都要点名。

    逐日实价口径下历史应当是冻结的，唯一会改写历史的情况是上游把某个历史日期的
    报价改了。那种情况要在日志里看得见，不能静默盖掉。
    """
    if not output_path.exists():
        return
    with open(output_path, 'r', encoding='utf-8') as f:
        old_by_date = {r['date']: r for r in json.load(f)}

    latest_new = new_records[-1]['date'] if new_records else None
    drifted = [
        (r['date'], old_by_date[r['date']]['cumulative_extra_total'], r['cumulative_extra_total'])
        for r in new_records
        if r['date'] in old_by_date
        and r['date'] != latest_new
        and abs(old_by_date[r['date']]['cumulative_extra_total'] - r['cumulative_extra_total']) > tolerance
    ]

    if not drifted:
        print("历史校验: 已入库的历史日期全部保持不变")
        return

    print(f"历史校验: 警告 —— {len(drifted)} 个历史日期的累计值被改写（通常意味着上游改了某天的历史报价）:")
    for date_str, old_value, new_value in drifted[:5]:
        print(f"  {date_str}: ${old_value:,.2f} -> ${new_value:,.2f}")
    if len(drifted) > 5:
        print(f"  ... 另有 {len(drifted) - 5} 天")
    raise ValueError('Historical cumulative values changed; publication blocked')


if __name__ == "__main__":
    calculate_cumulative_extra()
