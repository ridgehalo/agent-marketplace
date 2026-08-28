# GitHub safety contract

このreferenceはGitHubを使うskillだけが読む。利用リポジトリにより具体的な指示がある場合は、そちらをadapterとして優先する。

## 状態確認

最初に対象を確定する。

```bash
git status --short --branch
git remote -v
gh auth status
gh repo view OWNER/REPO --json nameWithOwner,url,defaultBranchRef
```

- 未commit変更はユーザーのものとして保護する
- 対象repo、Issue、base branchを推測しない
- `gh` 認証が失敗したらGitHub writeを止める
- token、header、credentialの値を出力・保存しない

## Issueとrelationship

```bash
gh issue view NUMBER --repo OWNER/REPO \
  --json number,title,body,state,url,labels,assignees
```

GitHubが提供するblocked-by、parent/sub-issue、closing PRなどの構造化relationshipを、本文中の手書きリンクより優先する。標準commandで読めない場合はGraphQLを使う。relationshipを確認できない場合は、その事実を未確認として残す。

## Write境界

- 調査・説明・review依頼はrepo writeやGitHub writeを許可しない
- IssueをPRまで処理する依頼は、対象repoのbranch、commit、push、PR作成までを許可する
- merge、手動close、repository visibility、権限、secret、releaseは別の明示依頼を必要とする
- bulk writeはdry-runと対象一覧を先に示す
- write後は同じ対象をAPIまたはCLIで読み戻す

## BranchとPR

- protected/default branchへ直接commitしない
- 最新baseから専用branchまたは隔離worktreeを作る
- unrelatedな差分をcommitへ含めない
- PRがIssueを完了する場合は、本文に完全なIssue URLを使う

```text
Closes https://github.com/OWNER/REPO/issues/NUMBER
```

PR作成後は少なくとも次を読み戻す。

```bash
gh pr view NUMBER --repo OWNER/REPO \
  --json number,title,state,isDraft,url,body,mergeable,reviewDecision,statusCheckRollup
```

CLI成功だけで完了とせず、作成先、branch、PR本文、check状態を区別して報告する。Project status、priority、labelなどは共通契約で固定せず、利用repoの指示がある場合だけ扱う。

## 失敗時

- auth、network、permission、CI、conflictをコード不良と混同しない
- local branchとcommitを保持し、失敗した操作と再開条件を残す
- 未実行のcheck、manual validation、deployを成功扱いしない
