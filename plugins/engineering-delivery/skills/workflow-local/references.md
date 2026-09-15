# 実行記録

記録は利用側の指定する非公開artifact先へ置く。token、secret、認証済みURL、原文の環境変数一覧を含めない。公開PRには必要な要約だけを転記する。

## 固定した参照

- repository / source SHA / 観測時刻
- workflowのパスとhash、選択job・matrix
- Actionの取得元と固定SHA、参照スクリプト・設定・lockfile
- ローカルOSとtoolchain実測version
- 依頼された範囲、承認済みscope、未解決の前提

## CIとの対応表

| job / step | CI参照・処理 | 条件・依存 | ローカルの処理と差 | 必要な承認 | 結果・証拠 |
| --- | --- | --- | --- | --- | --- |

全stepを列挙し、未実行の行を消さない。結果はpassed / failed / skipped / not-runのいずれかと理由を残す。source snapshotのmatchedはソース一致だけを意味し、処理のpassedとは別に記録する。

## 最終確認

- 依頼された工程の被覆、未実行の工程と理由
- 成果物hash、配布先とversion、外部読み戻し
- cleanup、起動プロセスの引き渡し、再試行時の重複防止
- CIとの差、同等性を確認できていない点

## スキルの確認シナリオ

発火対象:

- CI上限なので、同じworkflowの検査をローカルで実行して
- この配布workflowを参照して、手元からInternal配布して
- CIの失敗を同じcommitで再現して

対象外:

- 新しい配布基盤を設計して
- テストが失敗しているので無視して公開して
- Googleの管理者権限を付与して

性能確認では、workflowを更新後に再度読むこと、実コマンドをスキルから探さずCIから得ること、既承認scopeの再確認を増やさないことを見る。呼び出し回数だけを減らすために参照や読み戻しを省略しない。
