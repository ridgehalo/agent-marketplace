---
name: dev-experience-evidence
description: Capture reproducible screenshots, video or traces, logs, and user-flow evidence before asking someone to test a development UI. Use for UI, form, dashboard, or interaction changes where visual behavior matters.
---

# Dev Experience Evidence

ユーザーにDev環境を触ってもらう前に、主要導線を一度実行し、確認済み範囲と未確認範囲をIssueまたはPRから追跡できるようにする。ユーザー確認の代替ではない。

GitHubへ証跡を記録する場合は [GitHub safety contract](../../references/github-safety.md) を読む。

## 適用

次のいずれかで使う。

- UI、form、graph、dashboard、responsive layout、interactionを含む
- ダミーデータやfixtureでE2E journeyを再現できる
- screenshot、video、traceがreview判断に必要
- ユーザーへ「実際に触って確認してほしい」と依頼する直前

pure function、CLI、docsだけの変更には通常使わない。

## 証跡計画

対象URL、branch、commit、viewport、scenario、期待結果を確定する。実データではなくfixture、dummy、匿名化データを使う。既存のE2E frameworkがあれば優先し、UIを起動する前にtest dataと保存先を確認する。

## 実行

1. Dev serverを再現可能なcommandで起動する。
2. browser automationまたは同等手段で主要journeyを操作する。
3. 重要stateのscreenshotを取得する。
4. 動的変化や失敗調査に必要ならvideoまたはtraceを取得する。
5. console error、network error、test outputを確認する。
6. artifactが開け、対象commitと対応することを読み戻す。
7. 現在の依頼がIssueまたはPRへの書き込みを明示的に許可している場合だけ、scenario、artifact、結果、未確認事項を記録し、作成先から読み戻す。許可されていない場合はlocal artifactとコメント草案までで止め、投稿内容と対象を示して承認を得る。

browser automationを使えない場合は、static render、API response、local image、manual logなどの代替証拠と不足範囲を明記する。狭い代替証拠でE2E成功を主張しない。standaloneの証拠取得依頼はGitHub writeの承認を含まない。

## 保存禁止

- 氏名、住所、口座、card、health、careerなどの個人情報
- 実家計・本番customer data
- secret、token、cookie、authorization header、`.env`
- ログイン済み外部サービスの個人画面
- raw transcriptや目的外の長大なHTML

映り込みを検出したらartifactを公開せず、削除または安全なデータで再取得する。外部storageへのuploadは別の明示承認を必要とする。

## 記録形式

```markdown
## Dev体験前証跡

- 対象URL / commit:
- 実行日時:
- 使用データ:
- viewport:
- 操作scenario:
- evidence:
  - screenshot:
  - video / trace:
  - logs / test output:
- 確認できたこと:
- 確認できないこと:
- 個人情報・秘密情報の確認:
- ユーザーに触ってほしい観点:
```

## 停止条件

- 安全なtest dataで再現できない
- secretや個人情報の映り込みを除去できない
- serverまたはjourneyを起動できない
- artifactと対象commitの対応を証明できない

停止時は未取得理由、実行済み確認、解除条件を残す。
