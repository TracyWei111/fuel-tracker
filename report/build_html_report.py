#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a static, self-contained HTML report with historical charts.

Replaces the unreachable bare-IP dashboard (46.225.172.130) as the delivered
artifact. Reads directly from data/prices.json and data/cumulative_records.json
(NOT data/daily_records.json, which is stale since 2026-04-02 and must never
back the cumulative headline). Writes reports/<date>.html.

Run after the daily scraper + engine/cumulative_calc.py have updated data/.
The generated page is self-contained (inline CSS/JS, no CDN, no network
needed to view it).
"""
import json
import sys
from pathlib import Path
from datetime import datetime

import yaml

REPORT_DIR = Path(__file__).parent
REPO = REPORT_DIR.parent
sys.path.insert(0, str(REPO))
from engine.calculator import FuelCostCalculator  # noqa: E402

CONFIG_PATH = REPO / "config" / "jnt_params.yaml"
PRICES_PATH = REPO / "data" / "prices.json"
CUMULATIVE_PATH = REPO / "data" / "cumulative_records.json"
DAILY_RECORDS_PATH = REPO / "data" / "daily_records.json"  # unused for KPI math; see module docstring


def build_payload() -> dict:
    calc = FuelCostCalculator(str(CONFIG_PATH), str(PRICES_PATH), str(DAILY_RECORDS_PATH))
    country_keys = list(calc.config["countries"].keys())

    prices_meta = json.loads(PRICES_PATH.read_text(encoding="utf-8"))
    cumulative = json.loads(CUMULATIVE_PATH.read_text(encoding="utf-8"))
    cumulative_sorted = sorted(cumulative, key=lambda r: r["date"])
    latest_cum = cumulative_sorted[-1]

    countries = {}
    baseline_cost_groups: dict[float, list[str]] = {}
    total_daily_orders = 0
    weighted_cost_sum = 0.0
    baseline_weighted_sum = 0.0

    for key in country_keys:
        cfg = calc.config["countries"][key]
        result = calc.calculate_country_cost(key)
        if "error" in result:
            countries[key] = {"name_cn": cfg.get("name_cn", key), "error": result["error"]}
            continue

        series = sorted(calc.prices.get(key, {}).get("diesel", []), key=lambda p: p["date"])
        baseline_price = result["baseline_diesel_price"]
        indexed = [
            {"date": p["date"], "index": round(p["price"] / baseline_price * 100, 2) if baseline_price else None}
            for p in series
        ]

        daily_orders = result["daily_orders"]
        cost_per_order = result["cost_per_order"]
        baseline_cost_per_order = result["baseline_cost_per_order"]
        daily_extra_est = (cost_per_order - baseline_cost_per_order) * daily_orders

        countries[key] = {
            "name_cn": cfg.get("name_cn", key),
            "series": [{"date": p["date"], "price": p["price"], "price_local": p.get("price_local"), "currency": p.get("currency")} for p in series],
            "indexed_series": indexed,
            "baseline_price": baseline_price,
            "latest_price": result["diesel_price"],
            "latest_date": result["diesel_date"],
            "pct_change": result["price_change_pct"],
            "cost_per_order": cost_per_order,
            "baseline_cost_per_order": baseline_cost_per_order,
            "daily_orders": daily_orders,
            "daily_extra_est": round(daily_extra_est, 2),
        }

        baseline_cost_groups.setdefault(baseline_cost_per_order, []).append(key)
        total_daily_orders += daily_orders
        weighted_cost_sum += cost_per_order * daily_orders
        baseline_weighted_sum += baseline_cost_per_order * daily_orders

    placeholder_groups = [ks for ks in baseline_cost_groups.values() if len(ks) > 1]

    weighted_cost_per_order = weighted_cost_sum / total_daily_orders if total_daily_orders else 0
    baseline_weighted_cost = baseline_weighted_sum / total_daily_orders if total_daily_orders else 0
    cumulative_change_pct = (
        (weighted_cost_per_order - baseline_weighted_cost) / baseline_weighted_cost * 100
        if baseline_weighted_cost
        else 0
    )

    baseline_date = calc.get_baseline_date()
    days_tracked = (
        datetime.strptime(latest_cum["date"], "%Y-%m-%d") - datetime.strptime(baseline_date, "%Y-%m-%d")
    ).days

    payload = {
        "meta": {
            "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": prices_meta.get("source", "GlobalPetrolPrices.com"),
            "prices_last_update": prices_meta.get("last_update"),
            "baseline_date": baseline_date,
            "cumulative_as_of": latest_cum["date"],
        },
        "kpi": {
            "cumulative_extra_total": latest_cum["cumulative_extra_total"],
            "daily_extra_total_latest": latest_cum["daily_extra_total"],
            "cumulative_change_pct": round(cumulative_change_pct, 2),
            "days_tracked": days_tracked,
            "total_daily_orders": total_daily_orders,
            "weighted_cost_per_order": round(weighted_cost_per_order, 4),
            "baseline_weighted_cost": round(baseline_weighted_cost, 4),
        },
        "cumulative_series": [
            {"date": r["date"], "cumulative": r["cumulative_extra_total"], "daily": r["daily_extra_total"]}
            for r in cumulative_sorted
        ],
        "country_order": country_keys,
        "countries": countries,
        "caveats": {
            "placeholder_baseline_cost_groups": placeholder_groups,
            "indonesia_currency_unconfirmed": True,
        },
    }
    return payload


def render_html(payload: dict) -> str:
    template_path = REPORT_DIR / "report_template.html"
    template = template_path.read_text(encoding="utf-8")
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return template.replace("__REPORT_DATA__", data_json)


def main():
    payload = build_payload()
    html = render_html(payload)

    reports_dir = REPO / "reports"
    reports_dir.mkdir(exist_ok=True)
    as_of = payload["meta"]["cumulative_as_of"].replace("-", "")
    dated_path = reports_dir / f"{as_of}.html"
    latest_path = reports_dir / "latest.html"

    dated_path.write_text(html, encoding="utf-8")
    latest_path.write_text(html, encoding="utf-8")

    print(f"wrote {dated_path}")
    print(f"wrote {latest_path}")
    print(f"cumulative_extra_total as of {payload['meta']['cumulative_as_of']}: "
          f"${payload['kpi']['cumulative_extra_total']:,.2f}")
    if payload["caveats"]["placeholder_baseline_cost_groups"]:
        for group in payload["caveats"]["placeholder_baseline_cost_groups"]:
            print(f"caveat: {group} share one placeholder baseline_cost_per_order in jnt_params.yaml")


if __name__ == "__main__":
    main()
