#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fuel Price Tracker Dashboard
Flask Web 应用，提供 API 和可视化界面
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, jsonify, request

# 添加项目路径
project_dir = Path(__file__).parent.parent
sys.path.insert(0, str(project_dir))

from engine.calculator import FuelCostCalculator

# 创建 Flask 应用
app = Flask(__name__)

# 配置
CONFIG_PATH = project_dir / 'config' / 'jnt_params.yaml'
PRICES_PATH = project_dir / 'data' / 'prices.json'
RECORDS_PATH = project_dir / 'data' / 'daily_records.json'


def get_calculator():
    """获取计算引擎实例"""
    return FuelCostCalculator(
        str(CONFIG_PATH),
        str(PRICES_PATH),
        str(RECORDS_PATH)
    )


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/summary')
def api_summary():
    """获取汇总数据 API"""
    try:
        calc = get_calculator()
        summary = calc.calculate_global_summary()
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/prices')
def api_prices():
    """获取价格数据 API"""
    try:
        calc = get_calculator()
        days = request.args.get('days', 30, type=int)
        trend = calc.get_trend_data(days)

        return jsonify({
            'success': True,
            'data': trend
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/countries')
def api_countries():
    """获取国家列表和当前数据"""
    try:
        calc = get_calculator()
        summary = calc.calculate_global_summary()

        countries_data = []
        for c in summary['countries_detail']:
            countries_data.append({
                'key': c['country_key'],
                'name': c['country_cn'],
                'diesel_price': c['diesel_price'],
                'baseline_diesel_price': c['baseline_diesel_price'],
                'price_change_pct': c['price_change_pct'],
                'cost_per_order': c['cost_per_order'],
                'baseline_cost_per_order': c['baseline_cost_per_order'],
                'daily_orders': c['daily_orders'],
                'order_weight': c['daily_orders'] / summary['total_orders'] if summary['total_orders'] > 0 else 0
            })

        return jsonify({
            'success': True,
            'data': countries_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/config')
def api_config():
    """获取配置信息"""
    try:
        import yaml
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return jsonify({
            'success': True,
            'data': {
                'baseline_date': config.get('baseline_date'),
                'countries': list(config.get('countries', {}).keys())
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


def main():
    """启动服务"""
    print("=" * 60)
    print("Fuel Price Tracker Dashboard")
    print("=" * 60)
    print(f"访问地址: http://localhost:5005")
    print("按 Ctrl+C 停止服务")
    print("=" * 60)

    app.run(host='localhost', port=5005, debug=True)


if __name__ == '__main__':
    main()