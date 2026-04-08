#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GlobalPetrolPrices.com Scraper
使用 Playwright CDP 模式抓取各国柴油和汽油价格
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 设置 UTF-8 输出
sys.stdout = sys.stderr = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# Playwright 导入
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("需要安装 playwright: pip install playwright")
    sys.exit(1)

# 配置
BASE_URL = "https://www.globalpetrolprices.com"
CDP_URL = "http://localhost:9222"

# 国家列表（与 URL 路径对应）
COUNTRIES = {
    "China": {"url_name": "China", "name_cn": "中国"},
    "Vietnam": {"url_name": "Vietnam", "name_cn": "越南"},
    "Indonesia": {"url_name": "Indonesia", "name_cn": "印尼"},
    "Thailand": {"url_name": "Thailand", "name_cn": "泰国"},
    "Malaysia": {"url_name": "Malaysia", "name_cn": "马来西亚"},
    "Philippines": {"url_name": "Philippines", "name_cn": "菲律宾"},
    "Mexico": {"url_name": "Mexico", "name_cn": "墨西哥"},
    "Brazil": {"url_name": "Brazil", "name_cn": "巴西"},
    "South_Korea": {"url_name": "South-Korea", "name_cn": "韩国"},
    "USA": {"url_name": "USA", "name_cn": "美国"},
}

# 燃料类型
FUEL_TYPES = ["diesel", "gasoline"]

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def scrape_country_price(page, country_key: str, fuel_type: str) -> dict:
    """
    抓取单个国家的燃料价格

    Returns:
        {
            "price": float,  # USD per liter
            "date": str,     # YYYY-MM-DD
            "raw_text": str  # 原始价格文本
        }
    """
    country_info = COUNTRIES[country_key]
    url_name = country_info["url_name"]

    url = f"{BASE_URL}/{url_name}/{fuel_type}_prices/"
    logger.info(f"抓取: {url}")

    try:
        await page.goto(url, timeout=30000)
        await page.wait_for_load_state('domcontentloaded', timeout=15000)

        # 提取当前价格表格
        # 页面结构: table -> rowgroup -> row "Current price X.XX"
        price_table = await page.locator('table').first.locator('tbody tr').all()

        price = None
        date = None

        for row in price_table:
            cells = await row.locator('td').all()
            if len(cells) >= 2:
                label = await cells[0].text_content()
                value = await cells[1].text_content()

                label = label.strip()
                value = value.strip()

                if "Current price" in label:
                    # 提取数字
                    try:
                        price = float(value)
                    except ValueError:
                        # 可能包含其他字符，尝试提取
                        import re
                        match = re.search(r'(\d+\.?\d*)', value)
                        if match:
                            price = float(match.group(1))

                if "Last update" in label:
                    # 提取日期 YYYY-MM-DD
                    date = value

        if price is None:
            logger.warning(f"未能提取价格: {country_key} - {fuel_type}")
            return {"price": None, "date": None, "error": "price_not_found"}

        logger.info(f"成功: {country_info['name_cn']} {fuel_type} = ${price:.2f}/L ({date})")

        return {
            "price": price,
            "date": date,
            "country_cn": country_info["name_cn"],
            "fuel_type": fuel_type
        }

    except Exception as e:
        logger.error(f"抓取失败: {country_key} - {fuel_type}: {e}")
        return {"price": None, "date": None, "error": str(e)}


async def scrape_all_prices() -> dict:
    """
    抓取所有国家的柴油和汽油价格
    """
    results = {}

    async with async_playwright() as p:
        # 连接到已有 Chrome (CDP 模式)
        try:
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            logger.info(f"已连接到 Chrome CDP: {CDP_URL}")
        except Exception as e:
            logger.error(f"无法连接到 Chrome CDP: {e}")
            logger.error("请确保 Chrome 已启动并开启远程调试端口 9222")
            return results

        # 获取现有上下文或创建新的
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
        else:
            context = await browser.new_context()

        # 使用现有页面或创建新的
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()

        # 抓取每个国家
        for country_key in COUNTRIES:
            results[country_key] = {}

            for fuel_type in FUEL_TYPES:
                data = await scrape_country_price(page, country_key, fuel_type)
                results[country_key][fuel_type] = data

                # 等待一下避免请求过快
                await asyncio.sleep(1)

        # 不关闭浏览器（CDP 模式下浏览器是外部的）
        await browser.close()

    return results


def save_prices(prices: dict, output_path: str):
    """
    保存价格数据到 JSON 文件
    格式兼容设计文档中的 prices.json
    """
    # 读取现有数据
    existing = {}
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            try:
                existing = json.load(f)
            except:
                existing = {}

    # 合合新数据
    today = datetime.now().strftime('%Y-%m-%d')

    for country_key, country_data in prices.items():
        if country_key not in existing:
            existing[country_key] = {
                "diesel": [],
                "gasoline": []
            }

        for fuel_type in ["diesel", "gasoline"]:
            fuel_data = country_data.get(fuel_type, {})
            price = fuel_data.get("price")
            date = fuel_data.get("date") or today

            if price is not None:
                # 检查是否已有该日期的数据
                dates = [d["date"] for d in existing[country_key][fuel_type]]
                if date not in dates:
                    existing[country_key][fuel_type].append({
                        "date": date,
                        "price": price,
                        "country_cn": fuel_data.get("country_cn", "")
                    })
                    logger.info(f"添加新数据: {country_key} {fuel_type} {date} ${price:.2f}")
                else:
                    logger.info(f"跳过重复: {country_key} {fuel_type} {date}")

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    logger.info(f"数据已保存: {output_path}")


def main():
    """
    主函数
    """
    # 确定输出路径
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    output_path = project_dir / "data" / "prices.json"

    logger.info("=" * 50)
    logger.info("Fuel Price Scraper - GlobalPetrolPrices.com")
    logger.info("=" * 50)

    # 运行抓取
    prices = asyncio.run(scrape_all_prices())

    if prices:
        save_prices(prices, str(output_path))
        logger.info(f"抓取完成，共 {len(prices)} 个国家")
    else:
        logger.error("抓取失败，无数据")


if __name__ == "__main__":
    main()