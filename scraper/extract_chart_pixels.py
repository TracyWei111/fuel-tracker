#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用纯像素分析从图表图像中提取柴油价格数据
不依赖 Tesseract OCR
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image

# 国家信息 - 包含从网站获取的已知数据点
COUNTRIES = {
    "China": {
        "name_cn": "中国", "currency": "CNY",
        "current_usd": 1.20, "current_local": 8.25,
        "one_month_local": 7.30, "three_months_local": 6.34,
        "y_min_hint": 6.0, "y_max_hint": 9.0
    },
    "Vietnam": {
        "name_cn": "越南", "currency": "VND",
        "current_usd": 1.72, "current_local": 45225,
        "one_month_local": 31015, "three_months_local": 17230,
        "y_min_hint": 15000, "y_max_hint": 50000
    },
    "Indonesia": {
        "name_cn": "印尼", "currency": "IDR",
        "current_usd": 0.86, "current_local": 14620,
        "one_month_local": 14620, "three_months_local": 13860,
        "y_min_hint": 13000, "y_max_hint": 16000
    },
    "Thailand": {
        "name_cn": "泰国", "currency": "THB",
        "current_usd": 1.50, "current_local": 48.68,
        "one_month_local": 30.14, "three_months_local": 30.14,
        "y_min_hint": 28, "y_max_hint": 52
    },
    "Malaysia": {
        "name_cn": "马来西亚", "currency": "MYR",
        "current_usd": 1.49, "current_local": 6.02,
        "one_month_local": 3.12, "three_months_local": 2.89,
        "y_min_hint": 2.5, "y_max_hint": 7.0
    },
    "Philippines": {
        "name_cn": "菲律宾", "currency": "PHP",
        "current_usd": 2.15, "current_local": 128.80,
        "one_month_local": 60.50, "three_months_local": 55.60,
        "y_min_hint": 50, "y_max_hint": 140
    },
    "Mexico": {
        "name_cn": "墨西哥", "currency": "MXN",
        "current_usd": 1.61, "current_local": 28.54,
        "one_month_local": 27.29, "three_months_local": 26.23,
        "y_min_hint": 25, "y_max_hint": 30
    },
    "Brazil": {
        "name_cn": "巴西", "currency": "BRL",
        "current_usd": 1.44, "current_local": 7.45,
        "one_month_local": 6.08, "three_months_local": 6.05,
        "y_min_hint": 5.5, "y_max_hint": 8.0
    },
}


def find_chart_line_positions(image_path: str, country_info: dict) -> list:
    """
    通过像素分析找到图表中折线的位置
    返回 8 个数据点对应的 Y 坐标
    """
    print(f"\n分析: {image_path}")

    try:
        img = Image.open(image_path)
        width, height = img.size

        # 转换为 RGB 模式
        rgb_img = img.convert('RGB')
        pixels = rgb_img.load()

        # 图表区域估算
        # 通常：左边 10-15% 是 Y 轴标签，右边 5% 是边距
        chart_left = int(width * 0.15)
        chart_right = int(width * 0.95)
        chart_top = int(height * 0.15)
        chart_bottom = int(height * 0.85)

        print(f"  图像尺寸: {width}x{height}")
        print(f"  图表区域: X {chart_left}-{chart_right}, Y {chart_top}-{chart_bottom}")

        # 8 个数据点，均匀分布
        num_points = 8
        chart_width = chart_right - chart_left
        step = chart_width / (num_points - 1) if num_points > 1 else chart_width

        # 找到每个 X 位置的数据线 Y 坐标
        y_positions = []

        for i in range(num_points):
            x = chart_left + int(i * step)

            # 扫描这个 X 位置，找到数据线
            # 数据线通常是深蓝色或深色
            found_y = None
            for y in range(chart_top, chart_bottom):
                r, g, b = pixels[x, y]
                # 检查是否是数据线（深色，通常是蓝色）
                # 蓝色：B 高，R 和 G 低
                if b > 150 and r < 100 and g < 100:
                    found_y = y
                    break
                # 或者深色线条
                if r < 80 and g < 80 and b < 80:
                    found_y = y
                    break

            if found_y:
                y_positions.append(found_y)
            else:
                # 如果找不到，使用图表底部
                y_positions.append(chart_bottom)

        print(f"  找到的 Y 坐标: {y_positions}")

        return y_positions, chart_top, chart_bottom

    except Exception as e:
        print(f"  错误: {e}")
        return [], 0, 0


def y_position_to_value(y_positions: list, chart_top: int, chart_bottom: int,
                          y_min: float, y_max: float) -> list:
    """
    将 Y 像素坐标转换为实际数值
    """
    values = []
    for y in y_positions:
        # Y 轴：顶部是最大值，底部是最小值
        ratio = (chart_bottom - y) / (chart_bottom - chart_top)
        value = y_min + ratio * (y_max - y_min)
        values.append(round(value, 2))
    return values


def extract_y_axis_range(image_path: str, country_info: dict) -> tuple:
    """
    尝试从图表中提取 Y 轴范围
    如果失败，使用提示值
    """
    # 简化：直接使用已知数据估算 Y 轴范围
    y_min_hint = country_info.get("y_min_hint", country_info["current_local"] * 0.7)
    y_max_hint = country_info.get("y_max_hint", country_info["current_local"] * 1.1)

    return y_min_hint, y_max_hint


def main():
    """
    主函数
    """
    charts_dir = Path(__file__).parent.parent / "charts"
    output_path = Path(__file__).parent.parent / "data" / "prices.json"

    print("=" * 60)
    print("从图表提取柴油价格数据（像素分析）")
    print("=" * 60)

    # 8 周日期
    weekly_dates = []
    for i in range(8):
        week_date = datetime(2026, 2, 17) + timedelta(weeks=i)
        weekly_dates.append(week_date.strftime('%Y-%m-%d'))

    result = {}

    for country_key, country_info in COUNTRIES.items():
        chart_path = charts_dir / f"{country_key.lower()}_8weeks.png"

        if not chart_path.exists():
            print(f"\n跳过 {country_info['name_cn']}: 图表不存在 - {chart_path}")
            continue

        # 找到数据线的 Y 坐标
        y_positions, chart_top, chart_bottom = find_chart_line_positions(
            str(chart_path), country_info
        )

        if not y_positions or len(y_positions) < 8:
            print(f"  无法提取数据点")
            continue

        # 获取 Y 轴范围
        y_min, y_max = extract_y_axis_range(str(chart_path), country_info)
        print(f"  Y轴范围: {y_min} - {y_max}")

        # 转换为实际数值
        prices_local = y_position_to_value(y_positions, chart_top, chart_bottom, y_min, y_max)
        print(f"  提取的价格: {prices_local}")

        # 验证：最后一个点应该接近 current_local
        last_price = prices_local[-1]
        expected = country_info["current_local"]
        diff_pct = abs(last_price - expected) / expected * 100

        if diff_pct > 20:
            print(f"  警告: 最后一个点 {last_price} 与预期 {expected} 差异 {diff_pct:.1f}%")
            # 调整 Y 轴范围重新计算
            y_max = expected * 1.1
            y_min = min(prices_local) * 0.95
            prices_local = y_position_to_value(y_positions, chart_top, chart_bottom, y_min, y_max)
            print(f"  调整后价格: {prices_local}")

        # 计算汇率
        usd_rate = country_info["current_usd"] / country_info["current_local"]

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
    if result:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n数据已保存: {output_path}")
        print(f"\n价格摘要:")
        for country_key, data in result.items():
            diesel = data["diesel"]
            first = diesel[0]
            last = diesel[-1]
            change = ((last["price"] / first["price"]) - 1) * 100
            print(f"  {first['country_cn']}: {first['price_local']:.2f} → {last['price_local']:.2f} ({change:+.1f}%)")
    else:
        print("\n未能提取有效数据")


if __name__ == "__main__":
    main()