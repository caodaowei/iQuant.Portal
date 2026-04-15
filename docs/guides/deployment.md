# GitHub Actions 部署配置指南

## 1. 配置 Secrets

在 GitHub 仓库设置中添加以下 Secrets：

| Secret Name | 说明 | 示例 |
|-------------|------|------|
| `DEPLOY_HOST` | 部署服务器 IP/域名 | `43.156.51.119` |
| `DEPLOY_USER` | SSH 用户名 | `root` |
| `DEPLOY_KEY` | SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### 添加步骤：
1. 打开 https://github.com/caodaowei/iQuant.Portal/settings/secrets/actions
2. 点击 "New repository secret"
3. 添加上述三个 Secrets

## 2. SSH 密钥配置

在部署服务器上生成密钥（如果没有）：

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions
```

将公钥添加到 authorized_keys：
```bash
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
```

将私钥内容复制到 GitHub Secret `DEPLOY_KEY`：
```bash
cat ~/.ssh/github_actions
```

## 3. 部署流程

### 自动部署
- Push 代码到 `master` 分支
- GitHub Actions 自动：
  1. 构建 Docker 镜像
  2. 推送到 GitHub Container Registry
  3. SSH 到服务器执行部署

### 手动部署
```bash
# 在服务器上执行
./deploy.sh
```

## 4. 验证部署

```bash
# 检查容器状态
docker ps | grep iquant

# 查看日志
docker logs iquant-portal

# 测试 API
curl http://localhost:5000/api/status
```

## 5. 故障排查

### 镜像拉取失败
```bash
# 登录 GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
```

### 端口冲突
```bash
# 修改 docker-compose.yml 中的端口映射
ports:
  - "5001:5000"  # 改为 5001 端口
```

### 数据库连接失败
确保环境变量正确设置：
```bash
export DB_HOST=localhost
export DB_PASSWORD=your_password
docker-compose up -d
```
