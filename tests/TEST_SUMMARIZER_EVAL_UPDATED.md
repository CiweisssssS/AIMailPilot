# test_summarizer_eval.py 修改说明

## 修改目的

将 `tests/test_summarizer_eval.py` 的评估逻辑与 `eval/run_summarizer_*.py` 脚本对齐，确保测试结果一致。

## 主要修改

### 1. 导入 eval 脚本的评估函数

```python
from eval.run_pipeline import slot_acc
from eval.metrics.summarizer import fact_prf, format_compliance, rouge_l_like
from eval.pipeline import postprocess_summary, _extract_sender_name
```

### 2. 修改 `invoke_agent` 函数

**之前**：从 summary 文本中提取 facts（使用正则表达式）

**现在**：
- 如果 agent 是 `summarize_text`，直接调用 LLM 获取结构化 JSON
- 返回 `(structured_json, json_ok)` 而不是 `(summary_text, json_ok)`
- 结构化 JSON 包含：`actor, action, object, deadline, notes`

### 3. 修改 `evaluate_dataset` 函数

**之前**：
- 从 summary 文本中提取 facts
- 使用 `extract_predicted_facts()` 和 `score_facts()` 评估

**现在**：
- 直接使用结构化 JSON 比较
- 使用 `slot_acc()` 进行 slot-level 准确率评估
- 使用 `fact_prf()` 进行 fact-level PRF 评估
- 使用 `format_compliance()` 检查格式合规性
- 应用 `postprocess_summary()` 后处理（归一化 actor, action）

## 评估方式对比

| 特性 | 修改前 | 修改后 |
|------|--------|--------|
| **输入格式** | Summary 文本 | 结构化 JSON |
| **提取方式** | 正则表达式 | 直接使用 JSON 字段 |
| **评估函数** | `extract_predicted_facts()` + `score_facts()` | `slot_acc()` + `fact_prf()` |
| **后处理** | 无 | `postprocess_summary()` |
| **ROUGE** | 自定义实现 | `rouge_l_like()` |

## 使用方式

运行方式不变：

```bash
python -m tests.test_summarizer_eval \
  --agent app.services.summarizer:summarize_text \
  --data tests/data/summarizer_gold.jsonl \
  --max_words 20
```

## 预期效果

- ✅ 与 eval 脚本使用相同的评估逻辑
- ✅ 结果应该与 `eval/run_summarizer_*.py` 一致
- ✅ 不再出现 Object Accuracy = 0% 的问题（因为直接使用 JSON 字段，不需要文本提取）

## 注意事项

1. 确保 `eval/` 目录在 Python path 中
2. 数据格式需要包含 `ground_truth.summary` 或 `key_facts` 字段
3. 如果 LLM 调用失败，会回退到原来的文本提取方式

