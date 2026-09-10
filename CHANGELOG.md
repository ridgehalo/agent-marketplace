# Changelog

このプロジェクトの主な変更を記録します。

## [Unreleased]

- ADB接続のfail-closed判定と変更前Human Gateを共有し、`android-app-debugging`と`android-device-operations`を分離した`android-device-control` pluginを追加
- Marketplace、bootstrap、doctor、validator、CIを複数plugin対応へ拡張
- 対話中の開発に簡易Issue / PR形式と、必要な場合だけ人間アクションを示すガイドを追加
- 機械的なterminalReportと通常の会話表示の適用範囲を分離。既存contract versionとpinは変更しない

## [0.5.0] - 2026-09-01

contract-digest: 34614ac71512dab0816b0f3c0be0b4ece382e56c9a867ae5bd78f0126c512c62

### Added

- 正本、投影元、観測時刻、generated状態を表す公開SSOT projection contract
- Project current state、Issue specification、native Relationships、Git artifactの正本分離
- 二重正本、本文dependency、観測時刻なしsnapshot、current statusのmerge前分類流用を拒否するvalidatorとfixture

### Changed

- canonical Issue / PR templateとdelivery skillsからmutableなProject現在値の複製を除去
- PR本文のProject状態を`observed_at`付きmerge前classification snapshotへ変更

## [0.4.0] - 2026-09-01

contract-digest: 3311d9e2bbe8fae5dcf0165f7536351609d3dde8cb2806eb370fb2e42cbb5985

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
