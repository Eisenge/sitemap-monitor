# Sitemap Monitor

一个基于 GitHub Actions 的 Sitemap 变更监控工具。

## 功能
- 定时检查 Sitemap
- 检测新增 URL
- 检测删除 URL
- Telegram 通知
- 支持 sitemap index

## 使用步骤
1. 上传整个项目到 GitHub
2. 打开 Actions
3. 设置 Secrets:
   - TELEGRAM_TOKEN
   - TELEGRAM_CHAT_ID
4. 修改 config.json 添加需要监控的 sitemap
5. 等待 GitHub Actions 自动运行
