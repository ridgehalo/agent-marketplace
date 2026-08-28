# Security Policy

## 対象

このmarketplaceはagent skillを配布します。pluginは利用者権限で動作し得る高信頼コンポーネントとして扱ってください。

初期 `engineering-delivery` pluginはskills-onlyであり、hooks、MCP servers、apps、認証情報、background processを含みません。

## 報告

公開Issueへsecret、認証情報、未公開脆弱性の再現情報を投稿しないでください。GitHub repositoryのPrivate vulnerability reportingが有効な場合はそれを使います。有効でない場合は、詳細を公開せずmaintainerへ報告手段を問い合わせてください。

## 配布禁止情報

- API key、token、password、cookie、session state、private key
- 個人情報、家計・健康・Careerデータ、raw transcript
- ローカル絶対パス、private repository URL、内部Project ID
- 認証済みbrowser profileやfixture

## 権限変更

hooks、MCP、外部認証、外部write、unattended executionを追加する変更は通常のskill追加と分け、次を明記します。

- 必要権限と対象
- 起動条件と停止条件
- 書き込み前の確認
- read-back方法
- rollback

## 利用者向け確認

- 信頼できるtagまたはcommitを固定する
- install前にmanifestとskillを読む
- `scripts/validate.py` と `scripts/doctor.py` を実行する
- 外部commandを追加したpluginは、そのcommandの出所とversionも確認する
