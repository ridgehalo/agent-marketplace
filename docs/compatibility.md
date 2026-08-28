# 互換性とrelease policy

## 対応範囲

| Platform | 最低確認version | 検証方法 | 状態 |
| --- | --- | --- | --- |
| Codex Desktop | plugin marketplace対応build | manifest validator、marketplace表示、plugin導入、新規会話で代表prompt | 実repo作成後に実機確認 |
| Codex CLI | `plugin marketplace add` / `plugin add` 対応version | `codex plugin list` read-back | CLIがある環境で確認 |
| Claude Code | 2.1.149 | `plugin validate`、隔離configへのinstall、`plugin list --json`、`plugin details` | Gate前preflight済み |

version依存の高度なClaude marketplace機能は初期versionで使いません。相対plugin source、明示version、local / GitHub marketplaceという基本機能だけを使います。

## Versioning

- pluginとmarketplace entryはSemVerを使う
- root marketplace自体のversionは、catalog契約が変わる場合だけ更新する
- plugin releaseごとに `v<plugin-version>` tagを作る
- breaking changeはmajor、後方互換のcapability追加はminor、修正はpatch
- release tagの内容とmanifest versionが一致しない場合はreleaseしない

## Compatibility contract

- 同じplugin versionではskill名と主要な入力・出力契約を維持する
- 新しい外部command、MCP、認証、外部writeを追加する場合はminor以上とし、READMEとSECURITYへ明記する
- 権限拡大または既存Human Gateの削除はbreaking changeとして扱う
- 個人が所有するリポジトリなどの利用側固有policyはplugin versioningの対象外とし、consumer側で固定する

## Release checklist

1. manifestsとmarketplace entryのversionを揃える
2. `python3 scripts/validate.py` とunit testsを実行する
3. Codex / Claude validatorを実行する
4. clean cloneでbootstrapを実行する
5. `doctor` で両targetをread-backする
6. secret scanと公開境界reviewを行う
7. CHANGELOGを更新する
8. tagを作成する
