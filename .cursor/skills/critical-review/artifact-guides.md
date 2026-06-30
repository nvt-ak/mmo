# Artifact Guides — Critical Review

Đọc section phù hợp với loại artifact đã xác định ở step `scope`.

## Code / Diff

**Baseline:** spec liên quan, user story, AC, hoặc mô tả thay đổi từ user.

**Checklist:**

- [ ] `git diff` hoặc `git diff <base>...HEAD` — biết chính xác files thay đổi
- [ ] Đọc từng file changed, không chỉ diff hunks
- [ ] Logic: happy path + edge cases + error paths
- [ ] Regression: callers/callees bị ảnh hưởng?
- [ ] Tests: có test mới/cập nhật cho thay đổi? coverage đủ?
- [ ] Schema/migration: backward compatible?
- [ ] Config/env: default an toàn khi thiếu giá trị?

**Subagent:** diff > 10 files → spawn `cavecrew-reviewer` (`readonly: true`). Map findings vào bảng GAP/Risk — không copy nguyên văn mù quáng.

## Design Spec

**Baseline:** requirement gốc, problem statement, constraints đã chốt.

**Checklist:**

- [ ] Mọi section bắt buộc có mặt? (problem, solution, scope, out-of-scope, success criteria)
- [ ] Contradiction nội bộ giữa các section?
- [ ] Success criteria đo được được không?
- [ ] Scope creep — feature nào không trace về problem?
- [ ] Dependencies / assumptions ghi rõ chưa?
- [ ] Error handling, rollback, migration có đề cập?
- [ ] Files changed list khớp solution mô tả?

## Product Plan / User Story

**Baseline:** business goal, user pain, metric thành công.

**Checklist:**

- [ ] Acceptance criteria: cụ thể, testable, không mơ hồ ("nhanh hơn", "tốt hơn")
- [ ] IN/OUT scope rõ?
- [ ] Dependencies (team khác, API, infra) đã liệt kê?
- [ ] Risk: timeline, unknowns, technical feasibility
- [ ] User story format: ai, muốn gì, để làm gì — đủ 3 phần?
- [ ] Có metric đo success sau ship?

## Mixed

Khi artifact gồm code + spec + plan:

1. Trace requirements qua spec/plan trước (step `requirements_trace`)
2. Verify implementation trong code (step `correctness`)
3. GAP = requirement có trong spec nhưng thiếu/sai trong code
4. Risk gộp từ cả 3 layer — tag evidence đúng layer (`doc:section` vs `file:line`)
