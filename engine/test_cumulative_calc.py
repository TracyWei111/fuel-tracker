#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cumulative_calc 的口径守卫：逐日实价、历史冻结。

跑法（无需任何测试框架）: python engine/test_cumulative_calc.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from engine.cumulative_calc import get_baseline_price, get_price_series, price_on  # noqa: E402

BASELINE = '2026-02-23'
SERIES = [('2026-02-17', 0.99), ('2026-02-24', 1.02), ('2026-03-03', 1.10)]

failures = []


def check(name, got, want):
    if got != want:
        failures.append(f"{name}: 得到 {got}，应为 {want}")


def test_series_parsing():
    raw = {'countries': {'China': {'diesel': [
        {'date': '2026-03-03', 'price': 1.10},
        {'date': '2026-02-17', 'price': 0.99},
    ]}}}
    check('序列按日期升序', get_price_series(raw, 'China'), [('2026-02-17', 0.99), ('2026-03-03', 1.10)])
    check('未知国家返回空', get_price_series(raw, 'Nowhere'), [])


def test_baseline_price():
    check('基准价取基准日当天或之后第一次报价', get_baseline_price(SERIES, BASELINE), 1.02)
    check('基准日之后没有报价时退回最后一条', get_baseline_price(SERIES, '2026-12-31'), 1.10)


def test_price_on():
    check('基准日与首次报价之间用基准价', price_on(SERIES, '2026-02-23', BASELINE, 1.02), 1.02)
    check('报价当天取当天的价', price_on(SERIES, '2026-02-24', BASELINE, 1.02), 1.02)
    check('两次报价之间向前填充', price_on(SERIES, '2026-02-28', BASELINE, 1.02), 1.02)
    check('新报价当天起用新价', price_on(SERIES, '2026-03-05', BASELINE, 1.02), 1.10)


def test_history_is_frozen_when_a_new_price_arrives():
    """这是用户要的那条性质：今天来了新价，昨天及以前的每日价格一个都不许变。"""
    past_days = ['2026-02-23', '2026-02-24', '2026-02-28', '2026-03-03', '2026-03-10']
    before = [price_on(SERIES, d, BASELINE, 1.02) for d in past_days]

    extended = SERIES + [('2026-03-11', 1.55)]
    after = [price_on(extended, d, BASELINE, 1.02) for d in past_days]

    check('新价到达后历史逐日价格不变', after, before)
    check('新价只影响它当天及之后', price_on(extended, '2026-03-11', BASELINE, 1.02), 1.55)


if __name__ == '__main__':
    for test in [test_series_parsing, test_baseline_price, test_price_on,
                 test_history_is_frozen_when_a_new_price_arrives]:
        test()

    if failures:
        print(f"失败 {len(failures)} 条:")
        for line in failures:
            print(f"  - {line}")
        sys.exit(1)
    print("全部通过")
