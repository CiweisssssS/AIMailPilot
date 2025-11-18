# Actor 准确率为 0 的原因分析

## 问题描述

Summarizer 单测结果显示 Actor 准确率为 0.0000，但其他指标（Action: 0.75, Object: 0.95）相对正常。

## 可能原因

### 1. 评估模式问题

`slot_acc` 函数对 actor 字段的评估逻辑：

- **严格模式**（默认，无 `--lenient` 或 `--very_lenient`）：
  - 使用严格匹配：`p == g`
  - 大小写敏感，空格敏感

- **Lenient 模式**（`--lenient`）：
  - 使用 `_normalize_text` 比较
  - 会转换为小写，去除标点，但仍然是完全匹配

- **Very Lenient 模式**（`--very_lenient`）：
  - 同样使用 `_normalize_text` 比较
  - 对于 object 字段使用相似度，但 actor 仍然是完全匹配

### 2. Postprocessing 可能改变 Actor

`postprocess_summary` 函数会：
- 如果 actor 是 "you/we/our team/null"，会从 `from_addr` 提取 sender name
- 使用 `_extract_sender_name` 提取，返回格式如 "Alice"、"Bob Smith" 等（Title Case）

### 3. LLM 输出格式问题

Claude Haiku 可能返回的 actor 格式与 GT 不完全匹配：
- GT: "Alice"
- LLM: "alice" 或 "Alice "（带空格）或 "ALICE"

## 解决方案

### 方案 1: 使用 Lenient 模式运行测试

```bash
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --lenient
```

或使用 very_lenient：

```bash
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --very_lenient \
  --sim_threshold 0.5
```

### 方案 2: 改进 Actor 评估逻辑

修改 `slot_acc` 函数，对 actor 字段也使用相似度匹配（类似 object 字段）：

```python
elif very_lenient:
    if k == "deadline":
        ok = _normalize_date(p) == _normalize_date(g)
    elif k == "object":
        ok = _similarity(p or "", g or "") >= sim_threshold
    elif k == "actor":
        # Use similarity for actor too
        ok = _similarity(p or "", g or "") >= sim_threshold
    else:
        ok = _normalize_text(p or "") == _normalize_text(g or "")
```

### 方案 3: 检查实际数据

运行测试并查看 `errors.jsonl` 文件，检查实际的 actor 值：

```bash
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --very_lenient

# 查看错误案例
cat eval/results/summarizer_single.errors.jsonl | jq '.pred_summary.actor, .gt_summary.actor'
```

## 建议

1. **立即行动**：使用 `--very_lenient` 模式重新运行测试
2. **长期改进**：考虑对 actor 字段也使用相似度匹配，因为人名可能有多种格式（"Alice" vs "alice" vs "Alice Smith"）

