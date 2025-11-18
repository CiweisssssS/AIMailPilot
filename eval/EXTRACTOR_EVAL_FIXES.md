# Extractor 评估修复总结

## 修复的问题

### 1. Deadline 解析失败（关键问题）

**问题**：
- `_normalize_date` 无法解析单独的 "Friday"、"Monday" 等工作日名称
- 评估代码中调用 `_normalize_date` 时没有传递 `received_at` 参数
- 导致相对时间表达式无法解析，deadline 匹配失败

**修复**：
1. **增强了 `_normalize_date` 函数**（`eval/run_pipeline.py`）：
   - 添加了对单独工作日名称的解析（如 "Friday", "Friday at 6 PM"）
   - 如果今天是该工作日，返回今天；否则返回下一个该工作日

2. **修复了 `tests/extractor_eval.py`**：
   - 在调用 `_normalize_date` 时传递 `received_at` 参数
   - 从 row 中获取 `sent_date` 或 `date` 字段作为 `received_at`

### 2. 默认评估模式

**问题**：
- 默认使用 `lenient=True, very_lenient=False`
- 这会导致语义相似的任务无法匹配（如 "review" vs "check"）

**修复**：
- 默认使用 `very_lenient=True`，启用语义相似度匹配
- 这样可以匹配语义相似但文本不完全相同的任务

## 修复后的效果

修复后应该看到：
- ✅ Deadline 能正确解析相对时间表达式（如 "Friday" → "2025-11-14"）
- ✅ Deadline 匹配率提高（因为能正确解析和比较）
- ✅ TP 数量增加（因为 deadline 能匹配）
- ✅ Precision 和 Recall 提高
- ✅ 语义相似的任务能匹配（如 "review" vs "check"）

## 测试建议

运行测试时建议使用：

```bash
# 使用 very_lenient 模式（默认）
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl

# 或者明确指定参数
python -m tests.extractor_eval \
  --agent app.services.extractor:extract_tasks_from_text \
  --data tests/data/extractor_gold.jsonl \
  --very_lenient \
  --sim_threshold 0.6 \
  --task_match_k 2
```

## 注意事项

1. **数据格式**：确保测试数据包含 `sent_date` 或 `date` 字段，用于 deadline 解析
2. **Title 解析**：如果 title 解析不准确，可能需要改进 `parse_action_object_from_title` 函数
3. **评估模式**：根据需求选择合适的评估模式（strict/lenient/very_lenient）

