# RidgeHalo Agent Marketplace

Codexを主系として、複数リポジトリで再利用できるagent plugin / skillを配布するmarketplaceです。Claude Codeには同じ `skills/` 実体を読み込む薄いmanifestを提供します。

## 所有境界

| 場所 | 正本 |
| --- | --- |
| このリポジトリ | 公開可能な共通plugin、skill、bootstrap、doctor、互換性契約 |
| 利用リポジトリ | 導入pluginとversion、組織・プロジェクト固有ポリシー |
| 個人が所有するリポジトリ | 個人情報、価値判断、外部サービス認証、非公開workflow |

公開pluginは自己完結し、利用リポジトリ外のファイル、絶対パス、secretを参照しません。リポジトリ固有の `AGENTS.md`、`CLAUDE.md`、contribution policyがある場合は、共通skillより具体的なadapterとして優先します。

## Plugins

### `engineering-delivery` 0.4.0

- public contract: 4 Gate、risk routing、Evidence、cross-domain reference
- templates: Issue、Plan、Test Intent、Reviewer、PR Evidence
- canonical Issue / PR template: 全consumerで同じ番号付き8セクションとPR Evidenceを使用
- `issue-to-pr`: 既存Issueを専用branch、実装、検証、commit、PRまで進める
- `pr-self-review`: PR差分を人間レビュー前に横断確認する
- `loop-review`: 高リスク差分を同じ観点で複数ラウンド確認する
- `dev-experience-evidence`: UI確認前に再現可能な画面・操作証跡を残す
- terminal reporting: 完了・停止時の人間Actionを固定見出しと機械検査可能なfieldで返す

初期versionはskills-onlyです。hooks、MCP servers、apps、外部認証、自動外部書き込みを含みません。

## 導入

まず、このリポジトリをcloneし、固定したtagまたはcommitへcheckoutします。

```bash
git clone https://github.com/ridgehalo/agent-marketplace.git
cd agent-marketplace
git checkout <approved-version-or-commit>
```

実行内容を確認します。

```bash
python3 scripts/bootstrap.py install \
  --target all \
  --plugin engineering-delivery \
  --dry-run
```

導入します。`all` は全targetのCLI preflightに成功してから書き込みを始めるため、片方のCLIがない環境では部分導入しません。CLI実行途中のnetwork・permission failureでは、完了済みのmarketplace登録を破壊的にrollbackせず停止し、`doctor` で状態を確認します。

```bash
python3 scripts/bootstrap.py install \
  --target all \
  --plugin engineering-delivery
```

Codex CLIを利用できないCodex Desktop環境では、bootstrapが表示するmarketplace deeplinkを開いてpluginを導入します。Claude CodeはCLIから登録・導入できます。

個別target:

```bash
python3 scripts/bootstrap.py install --target codex --plugin engineering-delivery
python3 scripts/bootstrap.py install --target claude --plugin engineering-delivery
```

## Read-back

APIやCLIの成功だけで完了とせず、導入先から状態を読み戻します。

```bash
python3 scripts/doctor.py --target all --plugin engineering-delivery
python3 scripts/doctor.py --target all --plugin engineering-delivery --json
```

`doctor` はsource manifestの整合、CLI可用性、marketplace登録元、plugin導入、version、enabled状態を別々に報告します。確認できない項目や、登録元が現在のsourceと異なる状態を成功扱いしません。

consumer profileのcontract pinとContext Lockも読み戻せます。

```bash
python3 scripts/doctor.py \
  --target codex \
  --profile plugins/engineering-delivery/profiles/personal-consumer.json \
  --json
```

## Public delivery contract

`plugins/engineering-delivery/contracts/manifest.json` が、4 Gate、risk routing、Evidence type、schema、template、consumer profileの正本です。
生成された参照文書は
[`plugins/engineering-delivery/docs/generated/engineering-delivery-contract.md`](plugins/engineering-delivery/docs/generated/engineering-delivery-contract.md)
です。

```bash
python3 scripts/contracts.py validate
python3 scripts/contracts.py render-docs --check
python3 scripts/contracts.py compile \
  --profile plugins/engineering-delivery/profiles/product-consumer.json
```

plugin単体を配置したclean install先でも、同梱toolをそのまま使えます。

```bash
python3 scripts/contracts.py validate
python3 scripts/contracts.py compile --profile profiles/product-consumer.json
```

- personal / product consumerは同じpublic contractをpinする
- private state storeとProject固有fieldは各consumerが所有する
- 外部参照にはsource revision、観測時刻、stale stateを必須にする
- promotionは許可fieldとredaction classを固定する
- generated docsのdrift、古いcontract pin、invalid fixtureはCIで拒否する
- 必須Actionは対象、操作、理由、再開条件を持ち、操作不要時も明示文を返す

## 更新とversion固定

- releaseはSemVerと `v<version>` tagを使う
- 利用側はtagまたはcommit SHAを固定する
- plugin manifestと両marketplace entryのversionを一致させる
- 更新前に `CHANGELOG.md` と互換性表を確認する
- 更新後にbootstrapを再実行し、`doctor` でread-backする

開発中のCodex cache更新にだけSemVer build metadataのcachebusterを使い、公開release versionには残しません。

## Rollback

1. 利用リポジトリが固定するtag / commitを直前の正常versionへ戻す
2. そのversionのcloneからbootstrapを再実行する
3. `doctor` で導入versionを読み戻す
4. 既存のローカルskillは切替検証が終わるまで削除しない

公開済みcontentはforkやcloneから回収できません。公開前のsecret scanとreviewをrollbackの代替にしないことが重要です。

## 権限と非対応機能

- plugin導入はskillを利用可能にするだけで、GitHubその他の権限を付与しない
- GitHub書き込みは利用環境で既に認証された `gh` と、ユーザーが依頼した操作範囲だけを使う
- merge、Issue close、repository visibility変更、hooks、MCP、外部認証は個別承認なしに実行しない
- secret、token、cookie、認証済みsession、個人情報を配布物へ含めない

詳細は [architecture](docs/architecture.md)、[compatibility](docs/compatibility.md)、[security policy](SECURITY.md) を参照してください。

## 検証

```bash
python3 scripts/validate.py
python3 scripts/contracts.py validate
python3 scripts/contracts.py render-docs --check
python3 -m unittest discover -s tests -v
claude plugin validate .
claude plugin validate plugins/engineering-delivery
```

Codexは `.codex-plugin/plugin.json` と `.agents/plugins/marketplace.json` をvalidatorで検査し、実際のCodex Desktopで新しい会話から代表promptを確認します。

repository validatorは拡張子に依存せず、release content内の全non-binary fileを走査してsecret形式、private key、credential付きheader、ローカル絶対パスを検査します。

## License

Apache-2.0。詳細は `LICENSE` を参照してください。
