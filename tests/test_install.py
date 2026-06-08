#!/usr/bin/env python3
"""hooks/install.py 的临时目录模拟测试。

用环境变量把 Codex/Copilot/稳定位置都重定向到临时目录，不触碰真实配置。
覆盖：合并不破坏既有、幂等、精确卸载、Copilot 用户内容保留、稳定位置 copy，
以及边界——类型异常结构、损坏 JSON、多个 marker 块、无哨兵防误删。
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

INSTALL_PY = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "install.py"
)
SESSION_START = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hooks", "session-start"
)
MARKER_BEGIN = "<!-- BEGIN spellbook-skills:project-context -->"
MARKER_END = "<!-- END spellbook-skills:project-context -->"


def main():
    tmp = tempfile.mkdtemp()
    env = dict(os.environ)
    env["SPELLBOOK_HOME"] = os.path.join(tmp, "spellbook")
    env["CODEX_HOME"] = os.path.join(tmp, "codex")
    env["COPILOT_HOME"] = os.path.join(tmp, "copilot")
    os.makedirs(env["CODEX_HOME"])
    os.makedirs(env["COPILOT_HOME"])

    codex_file = os.path.join(env["CODEX_HOME"], "hooks.json")
    copilot_file = os.path.join(env["COPILOT_HOME"], "copilot-instructions.md")

    def run(action):
        subprocess.run([sys.executable, INSTALL_PY, action], env=env,
                       capture_output=True, text=True, check=True)

    def run_fails(action):
        return subprocess.run([sys.executable, INSTALL_PY, action], env=env,
                              capture_output=True, text=True).returncode != 0

    def reset(*, codex=None, copilot=None):
        for key in ("CODEX_HOME", "COPILOT_HOME"):
            shutil.rmtree(env[key])
            os.makedirs(env[key])
        if os.path.isdir(env["SPELLBOOK_HOME"]):
            shutil.rmtree(env["SPELLBOOK_HOME"])
        if codex is not None:
            with open(codex_file, "w") as handle:
                handle.write(codex)
        if copilot is not None:
            with open(copilot_file, "w") as handle:
                handle.write(copilot)

    def codex_ss():
        return json.load(open(codex_file))["hooks"]["SessionStart"]

    def has(entries, needle):
        return any(needle in h.get("command", "") for e in entries for h in e["hooks"])

    def commands(entries):
        return [h.get("command", "") for e in entries for h in e["hooks"]]

    checks = []

    def check(cond, msg):
        checks.append((bool(cond), msg))
        print(("  ✅ " if cond else "  ❌ ") + msg)

    # 预置：Codex 既有 codeisland + Stop；Copilot 既有用户规则
    with open(codex_file, "w") as handle:
        json.dump({"hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "timeout": 5,
                "command": "/Users/code4j/.codeisland/codeisland-bridge --source codex"}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "echo stop"}]}],
        }}, handle, indent=2)
    with open(copilot_file, "w") as handle:
        handle.write("# 我的全局规则\n始终用中文。\n")

    print("=== install（已有 codeisland + 用户规则）===")
    run("install")
    ss = codex_ss()
    full = json.load(open(codex_file))
    check(has(ss, "codeisland"), "Codex 保留 codeisland")
    check(has(ss, "session-start"), "Codex 已加我们的 hook")
    our_cmd = next(cmd for cmd in commands(ss) if "session-start" in cmd)
    check(sys.executable in our_cmd, "Codex hook 使用安装时实际可用的 Python 解释器")
    check("Stop" in full["hooks"], "Codex 保留 Stop 事件")
    check(len(ss) == 2, f"Codex SessionStart 共 2 条（实际 {len(ss)}）")
    ct = open(copilot_file).read()
    check("我的全局规则" in ct, "Copilot 保留用户内容")
    check("BEGIN spellbook-skills" in ct, "Copilot 已加 marker 块")
    check("项目上下文目录" in ct, "Copilot 规则内容已注入")
    hooks_dir = os.path.join(env["SPELLBOOK_HOME"], "hooks")
    check(os.path.isfile(os.path.join(hooks_dir, "session-start")), "稳定位置 copy 了 session-start")
    check(os.path.isfile(os.path.join(hooks_dir, "project-context.md")), "稳定位置 copy 了 project-context.md")
    check(os.access(os.path.join(hooks_dir, "session-start"), os.X_OK), "稳定位置脚本可执行")

    print("=== install 再次（幂等）===")
    run("install")
    ss = codex_ss()
    ours = [e for e in ss if has([e], "session-start")]
    check(len(ours) == 1, f"幂等：我们的 hook 仅 1 条（实际 {len(ours)}）")
    check(len(ss) == 2, f"幂等：SessionStart 仍 2 条（实际 {len(ss)}）")
    cnt = open(copilot_file).read().count("BEGIN spellbook-skills")
    check(cnt == 1, f"幂等：Copilot marker 仅 1 处（实际 {cnt}）")

    print("=== uninstall ===")
    run("uninstall")
    ss = codex_ss()
    full = json.load(open(codex_file))
    check(has(ss, "codeisland"), "卸载后 Codex codeisland 保留")
    check(not has(ss, "session-start"), "卸载后 Codex 我们的已精确移除")
    check(len(ss) == 1, f"卸载后 Codex 只剩 1 条 codeisland（实际 {len(ss)}）")
    check("Stop" in full["hooks"], "卸载后 Codex Stop 保留")
    ct = open(copilot_file).read()
    check("我的全局规则" in ct, "卸载后 Copilot 用户内容保留")
    check("spellbook-skills" not in ct, "卸载后 Copilot marker 块已移除")
    check(not os.path.isdir(env["SPELLBOOK_HOME"]), "卸载后稳定位置已删除")

    print("=== 边界：Copilot 纯我们的文件，卸载应删文件 ===")
    reset()
    run("install")
    run("uninstall")
    check(not os.path.isfile(copilot_file), "纯我们的 Copilot 文件卸载后删除")

    print("=== 边界：全新环境（无既有配置）===")
    reset()
    run("install")
    ss = codex_ss()
    check(len(ss) == 1 and has(ss, "session-start"), "全新环境 install 正常")
    run("uninstall")
    residual = json.load(open(codex_file)).get("hooks", {}).get("SessionStart")
    check(residual in (None, []), "全新环境 uninstall 后无残留")

    print("=== 边界：SessionStart 类型异常应被拒绝、不破坏文件、无半成品 ===")
    reset(codex='{"hooks": {"SessionStart": {}}}')
    check(run_fails("install"), "类型异常：install 非 0 退出")
    check(open(codex_file).read() == '{"hooks": {"SessionStart": {}}}', "类型异常：原文件未被破坏")
    check(not os.path.isdir(env["SPELLBOOK_HOME"]), "类型异常：预检拦截，未 copy payload")

    print("=== 边界：损坏 JSON 应被拒绝、不修改 ===")
    reset(codex="{ not json ")
    check(run_fails("install"), "损坏 JSON：install 非 0 退出")
    check(open(codex_file).read() == "{ not json ", "损坏 JSON：原文件未被修改")

    print("=== 边界：Copilot 多个 marker 块应全部移除 ===")
    reset(copilot=f"{MARKER_BEGIN}\n旧块1\n{MARKER_END}\n\n用户内容\n\n{MARKER_BEGIN}\n旧块2\n{MARKER_END}\n")
    run("install")
    ct = open(copilot_file).read()
    check(ct.count("BEGIN spellbook-skills") == 1, f"多块：install 后仅 1 个 marker（实际 {ct.count('BEGIN spellbook-skills')}）")
    check("用户内容" in ct, "多块：用户内容保留")
    run("uninstall")
    ct = open(copilot_file).read() if os.path.isfile(copilot_file) else ""
    check("spellbook-skills" not in ct, "多块：uninstall 后无残留 marker")
    check("用户内容" in ct, "多块：uninstall 后用户内容保留")

    print("=== 边界：稳定目录无哨兵时拒绝删除（防误删用户目录）===")
    reset()
    fake_hooks = os.path.join(env["SPELLBOOK_HOME"], "hooks")
    os.makedirs(fake_hooks)
    important = os.path.join(fake_hooks, "important-user-file.txt")
    with open(important, "w") as handle:
        handle.write("不该被删")
    run("uninstall")
    check(os.path.isfile(important), "无哨兵：remove_payload 拒绝删除，用户文件保留")

    print("=== 边界：Copilot 残缺 marker 应被拒绝（install/uninstall 都中止、不修改）===")
    broken = f"用户内容\n\n{MARKER_BEGIN}\n残缺块缺少结束标记\n"
    reset(copilot=broken)
    check(run_fails("install"), "残缺 marker：install 非 0 退出")
    check(open(copilot_file).read() == broken, "残缺 marker：install 未修改文件")
    check(not os.path.isdir(env["SPELLBOOK_HOME"]), "残缺 marker：未 copy payload（无半成品）")
    check(run_fails("uninstall"), "残缺 marker：uninstall 非 0 退出")
    check(open(copilot_file).read() == broken, "残缺 marker：uninstall 未修改文件")

    print("=== 边界：status 对残缺 marker 显示需修复、不误报已安装 ===")
    status_run = subprocess.run([sys.executable, INSTALL_PY, "status"], env=env,
                                capture_output=True, text=True)
    check(status_run.returncode == 0, "残缺 marker：status 容错不崩溃")
    copilot_line = next((ln for ln in status_run.stdout.splitlines() if "Copilot" in ln), "")
    check("残缺" in copilot_line, "残缺 marker：status 显示需修复")
    check("已安装" not in copilot_line, "残缺 marker：status 不误报已安装")

    print("=== 边界：session-start 在非 UTF-8 stdout 环境下仍输出 UTF-8 ===")
    utf8_env = dict(os.environ)
    utf8_env["PYTHONIOENCODING"] = "cp936"
    hook_run = subprocess.run([sys.executable, SESSION_START], env=utf8_env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    check(hook_run.returncode == 0, "session-start：非 UTF-8 环境运行成功")
    try:
        hook_run.stdout.decode("utf-8")
        utf8_ok = True
    except UnicodeDecodeError:
        utf8_ok = False
    check(utf8_ok, "session-start：stdout 可按 UTF-8 解码")

    shutil.rmtree(tmp)
    failed = [m for ok, m in checks if not ok]
    print()
    if failed:
        print(f"❌ {len(failed)}/{len(checks)} 项失败：")
        for m in failed:
            print("   -", m)
        sys.exit(1)
    print(f"🎉 全部 {len(checks)} 项断言通过")


if __name__ == "__main__":
    main()
