# Supabase 配置指南

## 1. 创建 Supabase 项目

1. 访问 [Supabase](https://supabase.com)
2. 注册/登录账号
3. 点击 "New Project"
4. 填写项目信息：
   - Name: iQuant Portal
   - Database Password: 设置一个强密码
   - Region: 选择离您最近的区域
5. 点击 "Create new project"

## 2. 获取 API 凭证

项目创建完成后：

1. 进入项目 Dashboard
2. 点击左侧菜单的 **Settings** (齿轮图标)
3. 选择 **API**
4. 复制以下信息：
   - **Project URL**: `https://xxxxx.supabase.co`
   - **anon public**: 公开的 anon key

## 3. 配置前端环境变量

在 `frontend/.env` 文件中填入：

```env
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

## 4. 启用邮箱认证

1. 在 Supabase Dashboard 中，进入 **Authentication** > **Providers**
2. 找到 **Email** 提供商
3. 确保它已启用
4. 可选配置：
   - 禁用邮箱验证（开发环境）：进入 Settings > Authentication > Disable email confirmations

## 5. 创建测试用户

### 方法一：通过 Supabase Dashboard

1. 进入 **Authentication** > **Users**
2. 点击 **Add user**
3. 输入邮箱和密码
4. 点击 **Create user**

### 方法二：通过应用注册

1. 启动应用：`npm run dev`
2. 访问登录页面
3. 点击 "注册新账号"
4. 输入邮箱和密码进行注册

## 6. 数据库表结构

您的 Supabase 项目已包含以下表：

- `public.users` - 用户信息
- `public.tasks` - 任务管理
- `public.task_categories` - 任务分类

## 7. 安全规则（RLS）

建议为所有表启用 Row Level Security：

```sql
-- 启用 RLS
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.task_categories ENABLE ROW LEVEL SECURITY;

-- 创建策略：用户可以查看自己的数据
CREATE POLICY "Users can view own data" ON public.tasks
  FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tasks" ON public.tasks
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tasks" ON public.tasks
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tasks" ON public.tasks
  FOR DELETE USING (auth.uid() = user_id);
```

## 8. 故障排除

### 问题：登录失败

- 检查 `.env` 文件中的配置是否正确
- 确认 Supabase 项目正在运行
- 检查浏览器控制台是否有错误信息

### 问题：注册后无法登录

- 检查是否启用了邮箱验证
- 如果启用了验证，请检查邮箱并点击验证链接
- 或在 Supabase Dashboard 中手动确认用户

### 问题：CORS 错误

- 确保在 Supabase Dashboard 中配置了正确的 CORS  origins
- 开发环境通常不需要额外配置

## 9. 参考资料

- [Supabase 文档](https://supabase.com/docs)
- [Supabase Auth 文档](https://supabase.com/docs/guides/auth)
- [Vue 3 集成指南](https://supabase.com/docs/guides/getting-started/tutorials/with-vue-3)
