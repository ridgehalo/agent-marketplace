---
name: issue-to-pr
description: Implement an existing GitHub Issue through a dedicated branch, verification, commit, push, and pull request. Use when the user asks to handle a named Issue through PR creation; do not use for read-only explanation or review.
---

# Issue to PR

既存GitHub Issueを、利用リポジトリの規約に従って検証済みPRへ進める。

GitHub操作を行う前に [GitHub safety contract](../../references/github-safety.md) を読む。

## 入力と完了条件

Issue URLまたは `OWNER/REPO#NUMBER` を優先する。番号だけの場合は現在のrepoを確定してから解決する。Projectの先頭Issueを選ぶ依頼では、APIから順序を再現できる場合だけ選び、手動順序やfilterが不明なら推測しない。

Issue本文から次を取り出す。

- 目的
- 完了条件
- やらないこと
- 必要な成果物
- Human Gateと権限境界
- relationshipと既存PR
- 要求ごとの検証証拠

plugin内に `contracts/manifest.json` がある場合は、利用repositoryの規約を上書きせず、公開contract version、risk routing、Evidence typeを解決する。Issue、Plan、Test Intent、Reviewer、PR Evidenceの雛形は `templates/` を使い、consumer固有値を公開coreへ書き戻さない。

chat上の調査結果だけで完了としない。IssueがPRまでの実装を求めるなら、branch、変更、検証、commit、push、PR作成、read-backまでが完了条件になる。

## 着手判断

次の場合は実装前に止める。

- 対象Issueまたはrepoを一意に決められない
- blocked-by relationshipが未解消
- Issueより大きい権限変更や公開操作が必要
- 既存PRが同じ完了条件を処理中
- 成果物の所有先が決まらず、選択が永続的な設計判断になる

Issueがduplicate、obsolete、すでに完了、または意味のある成果物を作れない場合は、PRを無理に作らずtriage結果を返す。

## 実行

1. rootと近接する永続指示、contribution guide、test commandを読む。
2. dirty worktreeを保護し、最新baseから専用branchまたは隔離worktreeを作る。
3. 要求を実装・docs・testへ対応付け、関連ファイルを読んでから変更する。
4. 最小差分ではなく、Issueの明示的な完了条件を満たす最小の一貫した変更を作る。
5. 変更種別に合うlint、test、build、manual checkを実行する。
6. 各要求に証拠があるか監査し、狭いtestで広い完了を主張しない。
7. unrelatedなユーザー差分を除外してcommitし、branchをpushする。
8. 背景、変更、検証、review観点、残リスク、Issue URLを含むPRを作る。
9. PRとchecksを作成先から読み戻す。
10. `pr-self-review` が利用可能なら、人間review前に実行して必要修正と再検証を同じbranchへ反映する。

## PR本文

最低限、次を含める。

```markdown
## 背景

## 対応内容

## 検証

## レビュー観点

## Relationship

## 残リスク

Closes https://github.com/OWNER/REPO/issues/NUMBER
```

Issueを完全には満たさないPRで `Closes` を使わない。Project固有statusや自動merge分類は利用repoの指示がある場合だけ追加する。

## 引き渡し

対象Issue、branch、commit、PR、実行した検証、未実行検証、relationship、残リスクを分けて報告する。PR作成に失敗した場合は、local成果を巻き戻さず、失敗した操作と再開方法を残す。
