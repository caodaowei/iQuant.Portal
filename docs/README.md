# iQuant 项目文档

本目录包含 iQuant 量化交易系统的所有文档，按类别组织。

## 📁 文档分类

### 📖 guides/ - 配置指南

面向用户和运维人员的配置和使用指南。

| 文档 | 说明 |
|------|------|
| [deployment.md](guides/deployment.md) | 系统部署和运维指南 |
| [supabase-setup.md](guides/supabase-setup.md) | Supabase 认证服务配置 |
| [redis-setup.md](guides/redis-setup.md) | Redis 缓存服务配置 |

### 🏗️ architecture/ - 架构设计

系统架构设计和优化方案。

| 文档 | 说明 |
|------|------|
| [optimization.md](architecture/optimization.md) | 系统架构优化方案 |

### 💻 development/ - 开发文档

面向开发者的技术文档。

| 文档 | 说明 |
|------|------|
| [testing.md](development/testing.md) | 测试框架和使用方法 |
| [security.md](development/security.md) | 安全最佳实践 |

### 📝 changelog/ - 开发日志

Quest 开发过程中产生的技术文档和变更记录（按时间正序，从早到晚）。

| 更新时间 | 文档 | 说明 |
|----------|------|------|
| 2026-04-15 11:09 | [async-implementation.md](changelog/async-implementation.md) | 异步编程模型实现 |
| 2026-04-15 11:32 | [db-optimization.md](changelog/db-optimization.md) | 数据库性能优化 |
| 2026-04-15 11:45 | [monitoring.md](changelog/monitoring.md) | 系统监控和告警方案 |
| 2026-04-15 11:50 | [implementation-summary.md](changelog/implementation-summary.md) | 功能实现总览 |
| 2026-04-15 12:43 | [code-cleanup.md](changelog/code-cleanup.md) | 代码重构和清理记录 |
| 2026-04-15 12:49 | [final-code-cleanup.md](changelog/final-code-cleanup.md) | 最终代码清理报告 |
| 2026-04-15 14:01 | [cache-implementation.md](changelog/cache-implementation.md) | Redis 缓存层实现总结 |

## 🔗 其他文档

- [项目主 README](../README.md) - 项目概述和快速开始
- [前端项目文档](../frontend/README.md) - Vue 3 前端项目说明

## 📌 推荐阅读顺序

### 新用户
1. [项目主 README](../README.md)
2. [Supabase 配置](guides/supabase-setup.md)（如需使用认证功能）
3. [Redis 配置](guides/redis-setup.md)（如需使用缓存功能）

### 开发者
1. [项目主 README](../README.md)
2. [本地开发调试指南](../README.md#本地开发调试指南)
3. [测试指南](development/testing.md)
4. [安全指南](development/security.md)

### 运维人员
1. [部署指南](guides/deployment.md)
2. [Redis 配置](guides/redis-setup.md)
3. [监控方案](changelog/monitoring.md)
