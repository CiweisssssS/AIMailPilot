# Actor 和 Deadline 准确率低的原因分析

## 问题描述

- **Actor 准确率**: 0.05 (5%)
- **Deadline 准确率**: 0.15 (15%)
- **Action 准确率**: 0.75 (75%) ✅
- **Object 准确率**: 0.95 (95%) ✅

## Actor 准确率低的原因

### 1. 评估模式过于严格

如果运行测试时**没有使用 `--lenient` 或 `--very_lenient`**，`slot_acc` 函数会使用严格匹配：

```python
# 严格模式（默认）
ok = p == g  # 完全匹配，包括大小写和空格
```

**问题示例**：
- GT: `"Alice"`
- LLM: `"alice"` → **不匹配** ❌
- LLM: `"Alice "` (带空格) → **不匹配** ❌
- LLM: `"Alice Smith"` → **不匹配** ❌

### 2. LLM 返回格式不一致

Claude Haiku 可能返回：
- 不同的大小写格式
- 带空格的字符串
- 完整的名字而不是首名

### 3. Postprocessing 可能改变 Actor

`postprocess_summary` 函数会从 `from_addr` 提取 sender name，但可能格式与 GT 不完全匹配。

## Deadline 准确率低的原因

### 1. 相对时间表达式未解析

`_normalize_date` 函数只能处理 ISO 格式日期，**不能处理相对时间表达式**：

```python
def _normalize_date(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    if "T" in s:
        s = s.split("T", 1)[0]  # 只移除时间部分
    return s  # 返回原始字符串（如果是 "EOW" 就还是 "EOW"）
```

**问题示例**：
- GT: `"2025-11-14"` (ISO 格式)
- LLM: `"EOW"` → 标准化后还是 `"EOW"` → **不匹配** ❌
- LLM: `"tomorrow"` → 标准化后还是 `"tomorrow"` → **不匹配** ❌
- LLM: `"end of week"` → 标准化后还是 `"end of week"` → **不匹配** ❌

### 2. 日期格式不一致

即使都是 ISO 格式，也可能有细微差异：
- GT: `"2025-11-14"`
- LLM: `"2025-11-14T10:00:00Z"` → 标准化后是 `"2025-11-14"` → **匹配** ✅

但如果有其他格式差异，可能不匹配。

## 解决方案

### 方案 1: 使用 Very Lenient 模式（推荐）

```bash
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --very_lenient \
  --sim_threshold 0.5
```

**效果**：
- Actor: 使用 `_normalize_text` 比较（忽略大小写和标点）
- Deadline: 使用 `_normalize_date` 比较（移除时间部分）
- Object: 使用相似度匹配（更灵活）

### 方案 2: 改进 Deadline 评估逻辑

修改 `eval/run_pipeline.py` 中的 `slot_acc` 函数，添加相对时间解析：

```python
def _normalize_date(s: str, received_at: str = None) -> str:
    """Normalize date, handling relative time expressions."""
    if not isinstance(s, str):
        return ""
    s = s.strip()
    
    # Handle ISO format with time
    if "T" in s:
        s = s.split("T", 1)[0]
    
    # Handle relative time expressions (需要 received_at 来计算)
    if received_at:
        s_lower = s.lower()
        if s_lower in ["eow", "end of week"]:
            # 计算本周五
            # ... 实现逻辑
            pass
        elif s_lower == "tomorrow":
            # 计算明天
            # ... 实现逻辑
            pass
    
    return s
```

### 方案 3: 改进 Prompt，要求 LLM 返回 ISO 格式日期

在 `app/core/prompts.py` 中，明确要求 LLM 返回 ISO 格式的日期：

```
Return JSON with keys: summary, actor, action, object, deadline.
- deadline: MUST be in ISO format (YYYY-MM-DD), e.g., "2025-11-14"
- Do NOT use relative time expressions like "EOW", "tomorrow", etc.
```

### 方案 4: 检查实际错误案例

运行测试并查看 `errors.jsonl`：

```bash
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --very_lenient

# 查看错误案例
cat eval/results/summarizer_single.errors.jsonl | python -c "
import sys, json
for line in sys.stdin:
    data = json.loads(line)
    print(f\"ID: {data['id']}\")
    print(f\"  Pred Actor: '{data.get('pred_summary', {}).get('actor')}'\" )
    print(f\"  GT Actor: '{data.get('gt_summary', {}).get('actor')}'\" )
    print(f\"  Pred Deadline: '{data.get('pred_summary', {}).get('deadline')}'\" )
    print(f\"  GT Deadline: '{data.get('gt_summary', {}).get('deadline')}'\" )
    print()
"
```

## 立即行动建议

1. **使用 `--very_lenient` 模式重新运行测试**
2. **查看 `errors.jsonl` 文件，分析具体的错误模式**
3. **如果 Deadline 仍然低，考虑改进 prompt 或添加相对时间解析逻辑**

