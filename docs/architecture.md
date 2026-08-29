# アーキテクチャ

## 推奨構成

```mermaid
flowchart TD
    M["ridgehalo/agent-marketplace\n公開配布の正本"]
    P["engineering-delivery\n共通skills実体"]
    K["public contract\nschema / template / validator"]
    C["Codex manifest\n主系"]
    H["Claude Code manifest\n薄いadapter"]
    U["個人が所有するリポジトリ\npersonal consumer"]
    R["RidgeHalo products\nproduct consumer"]

    M --> P
    P --> K
    P --> C
    P --> H
    C --> U
    C --> R
    H --> U
    H --> R
    K --> U
    K --> R
    U -. "個人情報・個人固有policyは残す" .-> U
    R -. "product固有policyは残す" .-> R
```

## 設計判断

### marketplaceはRidgeHaloに置く

配布物の所有者をRidgeHaloにし、個人が所有するリポジトリを一利用者にします。これにより、個人固有の文脈と第三者がcloneできる公開契約を分離できます。

### Codex-first、skills single-source

`.codex-plugin/plugin.json` と `.agents/plugins/marketplace.json` を主系の配布契約にします。Claude Codeは `.claude-plugin/` manifestから同じ `plugins/<name>/skills/` を配布します。skill本文をplatform別に二重管理しません。

### platform固有capabilityは分離する

hooks、MCP、subagents、認証、permission設定はskill本文へ埋め込まず、必要になった時点でplatform adapterとして設計します。追加前には権限、停止条件、rollbackをHuman Gateで確認します。

### contractとconsumer stateを分離する

公開coreはschema、template、validator、compilerだけを提供します。personal / product consumerは同じcontract versionをpinしますが、profile、Project field、private state storeを共有しません。外部stateはsource revisionと観測時刻を持つread-only projectionとして解決します。

### 利用側policyを優先する

共通skillはbranch、検証、read-backなどの不変条件だけを持ちます。Project URL、status名、priority、commit言語、required checksなどは利用リポジトリの指示へ残します。

## 信頼境界

| 境界 | 規則 |
| --- | --- |
| marketplace登録 | catalogが見えるだけ。全pluginを暗黙に導入しない |
| plugin導入 | skills-only。外部権限を付与しない |
| repo write | ユーザー依頼と対象repo policyの範囲に限定する |
| external write | 実行前に対象と変更内容を確定し、実行後にread-backする |
| public release | secret scan、manifest検証、clean clone検証後だけtagを作る |
| cross-domain projection | source revision / observed time必須。raw private stateを複製しない |
| promotion | allowed fields / redaction class / approval recordを固定する |

## 失敗時の原則

- `all` targetは全CLIのpreflight後に実行する。実行途中のfailureでは既完了状態を自動削除せず、read-backして安全に再実行する
- install成功と認識成功を分ける
- 認識状態を読めないtargetは `unverified` とする
- 利用側の既存skillはcutover承認まで残す
- publicからprivateへ戻しても既存cloneは回収できない前提で公開前検査を行う
