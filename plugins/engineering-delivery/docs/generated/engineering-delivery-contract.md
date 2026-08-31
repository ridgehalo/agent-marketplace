# Engineering Delivery Contract

この文書は `contracts/manifest.json` から生成する。手動編集しない。

## Version

`0.2.0`

Contract digest: `0e25c936b62c23a814b941905c2d905b0d761932347e7c443035d86b8a39d56a`

## Gates

`plan` → `build` → `verify` → `release`

`release`はmerge、deploy、公開、課金、権限変更のHuman Gateを含み、
`plan / build / verify`の成功から自動承認しない。

## Risk routing

| Risk | Read-only reviewers | Human decision required |
| --- | ---: | --- |
| low | 0 | no |
| medium | 1 | no |
| high | 2 | no |
| critical | 2 | yes |

## Goal Modes

| Mode | Selection | Standing authorization |
| --- | --- | --- |
| `manual` | interactive-only | - |
| `auto` | scheduled-eligible | repository-write, issue-update, project-update, pull-request |
| `hold` | excluded | - |

`auto`の除外対象: merge, deployment, publication, payment, permission-change

Goal Modeが未設定の場合: `excluded`

## Reviewer output

`severity` / `condition` / `impact` / `evidence` / `minimalFix`

1 reviewerには1 viewpointと必要最小限のcontextだけを渡し、直接編集させない。

## Safe test infrastructure

- `unique-namespace`
- `factory`
- `cleanup`
- `production-guard`
- `personal-data-guard`
- `external-write-command-separation`

## Evidence types

- `local-test`
- `ci`
- `build`
- `journey`
- `deployment`
- `external-read-back`

## Schemas

| Contract | Path |
| --- | --- |
| `externalWorkItemRef` | `contracts/schemas/external-work-item-ref.schema.json` |
| `promotionBundle` | `contracts/schemas/promotion-bundle.schema.json` |
| `contextAssemblyManifest` | `contracts/schemas/context-assembly-manifest.schema.json` |
| `deliveryEvent` | `contracts/schemas/delivery-event.schema.json` |
| `deliveryManifest` | `contracts/schemas/delivery-manifest.schema.json` |
| `consumerProfile` | `contracts/schemas/consumer-profile.schema.json` |

## Templates

| Template | Path |
| --- | --- |
| `issue` | `templates/issue-contract.md` |
| `plan` | `templates/plan-contract.md` |
| `testIntent` | `templates/test-intent.md` |
| `reviewer` | `templates/reviewer-contract.md` |
| `prEvidence` | `templates/pr-evidence.md` |

## Tools

| Tool | Path |
| --- | --- |
| `contracts` | `scripts/contracts.py` |

## Trust domains

- personal consumerとproduct consumerは同じpublic contract versionをpinする
- state storeは各consumerが所有し、共有databaseを要求しない
- external projectionはread-onlyで、source revisionと観測時刻を必須にする
- promotionは許可fieldとredaction classをHuman Gateの記録へ固定する

## Compatibility

- minimum contract version: `0.1.0`
- breaking change: `major`
- rollback: `pin-previous-version`
- skill昇格は2 consumer以上または
  `repeated-use`のEvidence後に行う
- Evidenceが不足する場合は`template`として保管する
