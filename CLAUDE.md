# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

maaker.ai 个人品牌落地页，承接小红书引流 + AI 日报邮件订阅。纯静态 HTML + Cloudflare Pages Functions，无构建步骤。

## Deploy

```bash
# 部署到 Cloudflare Pages（无需构建）
npx wrangler pages deploy . --project-name=maaker-landing --commit-dirty=true
```

推送 main 分支也会自动触发部署。

## Architecture

```
index.html              ← 单文件落地页（HTML + Tailwind CDN + inline JS）
functions/api/
  subscribe.js          ← POST /api/subscribe — 邮箱订阅 + 发欢迎邮件
  dispatch.js           ← POST /api/dispatch — 批量群发日报（Bearer Token 鉴权）
  subscribers.js        ← GET /api/subscribers — 查询订阅者数量（Bearer Token 鉴权）
```

**数据流：**
- 用户在页面订阅 → subscribe 写 KV + 发 Resend 欢迎邮件
- n8n 定时触发 → x-follower 生成 AI 摘要 → POST /api/dispatch → 读 KV 邮箱列表 → Resend 群发

## Key Bindings & Services

| 服务 | 说明 |
|------|------|
| Cloudflare KV `SUBSCRIBERS` | 存储订阅者邮箱，namespace ID: `2ce5a721b482469197ddf12852761c27` |
| Resend | 邮件发送，发件人 `ai-daily@maaker.ai` |
| n8n (Richard 100.99.77.112:5678) | 定时任务，workflow `ai-digest-dispatch` 每天 8:00 触发 |

## Environment Variables (Cloudflare Pages Settings)

- `RESEND_API_KEY` — Resend API 密钥
- `DISPATCH_SECRET` — dispatch/subscribers 端点的 Bearer Token

## KV Data Structure

- `{email}` key → `{ email, subscribedAt }` — 单条记录，用于去重
- `email_list` key → `["a@b.com", "c@d.com"]` — 邮箱数组，供 dispatch 批量读取

## Conventions

- 前端无框架，纯 HTML + Tailwind CSS CDN，不引入构建工具
- 配色：白底 + teal (#0D9488) 点缀
- 移动端优先，桌面端用 `md:` 前缀扩展
- API 函数放 `functions/api/` 目录，遵循 Cloudflare Pages Functions 规范
