// 既存のhookを上書きせず、Markdownのpre-pushを有効にする。
import { execFileSync } from "node:child_process";
import {
  existsSync,
  readFileSync,
  writeFileSync,
  mkdirSync,
  chmodSync,
} from "node:fs";
import { dirname, resolve } from "node:path";
const hook = resolve(
  execFileSync("git", ["rev-parse", "--git-path", "hooks/pre-push"], {
    encoding: "utf8",
  }).trim(),
);
const current = existsSync(hook) ? readFileSync(hook, "utf8") : "";
if (existsSync("lefthook.yml")) {
  if (
    current.includes("lefthook") &&
    readFileSync("lefthook.yml", "utf8").includes(
      "node tools/markdownlint/check.mjs",
    )
  ) {
    console.log("既存のLefthookからMarkdown検査を実行します。");
    process.exit(0);
  }
  console.error(
    "Lefthook管理のため単独hookは作成しません。mise run setup を実行してください。",
  );
  process.exit(2);
}
if (existsSync(hook)) {
  if (current.includes("ridgehalo-markdown-pre-push")) process.exit(0);
  console.error(
    "既存のpre-pushを保持しました。node tools/markdownlint/check.mjs を既存hookに追加してください。",
  );
  process.exit(2);
}
mkdirSync(dirname(hook), { recursive: true });
writeFileSync(
  hook,
  '#!/bin/sh\n# ridgehalo-markdown-pre-push\ncd "$(git rev-parse --show-toplevel)" || exit 2\nexec node tools/markdownlint/check.mjs\n',
  { flag: "wx", mode: 0o755 },
);
chmodSync(hook, 0o755);
console.log("Markdown pre-pushを有効にしました。");
