# 如何运行 test_summarizer_eval.py

## 基本运行命令

```bash
# 从项目根目录运行
python -m tests.test_summarizer_eval \
  --agent app.services.summarizer:summarize_text \
  --data tests/data/summarizer_gold.jsonl \
  --max_words 20
```

## 参数说明

- `--agent`: Agent 函数，格式为 `module:function`
  - 默认使用：`app.services.summarizer:summarize_text`
  
- `--data`: 测试数据文件路径（JSONL 格式）
  - 默认：`tests/data/summarizer_gold.jsonl`
  
- `--max_words`: Summary 最大单词数（用于合规性检查）
  - 默认：80
  
- `--csv_out`: （可选）输出 CSV 文件路径，包含 fact 不匹配详情
  
- `--per_case_dump`: （可选）输出每个 case 的详细 JSON 文件路径
  
- `--max_examples`: 打印的 FP/FN 示例数量
  - 默认：5

## 完整示例

```bash
# 基本运行
python -m tests.test_summarizer_eval \
  --agent app.services.summarizer:summarize_text \
  --data tests/data/summarizer_gold.jsonl \
  --max_words 20

# 带输出文件
python -m tests.test_summarizer_eval \
  --agent app.services.summarizer:summarize_text \
  --data tests/data/summarizer_gold.jsonl \
  --max_words 20 \
  --csv_out results/summarizer_errors.csv \
  --per_case_dump results/summarizer_per_case.json \
  --max_examples 10
```

## 环境要求

1. **API Keys**: 确保在 `.env` 文件中设置了相应的 API keys
   ```bash
   OPENAI_API_KEY=your_key
   ANTHROPIC_API_KEY=your_key  # 如果使用 Claude
   GOOGLE_API_KEY=your_key      # 如果使用 Gemini
   ```

2. **Python 路径**: 确保从项目根目录运行，或者将项目添加到 PYTHONPATH

## 输出说明

运行后会显示：

```
Summarizer Evaluation Summary
--------------------------------
Total cases evaluated: 20
Mean ROUGE-1 Recall: 0.7443
Mean ROUGE-L Recall: 0.6800
Fact TP (strict): 50
Fact TP (partial): 1
Fact FP: 10
Fact FN: 29
Key Fact Precision: 0.8361
Key Fact Recall: 0.6375
Key Fact F1: 0.7234
Fact Slot Accuracy (strict only):
  Actor: 100.00%
  Action: 60.00%
  Object: 0.00%
  Deadline: 90.00%
Fact Slot Coverage (strict+partial):
  Actor: 100.00%
  Action: 60.00%
  Object: 0.00%
  Deadline: 95.00%
Compliance Rates:
  Action Verb: 85.00%
  Starts With Sender: 100.00%
  Length OK: 100.00%
  Ends With Period: 100.00%
  JSON Parse OK: 100.00%
```

## 与 eval 脚本的对比

修改后的 `test_summarizer_eval.py` 现在使用与 `eval/run_summarizer_*.py` 相同的评估逻辑：

- ✅ 直接使用结构化 JSON 比较（不再从文本提取）
- ✅ 使用相同的评估函数（`slot_acc`, `fact_prf`, `format_compliance`）
- ✅ 应用相同的后处理（`postprocess_summary`）

因此，结果应该与 eval 脚本一致。

## 故障排除

1. **ImportError**: 确保从项目根目录运行，或设置 PYTHONPATH
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **API Key 错误**: 检查 `.env` 文件中的 API keys

3. **数据文件不存在**: 确保 `tests/data/summarizer_gold.jsonl` 存在

