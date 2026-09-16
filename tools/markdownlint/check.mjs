// 追跡済みMarkdownを列挙し、CIとpre-pushで同じ検査を行う。
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
const root = fileURLToPath(new URL("../../", import.meta.url));
const cli = fileURLToPath(
  new URL(
    "node_modules/markdownlint-cli2/markdownlint-cli2-bin.mjs",
    import.meta.url,
  ),
);
if (!existsSync(cli)) {
  console.error(
    "Markdown検査の依存がありません。npm ci --prefix tools/markdownlint --ignore-scripts を実行してください。",
  );
  process.exit(2);
}
const listed = spawnSync(
  "git",
  ["ls-files", "-z", "--", "*.md", "*.markdown"],
  { cwd: root, encoding: "utf8" },
);
if (listed.status !== 0) process.exit(listed.status || 2);
const files = listed.stdout.split("\0").filter(Boolean);
if (!files.length) {
  console.log("追跡対象のMarkdownはありません。");
  process.exit(0);
}
let status = 0;
for (let i = 0; i < files.length; i += 100) {
  const result = spawnSync(
    process.execPath,
    [cli, "--no-globs", ...files.slice(i, i + 100).map((name) => ":" + name)],
    { cwd: root, stdio: "inherit" },
  );
  if (result.status !== 0) status = result.status || 2;
}
process.exit(status);
