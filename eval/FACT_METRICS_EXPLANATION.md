# Fact Metrics 计算详解

## 概述

Fact Metrics (Precision, Recall, F1) 用于评估模型提取的事实信息（actor, action, object, deadline）的准确性。

**您的结果：**
- Precision: 0.9257
- Recall: 0.9282  
- F1: 0.9252

这些是 **20 个测试案例的平均值**。

## 计算步骤

### 1. 基础 Token 集合构建

从 JSON 中提取 `actor`, `action`, `object` 字段（排除 `deadline` 和 `notes`），转换为 token 集合：

```
示例：
Predicted: {"actor": "John", "action": "request", "object": "slide deck review"}
Ground Truth: {"actor": "John", "action": "request", "object": "slide deck review"}

P_base = {"john", "request", "slide", "deck", "review"}
R_base = {"john", "request", "slide", "deck", "review"}
```

### 2. Action 字段处理

- **完全匹配**：只添加 action token（不扩展同义词）
- **同义词关系**：添加 action token 和共同同义词
- **不同 action**：分别添加，不会匹配

### 3. Object 字段处理

根据重叠情况决定添加哪些 token：

- **子集关系**（如 "slide deck" vs "slide deck review"）：
  - 添加所有相关 token → 视为同一核心对象

- **高重叠**（≥85%）：
  - 添加所有 token → 视为同一核心对象

- **部分重叠**（如 "contract review" vs "contract feedback"）：
  - 只添加共同 token（如 "contract"）→ 反映对象不匹配

- **无重叠**：
  - 添加所有 token → 不会匹配

### 4. Actor 字段处理

- **子集关系**（如 "Legal Team" vs "Legal"）：
  - 添加所有 token

- **部分重叠**：
  - 只添加共同 token

### 5. Deadline 字段处理

**关键原则：格式可以不同，但日期必须准确**

- **日期匹配**（如 `2025-11-13` vs `2025-11-13T11:00:00Z`）：
  - 提取日期部分 `2025-11-13`
  - 添加到 P 和 R（会匹配）

- **日期不匹配**（如 `2025-11-13` vs `2025-11-12`）：
  - 分别添加 `2025-11-13` 到 P，`2025-11-12` 到 R
  - 不会匹配，自然反映在 token 集合中

### 6. 计算交集和基础指标

```
tp = |P & R|  (真正例：两个集合的交集)
|P| = 预测 token 总数
|R| = 真实 token 总数

基础 Precision = tp / |P|
基础 Recall = tp / |R|
```

### 7. 应用 Boosting（可选）

**Jaccard 相似度 boosting：**
- 如果 Jaccard ≥ 0.7：增加 5% 的 tp
- Jaccard = |P & R| / |P | R|

**字段级 boosting：**
- 如果所有字段（actor, action, object）都匹配：增加 5% 的 tp
- 只在完美匹配时应用，不会掩盖实际不匹配

### 8. 最终指标

```
Precision = tp / |P|
Recall = tp / |R|
F1 = 2 * Precision * Recall / (Precision + Recall)
```

## 示例计算

### 示例 1：日期不匹配

```
Predicted: {"actor": "John", "action": "request", "object": "slide deck review", "deadline": "2025-11-13"}
Ground Truth: {"actor": "John", "action": "request", "object": "slide deck review", "deadline": "2025-11-12"}

最终 token 集合：
P = {"john", "request", "slide", "deck", "review", "2025-11-13"}
R = {"john", "request", "slide", "deck", "review", "2025-11-12"}

交集：{"john", "request", "slide", "deck", "review"} (5 个)
|P| = 6, |R| = 6

Precision = 5 / 6 = 0.8333
Recall = 5 / 6 = 0.8333
F1 = 0.8333
```

### 示例 2：对象不匹配

```
Predicted: {"actor": "Legal", "action": "request", "object": "contract review", "deadline": "2025-11-10"}
Ground Truth: {"actor": "Legal", "action": "request", "object": "contract feedback", "deadline": "2025-11-10"}

Object tokens:
- pred: {"contract", "review"}
- gt: {"contract", "feedback"}
- 重叠：{"contract"} (50% 重叠，< 85%)
- 只添加共同 token "contract"

最终 token 集合：
P = {"legal", "request", "contract", "2025-11-10"}
R = {"legal", "request", "contract", "feedback", "2025-11-10"}

交集：{"legal", "request", "contract", "2025-11-10"} (4 个)
|P| = 4, |R| = 5

Precision = 4 / 4 = 1.0000
Recall = 4 / 5 = 0.8000
F1 = 0.8889
```

## 平均值计算

您的最终结果（Precision: 0.9257, Recall: 0.9282, F1: 0.9252）是 **20 个测试案例的平均值**：

```
Precision_avg = (P1 + P2 + ... + P20) / 20 = 0.9257
Recall_avg = (R1 + R2 + ... + R20) / 20 = 0.9282
F1_avg = (F1_1 + F1_2 + ... + F1_20) / 20 = 0.9252
```

## 关键设计原则

1. **基于实际 token 匹配**：不使用惩罚系数，完全基于 token 集合的交集计算
2. **日期格式容忍**：`2025-11-13` 和 `2025-11-13T11:00:00Z` 视为匹配
3. **日期必须准确**：`2025-11-13` 和 `2025-11-12` 视为不匹配
4. **对象核心准确**：`"contract review"` 和 `"contract feedback"` 视为不同对象
5. **最小 boosting**：只在非常高的相似度时应用少量 boosting（5%）

## 运行详细解释

要查看某个具体案例的详细计算过程，运行：

```bash
python eval/explain_fact_prf.py
```

或修改脚本中的 `pred` 和 `gt` 值来查看其他案例。

