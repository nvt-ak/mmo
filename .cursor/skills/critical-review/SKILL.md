---
name: critical-review
description: >
  Critical review với GAP analysis, risk matrix, anti-hallucination gate.
  Readonly — không sửa file. Dùng khi user gọi /critical-review, attach skill,
  hoặc yêu cầu đánh giá GAP/risk/phân tích có bằng chứng trên code, spec, plan.
disable-model-invocation: true
---

# Critical Review

Readonly review skill. Phân tích GAP, Risk, correctness — output tiếng Việt, có bằng chứng.

<HARD-GATE>
KHÔNG dùng Write, StrReplace, Delete, EditNotebook khi skill active.
KHÔNG git commit/push, graphify update.
User yêu cầu fix → từ chối, đề xuất task implement riêng.
</HARD-GATE>

## Khởi động

1. Đọc `.cursor/workflows/critical-review.yaml` — source of truth cho steps
2. Đọc [artifact-guides.md](artifact-guides.md) theo loại artifact
3. Thực hiện từng step theo thứ tự; không skip gate
4. Xuất báo cáo theo template dưới

## Workflow (tóm tắt)

| Step | Mục đích | Skip khi |
|------|----------|----------|
| `scope` | Artifact type + files + baseline | — |
| `context` | Đọc docs/code liên quan | — |
| `requirements_trace` | Map yêu cầu → thực tế | code-only, không có spec/AC |
| `correctness` | Bugs, edge cases, tests | plan-only |
| `risk` | Security, data, ops, maintainability | — |
| `evidence_gate` | Re-check citations | — |
| `verdict` | Kết luận có blockers | — |

Copy checklist vào output, tick `[x]` khi xong. Step skip → ghi lý do.

## Anti-sycophancy

| Rule | Hành vi |
|------|---------|
| No praise | Cấm "Looks good", "Great work", "Overall solid" |
| Evidence or tag | Mọi claim cần `file:line` / `doc:section` / diff ref. Không có → `[CHƯA XÁC MINH]` |
| No invented files | Không cite file chưa đọc |
| Fact vs inference | Inference → tag `[SUY LUẬN]` |
| Empty OK | Không ép tìm issue; phải show checklist + trace log |
| Disagree | User assumption sai → nói thẳng, cite evidence |
| No fix | Chỉ đề xuất |

## Severity

| Tag | Khi nào |
|-----|---------|
| 🔴 blocker | Bug, security, GAP requirement bắt buộc |
| 🟡 risk | Hoạt động nhưng fragile |
| 🔵 nit | Style, naming |
| ❓ question | Thiếu context |

## Subagent (optional)

Khi diff > 10 files hoặc user yêu cầu deep code review:

```
Task subagent_type=cavecrew-reviewer, readonly=true
```

Main thread map findings → GAP/Risk tables. Không auto-fix.

## Output template

```markdown
# Báo cáo Critical Review

## 1. Phạm vi
- **Loại artifact**: [code | spec | plan | mixed]
- **Files/docs đã đọc**: ...
- **Baseline so sánh**: ...

## 2. Workflow checklist
- [x] scope — [skip: lý do nếu có]
- [x] context
- [x] requirements_trace
- [x] correctness
- [x] risk
- [x] evidence_gate
- [x] verdict

## 3. GAP (thiếu / chưa đáp ứng)
| ID | Mô tả | Yêu cầu gốc | Thực tế | Mức độ |
|----|-------|-------------|---------|--------|
| G1 | ... | `doc:section` | `file:line` | 🔴/🟡/🔵 |

*Không có GAP: ghi "Không phát hiện GAP" + liệt kê yêu cầu đã trace.*

## 4. Risk
| ID | Risk | Impact | Likelihood | Mitigation đề xuất | Evidence |
|----|------|--------|------------|-------------------|----------|
| R1 | ... | Cao/TB/Thấp | Cao/TB/Thấp | ... | `file:line` |

## 5. Findings (correctness / quality)
| Severity | Location | Vấn đề | Đề xuất |
|----------|----------|--------|---------|
| 🔴 bug | `path:L42` | ... | ... |

## 6. Verdict
- **Kết luận**: [Đủ điều kiện | Cần sửa trước khi merge | Cần làm rõ thêm]
- **Lý do**: 1–3 câu, cite evidence
- **Blockers** (nếu có): G1, R1, ...
```

## Phân biệt với skills khác

| Skill | Dùng khi |
|-------|----------|
| `caveman-review` | Terse PR comments nhanh |
| `review-bugbot` | Bug hunt qua subagent |
| `review-security` | Security-focused |
| `critical-review` | Full GAP + Risk + evidence gate + readonly |
