# iQuant 前端 Vue 3 + TypeScript 实施说明

## 📦 项目结构

```
frontend/
├── src/
│   ├── api/              # API 接口封装
│   │   └── index.ts
│   ├── layouts/          # 布局组件
│   │   └── MainLayout.vue
│   ├── lib/              # 第三方库配置
│   │   └── supabase.ts   # Supabase 客户端
│   ├── router/           # 路由配置
│   │   └── index.ts
│   ├── stores/           # Pinia 状态管理
│   │   └── user.ts
│   ├── utils/            # 工具函数
│   │   └── request.ts
│   ├── views/            # 页面视图
│   │   ├── Login.vue
│   │   ├── Dashboard.vue
│   │   ├── Strategies.vue
│   │   └── Backtest.vue
│   ├── App.vue
│   └── main.ts
├── .env                  # 环境变量（需要配置）
├── .env.example          # 环境变量示例
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 配置 Supabase

复制环境变量示例文件并填写您的 Supabase 配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入您的 Supabase 项目信息：

```env
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

**获取 Supabase 配置：**
1. 登录 [Supabase Dashboard](https://supabase.com/dashboard)
2. 选择您的项目
3. 进入 Settings > API
4. 复制 Project URL 和 anon public key

### 3. 启动开发服务器

```bash
npm run dev
```

访问 http://localhost:3000

### 4. 构建生产版本

```bash
npm run build
```

## 📋 已完成的功能

### ✅ 核心架构
- Vue 3 + TypeScript 项目初始化
- Vite 构建配置
- Element Plus UI 框架集成
- Vue Router 路由配置（带权限守卫）
- Pinia 状态管理
- Axios HTTP 客户端（带拦截器）

### ✅ 认证系统（Supabase）
- Supabase Auth 集成
- 邮箱/密码登录页面
- 用户注册功能
- 密码重置功能
- JWT Token 自动管理
- 路由权限守卫
- 会话持久化

### ✅ 布局系统
- 响应式侧边栏布局
- 顶部导航栏
- 用户信息显示
- 菜单折叠/展开

### ✅ 页面组件
- **Login**: 登录页面
- **Dashboard**: 仪表盘（系统状态、快速操作）
- **Strategies**: 策略列表管理
- **Backtest**: 回测中心（参数配置、结果展示、图表）

### ✅ API 封装
- 策略管理 API
- 回测 API
- AI 诊断 API
- 数据同步 API
- 任务管理 API
- 系统状态 API

## 🎨 UI 特性

- Element Plus 组件库
- 响应式设计
- 平滑过渡动画
- 渐变背景
- 卡片式布局
- 图标集成

## 🔐 安全特性

- Token 自动管理
- 请求拦截器（自动添加 Authorization）
- 响应拦截器（401 自动刷新 Token）
- 路由级别权限控制
- 角色-based 菜单显示

## 📊 下一步

### 待实现页面
- [ ] Trading.vue - 模拟交易
- [ ] Positions.vue - 持仓管理
- [ ] Diagnosis.vue - AI 诊断
- [ ] Data.vue - 数据管理

### 增强功能
- [ ] ECharts 完整图表集成
- [ ] WebSocket 实时数据推送
- [ ] 主题切换（暗色模式）
- [ ] 国际化（i18n）
- [ ] 单元测试（Vitest）

## 🛠️ 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| TypeScript | 5.3+ | 类型系统 |
| Vite | 5.0+ | 构建工具 |
| Element Plus | 2.5+ | UI 组件库 |
| Vue Router | 4.2+ | 路由管理 |
| Pinia | 2.1+ | 状态管理 |
| Axios | 1.6+ | HTTP 客户端 |
| ECharts | 5.4+ | 图表库 |
