# Supabase 集成配置指南

本指南将帮助您在 AIMailPilot 项目中配置 Supabase 数据库，实现 Flag 和 Set Deadline 功能的数据持久化。

---

## 📋 **第一步：创建 Supabase 项目**

### 1.1 注册/登录 Supabase
1. 访问 [supabase.com](https://supabase.com)
2. 点击右上角 **"Sign In"** 或 **"Start your project"**
3. 使用 GitHub、Google 或其他方式登录

### 1.2 创建新项目
1. 登录后，点击 **"New Project"** 按钮
2. 填写项目信息：
   ```
   Organization: 选择或创建一个 organization
   Name: aimailpilot-db （或您喜欢的名称）
   Database Password: 创建一个强密码（务必保存！）
   Region: 选择 Southeast Asia (Singapore) 或离您最近的区域
   Pricing Plan: Free
   ```
3. 点击 **"Create new project"**
4. 等待 1-2 分钟，直到项目初始化完成（显示绿色对勾）

---

## 📋 **第二步：创建数据库表**

### 2.1 打开 SQL Editor
1. 在项目仪表板左侧菜单，点击 **"SQL Editor"**
2. 点击 **"New query"** 创建新查询

### 2.2 执行 Schema 脚本
1. 复制以下完整 SQL 脚本：

```sql
-- AIMailPilot Database Schema for Supabase
-- This script creates the necessary tables for data persistence

-- ==========================================
-- Table: flag_status
-- Purpose: Store user's flagged/bookmarked emails
-- ==========================================
CREATE TABLE IF NOT EXISTS flag_status (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    email_id VARCHAR(255) NOT NULL,
    is_flagged BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_email_flag UNIQUE(user_email, email_id)
);

-- Index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_flag_status_user_email ON flag_status(user_email);
CREATE INDEX IF NOT EXISTS idx_flag_status_user_email_flagged ON flag_status(user_email, is_flagged);

-- ==========================================
-- Table: deadline_overrides
-- Purpose: Store user's manually edited task deadlines
-- ==========================================
CREATE TABLE IF NOT EXISTS deadline_overrides (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    email_id VARCHAR(255) NOT NULL,
    task_index INTEGER NOT NULL,
    original_deadline VARCHAR(100),
    override_deadline VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_email_task UNIQUE(user_email, email_id, task_index)
);

-- Index for faster queries by user
CREATE INDEX IF NOT EXISTS idx_deadline_overrides_user_email ON deadline_overrides(user_email);

-- ==========================================
-- Trigger: Auto-update updated_at timestamp
-- ==========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_flag_status_updated_at BEFORE UPDATE ON flag_status
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_deadline_overrides_updated_at BEFORE UPDATE ON deadline_overrides
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

2. 将脚本粘贴到 SQL Editor
3. 点击右下角 **"Run"** 按钮执行脚本
4. 确认显示 **"Success. No rows returned"** 消息

### 2.3 验证表创建成功
1. 在左侧菜单点击 **"Table Editor"**
2. 确认看到两个表：
   - ✅ `flag_status`
   - ✅ `deadline_overrides`

---

## 📋 **第三步：获取连接凭据**

### 3.1 获取 Supabase URL
1. 在项目仪表板，点击左侧菜单 **"Settings"** → **"API"**
2. 在 **"Project URL"** 部分，复制完整 URL
   ```
   示例: https://abcdefghijklmn.supabase.co
   ```
3. **保存此 URL**（稍后将其添加到 Replit Secrets）

### 3.2 获取 Supabase Anon Key
1. 在同一页面（Settings → API），向下滚动到 **"Project API keys"**
2. 找到 **"anon public"** key
3. 点击 **"Copy"** 按钮复制密钥
   ```
   示例: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...（很长的字符串）
   ```
4. **保存此 Key**（稍后将其添加到 Replit Secrets）

---

## 📋 **第四步：在 Replit 配置环境变量**

### 4.1 打开 Replit Secrets
1. 在 Replit 项目中，点击左侧工具栏的 **🔒 Secrets** 图标
   （或按快捷键查找 "Secrets"）

### 4.2 添加 SUPABASE_URL
1. 点击 **"New Secret"** 按钮
2. 填写：
   ```
   Key: SUPABASE_URL
   Value: https://abcdefghijklmn.supabase.co （粘贴您在第三步复制的 URL）
   ```
3. 点击 **"Add Secret"**

### 4.3 添加 SUPABASE_KEY
1. 再次点击 **"New Secret"** 按钮
2. 填写：
   ```
   Key: SUPABASE_KEY
   Value: eyJhbGciOiJIUzI1NiIsInR5... （粘贴您在第三步复制的 anon key）
   ```
3. 点击 **"Add Secret"**

### 4.4 验证配置
确认您已添加以下两个 Secrets：
- ✅ `SUPABASE_URL`
- ✅ `SUPABASE_KEY`

---

## 📋 **第五步：通知开发者继续**

完成以上所有步骤后，请在聊天中告诉我：

**"Supabase 配置已完成"**

我将继续：
1. 更新前端组件以调用新的持久化 API
2. 实现 Flag 功能的数据库存储
3. 实现 Set Deadline 功能的数据库存储
4. 更新 Flagged Mails 视图显示真实数据
5. 测试完整的数据持久化流程

---

## 🔍 **常见问题**

### Q1: 我忘记了数据库密码怎么办？
**A**: 数据库密码仅用于直接 PostgreSQL 连接。在本项目中，我们使用 Supabase API（anon key），不需要数据库密码。

### Q2: 如何检查表是否创建成功？
**A**: 在 Supabase 仪表板，点击 **Table Editor**，应该看到 `flag_status` 和 `deadline_overrides` 两个表。

### Q3: 如果 SQL 脚本执行失败怎么办？
**A**: 
1. 确保您复制了完整的 SQL 脚本（包括所有注释和分号）
2. 如果表已存在，脚本会跳过（`IF NOT EXISTS` 保护）
3. 检查是否有语法错误或红色错误提示

### Q4: Anon Key 安全吗？
**A**: 是的。Supabase 的 anon（匿名）key 设计用于客户端使用，配合 Row Level Security (RLS) 策略确保数据安全。我们的 API 会额外检查用户身份验证。

### Q5: 免费计划的限制是什么？
**A**: Supabase 免费计划包括：
- 500 MB 数据库空间
- 1 GB 文件存储
- 50 MB 文件上传大小
- 对于 AIMailPilot 来说绰绰有余

---

## ⚠️ **重要提示**

1. **不要分享您的 anon key**：虽然它是公开 key，但最好只在 Replit Secrets 中配置
2. **保存数据库密码**：即使现在不需要，将来直接访问数据库时可能用到
3. **检查区域选择**：选择离您最近的区域以获得最佳性能
4. **Free Plan 限制**：如果项目长期不活跃，Supabase 可能暂停免费项目（会提前通知）

---

## 📞 **需要帮助？**

如果在配置过程中遇到任何问题，请：
1. 截图错误消息或问题页面
2. 在聊天中描述具体问题
3. 告诉我您完成到第几步

我会帮助您解决问题！🚀
