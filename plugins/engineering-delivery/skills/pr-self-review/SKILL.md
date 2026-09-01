---
name: pr-self-review
description: Review a pull request before human review, find cross-file omissions, apply authorized fixes, rerun verification, and update the review evidence. Use after PR creation or when the user explicitly requests a PR self-review.
---

# PR Self Review

人間reviewを置き換えず、その前にAIが見つけやすい抜け漏れを潰す。

GitHubを読む・更新する場合は [GitHub safety contract](../../references/github-safety.md) を読む。

## 対象

明示されたPRを優先する。省略時は現在branchに対応するPRを正確に解決する。PRがまだない場合はlocal diff reviewとして実行し、PR本文更新は未実行と明記する。

repoの永続指示、linked Issue、PR本文、review comments、Issue comments、checks、baseとの差分を読む。コメントやcheckを取得できない場合は未確認として扱う。dependencyとparent / childはnative Relationshipsを正本として読み戻す。

## Review設計

変更を `code / test / script / docs / skill / configuration / content` に分類し、影響が大きい1〜3観点へ絞る。

- correctness: 仕様、境界値、error handling、data loss
- security: 入力、権限、secret、外部write、supply chain
- delivery: Issueとの対応、branch、PR本文、verification、rollback
- consistency: docs、skill、config、旧説明、利用側contract
- user evidence: UI導線、accessibility、実機またはbrowser evidence

指摘はP0からP3で重大度を付け、ファイルと根拠を示す。根拠のない一般論やstyle preferenceをfindingにしない。

## 実行

1. PR diffと要求を対応付ける。
2. 変更波及先とコメント取り込み漏れを探す。
3. 既存testが要求を本当にcoverするか確認する。
4. delivery manifestがある場合は、最終HEAD、risk別reviewer数、Gate、Evidence type、未確認項目がpublic contractと一致するか確認する。
5. 修正が依頼範囲内で許可済みなら、メイン作業branchで反映する。reviewだけの依頼では変更しない。
6. 修正後に必要なlint、test、build、manual checkを再実行する。
7. PR本文の対応内容と検証結果が古ければ、許可されたGitHub writeとして更新してread-backする。
8. findingがない場合も、確認した観点と証拠を明記する。

Projectのcurrent `Status`、`Priority`、`Goal Mode`等をIssue / PR本文の古い値から推測しない。
PR本文のmerge前classificationには投影元と`observed_at`があり、現在値の正本を名乗って
いないことを確認する。

独立reviewを使う場合は読み取り中心に限定し、同じファイルを並列編集させない。利用環境がagent delegationを許可していない場合は、単一agentで観点を分けて実行する。

## 結果形式

```markdown
## AIセルフレビュー

- 対象差分:
- 観点:
- Findings:
- 修正:
- 再検証:
- コメント取り込み:
- 未確認:
- 人間レビューで見てほしい点:
```

## 完了条件

- actionable findingが解消済み、または残す理由とownerが明確
- 修正後の検証結果がある
- PR本文と実際の状態が一致する
- 人間判断が必要な公開、権限、仕様、残リスクが短く整理されている

mergeは行わない。mergeabilityやgreen checksだけで人間review不要と判断しない。

## 終端報告

セルフレビューが完了または停止したときは、findingsと再検証結果を先に示し、その後に固定見出し
`## あなたにお願いしたいアクション`を必ず置く。

- 必須Actionには`対象`、`操作`、`理由`、`再開条件`を含める。
- `任意の提案`は必須Actionから分離する。
- 操作がなければ`ありません。今回の処理は完了です。`または
  `ありません。外部状態が変わるまで待機します。`と明記する。
- 現在のsource stateをlive read-backし、standing authorizationとOperation Requestが
  一致するroutine writeを新しい承認依頼へ戻さない。
- merge、公開、権限、仕様判断など、未承認のHuman Gateだけを必須Actionにする。
