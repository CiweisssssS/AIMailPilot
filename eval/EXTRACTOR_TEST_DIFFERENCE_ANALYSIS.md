# Extractor 测试结果差异分析

## 问题描述

之前的单测和组合测试显示 **Gemini Flash 效果比 GPT-4o-mini 好**，但现在使用 `tests/extractor_eval.py` 测试时，**GPT-4o-mini 表现更好**。

## 测试结果对比

### 之前的测试（eval 脚本）
- **Gemini Flash**: F1=0.79, Precision=0.783, Recall=0.825
- 测试脚本：`eval/run_extractor_gemini.py`
- 评估逻辑：`eval/run_pipeline.py` 的 `prf_tasks` 函数
- 测试数据：`eval/dataset/emails.jsonl`

### 现在的测试（tests 脚本）
- **Gemini Flash**: F1=0.9020, Precision=0.8846, Recall=0.9200, **Strict TP=0**
- **GPT-4o-mini**: F1=0.9412, Precision=0.9231, Recall=0.9600, **Strict TP=2**
- 测试脚本：`tests/extractor_eval.py`
- 评估逻辑：自定义的 `title_similarity` 和 `due_match` 函数
- 测试数据：`tests/data/extractor_gold.jsonl`

## 关键差异分析

### 1. 不同的测试数据集

**eval/dataset/emails.jsonl**:
- 可能包含不同难度和类型的邮件
- 可能更关注结构化字段的准确性

**tests/data/extractor_gold.jsonl**:
- 可能包含不同风格的任务描述
- 可能更关注 title 的语义匹配

### 2. 不同的评估逻辑

#### eval/run_pipeline.py 的 `prf_tasks` 函数
- **匹配方式**：基于结构化字段（action, object, owner, deadline）的 k-of-4 匹配
- **相似度计算**：使用 `_similarity` 函数（Jaccard 相似度 + 子集关系检测）
- **匹配标准**：
  - `very_lenient` 模式：需要 k 个字段匹配（默认 k=2）
  - 使用 `_similarity` 计算 action 和 object 的相似度
  - 更关注**结构化字段的准确性**

#### tests/extractor_eval.py 的评估逻辑
- **匹配方式**：基于 **title 相似度**的匹配
- **相似度计算**：`title_similarity = 0.6 * jaccard + 0.4 * seq_ratio`
- **匹配标准**：
  - **Strict match**：title 相似度 >= 阈值（默认 0.5，会根据 title 长度调整）
  - **Partial match**：title 相似度 >= 降低后的阈值（阈值 - 0.15）
  - 更关注**title 的语义相似度**

### 3. 关键发现：Strict TP = 0

**Gemini Flash 的 Strict TP = 0** 说明：
- Gemini 提取的 task title 与 ground truth 的 title **没有完全匹配**（即使经过相似度计算）
- 所有匹配都是 **partial match**（相似度在阈值范围内，但不是完全匹配）
- 这表明 Gemini 可能在 **title 表达方式**上与 ground truth 有差异

**GPT-4o-mini 的 Strict TP = 2** 说明：
- GPT-4o-mini 至少有 2 个 task 的 title 与 ground truth **完全匹配**（或相似度很高）
- 这表明 GPT-4o-mini 在 **title 表达方式**上更接近 ground truth

## 可能的原因

### 1. Title 表达方式差异

**Gemini Flash** 可能：
- 使用更自然的语言表达 task title
- 添加更多细节或修饰词
- 使用不同的动词形式

**GPT-4o-mini** 可能：
- 更接近 ground truth 的表达方式
- 更简洁、直接的 task title
- 更符合测试数据的风格

### 2. 评估标准偏向

**tests/extractor_eval.py** 的评估标准：
- **主要依赖 title 相似度**，而不是结构化字段
- 如果 ground truth 的 title 风格与 GPT-4o-mini 的输出风格更接近，GPT-4o-mini 会获得更高分数

**eval/run_pipeline.py** 的评估标准：
- **主要依赖结构化字段**（action, object, owner, deadline）
- 如果 Gemini 在结构化字段提取上更准确，Gemini 会获得更高分数

### 3. 测试数据差异

- `eval/dataset/emails.jsonl` 可能包含更多需要结构化字段准确性的场景
- `tests/data/extractor_gold.jsonl` 可能包含更多需要 title 语义匹配的场景

## 建议

### 1. 统一评估标准

建议使用 **eval/run_pipeline.py** 的评估逻辑，因为：
- 它更关注结构化字段的准确性（action, object, owner, deadline）
- 这些字段对于下游任务（如任务管理、优先级排序）更重要
- 评估逻辑更标准化，便于比较不同模型

### 2. 使用相同的测试数据

在两个测试脚本中使用相同的测试数据集，确保结果可比性。

### 3. 分析具体案例

查看 `tests/extractor_eval.py` 生成的错误示例，分析：
- Gemini 的 title 与 ground truth 的具体差异
- 为什么 GPT-4o-mini 的 title 更接近 ground truth
- 是否可以通过 prompt 优化来改善 Gemini 的 title 表达

### 4. 综合考虑

- **如果关注结构化字段准确性**：使用 eval 脚本的结果，Gemini 可能更好
- **如果关注 title 语义匹配**：使用 tests 脚本的结果，GPT-4o-mini 可能更好
- **实际应用**：应该更关注结构化字段的准确性，因为 title 可以后处理，但结构化字段是核心功能

## 结论

测试结果差异的主要原因是：
1. **不同的评估逻辑**：eval 脚本关注结构化字段，tests 脚本关注 title 相似度
2. **不同的测试数据**：可能包含不同难度和类型的场景
3. **不同的匹配标准**：strict vs partial match 的定义不同

**建议**：使用 `eval/run_pipeline.py` 的评估逻辑和测试数据，因为它更关注结构化字段的准确性，这对实际应用更重要。

