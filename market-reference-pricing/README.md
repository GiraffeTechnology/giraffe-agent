# market-reference-pricing

> **重要声明（必读）：** 本模块产出仅为**市场参考价格区间**，不构成 GPM 正式定价依据。任何将本模块输出直接用于覆盖 GPM 核心定价参数的行为均属于**误用**。

本模块从 B2B 平台（1688、Alibaba.com、Made-in-China.com）采集公开报价数据，计算 SKU 加权参考价格区间，供 GPM（Giraffe Pricing Model）冷启动用户辅助参考。

## 架构隔离约束

| 约束 | 说明 |
|------|------|
| **代码分支隔离** | 禁止合并入 `main/master`，必须在独立特性分支开发 |
| **容器隔离** | 独立 Docker 容器，独立 PostgreSQL schema（`market_reference`） |
| **调用隔离** | GPM 仅通过 HTTP API 查询，不存在 Python `import` 依赖 |
| **UI 标注要求** | 所有输出必须标注：「市场参考价格区间（第三方平台公开报价统计，非成交价，仅供参考）」 |

## 快速启动

```bash
# 1. 配置环境变量
cp .env.example .env.market-reference
vi .env.market-reference  # 填入 DASHSCOPE_API_KEY、DB_PASSWORD 等

# 2. 启动服务
docker-compose up --build

# 3. 执行数据库迁移
docker-compose exec api alembic upgrade head

# 4. 运行单元测试
docker-compose exec api pytest tests/ -v
```

## 独立迁移验证

以下命令必须在全新环境下成功运行，不依赖主仓库任何代码：

```bash
git clone <仅market-reference-pricing子目录或独立仓库>
cd market-reference-pricing
docker-compose up --build
# 应能独立完成：抓取 -> 抽取 -> 匹配 -> 聚合 -> API查询 全流程
```

## 数据流

```
B2B平台(官方API/人工) → scraper → HTML/API快照 → qwen_field_extractor
  → 二次正则校验 → raw_market_quotes → weighted_average
  → sku_reference_price → reference_price_api → GPM(HTTP调用)
```

## 数据追溯字段

每条记录可逐条追溯：
- `source_url`：原始页面/API URL
- `raw_html_snapshot_path`：HTML/JSON 快照本地路径
- `scraped_at`：抓取时间戳（UTC）
- `seller_id`：卖家标识
- `extraction_method`：固定值 `qwen_nlp_extraction`
- `extraction_confidence`：Qwen 抽取置信度（低于 0.8 需人工复核）

## 合规说明

详见 `docs/data-sourcing-compliance.md`。**所有目标平台均禁止未经授权的自动化爬虫**，必须通过官方 API 或人工采集获取数据。在 1688 开放平台 API 权限申请完成前，使用 `scripts/manual_import_tool.py` 进行人工导入。

## 验收标准摘要

部署到生产前必须满足（详见任务规范第 6 节）：
- `raw_market_quotes` 记录数 ≥ 10,000 条
- 独立 SKU 覆盖 ≥ 200 个
- 至少 50% SKU 类别聚合报价数 ≥ 15 条
- 价格字段抽取准确率 ≥ 98%
- 20 组手工验证边界 case 全部通过

---

*本模块不属于 GPM 核心计算逻辑。请勿将本模块的任何输出直接写入 GPM 定价公式、参数表或任何会被 GPM 确定性计算直接消费的字段。*
