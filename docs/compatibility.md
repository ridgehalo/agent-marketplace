# 互換性とrelease policy

## 対応範囲

| Platform | 最低確認version | 検証方法 | 状態 |
| --- | --- | --- | --- |
| Codex Desktop | plugin marketplace対応build | manifest validator、marketplace表示、plugin導入、新規会話で代表prompt | 実repo作成後に実機確認 |
| Codex CLI | `plugin marketplace add` / `plugin add` 対応version | `codex plugin list` read-back | CLIがある環境で確認 |
| Claude Code | 2.1.149 | `plugin validate`、隔離configへのinstall、`plugin list --json`、`plugin details` | Gate前preflight済み |

public delivery contractはplatform CLIに依存せずPython標準ライブラリで検証・compileする。現在のcontract version `0.2.2`をconsumer profileでpinし、plugin versionとは別に`doctor --profile`で古いcontract pinを拒否する。

現在のcontract digest `caf6ad24dc819d01c61fbd3a7950a2f50dde8969e0e7dec4240e52b32ef4130a`は、manifest、schema、template、validator / compilerの内容から決定する。consumer profileはこのdigestをpinし、変更時にdigest、generated docs、CHANGELOG、互換性宣言が揃わなければCIを失敗させる。

version依存の高度なClaude marketplace機能は初期versionで使いません。相対plugin source、明示version、local / GitHub marketplaceという基本機能だけを使います。

## Versioning

- pluginとmarketplace entryはSemVerを使う
- root marketplace自体のversionは、catalog契約が変わる場合だけ更新する
- plugin releaseごとに `v<plugin-version>` tagを作る
- public contractは独立したSemVerを持ち、consumer profileが明示的にpinする
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
3. `scripts/contracts.py validate` とgenerated docs checkを実行する
4. Codex / Claude validatorを実行する
5. clean cloneでbootstrapを実行する
6. `doctor` で両targetとconsumer profileをread-backする
7. secret scanと公開境界reviewを行う
8. CHANGELOGを更新する
9. tagを作成する
