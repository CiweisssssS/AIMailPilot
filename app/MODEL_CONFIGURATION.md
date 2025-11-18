# 模型配置说明

## 默认模型配置

系统已配置为使用以下默认模型：

- **Summarizer（摘要）**: Claude 3.5 Haiku (`anthropic:claude-3-5-haiku`)
- **Extractor（任务提取）**: Gemini Flash (`google:gemini-flash`)
- **Extractor Fallback（复杂时间）**: GPT-4o (`openai:gpt-4o`)

## 配置方式

### 1. 环境变量配置

在 `.env` 文件中添加以下 API 密钥：

```bash
# OpenAI (用于 fallback)
OPENAI_API_KEY=your_openai_key

# Anthropic (用于 Summarizer)
ANTHROPIC_API_KEY=your_anthropic_key

# Google (用于 Extractor)
GOOGLE_API_KEY=your_google_key
```

### 2. 模型配置（可选）

如果需要修改默认模型，可以在 `.env` 文件中设置：

```bash
# 默认模型配置
SUMMARIZER_MODEL=anthropic:claude-3-5-haiku
EXTRACTOR_MODEL=google:gemini-flash
EXTRACTOR_FALLBACK_MODEL=openai:gpt-4o
```

## 复杂时间检测

Extractor 会自动检测复杂时间表达式，并在需要时切换到 GPT-4o fallback 模型。

### 触发 Fallback 的时间表达式示例：

- "next week", "this month", "this quarter"
- "early next week", "mid next month"
- "in 2 weeks", "3 months later"
- "end of next week", "beginning of next month"
- "first week of October"
- "before the end of", "after the start of"
- "by the end of next week"
- "10/15/2024 at 3:30pm"
- "Friday morning", "next Friday evening"

### 检测逻辑

`app/services/extractor.py` 中的 `_has_complex_time_expression()` 函数会检查文本中是否包含复杂时间表达式。如果检测到，会自动使用 GPT-4o fallback 模型。

## 代码位置

- **配置文件**: `app/core/config.py`
- **LLM 提供者**: `app/core/llm.py`
- **Extractor 服务**: `app/services/extractor.py`
- **Summarizer 服务**: `app/services/summarizer.py`

## 模型 ID 格式

模型 ID 使用 `provider:model-name` 格式：

- `anthropic:claude-3-5-haiku` - Claude 3.5 Haiku
- `google:gemini-flash` - Gemini Flash
- `openai:gpt-4o` - GPT-4o

## 向后兼容性

系统仍然支持旧的 OpenAI 配置方式（通过 `OPENAI_MODEL`, `OPENAI_SUMMARY_MODEL`, `OPENAI_EXTRACTOR_MODEL`），但新的多模型配置优先。

## 安装依赖

确保安装了所需的 SDK：

```bash
pip install anthropic google-generativeai openai
```

