# Changelog

このプロジェクトの主な変更を記録します。

## [Unreleased]

## [0.4.0] - 2026-09-01

contract-digest: 9c3e7591788d69801e383c312f01f49744c74d7d59fea21935de42a740249988

### Added

- 完了・停止時の人間Actionを表す公開terminal reporting contractとJSON schema
- 固定見出し、必須Action field、操作なし、standing authorizationのfixtureとvalidator
- `issue-to-pr`と`pr-self-review`の共通終端報告形式

## [0.3.3] - 2026-08-31

contract-digest: caf6ad24dc819d01c61fbd3a7950a2f50dde8969e0e7dec4240e52b32ef4130a

### Fixed

- canonical Issue templateにTest Intentのtopology、failure case、安全なtest infrastructureを統合

## [0.3.2] - 2026-08-31

contract-digest: 078fdbcd7cf70dfcfe727319f54459f3719db85739316a2b2ed3bfdacfb81546

### Fixed

- canonical Issue templateへ既存mobile consumerが要求するRelease Human Gates欄を追加
- canonical PR templateのIssue URLをMarkdown lint互換の表記へ修正

## [0.3.1] - 2026-08-31

contract-digest: 6fe80da20eae19e423f371fa55b346e269c52a44c9509cbacb92ab88de24ebee

### Fixed

- canonical PR templateをconsumerのPrettierとbyte単位で安定する形式へ正規化

## [0.3.0] - 2026-08-31

contract-digest: 0e25c936b62c23a814b941905c2d905b0d761932347e7c443035d86b8a39d56a

### Added

- canonical Issue / PR template with the same numbered eight-section reading order
- machine-readable Appendix A-M ownership and adoption decisions
- repository copy and template structure drift validation

## [0.2.0] - 2026-08-29

contract-digest: 31151b5aa90239be684e059e816835fb2e5e7abcec9de91c8239db9e292b4490

### Added

- versioned public contract manifest and JSON schemas
- Issue、Plan、Test Intent、Reviewer、PR Evidence templates
- isolated personal / product consumer profiles and context lock compiler
- valid / invalid fixtures for risk、Evidence、projection、promotion boundaries
- generated contract documentation and consumer profile read-back

## [0.1.0] - 2026-08-28

### Added

- Codex-first marketplace manifests
- Claude Code marketplace adapter
- `engineering-delivery` plugin
- selective bootstrap and read-back doctor
- manifest、skill構造、公開境界の検証
