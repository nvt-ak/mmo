# Critical Review Skill — Design Spec

**Date:** 2026-07-01  
**Status:** Approved (brainstorming)  
**Scope:** Project-level skill + rule + YAML workflow in `.cursor/`

## Problem

Agent review hiện tại (caveman-review, review-bugbot, cavecrew-reviewer) thiên về terse PR comments hoặc bug hunt. Thiếu:

- GAP analysis (yêu cầu ↔ thực tế)
- Risk matrix có evidence
- Anti-sycophancy / anti-hallucination gates
- Readonly enforcement — không sửa file khi review
- Workflow step-by-step bắt buộc — tránh miss step

## Requirements (đã chốt)

| Item | Decision |
|------|----------|
| Artifact scope | Code + design spec + product plan (một skill thống nhất) |
| Location | Project `.cursor/` (share với team) |
| Output language | Tiếng Việt |
| Trigger | Manual only (`/critical-review`, attach skill) |
| Execution | Inline mặc định; optional subagent khi diff > 10 files |
| Verdict stance | Trung thực có bằng chứng — không issue thì nói rõ, phải chứng minh đã check đủ steps |
| Hard constraint | Readonly — không sửa bất kỳ file nào khi dùng skill |

## Approach

**Skill + YAML workflow + Rule** (Approach B):

- `SKILL.md` = orchestrator, mindset, output template
- `workflows/critical-review.yaml` = source of truth cho steps bắt buộc
- `rules/critical-review-readonly.mdc` = enforce readonly độc lập skill

## File Structure

```
.cursor/
├── skills/
│   └── critical-review/
│       ├── SKILL.md              # orchestrator + output template
│       └── artifact-guides.md    # checklist per artifact type
├── rules/
│   └── critical-review-readonly.mdc
└── workflows/
    └── critical-review.yaml      # step-by-step bắt buộc
```

## SKILL.md

~150–200 dòng. Frontmatter:

```yaml
---
name: critical-review
description: >
  Critical review với GAP analysis, risk matrix, anti-hallucination gate.
  Readonly — không sửa file. Dùng khi user gọi /critical-review, attach skill,
  hoặc yêu cầu đánh giá GAP/risk/phân tích có bằng chứng trên code, spec, plan.
disable-model-invocation: true
---
```

Nội dung chính:

1. **HARD-GATE readonly** — forbidden tools: Write, StrReplace, Delete, EditNotebook, Shell có side effects
2. **Bắt buộc** đọc `.cursor/workflows/critical-review.yaml` đầu session
3. Copy checklist từ YAML vào response, tick từng step
4. Anti-hallucination rules (xem section dưới)
5. Output template tiếng Việt
6. Link tới `artifact-guides.md` cho progressive disclosure

## artifact-guides.md

Checklist khác nhau per loại artifact:

| Type | Focus |
|------|-------|
| **code/diff** | git diff, logic, edge cases, tests; optional cavecrew-reviewer nếu >10 files |
| **design spec** | consistency, missing sections, contradictions, scope |
| **product plan** | acceptance criteria measurability, scope creep, dependencies |

## critical-review.yaml

```yaml
name: critical-review
version: 1
readonly: true

forbidden_tools:
  - Write
  - StrReplace
  - Delete
  - EditNotebook
  - Shell  # except read-only: git diff, git log, git status, cat, ls

allowed_read_tools:
  - Read
  - Grep
  - Glob
  - SemanticSearch
  - CallMcpTool  # read-only MCP only
  - Task  # subagent readonly only

subagent_triggers:
  diff_file_threshold: 10
  subagent_type: cavecrew-reviewer
  readonly: true

steps:
  - id: scope
    name: "Xác định phạm vi"
    required: true
    gate: "Không sang step tiếp nếu chưa liệt kê artifact type + danh sách files"
    actions:
      - Xác định loại: code | spec | plan | mixed
      - Liệt kê files/docs trong phạm vi review
      - Xác định baseline (spec, AC, user story, requirement gốc)
    output: scope_summary

  - id: context
    name: "Thu thập context"
    required: true
    gate: "Phải đọc ít nhất baseline doc trước khi đánh giá"
    actions:
      - Đọc spec/requirement/AC liên quan
      - Đọc ARCHITECTURE.md / AGENTS.md nếu review code
      - Đọc git diff hoặc target files
    output: context_notes

  - id: requirements_trace
    name: "Trace yêu cầu → thực tế"
    required: true
    skip_when: "artifact type = code-only, không có spec/AC"
    actions:
      - Liệt kê từng requirement/AC
      - Map: implemented | partial | missing | out-of-scope
      - Ghi GAP cho partial/missing
    output: trace_matrix

  - id: correctness
    name: "Kiểm tra correctness"
    required: true
    skip_when: "artifact type = plan-only (không có code)"
    actions:
      - Logic bugs, edge cases, error handling
      - Regression risk so với code xung quanh
      - Test coverage cho thay đổi (nếu có)
      - Optional: spawn cavecrew-reviewer nếu diff > threshold
    output: findings_correctness

  - id: risk
    name: "Phân tích risk"
    required: true
    actions:
      - Security (injection, auth, secrets, data leak)
      - Data integrity (migration, schema, race)
      - Ops (deploy, rollback, config)
      - Maintainability (coupling, dead code, unclear boundary)
      - Mỗi risk: Impact × Likelihood
    output: risk_matrix

  - id: evidence_gate
    name: "Anti-hallucination gate"
    required: true
    gate: "BLOCKER — không sang verdict nếu có finding không có citation"
    actions:
      - Re-check mọi GAP/finding/risk có evidence
      - Tag [CHƯA XÁC MINH] cho claim không verify được
      - Tag [SUY LUẬN] cho inference không có fact trực tiếp
      - Xóa hoặc downgrade finding không có basis
    output: validated_findings

  - id: verdict
    name: "Verdict"
    required: true
    gate: "Chỉ chạy khi steps 1–6 (hoặc skip hợp lệ) đã tick"
    actions:
      - Tổng hợp blockers
      - Verdict: Đủ điều kiện | Cần sửa | Cần làm rõ
      - Không praise, không hedge
    output: final_report
```

## critical-review-readonly.mdc

```yaml
---
description: Enforce readonly khi critical-review skill active
alwaysApply: false
---
```

Nội dung (~30 dòng):

- Khi user gọi `/critical-review` hoặc attach skill `critical-review` → readonly mode
- Forbidden: Write, StrReplace, Delete, EditNotebook, git commit/push, graphify update
- Shell chỉ cho read: `git diff`, `git log`, `git status`, `git show`
- User yêu cầu fix → từ chối: *"Skill này readonly. Muốn fix → tách task implement riêng."*
- Phải load `.cursor/workflows/critical-review.yaml` và tick checklist trong output

## Output Template (tiếng Việt)

```markdown
# Báo cáo Critical Review

## 1. Phạm vi
- **Loại artifact**: [code | spec | plan | mixed]
- **Files/docs đã đọc**: ...
- **Baseline so sánh**: [spec/requirement/AC nào]

## 2. Workflow checklist
- [x] scope
- [x] context
- [x] requirements_trace
- [x] correctness
- [x] risk
- [x] evidence_gate
- [x] verdict

## 3. GAP (thiếu / chưa đáp ứng)
| ID | Mô tả | Yêu cầu gốc | Thực tế | Mức độ |
|----|-------|-------------|---------|--------|
| G1 | ... | `doc:section` hoặc AC | `file:line` hoặc thiếu hẳn | 🔴/🟡/🔵 |

*Nếu không có GAP: ghi "Không phát hiện GAP" + liệt kê yêu cầu đã trace.*

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

## Anti-Sycophancy Rules

| Rule | Chi tiết |
|------|----------|
| **No praise opener** | Cấm "Looks good", "Great work", "Overall solid" |
| **Evidence or tag** | Mọi claim cần `file:line` / `doc:section` / git diff ref. Không có → `[CHƯA XÁC MINH]` |
| **No invented files** | Không cite file chưa đọc |
| **Distinguish fact vs inference** | Inference tag `[SUY LUẬN]` |
| **Empty table = OK** | Không ép tìm issue; phải show checklist done + trace log |
| **Disagree when warranted** | User assumption sai → nói thẳng, cite evidence |
| **No fix during review** | Chỉ đề xuất; fix → task riêng |

## Severity Taxonomy

| Tag | Dùng khi |
|-----|----------|
| 🔴 **blocker** | Bug, security hole, GAP vs requirement bắt buộc |
| 🟡 **risk** | Hoạt động nhưng fragile |
| 🔵 **nit** | Style, naming — không block |
| ❓ **question** | Thiếu context — cần user clarify |

## Subagent Delegation

Trigger khi diff > 10 files hoặc user yêu cầu deep code review:

1. Spawn `cavecrew-reviewer` với `readonly: true`
2. Main thread map findings → GAP/Risk tables
3. Không auto-fix

## Differentiation vs Existing Skills

| Skill | Vai trò |
|-------|---------|
| `caveman-review` | Terse PR comments, không GAP/spec |
| `review-bugbot` | Bug hunt qua subagent |
| `review-security` | Security-focused subagent |
| `critical-review` | Full GAP + Risk + evidence gate + readonly + YAML workflow |

## Success Criteria

1. Agent load workflow YAML và tick đủ 7 steps trong mọi review
2. Không Write/StrReplace/Delete khi skill active
3. Mọi finding có citation hoặc tag `[CHƯA XÁC MINH]`
4. Output tiếng Việt theo template
5. Verdict trung thực — không praise, không ép tìm issue giả

## Out of Scope

- Auto-trigger khi user nói "review"
- Fix code trong cùng session review
- Integration với CI/PR bot
- Workflow variants riêng (code-only, spec-only) — có thể thêm sau

## Implementation Files (next step)

| File | Action |
|------|--------|
| `.cursor/skills/critical-review/SKILL.md` | Create |
| `.cursor/skills/critical-review/artifact-guides.md` | Create |
| `.cursor/workflows/critical-review.yaml` | Create |
| `.cursor/rules/critical-review-readonly.mdc` | Create |
