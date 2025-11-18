# 如何运行 extractor_eval.py

## 基本运行命令

```bash
# 从项目根目录运行
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl
```

## 参数说明

- `--agent`: Extractor 函数（必需），格式为 `module:function`
  - **推荐使用**：`app.services.extractor:extract_tasks_from_text`
    - 函数签名：`extract_tasks_from_text(text: str, subject: str = "", sent_date: Optional[str] = None)`
    - 返回：`Dict[str, Any]` 包含 `{"tasks": [...]}`
  - 或使用 `extract_tasks` 函数：`app.services.extractor:extract_tasks`
    - 注意：此函数期望 `messages: List[Dict[str, Any]]`，需要适配
  
- `--data`: 测试数据文件路径（JSONL 格式）
  - 默认：`tests/data/extractor_gold.jsonl`
  
- `--title_thresh`: Title 相似度阈值（用于匹配任务）
  - 默认：0.5
  - 值越高，匹配越严格
  
- `--tolerance_minutes`: Due date 匹配的允许时间差（分钟）
  - 默认：60 分钟
  - 例如：如果预测是 "2025-11-14 10:00"，实际是 "2025-11-14 10:30"，在 60 分钟容差内算匹配
  
- `--max_examples`: 打印的 FP/FN 示例数量
  - 默认：5
  
- `--builtin_cases`: 使用内置测试用例（可选）
  - 选项：`long`, `medium`, `extra`, `all`
  - 如果指定，将使用内置用例而不是加载 JSONL 文件

## 完整示例

### 1. 基本运行（使用 JSONL 数据文件）

```bash
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl
```

### 2. 使用自定义阈值

```bash
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl \
  --title_thresh 0.6 \
  --tolerance_minutes 30
```

### 3. 使用内置测试用例

```bash
# 使用 long 用例
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --builtin_cases long

# 使用所有内置用例
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --builtin_cases all
```

### 4. 显示更多错误示例

```bash
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl \
  --max_examples 10
```

## 数据格式

测试数据文件（JSONL 格式）每行应包含：

```json
{
  "id": "e001",
  "subject": "Brand Guidelines Review",
  "from_": "Rebecca Lee <rebecca@designhub.com>",
  "body": "Hi Mark,\n\nWe've completed...",
  "tasks": [
    {
      "title": "Review updated brand guidelines and send feedback",
      "owner": "Mark",
      "due_raw": "Friday at 6 PM"
    }
  ]
}
```

## 输出说明

运行后会显示：

```
Evaluation Summary
------------------
TP (strict matches): 15
TP (partial matches): 3
TP (total): 18
FP: 2
FN: 5
Task Precision: 0.9000
Task Recall: 0.7826
Task F1: 0.8372
Owner match rate (informational): 0.8500
Due match rate (informational): 0.9000
```

### 指标说明

- **TP (strict matches)**: 完全匹配的任务数量
- **TP (partial matches)**: 部分匹配的任务数量（title 相似度在阈值内）
- **TP (total)**: 总匹配数 = strict + partial
- **FP**: False Positive（预测了但不存在于 ground truth）
- **FN**: False Negative（ground truth 中存在但未预测到）
- **Task Precision**: TP / (TP + FP)
- **Task Recall**: TP / (TP + FN)
- **Task F1**: 2 * (Precision * Recall) / (Precision + Recall)
- **Owner match rate**: Owner 字段匹配的准确率
- **Due match rate**: Due date 匹配的准确率（在容差范围内）

## 环境要求

1. **API Keys**: 确保在 `.env` 文件中设置了相应的 API keys
   ```bash
   OPENAI_API_KEY=your_key
   ANTHROPIC_API_KEY=your_key  # 如果使用 Claude
   GOOGLE_API_KEY=your_key      # 如果使用 Gemini
   ```

2. **Python 路径**: 确保从项目根目录运行，或者将项目添加到 PYTHONPATH

3. **依赖**: 确保安装了所有依赖
   ```bash
   pip install -r requirements.txt
   ```

## 故障排除

1. **ImportError**: 确保从项目根目录运行，或设置 PYTHONPATH
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **API Key 错误**: 检查 `.env` 文件中的 API keys

3. **数据文件不存在**: 确保 `tests/data/extractor_gold.jsonl` 存在

4. **函数签名不匹配**: 
   - `extract_tasks` 期望参数：`messages: List[Dict[str, Any]]`
   - `extract_tasks_from_text` 期望参数：`text: str, subject: str = "", sent_date: Optional[str] = None`
   
   确保数据格式与函数签名匹配

## 与 summarizer 测试的区别

- **Extractor 测试**：评估任务提取（title, owner, due date）
- **Summarizer 测试**：评估摘要生成（actor, action, object, deadline）

两者使用不同的评估指标和匹配逻辑。

