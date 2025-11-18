# 单模型测试脚本运行说明

## 概述

这两个脚本用于测试实际的 `app.services.summarizer` 和 `app.services.extractor` 函数，使用与 eval 脚本相同的评估逻辑。

## 1. Summarizer 单测

### 文件
`eval/run_summarizer_single.py`

### 运行命令

```bash
# 基本运行
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv

# 使用 lenient 匹配
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --lenient

# 使用 very_lenient 匹配
python -m eval.run_summarizer_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/summarizer_single.csv \
  --very_lenient \
  --sim_threshold 0.5
```

### 参数说明

- `--dataset`: 测试数据集路径（JSONL 格式）
- `--output`: 输出 CSV 文件路径
- `--lenient`: 使用 lenient 匹配模式
- `--very_lenient`: 使用 very_lenient 匹配模式
- `--sim_threshold`: 相似度阈值（默认：0.6）

### 输出文件

- `{output}.csv`: 每个样本的详细结果
- `{output}.aggregate.json`: 聚合结果
- `{output}.errors.jsonl`: 错误案例（slot accuracy < 1.0）

### 评估指标

- **Slot Accuracy**: actor, action, object, deadline
- **Fact Metrics**: precision, recall, F1
- **ROUGE-like**: 文本相似度
- **JSON Parse Rate**: JSON 解析成功率
- **Format Compliance**: 格式合规率
- **Latency**: 平均和 median 延迟

---

## 2. Extractor 单测

### 文件
`eval/run_extractor_single.py`

### 运行命令

```bash
# 基本运行
python -m eval.run_extractor_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/extractor_single.csv

# 使用 lenient 匹配
python -m eval.run_extractor_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/extractor_single.csv \
  --lenient

# 使用 very_lenient 匹配
python -m eval.run_extractor_single \
  --dataset eval/dataset/emails.jsonl \
  --output eval/results/extractor_single.csv \
  --very_lenient \
  --sim_threshold 0.5 \
  --task_match_k 2
```

### 参数说明

- `--dataset`: 测试数据集路径（JSONL 格式）
- `--output`: 输出 CSV 文件路径
- `--lenient`: 使用 lenient 匹配模式
- `--very_lenient`: 使用 very_lenient 匹配模式（k-of-4 字段匹配）
- `--sim_threshold`: 相似度阈值（默认：0.6）
- `--task_match_k`: 最少匹配字段数（默认：2）

### 输出文件

- `{output}.csv`: 每个样本的详细结果
- `{output}.aggregate.json`: 聚合结果

### 评估指标

- **Task Metrics**: precision, recall, F1
- **Due Date Correctness**: Deadline 匹配准确率
- **Owner Match**: Owner 匹配准确率
- **JSON Parse Rate**: JSON 解析成功率
- **Latency**: 延迟（毫秒）

---

## 与 Eval 脚本的一致性

### 相同点

1. ✅ 使用相同的评估函数：
   - `slot_acc()` - Summarizer slot accuracy
   - `prf_tasks()` - Extractor task PRF
   - `fact_prf()` - Fact-level PRF
   - `due_date_correctness()` - Due date matching
   - `rouge_l_like()` - ROUGE-like score

2. ✅ 使用相同的后处理：
   - `postprocess_summary()` - Summarizer 后处理
   - 任务格式转换逻辑

3. ✅ 使用相同的数据格式：
   - 输入：`EmailSample` 格式
   - 输出：与 eval 脚本相同的 CSV 和 JSON 格式

### 不同点

1. **调用方式**：
   - Eval 脚本：直接调用模型客户端（`get_model_client()`）
   - 单测脚本：调用实际的 `app.services` 函数

2. **模型选择**：
   - Eval 脚本：可以指定任意模型
   - 单测脚本：使用 `app.core.config.py` 中配置的默认模型

---

## 数据格式要求

### 输入数据（JSONL）

```json
{
  "id": "email_001",
  "subject": "Project sync next Tuesday",
  "from": "alice@example.com",
  "to": ["me@example.com"],
  "cc": [],
  "received_at": "2025-11-10T09:30:00Z",
  "body_text": "Hi, hope your week is off to a good start...",
  "ground_truth": {
    "summary": {
      "actor": "Alice",
      "action": "request",
      "object": "project draft",
      "deadline": "2025-11-14",
      "notes": "..."
    },
    "tasks": [
      {
        "owner": "me",
        "action": "send",
        "object": "project draft",
        "deadline": "2025-11-14",
        "priority": "high"
      }
    ]
  }
}
```

---

## 环境要求

1. **API Keys**: 确保在 `.env` 文件中设置了相应的 API keys
   ```bash
   OPENAI_API_KEY=your_key
   ANTHROPIC_API_KEY=your_key  # 如果使用 Claude
   GOOGLE_API_KEY=your_key      # 如果使用 Gemini
   ```

2. **Python 路径**: 确保从项目根目录运行

---

## 示例输出

### Summarizer 单测输出

```
Summarizer Single Model Evaluation
Model: app.services.summarizer:summarize_text
Total cases: 20
Slot Accuracy:
  Actor: 0.9500
  Action: 0.6000
  Object: 0.3000
  Deadline: 0.9000
Fact Metrics:
  Precision: 0.8361
  Recall: 0.6375
  F1: 0.7234
ROUGE-like: 0.7443
JSON Parse Rate: 1.0000
Format Compliance: 1.0000
Avg Latency: 1234.56 ms
```

### Extractor 单测输出

```
Extractor Single Model Evaluation
Model: app.services.extractor:extract_tasks_from_text
Total cases: 20
Task Metrics:
  Precision: 0.8148
  Recall: 0.8800
  F1: 0.8462
Due Date Correctness: 0.5000
Owner Match: 0.9091
JSON Parse Rate: 1.0000
```

---

## 故障排除

1. **ImportError**: 确保从项目根目录运行
2. **API Key 错误**: 检查 `.env` 文件
3. **数据文件不存在**: 确保数据集文件存在
4. **模型配置错误**: 检查 `app/core/config.py` 中的模型配置

