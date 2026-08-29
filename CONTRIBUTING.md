# Contributing

## 変更方針

- 共通化するのは、複数リポジトリで再利用できる手順と検証契約だけです
- 個人情報、組織固有URL、認証、価値判断はconsumer側adapterへ残します
- skill本文は両platformで共有し、platform別コピーを作りません
- hooks、MCP、外部writeは独立した権限reviewなしに追加しません

## Pull Request

PRには次を含めてください。

- 背景と利用例
- 変更した契約
- 検証結果
- 権限・公開境界
- compatibilityとrollback

変更後に次を実行します。

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
claude plugin validate .
claude plugin validate plugins/engineering-delivery
```

Codex pluginの変更はCodex Desktopでも新規会話から代表promptを確認してください。
