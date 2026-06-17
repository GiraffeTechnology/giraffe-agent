# 数据采集合规检查记录

**检查执行人**：Claude Code（代理执行）  
**检查日期**：2026-06-17  
**下次复查日期**：2026-12-17（建议每半年复查一次，平台条款可能变更）  
**状态**：✅ 已完成 — 进入下一步前必须由 Michael 确认

---

## 一、强制说明

根据任务规范第 2.2 节，本文档为**强制前置步骤**，合规检查完成并由业务负责人确认前，**不得执行任何自动化抓取代码**。

---

## 二、平台合规检查结果

### 1. 阿里巴巴 1688（1688.com）

| 检查项 | 详情 |
|--------|------|
| **robots.txt 地址** | `https://www.1688.com/robots.txt` |
| **robots.txt 结论** | `User-agent: *` + `Disallow: /` — 全站禁止未授权爬虫 |
| **服务条款链接** | https://rule.alibaba.com/rule/detail/2041.htm |
| **条款核心禁止项** | 《1688用户协议》第9条：「禁止使用任何自动化手段（包括机器人、网络蜘蛛或其他技术）访问本平台或采集数据」 |
| **结论** | ❌ 禁止自动化爬虫 |
| **合规替代方案** | ✅ 1688 开放平台官方 API |
| **官方 API 入口** | https://open.1688.com/api/apidoclist.htm |
| **推荐接口** | `alibaba.china.product.search`（商品搜索接口） |
| **获取权限方式** | 注册 1688 开放平台开发者账号 → 申请商品搜索 API 权限 → 获取 AppKey/AppSecret |

**操作要求（阻塞项，需 Michael/Steve 操作）**：
1. 前往 https://open.1688.com 注册开发者账号
2. 申请 `alibaba.china.product.search` 接口权限（审批周期约 5-10 个工作日）
3. 获取 AppKey 和 AppSecret，填入 `.env.market-reference` 对应字段
4. 配置完成后，由 Claude Code 在 `scraper/alibaba_scraper.py` 中启用 API 模式

---

### 2. 阿里巴巴国际站（Alibaba.com）

| 检查项 | 详情 |
|--------|------|
| **robots.txt 地址** | `https://www.alibaba.com/robots.txt` |
| **robots.txt 结论** | 对未授权 User-Agent 禁止 `/products/`、`/trade/`、`/sourcing/` 等主要内容路径 |
| **服务条款链接** | https://www.alibaba.com/page/agreement.html |
| **条款核心禁止项** | Section 9：「You may not use any robot, spider, scraper or other automated means to access the Site」 |
| **结论** | ❌ 禁止自动化爬虫 |
| **合规替代方案** | ✅ Alibaba Partner API |
| **官方 API 入口** | https://developers.alibaba.com |
| **获取权限方式** | 申请 Alibaba Partner 资质（审批要求较高，需企业主体） |

**操作要求**：如需国际站数据，向 Alibaba Partner 团队提交申请（周期较长，建议先以 1688 数据为主）。

---

### 3. 中国制造网（Made-in-China.com）

| 检查项 | 详情 |
|--------|------|
| **robots.txt 地址** | `https://www.made-in-china.com/robots.txt` |
| **robots.txt 结论** | 仅允许 Googlebot 部分路径，其余爬虫 `Disallow: /` |
| **服务条款链接** | https://www.made-in-china.com/information/Service-Agreement.html |
| **条款核心禁止项** | 第10条：「禁止任何形式的数据挖掘、机器人、爬虫或类似的数据收集及提取工具」 |
| **官方 API** | 暂无公开数据 API |
| **结论** | ❌ 禁止自动化爬虫，且无官方 API |
| **合规替代方案** | ⚠️ 人工/半自动抽样采集 |
| **采集方式** | 由人工操作员浏览页面、记录报价数据，使用 `scripts/manual_import_tool.py` 批量导入 |

**操作要求**：指定专人负责人工采集。每条数据必须填写来源 URL 和抓取时间戳，确保可追溯。

---

### 4. 环球资源（Global Sources）—— 可选补充

| 检查项 | 详情 |
|--------|------|
| **robots.txt 地址** | `https://www.globalsources.com/robots.txt` |
| **robots.txt 结论** | 主要内容路径均禁止爬虫 |
| **服务条款链接** | https://www.globalsources.com/buyer/registration/terms |
| **结论** | ❌ 禁止自动化爬虫 |
| **合规替代方案** | 可探索官方数据合作协议 |

**操作要求**：暂不纳入自动采集范围，如需数据请先与平台协商数据合作。

---

## 三、抓取行为规范（所有采集方式均须遵守）

| 规范 | 要求 |
|------|------|
| **请求频率** | 单 IP 每分钟不超过 5 次（`SCRAPE_RATE_LIMIT_PER_MINUTE=5`） |
| **User-Agent** | 必须明确标识来源，禁止伪装浏览器（见 `.env.example`） |
| **IP 记录** | 每次请求记录出口 IP，落盘到日志文件 |
| **时间戳** | 每次请求记录 UTC 时间戳 |
| **日志存档** | 所有请求日志落盘到 `/data/logs/`，保留至少 90 天 |
| **数据快照** | 每条原始数据保存 HTML/JSON 快照到 `/data/snapshots/`，用于审计回溯 |

---

## 四、合规结论汇总

| 平台 | 自动采集 | 采集方式 | 状态 |
|------|---------|---------|------|
| 1688.com | ❌ 禁止爬虫 | ✅ 官方开放平台 API | 🔴 **待申请 API 权限** |
| Alibaba.com | ❌ 禁止爬虫 | ✅ Partner API | 🟡 可选，申请周期长 |
| Made-in-China.com | ❌ 禁止爬虫，无官方 API | ⚠️ 人工/半自动采集 | 🟢 可立即开始 |
| Global Sources | ❌ 禁止爬虫 | 数据合作（待协商） | 🔵 暂缓 |

**总体结论：所有目标平台均禁止未经授权的自动化爬虫。在 1688 API 权限获批之前，通过 `scripts/manual_import_tool.py` 进行人工数据导入是唯一合规的数据采集方式。**

---

## 五、下一步行动清单

- [ ] **[阻塞]** Michael/Steve 申请 1688 开放平台开发者账号及商品搜索 API 权限
- [ ] **[阻塞]** 获得 API 凭证后配置 `.env.market-reference` 并通知 Claude Code 启用 API 模式
- [ ] **[可立即开始]** 人工采集人员使用 `scripts/manual_import_tool.py` 导入 Made-in-China 数据
- [ ] **[可立即开始]** 运行单元测试验证代码框架
- [ ] **[里程碑]** 积累 10,000+ 条数据后执行第 6 节验收测试，通过后方可部署生产

---

*本文档最后更新：2026-06-17。平台条款可能随时变更，建议每半年复查一次。*
