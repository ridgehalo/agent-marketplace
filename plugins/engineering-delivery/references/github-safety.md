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

## コミットへのリンクを書く

Issue・PR本文、レビュー返信、コミットメッセージなどの文章中でコミットハッシュを示す場合、
括弧の有無にかかわらず、前後に必ず半角スペースを入れる。行頭・行末は改行を区切りとしてよい。
日本語・句読点・括弧・その他の記号にハッシュを直接つなげない。
自動リンクを期待するハッシュはインラインコードで囲まない。

```text
良い例: 対応しました（ abc1234 ）。
良い例: コミット abc1234 で修正しました。
良い例: 修正: abc1234 / def5678
避ける例: 対応しました（abc1234）。
避ける例: コミットabc1234で修正しました。
避ける例: 修正:abc1234/def5678
避ける例: 対応しました（ `abc1234` ）。
```

この区切りは明示的なMarkdownリンクの前後にも適用する。
自動リンクは表示する場所やリポジトリの文脈に依存する。別リポジトリのコミットを参照するときや、
リンク先を確実に指定したいときは、確認したコミットURLを使ったMarkdownリンクにする。
次は書式例であり、実際の返信では存在を確認したハッシュとURLへ置き換える。

```markdown
対応しました（ [abc1234](https://github.com/OWNER/REPO/commit/FULL_SHA) ）。
```

書き込み後は本文だけでなく、可能ならGitHubの表示でもリンク先を確認する。APIの読み戻しだけなら、
本文の保存を確認したことと画面上のリンク表示が未確認であることを区別する。

## 失敗時

- auth、network、permission、CI、conflictをコード不良と混同しない
- local branchとcommitを保持し、失敗した操作と再開条件を残す
- 未実行のcheck、manual validation、deployを成功扱いしない
