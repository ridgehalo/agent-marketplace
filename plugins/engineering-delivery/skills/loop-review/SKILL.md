---
name: loop-review
description: Run focused multi-round review on a high-risk or cross-cutting change until major findings are resolved or a human decision is required. Use when the user asks for extra review depth beyond an ordinary self-review.
---

# Loop Review

通常reviewより精度が必要な差分だけを、同じ観点で再確認する。標準のPR self-reviewを無条件に重くしない。

GitHub上のPRを扱う場合は [GitHub safety contract](../../references/github-safety.md) を読む。

## 向いている変更

- 複数module、skill、docsをまたぐcontract変更
- migration、data loss、security、権限、公開境界
- CI/CD、automation、review policy
- release前の重要なuser journey

単純な小差分や、速さを優先する通常reviewでは使わない。

## Round contract

1. 要求と差分から1〜3個の観点を選ぶ。
2. 各観点について独立にevidenceを集め、重大度付きfindingを出す。
3. 許可された修正だけをメインbranchへ反映する。
4. 影響するlint、test、build、manual checkを再実行する。
5. 同じ観点で再reviewし、findingが解消したか確認する。

roundごとに観点を増やさない。新しい重大リスクが見つかった場合だけ追加し、なぜ必要かを記録する。3 roundを目安とし、回数ではなく停止条件を優先する。

## 停止条件

- P0/P1 findingがなく、P2以下に対応方針がある
- 同じfindingが証拠なしに繰り返されている
- 仕様、公開、権限など人間判断が必要
- 必要なenvironmentやexternal evidenceがなく、追加roundで精度が上がらない

## 出力

```markdown
## Loop Review

- 対象:
- 観点:
- Round 1 findings / fixes / verification:
- Round 2 findings / fixes / verification:
- Round 3 findings / fixes / verification:
- 残リスク:
- 停止理由:
- 人間判断:
```

独立agentを使う場合は、利用環境が明示的に許可するときだけ読み取り中心のreviewを委譲する。編集、merge、外部writeはメイン作業者が権限を確認して行う。
