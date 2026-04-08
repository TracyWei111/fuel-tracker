#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuel Cost Calculator Engine
计算极兔每单油价成本、涨幅、累计多付等指标
"""

import sys
import os
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class FuelCostCalculator:
    """燃油成本计算引擎"""

    def __init__(self, config_path: str, prices_path: str, records_path: str):
        """
        初始化计算引擎

        Args:
            config_path: jnt_params.yaml 路径
            prices_path: prices.json 路径
            records_path: daily_records.json 路径
        """
        self.config_path = config_path
        self.prices_path = prices_path
        self.records_path = records_path

        # 加载配置
        self.config = self._load_config()
        self.prices = self._load_prices()
        self.records = self._load_records()

    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_prices(self) -> dict:
        """加载价格数据"""
        with open(self.prices_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _load_records(self) -> list:
        """加载历史记录"""
        if os.path.exists(self.records_path):
            with open(self.records_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_records(self):
        """保存历史记录"""
        with open(self.records_path, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)

    def get_baseline_date(self) -> str:
        """获取基准日期"""
        return self.config.get('baseline_date', '2026-02-23')

    def get_latest_price(self, country_key: str, fuel_type: str = 'diesel') -> dict:
        """
        获取某国某燃料的最新价格

        Returns:
            {'price': float, 'date': str} 或 {'error': str}
        """
        try:
            country_data = self.prices.get(country_key, {})
            fuel_data = country_data.get(fuel_type, [])

            if not fuel_data:
                return {'error': f'No {fuel_type} data for {country_key}'}

            # 返回最新的价格记录
            latest = sorted(fuel_data, key=lambda x: x['date'])[-1]
            return {'price': latest['price'], 'date': latest['date']}

        except Exception as e:
            return {'error': str(e)}

    def get_baseline_price(self, country_key: str, fuel_type: str = 'diesel') -> dict:
        """
        获取某国某燃料的基准价格（2月23日或最接近的日期）

        Returns:
            {'price': float, 'date': str} 或 {'error': str}
        """
        baseline_date = self.get_baseline_date()

        try:
            country_data = self.prices.get(country_key, {})
            fuel_data = country_data.get(fuel_type, [])

            if not fuel_data:
                return {'error': f'No {fuel_type} data for {country_key}'}

            # 查找基准日期或最接近的价格
            for record in sorted(fuel_data, key=lambda x: x['date']):
                if record['date'] >= baseline_date:
                    return {'price': record['price'], 'date': record['date']}

            # 如果没有找到，返回最早的价格
            earliest = sorted(fuel_data, key=lambda x: x['date'])[0]
            return {'price': earliest['price'], 'date': earliest['date']}

        except Exception as e:
            return {'error': str(e)}

    def calculate_country_cost(self, country_key: str, use_baseline: bool = False) -> dict:
        """
        计算某国的每单油价成本

        Args:
            country_key: 国家代码
            use_baseline: 是否使用基准价格

        Returns:
            {
                'country_key': str,
                'country_cn': str,
                'diesel_price': float,
                'diesel_date': str,
                'cost_per_order': float,
                'baseline_cost_per_order': float,
                'price_change_pct': float
            }
        """
        country_config = self.config['countries'].get(country_key, {})

        # 获取柴油价格
        if use_baseline:
            price_data = self.get_baseline_price(country_key, 'diesel')
        else:
            price_data = self.get_latest_price(country_key, 'diesel')

        if 'error' in price_data:
            return {'error': price_data['error'], 'country_key': country_key}

        current_diesel_price = price_data['price']
        diesel_date = price_data['date']

        # 获取基准柴油价格
        baseline_price_data = self.get_baseline_price(country_key, 'diesel')
        baseline_diesel_price = baseline_price_data.get('price', current_diesel_price)

        # 获取配置参数
        baseline_cost = country_config.get('baseline_cost_per_order', 0)
        daily_orders = country_config.get('daily_orders', 0)
        country_cn = country_config.get('name_cn', country_key)

        # 计算当前每单成本
        # 公式: 当前每单成本 = 基准每单成本 × (当前柴油价格 / 基准柴油价格)
        if baseline_diesel_price > 0:
            price_ratio = current_diesel_price / baseline_diesel_price
            current_cost = baseline_cost * price_ratio
        else:
            current_cost = baseline_cost
            price_ratio = 1.0

        # 涨幅
        price_change_pct = (price_ratio - 1) * 100 if baseline_diesel_price > 0 else 0

        return {
            'country_key': country_key,
            'country_cn': country_cn,
            'diesel_price': current_diesel_price,
            'diesel_date': diesel_date,
            'baseline_diesel_price': baseline_diesel_price,
            'cost_per_order': current_cost,
            'baseline_cost_per_order': baseline_cost,
            'price_change_pct': price_change_pct,
            'daily_orders': daily_orders
        }

    def calculate_global_summary(self) -> dict:
        """
        计算全球汇总指标

        Returns:
            {
                'weighted_cost_per_order': float,
                'baseline_weighted_cost': float,
                'cumulative_change_pct': float,
                'extra_per_order': float,
                'daily_extra_total': float,
                'cumulative_extra_total': float,
                'total_orders': int,
                'countries_detail': list
            }
        """
        countries_detail = []
        total_orders = 0
        weighted_cost_sum = 0
        baseline_weighted_sum = 0

        # 计算每个国家的数据
        for country_key in self.config['countries'].keys():
            result = self.calculate_country_cost(country_key)

            if 'error' not in result:
                countries_detail.append(result)

                weight = result['daily_orders']
                total_orders += weight
                weighted_cost_sum += result['cost_per_order'] * weight
                baseline_weighted_sum += result['baseline_cost_per_order'] * weight

        # 计算加权平均
        if total_orders > 0:
            weighted_cost_per_order = weighted_cost_sum / total_orders
            baseline_weighted_cost = baseline_weighted_sum / total_orders
        else:
            weighted_cost_per_order = 0
            baseline_weighted_cost = 0

        # 计算涨幅和多付金额
        extra_per_order = weighted_cost_per_order - baseline_weighted_cost
        cumulative_change_pct = (extra_per_order / baseline_weighted_cost * 100) if baseline_weighted_cost > 0 else 0

        daily_extra_total = extra_per_order * total_orders

        # 计算累计多付
        # 如果今天的记录已存在，不重复累加
        today = datetime.now().strftime('%Y-%m-%d')
        today_exists = any(r.get('date') == today for r in self.records)

        if today_exists:
            # 已包含今天的记录
            cumulative_extra_total = sum(r.get('daily_extra_total', 0) for r in self.records)
        else:
            # 历史记录 + 今天
            cumulative_extra_total = sum(r.get('daily_extra_total', 0) for r in self.records) + daily_extra_total

        return {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'weighted_cost_per_order': round(weighted_cost_per_order, 4),
            'baseline_weighted_cost': round(baseline_weighted_cost, 4),
            'cumulative_change_pct': round(cumulative_change_pct, 2),
            'extra_per_order': round(extra_per_order, 4),
            'daily_extra_total': round(daily_extra_total, 2),
            'cumulative_extra_total': round(cumulative_extra_total, 2),
            'total_orders': total_orders,
            'countries_detail': countries_detail
        }

    def save_daily_record(self, summary: dict):
        """保存每日记录"""
        record = {
            'date': summary['date'],
            'weighted_cost_per_order': summary['weighted_cost_per_order'],
            'baseline_weighted_cost': summary['baseline_weighted_cost'],
            'extra_per_order': summary['extra_per_order'],
            'daily_extra_total': summary['daily_extra_total'],
            'total_orders': summary['total_orders']
        }

        # 检查是否已有该日期的记录
        dates = [r['date'] for r in self.records]
        if record['date'] not in dates:
            self.records.append(record)
            self._save_records()
            print(f"已保存 {record['date']} 的记录")
        else:
            print(f"{record['date']} 的记录已存在")

    def get_trend_data(self, days: int = 30) -> dict:
        """
        获取趋势数据用于图表

        Returns:
            {
                'dates': ['2026-02-23', '2026-02-24', ...],
                'countries': {
                    'China': {'prices': [...], 'changes': [...]},
                    ...
                }
            }
        """
        result = {
            'dates': [],
            'countries': {}
        }

        # 从 prices.json 收集所有唯一日期
        all_dates = set()
        for country_key in self.config['countries'].keys():
            country_prices = self.prices.get(country_key, {}).get('diesel', [])
            for p in country_prices:
                all_dates.add(p['date'])

        # 排序日期
        result['dates'] = sorted(list(all_dates))

        # 从 prices.json 获取各国的价格趋势
        for country_key in self.config['countries'].keys():
            country_prices = self.prices.get(country_key, {}).get('diesel', [])

            if country_prices:
                # 获取基准价格
                baseline = self.get_baseline_price(country_key, 'diesel')
                baseline_price = baseline.get('price', 1)

                # 按日期排序
                sorted_prices = sorted(country_prices, key=lambda x: x['date'])

                prices = []
                changes = []

                for p in sorted_prices:
                    prices.append(p['price'])
                    if baseline_price > 0:
                        changes.append(round((p['price'] / baseline_price - 1) * 100, 2))
                    else:
                        changes.append(0)

                result['countries'][country_key] = {
                    'prices': prices,
                    'changes': changes,
                    'country_cn': self.config['countries'][country_key].get('name_cn', country_key)
                }

        return result


def main():
    """主函数"""
    # 获取路径
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    config_path = project_dir / 'config' / 'jnt_params.yaml'
    prices_path = project_dir / 'data' / 'prices.json'
    records_path = project_dir / 'data' / 'daily_records.json'

    print("=" * 60)
    print("Fuel Cost Calculator")
    print("=" * 60)

    # 创建计算引擎
    calc = FuelCostCalculator(str(config_path), str(prices_path), str(records_path))

    # 计算汇总
    summary = calc.calculate_global_summary()

    print(f"\n日期: {summary['date']}")
    print(f"全球加权每单成本: ${summary['weighted_cost_per_order']:.4f}")
    print(f"基准每单成本: ${summary['baseline_weighted_cost']:.4f}")
    print(f"累计涨幅: {summary['cumulative_change_pct']:.2f}%")
    print(f"每单多付: ${summary['extra_per_order']:.4f}")
    print(f"当日多付总额: ${summary['daily_extra_total']:,.2f}")
    print(f"累计多付总额: ${summary['cumulative_extra_total']:,.2f}")
    print(f"总单量: {summary['total_orders']:,}")

    print("\n各国明细:")
    print("-" * 60)
    for c in summary['countries_detail']:
        print(f"  {c['country_cn']}: 柴油 ${c['diesel_price']:.2f}/L, "
              f"每单 ${c['cost_per_order']:.4f}, "
              f"涨幅 {c['price_change_pct']:.1f}%")

    # 保存记录
    calc.save_daily_record(summary)


if __name__ == "__main__":
    main()