---
name: Goal / PBI
about: 実装・調査・運用改善をIssueからPRまで一続きで扱う
title: ""
labels: ""
assignees: ""
---

## 1. 概要

### Outcome

<!-- 初めて読む人にも分かる言葉で、完了すると誰が何をできるようになるかを書きます。 -->

### Work Routing

- Product:
- Work Type: `implementation | documentation | research`
- Target Repository:
- Goal Mode: `Manual | Auto | Hold`

## 2. 背景

<!-- なぜ今必要か、現在地、関連する判断やEvidenceをURL付きで書きます。 -->

## 3. 詳細設計

### ゴール

<!-- 実装手段ではなく、完了時に成立している状態を書きます。 -->

### Complexity and dependencies

- Complexity: `low | medium | high | critical`
- Dependency boundaries:
- Functional Core:
- Imperative Shell:

### Risk and Human Gates

- Risk:
- Risk Triggers:
- Reviewer Routing:
- Human Gate Requirement:
- Release Human Gates:
- Human Gate Approval Evidence:

## 4. テスト影響範囲

### Test Intent

- 影響するproduct / repository / contract:
- 既存テストへの影響:
- Unit / Integration / E2Eの採用・非採用理由:
- 境界値、失敗条件、再試行、並行実行、stale state:
- namespace / factory / cleanup:
- production / personal-data / external-write guard:

#### Test topology

- Unit:
- Integration:
- E2E:
- Not selected and why:

#### Boundary and failure cases

#### Safe test infrastructure

- Unique namespace:
- Factory:
- Cleanup:
- Production / personal-data guards:
- External-write command separation:

## 5. 新規テストケース

### Acceptance criteria

- [ ] Positive scenario:
- [ ] Negative scenario:
- [ ] 必要な検証を実行し、成功・失敗・未実行を区別した

### Verification Plan

- Local test:
- CI:
- Build:
- Manual journey:
- Deployment:
- External read-back:

## 6. 実装順

1. <!-- Plan -->
2. <!-- Test first / Build -->
3. <!-- Verify / review -->
4. <!-- PR / Project read-back -->

## 7. マージ前確認

- [ ] 最終HEADで必要な検証を実行した
- [ ] AIセルフレビューを実施した
- [ ] Issue / PR / Relationships / Projectを読み戻した
- [ ] Human Gateが必要な操作を未承認で実行していない
- [ ] 未実行の確認と残存リスクを記録した

## 8. スコープ外

### Non-goals

- <!-- 今回行わないことを書きます。 -->

## Project Status

- Status: `Todo`
- Priority:
- Codex Priority: `C2`
- Area:
- Product:

### 関連Issue / PR

- Parent:
- Blocked by:
- Blocks:
- Related:
- Existing PR:
