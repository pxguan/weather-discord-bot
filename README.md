# GitHub Actions - RSS Daily Report

自动获取 Andrej Karpathy 精选 RSS 内容并生成飞书日报。

## 功能特性

- 📡 自动获取 RSS Pack 中的所有订阅源
- 🔍 筛选过去 24 小时的内容更新
- 📖 抓取原文内容进行深度阅读
- 🤖 智能生成结构化日报
- 📄 自动发布到飞书文档

## 使用方法

### 1. 配置飞书 API 凭证

在 GitHub 仓库的 Settings → Secrets and variables → Actions 中添加以下 secrets：

- `FEISHU_APP_ID`: 飞书应用 ID
- `FEISHU_APP_SECRET`: 飞书应用 Secret

#### 获取飞书凭证

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 在应用的「凭证与基础信息」页面获取 App ID 和 App Secret
4. 配置应用权限：
   - `docx:document` - 文档操作权限
   - `wiki:wiki` - 知识库权限
   - `drive:drive` - 云空间权限

### 2. 启用 GitHub Actions

推送代码到 GitHub 后，Actions 会自动启用。

### 3. 手动触发（可选）

在 Actions 页面，选择 "RSS Daily Report to Feishu" workflow，点击 "Run workflow" 按钮即可手动触发。

## 定时任务

默认配置为每天 UTC 0:00（北京时间 8:00）自动运行。

如需修改时间，编辑 `.github/workflows/scheduled-rss-daily.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # 分钟 小时 日 月 星期
```

## 日报格式

生成的日报包含：

- 📊 今日数据统计
- 🔥 核心主题提取
- 📖 分类内容展示
- 💡 编者观察

模板示例：

```markdown
> Andrej Karpathy 精选的信源资讯汇总 | 共 N 条更新

---

## 🔥 核心主题

**AI**、**Machine Learning**、**Deep Learning**

---

## 📖 Example Source

### [Article Title](link)

Article content summary...

*来源: Source Name | 2024-01-01 12:00*

---

## 📊 今日数据

- **10** 条 RSS 更新
- **8** 篇精选深度阅读
- **5** 个信息源
- **3** 个核心主题

## 💡 编者观察

---

*本日报由 AI 自动生成 | 数据源：[Andrej Karpathy curated RSS](https://youmind.com/rss/pack/andrej-karpathy-curated-rss)*
```

## 本地测试

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export FEISHU_APP_ID="your_app_id"
export FEISHU_APP_SECRET="your_app_secret"

# 运行脚本
python scripts/rss_daily_report.py
```

## 故障排查

### 1. 飞书 API 认证失败

- 检查 App ID 和 App Secret 是否正确
- 确认应用已启用并发布
- 检查应用权限配置

### 2. RSS 获取失败

- 检查网络连接
- 确认 RSS Pack URL 可访问
- 查看 GitHub Actions 日志

### 3. 文档创建失败

- 检查飞书应用权限
- 确认有创建文档的权限
- 检查飞书 API 配额限制

## 文件结构

```
.
├── .github/
│   └── workflows/
│       ├── scheduled-rss-daily.yml      # RSS 日报 workflow
│       └── scheduled-weather-discord.yml # 天气推送 workflow
├── scripts/
│   └── rss_daily_report.py              # RSS 日报生成脚本
├── requirements.txt                      # Python 依赖
└── README.md                            # 说明文档
```

## 安全提示

⚠️ **重要：请勿在代码中直接写入 API 凭证！**

- 所有敏感信息应配置在 GitHub Secrets 中
- 不要将 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET` 提交到代码库
- 定期更换 API 凭证以确保安全

## 许可证

MIT License
