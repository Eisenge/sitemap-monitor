# Sitemap Monitor

GitHub Pages 中文监控后台 + Supabase 免费数据库/Auth + GitHub Actions 每小时扫描，不需要服务器。支持分组/网站真实 CRUD、自动发现 robots.txt 中的全部 Sitemap、sitemap index 和嵌套 sitemap、URL 新增/删除/总量历史、404/超时/XML 异常、robots.txt 变化及 Telegram 通知。

为保护免费数据库，每个网站默认最多处理 30 个 Sitemap、保存 5000 个 URL、分析 10 个新页面，并设有 180 秒单站时间上限。

新增 URL 会进入页面分析队列：每次扫描最多抓取 25 个尚未分析的 HTML 页面，保存 Title、Meta Description、H1、语言和本地提取的中英文内容关键词。Dashboard 会聚合近期关键词并列出竞品新页面；这些是页面内容信号，不冒充搜索量或 KD。

## 一次性配置（约 10 分钟）

1. 在 Supabase 新建免费项目。打开 **SQL Editor**，复制并运行 `supabase/schema.sql`。
   已部署旧版 schema 的项目，再额外运行一次 `supabase/keyword_analysis.sql`。
2. 打开 **Authentication → Providers → Email**。个人使用可关闭 Confirm email，减少一次邮件确认。
3. GitHub 仓库打开 **Settings → Secrets and variables → Actions**，添加：
   - `SUPABASE_URL`：Supabase Project URL
   - `SUPABASE_ANON_KEY`：Supabase Publishable key（或旧版 anon key）
   - `SUPABASE_SERVICE_ROLE_KEY`：Supabase Secret key（或旧版 service_role key；只能放 Secret，不能放网页）
   - `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`：可选，不用 Telegram 可不填
4. GitHub 打开 **Settings → Pages → Build and deployment**，Source 选择 **GitHub Actions**。
5. 打开 **Actions → Deploy dashboard → Run workflow**。完成后访问 `https://Eisenge.github.io/sitemap-monitor/`，使用 Supabase 中已确认的固定邮箱和密码登录。
6. 在网页添加分组、网站；然后运行一次 **Actions → Scan sitemaps → Run workflow**。以后每小时自动扫描。

## Telegram（可选）

联系 `@BotFather` 创建 bot 并取得 token。给 bot 发消息后访问 `https://api.telegram.org/bot<TOKEN>/getUpdates`，从 `chat.id` 取得 Chat ID。仅在 URL/robots 变化或扫描异常时通知。

## 安全与 Pages 子路径

网页只使用 anon key，并由 Supabase RLS 限制为当前账号数据；service-role key 只在 GitHub Actions Secrets 中。静态文件全部采用相对路径，原生兼容 `/sitemap-monitor/`，无需手改 base path。

## 本地测试

```bash
python3 -m pip install -r requirements.txt pytest
pytest -q
```

本地预览时，将 `site/config.example.js` 复制成 `site/config.js` 并填写 URL/anon key，再运行 `python3 -m http.server 8080 -d site`；`site/config.js` 已被 git 忽略。

## 每天 09:00 日报（Telegram + 邮箱）

工作流按北京时间每天 09:00 自动按网站分组汇总最近 24 小时的 URL 新增/删除和异常，并从新增页面的 Title、Meta Description、Meta Keywords、H1 与正文中提取综合关键词，同时列出代表性新页面及 H1。Telegram 使用上面的两个 Secrets；邮件以 Gmail 为例，再添加：`REPORT_EMAIL_TO`、`SMTP_HOST=smtp.gmail.com`、`SMTP_PORT=465`、`SMTP_USERNAME`、`SMTP_PASSWORD`（Google 应用专用密码）。两种渠道可单独启用。
