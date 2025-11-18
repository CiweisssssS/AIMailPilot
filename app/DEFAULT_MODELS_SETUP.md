# 默认模型配置完成说明

## ✅ 已完成的配置

插件实际运行时的默认 AI 模型已按以下要求配置：

### 1. **Summarizer（摘要服务）**
- **默认模型**: Claude 3.5 Haiku (`anthropic:claude-3-5-haiku`)
- **配置文件**: `app/core/config.py`
- **使用位置**: `app/services/summarizer.py` → `llm_provider.call_with_json_mode()`

### 2. **Extractor（任务提取服务）**
- **默认模型**: Gemini Flash (`google:gemini-flash`)
- **Fallback 模型**: GPT-4o (`openai:gpt-4o`) - 用于复杂时间表达式
- **配置文件**: `app/core/config.py`
- **使用位置**: `app/services/extractor.py` → `llm_provider.extract_tasks()`

### 3. **复杂时间检测**
- **检测函数**: `_has_complex_time_expression()` 在 `app/services/extractor.py`
- **触发条件**: 检测到复杂时间表达式时自动切换到 GPT-4o
- **复杂时间模式**: 
  - "next week", "this month", "end of next week"
  - "in 2 weeks", "3 months later"
  - "first week of October"
  - "Friday morning", "next Friday evening"
  - 等等...

## 📝 配置文件位置

### 主配置文件
- `app/core/config.py` - 默认模型配置

### 核心实现
- `app/core/llm.py` - 多模型提供商实现
- `app/services/summarizer.py` - 摘要服务（使用 Claude）
- `app/services/extractor.py` - 任务提取服务（使用 Gemini/GPT-4o）

## 🔧 环境变量设置

在 `.env` 文件中添加以下 API 密钥：

```bash
# Anthropic (用于 Summarizer)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Google (用于 Extractor)
GOOGLE_API_KEY=your_google_key_here

# OpenAI (用于 Extractor Fallback)
OPENAI_API_KEY=your_openai_key_here
```

## 🚀 运行方式

配置完成后，插件会自动：

1. **Summarizer** 使用 Claude 3.5 Haiku 生成摘要
2. **Extractor** 默认使用 Gemini Flash 提取任务
3. **遇到复杂时间** 自动切换到 GPT-4o 进行更准确的解析

无需修改任何代码，系统会根据配置自动选择正确的模型。

## 📊 验证配置

可以通过查看日志来验证使用的模型：

- Summarizer: 日志会显示使用 Claude
- Extractor: 日志会显示 "Using default extractor model (Gemini Flash)" 或 "Complex time expression detected, using fallback model (GPT-4o)"

## 🔄 如何修改默认模型（可选）

如果需要修改默认模型，可以在 `.env` 文件中设置：

```bash
SUMMARIZER_MODEL=anthropic:claude-3-5-haiku
EXTRACTOR_MODEL=google:gemini-flash
EXTRACTOR_FALLBACK_MODEL=openai:gpt-4o
```

或者直接修改 `app/core/config.py` 中的默认值。

## ✅ 完成状态

- ✅ Summarizer 默认使用 Claude Haiku
- ✅ Extractor 默认使用 Gemini Flash  
- ✅ 复杂时间自动 fallback 到 GPT-4o
- ✅ 所有注释和文档已更新
- ✅ 代码已通过 lint 检查

配置已完成，可以直接使用！

