// 隠しディレクトリの記法違反と、既存hookの保護を確認する。
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  mkdtempSync,
  mkdirSync,
  copyFileSync,
  symlinkSync,
  writeFileSync,
  readFileSync,
  rmSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

test("全追跡Markdown・pre-pushの失敗と復旧・既存hookの保護", () => {
  const root = mkdtempSync(join(tmpdir(), "markdown-quality-"));
  const run = (cmd, args) =>
    spawnSync(cmd, args, { cwd: root, encoding: "utf8" });
  try {
    assert.equal(run("git", ["init", "--quiet"]).status, 0);
    const dir = join(root, "tools/markdownlint");
    mkdirSync(dir, { recursive: true });
    for (const name of ["check.mjs", "install-hook.mjs"])
      copyFileSync(
        fileURLToPath(new URL(name, import.meta.url)),
        join(dir, name),
      );
    symlinkSync(
      fileURLToPath(new URL("node_modules", import.meta.url)),
      join(dir, "node_modules"),
      "dir",
    );
    mkdirSync(join(root, ".hidden"));
    const file = join(root, ".hidden/test.md");
    writeFileSync(file, "# Example\n\n** spaced **\n");
    assert.equal(run("git", ["add", ".hidden/test.md"]).status, 0);
    assert.equal(
      run(process.execPath, ["tools/markdownlint/install-hook.mjs"]).status,
      0,
    );
    const hook = join(root, ".git/hooks/pre-push");
    const failed = run(hook, []);
    assert.notEqual(failed.status, 0);
    assert.match(failed.stderr, /MD037/);
    writeFileSync(file, "# Example\n\nA **valid** example.\n");
    assert.equal(run(hook, []).status, 0);
    writeFileSync(hook, "#!/bin/sh\nexit 7\n");
    assert.equal(
      run(process.execPath, ["tools/markdownlint/install-hook.mjs"]).status,
      2,
    );
    assert.equal(readFileSync(hook, "utf8"), "#!/bin/sh\nexit 7\n");
    rmSync(hook);
    writeFileSync(
      join(root, "lefthook.yml"),
      "pre-push:\n  commands:\n    markdown-all:\n      run: node tools/markdownlint/check.mjs\n",
    );
    assert.equal(
      run(process.execPath, ["tools/markdownlint/install-hook.mjs"]).status,
      2,
    );
    assert.throws(() => readFileSync(hook));
    writeFileSync(hook, "#!/bin/sh\n# lefthook\nexit 0\n");
    assert.equal(
      run(process.execPath, ["tools/markdownlint/install-hook.mjs"]).status,
      0,
    );
    rmSync(join(dir, "node_modules"));
    assert.equal(
      run(process.execPath, ["tools/markdownlint/check.mjs"]).status,
      2,
    );
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
