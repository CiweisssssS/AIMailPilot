# AI 模型配置更新总结

## 更新内容

### 1. Summarizer 模型
- **之前**: GPT-4o-mini (`openai:gpt-4o-mini`)
- **现在**: Claude 3.5 Haiku (`anthropic:claude-3-5-haiku`)

### 2. Extractor 模型
- **之前**: GPT-4o-mini (`openai:gpt-4o-mini`)
- **现在**: Gemini Flash (`google:gemini-flash`)
- **Fallback**: GPT-4o-mini (用于复杂时间表达式)

## 修改的文件

### 1. `app/core/config.py`
```python
# 修改前
summarizer_model: str = "openai:gpt-4o-mini"
extractor_model: str = "openai:gpt-4o-mini"

# 修改后
summarizer_model: str = "anthropic:claude-3-5-haiku"
extractor_model: str = "google:gemini-flash"
```

### 2. `app/services/summarizer.py`
- 更新文件头部注释
- 更新函数文档字符串中的模型名称

### 3. `app/services/extractor.py`
- 更新文件头部注释
- 更新函数文档字符串中的模型名称
- 更新日志信息中的模型名称

## 环境变量要求

确保在 `.env` 文件中设置了相应的 API keys：

```bash
# Anthropic API key (用于 Summarizer)
ANTHROPIC_API_KEY=your_anthropic_key

# Google API key (用于 Extractor)
GOOGLE_API_KEY=your_google_key

# OpenAI API key (用于 Extractor fallback)
OPENAI_API_KEY=your_openai_key
```

## 模型使用说明

### Summarizer
- **默认模型**: Claude 3.5 Haiku
- **用途**: 生成邮件摘要
- **配置位置**: `app/core/config.py:18`

### Extractor
- **默认模型**: Gemini Flash
- **Fallback 模型**: GPT-4o-mini (当检测到复杂时间表达式时)
- **用途**: 提取任务
- **配置位置**: `app/core/config.py:19-20`

## 验证

运行以下命令验证配置：

```bash
# 检查配置
python -c "from app.core.config import settings; print(f'Summarizer: {settings.summarizer_model}'); print(f'Extractor: {settings.extractor_model}'); print(f'Extractor Fallback: {settings.extractor_fallback_model}')"
```

预期输出：
```
Summarizer: anthropic:claude-3-5-haiku
Extractor: google:gemini-flash
Extractor Fallback: openai:gpt-4o-mini
```

## 注意事项

1. **API Keys**: 确保设置了所有必需的 API keys
2. **模型可用性**: 确保 API keys 有权限访问相应的模型
3. **Fallback 机制**: Extractor 在检测到复杂时间表达式时会自动切换到 GPT-4o-mini

