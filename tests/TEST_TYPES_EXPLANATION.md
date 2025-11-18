# 集成测试 vs 评估测试的区别

## 📋 概述

你的项目中有两种不同类型的测试：

1. **集成测试** (`app/tests/test_process_thread.py`) - 功能测试
2. **评估测试** (`tests/test_summarizer_eval.py`) - 质量评估

## 🔍 详细对比

### 1. 集成测试 (Integration Test)

**文件**: `app/tests/test_process_thread.py`

**目的**: 
- ✅ 验证功能是否正常工作
- ✅ 确保代码不会崩溃
- ✅ 检查基本功能是否可用

**测试内容**:
```python
# 测试整个处理流程
summary = await summarize_thread(messages_dict)
assert len(summary) > 0  # 只要生成了摘要就算通过

tasks = await extract_tasks(messages_dict)
assert len(tasks) >= 1  # 只要提取到任务就算通过
```

**特点**:
- ✅ **简单快速** - 只检查功能是否可用
- ✅ **不评估质量** - 不关心摘要好坏
- ✅ **使用简单数据** - 几个测试用例
- ✅ **通过/失败** - 二元结果（pass/fail）

**运行方式**:
```bash
pytest app/tests/test_process_thread.py -v
```

**适用场景**:
- 开发过程中快速验证功能
- CI/CD 自动化测试
- 确保代码修改后功能正常

---

### 2. 评估测试 (Evaluation Test)

**文件**: `tests/test_summarizer_eval.py`

**目的**:
- 📊 评估输出质量
- 📊 计算性能指标
- 📊 对比 gold standard（标准答案）
- 📊 找出改进方向

**测试内容**:
```python
# 计算各种质量指标
- ROUGE-1 分数（词汇重叠）
- ROUGE-L 分数（最长公共子序列）
- 关键事实准确率（actor, action, object, deadline）
- 格式合规性（长度、标点、动作动词等）
- 精确率/召回率/F1 分数
```

**特点**:
- 📊 **详细分析** - 多个质量指标
- 📊 **使用 gold data** - 对比标准答案
- 📊 **量化结果** - 给出具体分数
- 📊 **错误分析** - 找出失败案例

**运行方式**:
```bash
python tests/test_summarizer_eval.py \
  --agent "app.services.summarizer:summarize_text" \
  --data tests/data/summarizer_gold.jsonl \
  --csv_out results.csv
```

**输出示例**:
```
Summarizer Evaluation Summary
--------------------------------
Total cases evaluated: 20
Mean ROUGE-1 Recall: 0.8235
Mean ROUGE-L Recall: 0.7892
Fact TP (strict): 45
Fact TP (partial): 12
Fact FP: 8
Fact FN: 15
Key Fact Precision: 0.8723
Key Fact Recall: 0.7500
Key Fact F1: 0.8065
Fact Slot Accuracy (strict only):
  Actor: 95.00%
  Action: 85.00%
  Object: 70.00%
  Deadline: 80.00%
```

**适用场景**:
- 模型性能评估
- 优化改进方向
- 发布前质量检查
- 对比不同模型版本

---

## 📊 对比表格

| 特性 | 集成测试 | 评估测试 |
|------|---------|---------|
| **目的** | 验证功能可用 | 评估输出质量 |
| **复杂度** | 简单 | 复杂 |
| **运行时间** | 快（秒级） | 慢（分钟级，需要调用 API） |
| **测试数据** | 少量简单用例 | 大量 gold data |
| **输出** | Pass/Fail | 详细指标和分数 |
| **使用场景** | 开发/CI | 性能评估/优化 |
| **成本** | 低（可能用 mock） | 高（需要真实 API 调用） |

---

## 🎯 实际例子

### 集成测试示例
```python
# 测试：能否生成摘要？
summary = await summarize_thread(messages)
assert len(summary) > 0  # ✅ 通过：生成了摘要
# ❌ 失败：没有生成摘要（可能是 bug）
```

### 评估测试示例
```python
# 测试：摘要质量如何？
gold = "Alice asks Bob to review the project draft by Friday."
pred = "Alice requests Bob to check the project draft by Friday."

# 计算相似度
rouge_score = calculate_rouge(gold, pred)  # 0.85
fact_accuracy = compare_facts(gold_facts, pred_facts)  # 0.90

# 输出：质量分数 0.85，事实准确率 90%
```

---

## 💡 使用建议

### 开发阶段
- ✅ 使用**集成测试**快速验证功能
- ✅ 确保代码修改后基本功能正常

### 优化阶段
- 📊 使用**评估测试**评估改进效果
- 📊 对比不同模型/参数的性能

### 发布前
- ✅ 运行**集成测试**确保功能正常
- 📊 运行**评估测试**确保质量达标

---

## 🔧 运行命令总结

```bash
# 集成测试（快速验证功能）
pytest app/tests/test_process_thread.py -v

# 评估测试（详细质量分析）
python tests/test_summarizer_eval.py \
  --agent "app.services.summarizer:summarize_text" \
  --data tests/data/summarizer_gold.jsonl \
  --csv_out results.csv \
  --per_case_dump details.json
```

---

## 📝 总结

- **集成测试** = "能工作吗？" ✅/❌
- **评估测试** = "工作得好吗？" 📊 (分数和指标)

两者互补，缺一不可！

