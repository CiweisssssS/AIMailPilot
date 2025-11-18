# Extractor 模型对比分析：为什么结果相反？

## 测试结果对比

### 单测结果 (tests/extractor_eval.py)
- **GPT-4o-mini**: F1=0.9412, Precision=0.9231, Recall=0.9600
- **Gemini Flash**: F1=0.9020, Precision=0.8846, Recall=0.9200
- **结论**: GPT-4o-mini 表现更好

### Eval 脚本结果 (eval/run_extractor_*.py)
- **Gemini Flash**: F1=0.9020, Precision=0.8846, Recall=0.9200
- **GPT-4o-mini**: F1=0.8980, Precision=0.9167, Recall=0.8800
- **结论**: Gemini Flash 表现更好（但差异很小）

## 关键差异分析

### 1. 数据集不同

**单测数据集** (`tests/data/extractor_gold.jsonl`):
- 格式：`{title, owner, due_raw}`
- Ground truth 示例：
  ```json
  {
    "title": "Review updated brand guidelines and send feedback",
    "owner": "Mark",
    "due_raw": "Friday at 6 PM"
  }
  ```
- 特点：使用自然语言 title

**Eval 数据集** (`eval/dataset/emails.jsonl`):
- 格式：`{action, object, owner, deadline}`
- Ground truth 示例：
  ```json
  {
    "owner": "me",
    "action": "send",
    "object": "project draft",
    "deadline": "2025-11-14"
  }
  ```
- 特点：使用结构化字段

### 2. 评估逻辑不同

**单测评估逻辑** (`tests/extractor_eval.py`):
- **主要关注**: title 的语义相似度
- **匹配方式**: 
  - Strict match: title 相似度 >= 阈值（默认 0.5，会根据 title 长度调整）
  - Partial match: title 相似度 >= 降低后的阈值（阈值 - 0.15）
- **相似度计算**: `title_similarity = 0.6 * jaccard + 0.4 * seq_ratio`
- **特点**: 更关注 title 的整体语义匹配

**Eval 评估逻辑** (`eval/run_pipeline.py` 的 `prf_tasks`):
- **主要关注**: 结构化字段的准确性（action, object, owner, deadline）
- **匹配方式**:
  - Strict/lenient: 基于 JSON 字符串的完全匹配（经过标准化）
  - Very lenient: k-of-4 字段匹配（默认 k=2）
- **特点**: 更关注结构化字段的准确性

### 3. 任务格式转换

**单测**:
- LLM 返回：`{title: "[Submit Q4 report Alice]", owner: "Alice", due: "Friday"}`
- Ground truth：`{title: "Submit Q4 report", owner: "Alice", due_raw: "Friday"}`
- **评估**: 直接比较 title 相似度

**Eval**:
- LLM 返回：`{title: "[Submit Q4 report Alice]", owner: "Alice", due: "Friday"}`
- 转换为：`{action: "submit", object: "q4 report", owner: "Alice", deadline: "Friday"}`
- Ground truth：`{action: "send", object: "project draft", owner: "me", deadline: "2025-11-14"}`
- **评估**: 比较结构化字段（action, object, owner, deadline）

## 为什么结果相反？

### 1. GPT-4o-mini 的优势（单测中表现更好）

**Title 表达更接近自然语言**:
- GPT-4o-mini 生成的 title 可能更接近 ground truth 的自然语言风格
- 例如：GT 是 "Review updated brand guidelines and send feedback"
- GPT-4o-mini 可能生成类似的自然语言 title
- Gemini 可能生成更结构化的 title（如 "[Review brand guidelines team]"）

**语义相似度匹配**:
- 单测使用 title 相似度匹配，GPT-4o-mini 的自然语言 title 更容易匹配
- 即使有细微差异，语义相似度也能捕获

### 2. Gemini Flash 的优势（Eval 中表现更好）

**结构化字段提取更准确**:
- Gemini 可能更严格地遵循 EXTRACTION_PROMPT 的格式要求
- 生成的 title 格式 `[VERB OBJECT OWNER]` 更容易解析为 action 和 object
- 解析后的 action 和 object 更准确

**字段匹配优势**:
- Eval 使用结构化字段匹配，Gemini 的结构化输出更容易匹配
- 即使 title 不完全匹配，解析后的 action/object 可能更准确

### 3. 数据集差异的影响

**单测数据集** (`extractor_gold.jsonl`):
- 可能包含更多自然语言风格的 title
- 更适合测试 title 相似度匹配

**Eval 数据集** (`emails.jsonl`):
- 使用结构化字段作为 ground truth
- 更适合测试结构化字段提取的准确性

## 结论

1. **评估标准不同导致结果相反**：
   - 单测关注 title 语义相似度 → GPT-4o-mini 表现更好
   - Eval 关注结构化字段准确性 → Gemini 表现更好

2. **模型特性不同**：
   - GPT-4o-mini：更擅长生成自然语言风格的 title
   - Gemini Flash：更擅长生成结构化格式的 title

3. **实际应用建议**：
   - 如果关注 title 的语义匹配 → 使用 GPT-4o-mini
   - 如果关注结构化字段的准确性 → 使用 Gemini Flash
   - **对于实际应用，结构化字段的准确性更重要**，因为：
     - 结构化字段（action, object, owner, deadline）是下游任务的核心
     - Title 可以后处理，但结构化字段需要准确提取

## 建议

1. **统一评估标准**：使用 eval 脚本的评估逻辑（基于结构化字段），因为它更符合实际应用需求

2. **改进模型输出**：
   - 如果使用 GPT-4o-mini，可以改进 title 解析逻辑，确保从 title 中准确提取 action 和 object
   - 如果使用 Gemini，可以改进 prompt，使其生成的 title 更接近自然语言（如果下游需要）

3. **综合考虑**：
   - 虽然 Gemini 在 eval 中表现略好（F1: 0.9020 vs 0.8980），但差异很小
   - 可以根据其他因素（成本、延迟、可用性）来选择模型

