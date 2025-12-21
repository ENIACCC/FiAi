# AGENTS.md - AI Agent Instructions for FiAi

## 🎯 Project Overview

You're building **FiAi** for someone with programming experience. Please:
- Explain key trade-offs efficiently with best practices
- Provide working code with small, reviewable changes
- Keep PRD boundaries (no investment advice, no profit claims)
- Balance MVP speed with architecture that can evolve

## 📚 What We're Building

**App:** FiAi Web MVP  
**Purpose:** 面向新手的 A 股 AI 辅助投研与策略系统（研究与决策支持 + 可配置策略 + 回测/模拟盘验证）  
**Primary User Story (PRD):** 新手/轻度交易者：希望理解信号来源、风险与失效条件，愿意用“回测/模拟盘”验证规则  
**Tech Stack:**
- **Frontend (Vite + React + TS + antd + echarts + zustand + react-router-dom + axios):** 快速迭代 Web UI，图表与信息密度界面落地
- **Backend (Django 5 + DRF + JWT + akshare + pandas):** 业务编排与 API，承载数据采集、策略/回测任务入口
- **Database (MVP 目标 PostgreSQL; 当前仓库含 SQLite):** 行情时序与事件索引，支撑回测/回放的可复现读取
- **Deployment (MVP 目标 Docker Compose):** 单机低成本部署，后续可扩容
**Learning Goals:** Django/DRF API 设计、A 股行情与事件对齐、可复现回测与风控口径、React 数据密度界面

**Must-Have Features (PRD 页面清单):**
- 工作台 `Dashboard`
- 自选&分组 `Watchlist`
- 个股研究 `Stock Page`
- 策略实验室 `Strategy Lab`
- 回测报告 `Backtest Report`
- 复盘 `Journal / AnalysisHistory`
- 设置 `Settings`

**Success Metrics (PRD):**
- Web 端形成闭环“选股 → 盯盘 → 复盘 → 策略验证/回测 → 规则生成（用于模拟盘）”
- 所有策略输出可解释、可追溯、可复现
- 最大回撤（Max Drawdown）`<= 25%`（回测/模拟盘同口径可验证）

## 🛠 Setup Instructions

### Prerequisites Check
```bash
# Ensure these are installed:
node --version
npm --version
git --version
python --version
```

### Project Initialization
```bash
# Frontend
cd E:\01_Project\FiAi\fronted
npm install
npm run dev

# Backend (Windows example)
cd E:\01_Project\FiAi\backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Project Structure
```
E:\01_Project\FiAi\
├─ fronted\
│  ├─ src\
│  │  ├─ api\index.ts
│  │  ├─ components\{AIChat.tsx,StockChart.tsx,StockList.tsx}
│  │  ├─ layout\MainLayout.tsx
│  │  ├─ pages\{Dashboard.tsx,StockPage.tsx,AnalysisHistory.tsx,Settings.tsx,Login.tsx,Register.tsx}
│  │  ├─ store\useStore.ts
│  │  └─ App.tsx
│  └─ package.json
└─ backend\
   ├─ api\{models.py,serializers.py,views.py,urls.py}
   ├─ finance_project\settings.py
   ├─ manage.py
   └─ requirements.txt
```

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** 跑通“登录/自选/个股页/AI 对话”的现有链路，并建立数据与任务的扩展骨架

1. **Stabilize Local Dev**
   - Ensure frontend can call backend `/api/*` successfully
   - Ensure JWT login works and requests include `Authorization`

2. **Baseline Data Access**
   - Confirm AkShare endpoints used in `backend/api/views.py` are stable
   - Add caching boundaries for heavy endpoints (short TTL)

3. **Test Foundation**
   - Action: 登录后访问 Dashboard，调用市场概览接口
   - Expected: 页面渲染成功，接口无 401/跨域错误

### Phase 2: Core Features (Week 2–4)
**Goal:** 完成 PRD 的 MVP 必选页面闭环，并落地“验证模式”门槛

#### Feature 1: 自选&分组 Watchlist（分组列表 + 股票表格 + 快速过滤）
**Learning Focus:** 前端表格信息密度设计 + 后端过滤与分页

1. **Extend Watchlist API**
   - Add filtering for ST/停牌/流动性不足/数据质量差（先以规则字段与占位实现）

2. **Implement Watchlist Page**
   - Route: `/watchlist`
   - UI: 分组列表 + 表格列配置 + 快速过滤

3. **Test Feature**
   - Action: 新建分组 → 加入股票 → 切换分组查看
   - Expected: 列表一致、无重复、删除生效

#### Feature 2: 事件流 + 信号解释（个股页右侧证据栏 + 时间线）
**Learning Focus:** 事件时间对齐到 K 线与可审计数据结构

1. **Event Model + Read API**
   - Persist `event_time` and `market_effective_time`
   - Provide `GET /api/events?symbol=&start=&end=`

2. **Stock Page Integration**
   - Plot markers on chart by `market_effective_time`
   - Render signal cards with required fields

3. **Test Feature**
   - Action: 打开个股页，加载 K 线与事件标注
   - Expected: 事件点可定位，证据可追溯到来源

#### Feature 3: 策略实验室 + L1 回测 + 回测报告
**Learning Focus:** 可复现回测配置、同口径风控、样本外验证与反过拟合提醒

1. **Strategy Templates API**
   - Provide `GET /api/strategies/templates` with 3+ templates

2. **Backtest Runner (L1)**
   - Provide `POST /api/backtests` and `GET /api/backtests/{run_id}`
   - Enforce max drawdown gating for “导出规则到模拟盘”

3. **Backtest Report UI**
   - Route: `/backtests/:runId`
   - Render metrics + stability set + trade list + reproducible config

### Phase 3: Polish & Deploy (Week 5–6)
**Goal:** 新手不误导机制落地 + 模拟盘骨架 + 低成本部署

1. **Add Error Handling**
   - Standardize API error surfaces (401, 429, 5xx) and UX feedback

2. **Style & Responsiveness**
   - Use antd grid + drawers for finscope 风格三栏布局

3. **Deploy to Docker Compose**
   - Backend: gunicorn + nginx
   - Services: postgres + redis + celery worker/beat

## 💡 Learning Resources

### For Django REST Framework:
- **Quick Start:** https://www.django-rest-framework.org/tutorial/quickstart/
- **Deep Dive:** https://www.django-rest-framework.org/api-guide/

### For React Router v6:
- **Quick Start:** https://reactrouter.com/en/main/start/tutorial

### When Stuck:
1. **Documentation:** Django / DRF / antd / echarts official docs
2. **AI Help:** 提供“复现步骤 + 期望/实际 + 相关日志 + 相关文件路径”再求解

## 🐛 Common Issues & Solutions

### "401 Unauthorized"
**Why it happens:** 前端未携带 JWT 或后端接口权限配置不一致  
**Fix:**
```bash
# Check frontend localStorage has token
# Check backend endpoint permission_classes and JWT settings
```

### "CORS error"
**Why it happens:** 前后端端口不同，后端未允许来源  
**Fix:**
```bash
# Enable django-cors-headers and set CORS_ALLOWED_ORIGINS
```

### "AkShare timeout / data fetch failed"
**Why it happens:** 数据源不稳定或频率过高  
**Fix:**
```bash
# Add short TTL caching and retries with backoff in worker jobs
```

## 📝 Code Patterns to Use

### Component Structure
```tsx
import { useEffect, useState } from 'react';
import { Card } from 'antd';

export function FeatureCard() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      setLoading(true);
      try {
        if (!cancelled) setData({});
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  return <Card loading={loading}>{JSON.stringify(data)}</Card>;
}
```

### API Calls
```ts
import api from '../api';

export async function fetchSomething() {
  const resp = await api.get('market/index/');
  return resp.data;
}
```

### State Management
```ts
import { create } from 'zustand';

type AppState = {
  token: string | null;
  setToken: (token: string | null) => void;
};

export const useAppStore = create<AppState>((set) => ({
  token: null,
  setToken: (token) => set({ token }),
}));
```

## 🧪 Testing Your Features

### Manual Testing Checklist:
- [ ] **Auth:** 注册/登录后访问受保护路由正常
- [ ] **Watchlist:** 分组增删改查，自选增删，重复约束正确
- [ ] **Stock Page:** K 线加载、指标叠加、事件标注展示正常
- [ ] **Strategy Lab:** 能创建回测任务并查看结果
- [ ] **Backtest Gate:** 样本外缺失/MaxDD 超限时阻断导出到模拟盘
- [ ] **Error cases:** 超时/限流/401 时 UX 明确

### Simple Automated Test:
```ts
// Not configured in repo yet.
// If adding, prefer Vitest for frontend and Django test client for backend.
```

## 📊 Understanding the Architecture

### Data Flow:
```
[User Action] → [React Page] → [axios /api/*] → [DRF View] → [DB/AkShare/DeepSeek] → [JSON] → [UI Update]
```

### Key Concepts Explained:
1. **market_effective_time:** 事件转为“可交易生效时间”，避免未来函数与盘后信息泄漏
2. **Reproducible backtest config:** 回测结果必须能用同一份配置再次跑出相同结果
3. **Same code path:** 回测与模拟盘共享撮合/费用/风控，避免口径漂移

## 🚀 Deployment Guide

### Pre-deployment:
- [ ] 确认无敏感信息写入日志
- [ ] 配置 CORS、JWT、DB 连接
- [ ] 回测与任务相关的超时/重试/限流参数已设置

### Deploy to Docker Compose:
1. **Build Images**
   ```bash
   # Add docker-compose.yml (services: backend, frontend, postgres, redis, celery)
   ```
2. **Configure Env**
   - Set `DATABASE_URL`, `REDIS_URL`, `DJANGO_SECRET_KEY`
3. **Verify**
   - Healthcheck API + frontend pages + a sample backtest run

### Post-deployment:
- [ ] 走通一次完整流程：选股→个股→回测→报告→导出到模拟盘（门槛通过）

## 🎯 Definition of Done

Your MVP is complete when:
- [ ] All PRD pages work: `Dashboard`、`Watchlist`、`Stock Page`、`Strategy Lab`、`Backtest Report`、`Journal/AnalysisHistory`、`Settings`
- [ ] “研究模式/验证模式”机制生效：缺样本外验证或超回撤时阻断导出到模拟盘
- [ ] 回测/模拟盘同口径：撮合/费用/风控复用同一实现
- [ ] Deployed and accessible via URL（本地/服务器均可）

## 📁 Reference Documents

- **Requirements:** `vibe-coding-prompt-template-main/result/PRD-FiAi-MVP.md`
- **Technical Plan:** `vibe-coding-prompt-template-main/result/TechDesign-FiAi-MVP.md`
- **Agent Template Notes:** `vibe-coding-prompt-template-main/part4-notes-for-agent.md`

## 💬 Final Notes

Remember:
- 不输出具体个股买卖建议，不承诺盈利
- 任何信号都必须可解释、可追溯、可复现
- 先把 L1 回测 + 门槛阻断做对，再扩到分钟线与更细撮合
