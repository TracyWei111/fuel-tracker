# Fuel Price Tracker

极兔(J&T Express)燃油价格追踪工具，用于追踪 10 个国家的柴油和汽油价格变化，计算每单油价成本涨幅。

## 快速开始

### 1. 配置参数

编辑 `config/jnt_params.yaml`，填入各国实际数据：

```yaml
countries:
  China:
    baseline_cost_per_order: 0.38  # 2月23日每单油价成本 ($)
    daily_orders: 500000           # 日单量
```

### 2. 启动 Dashboard

双击 `run.bat` 或运行：

```bash
python dashboard/app.py
```

然后访问 http://localhost:5005

## 目录结构

```
fuel-tracker/
├── config/
│   └── jnt_params.yaml     # 用户参数配置
├── data/
│   ├── prices.json         # 油价历史数据
│   ├── daily_records.json  # 每日计算记录
│   └── baseline.json       # 基准数据
├── scraper/
│   └── globalpetrol.py     # 爬虫脚本
├── engine/
│   └── calculator.py       # 计算引擎
├── dashboard/
│   ├── app.py              # Flask 服务
│   └── templates/
│       └── index.html      # Web 界面
├── run.bat                 # 启动 Dashboard
└── update.bat              # 更新数据
```

## 计算公式

```
柴油价格涨幅 = 当日柴油价格 / 2月23日柴油价格

当日每单成本 = 基准每单成本 × 柴油价格涨幅

全球加权每单成本 = Σ(各国当日成本 × 单量占比)

累计多付总额 = Σ(从2/23到今天的每日多付总额)
```

## 数据来源

- GlobalPetrolPrices.com
- 柴油价格每周更新一次

## 注意事项

1. 印尼的价格数据需要手动确认（当地货币换算问题）
2. 需要定期更新 jnt_params.yaml 中的单量数据
3. 建议每天运行一次数据更新

## API 接口

| 接口 | 说明 |
|------|------|
| GET /api/summary | 获取汇总数据 |
| GET /api/prices | 获取价格趋势 |
| GET /api/countries | 获取国家列表 |
| GET /api/config | 获取配置信息 |