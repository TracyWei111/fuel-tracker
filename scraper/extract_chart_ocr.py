#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 OCR 从图表图像中提取柴油价格数据
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# 设置 UTF-8 输出
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from PIL import Image
import pytesseract

# 国家信息
COUNTRIES = {
    "China": {"name_cn": "中国", "currency": "CNY", "current_usd": 1.20, "current_local": 8.25},
    "Vietnam": {"name_cn": "越南", "currency": "VND", "current_usd": 1.72, "current_local": 45225},
    "Indonesia": {"name_cn": "印尼", "currency": "IDR", "current_usd": 0.86, "current_local": 14620},
    "Thailand": {"name_cn": "泰国", "currency": "THB", "current_usd": 1.50, "current_local": 48.68},
    "Malaysia": {"name_cn": "马来西亚", "currency": "MYR", "current_usd": 1.49, "current_local": 6.02},
    "Philippines": {"name_cn": "菲律宾", "currency": "PHP", "current_usd": 2.15, "current_local": 128.80},
    "Mexico": {"name_cn": "墨西哥", "currency": "MXN", "current_usd": 1.61, "current_local": 28.54},
    "Brazil": {"name_cn": "巴西", "currency": "BRL", "current_usd": 1.44, "current_local": 7.45},
}


def extract_chart_data(image_path: str, country_info: dict) -> dict:
    """
    从图表图像中提取价格数据
    """
    print(f"\n分析图表: {image_path}")

    try:
        img = Image.open(image_path)
        width, height = img.size
        print(f"  图像尺寸: {width}x{height}")

        # 转换为灰度图像提高 OCR 效果
        gray_img = img.convert('L')

        # 对整个图像进行 OCR
        full_text = pytesseract.image_to_string(gray_img)
        print(f"  OCR 完整文本 (前500字符):\n{full_text[:500]}")

        # 提取 Y 轴刻度（左侧区域）
        y_axis_img = gray_img.crop((0, 0, int(width * 0.12), height))
        y_axis_text = pytesseract.image_to_string(y_axis_img)
        print(f"  Y轴文本:\n{y_axis_text}")

        # 提取 Y 轴数字
        y_values = re.findall(r'(\d+\.?\d*)', y_axis_text)
        print(f"  Y轴刻度值: {y_values}")

        # 提取数据区域（中间部分）
        data_img = gray_img.crop((int(width * 0.12), 0, int(width * 0.95), height))
        data_text = pytesseract.image_to_string(data_img)

        # 提取所有数字
        all_numbers = re.findall(r'(\d+\.?\d*)', data_text)
        print(f"  数据区域数字: {all_numbers[:20]}")

        # 分析数据点位置
        # 图表通常有 8 个数据点对应 8 周
        # 我们需要识别折线的高度来推断数值

        return {
            "y_values": y_values,
            "all_numbers": all_numbers,
            "full_text": full_text
        }

    except Exception as e:
        print(f"  错误: {e}")
        return {"error": str(e)}


def analyze_chart_pixels(image_path: str, country_info: dict) -> list:
    """
    通过像素分析提取图表数据点
    分析折线图的线条位置来推断数值
    """
    print(f"\n像素分析: {image_path}")

    try:
        img = Image.open(image_path)
        width, height = img.size
        gray_img = img.convert('L')

        # 获取像素数据
        pixels = gray_img.load()

        # Y轴刻度区域（左侧）
        # 数据区域起点和终点
        chart_left = int(width * 0.12)
        chart_right = int(width * 0.95)
        chart_top = int(height * 0.1)
        chart_bottom = int(height * 0.85)

        # 提取 Y 轴刻度值
        y_axis_img = gray_img.crop((0, chart_top, chart_left, chart_bottom))
        y_axis_text = pytesseract.image_to_string(y_axis_img)
        y_values_str = re.findall(r'(\d+\.?\d*)', y_axis_text)

        if len(y_values_str) >= 2:
            y_min = float(y_values_str[0]) if y_values_str else 0
            y_max = float(y_values_str[-1]) if y_values_str else 100
        else:
            # 使用已知数据
            y_min = country_info["current_local"] * 0.7
            y_max = country_info["current_local"]

        print(f"  Y轴范围: {y_min} - {y_max}")

        # 扫描数据点
        # 8周数据，均匀分布在图表宽度上
        num_points = 8
        chart_width = chart_right - chart_left
        step = chart_width / (num_points - 1) if num_points > 1 else chart_width

        data_points = []

        for i in range(num_points):
            x = chart_left + int(i * step)

            # 在这个 X 位置，从上到下扫描找到数据线
            # 通常数据线是深色的（灰度值低）
            for y in range(chart_top, chart_bottom):
                pixel_val = pixels[x, y]
                # 检查是否是数据线（深色）
                if pixel_val < 100:  # 灰度阈值
                    # 找到了数据点
                    y_position = y
                    # 将像素位置转换为数值
                    # Y轴：顶部是最大值，底部是最小值
                    ratio = (chart_bottom - y_position) / (chart_bottom - chart_top)
                    value = y_min + ratio * (y_max - y_min)
                    data_points.append((i, x, y, value))
                    break

        print(f"  提取的数据点: {[round(p[3], 2) for p in data_points]}")

        return [round(p[3], 2) for p in data_points]

    except Exception as e:
        print(f"  错误: {e}")
        return []


def main():
    """
    主函数
    """
    charts_dir = Path(__file__).parent.parent / "charts"
    output_path = Path(__file__).parent.parent / "data" / "prices.json"

    print("=" * 60)
    print("从图表提取柴油价格数据")
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
            print(f"\n跳过 {country_info['name_cn']}: 图表不存在")
            continue

        # 提取数据
        extracted = extract_chart_data(str(chart_path), country_info)

        # 尝试像素分析
        pixel_values = analyze_chart_pixels(str(chart_path), country_info)

        if pixel_values and len(pixel_values) >= 8:
            prices_local = pixel_values[:8]
        else:
            # 如果像素分析失败，显示 OCR 结果让用户确认
            print(f"  无法自动提取，请手动确认数据")
            print(f"  已知当前价格: {country_info['current_local']} {country_info['currency']}")
            prices_local = None

        if prices_local:
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
    else:
        print("\n未能提取有效数据")


if __name__ == "__main__":
    main()