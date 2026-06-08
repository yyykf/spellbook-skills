#!/usr/bin/env python3
"""安装/卸载 .project_context 规则注入到 Codex 与 Copilot。

Claude Code 靠插件自动加载本目录的 hooks.json，无需本脚本。
本脚本仅处理两个「不自动加载插件 hook」的平台：
  - Codex：把 SessionStart hook 合并进 ~/.codex/hooks.json
  - Copilot：把规则写进 ~/.copilot/copilot-instructions.md（personal 级，抗 compact）

注入脚本与规则正文会先 copy 到稳定位置（默认 ~/.local/share/spellbook-skills/hooks/）。

健壮性保障：
  - 稳定目录写哨兵文件，卸载只删带哨兵的目录（绝不误删用户目录）
  - 所有配置文件原子写入（临时文件 + os.replace），中断不留半成品
  - 合并/卸载前做 JSON 解析与类型校验，异常结构不破坏用户配置
  - Copilot instructions 用 manifest 记录创建来源，只删本工具建的文件

用法：
  python3 install.py install      安装（Codex + Copilot）
  python3 install.py uninstall    卸载（精确移除自己加的部分）
  python3 install.py status       查看安装状态

环境变量覆盖路径（主要用于测试）：
  SPELLBOOK_HOME / CODEX_HOME / COPILOT_HOME
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

# Windows 控制台默认 GBK/cp936，无法编码状态提示里的对勾/警告 emoji，
# 会让 install/uninstall 因 UnicodeEncodeError 崩溃。这里强制标准流走 UTF-8
#（Python 3.7+），保证输出永不中断。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")

MARKER_BEGIN = "<!-- BEGIN spellbook-skills:project-context -->"
MARKER_END = "<!-- END spellbook-skills:project-context -->"
SENTINEL = ".spellbook-install-marker"  # 标记稳定目录由本工具创建


# ---------- 路径（均可被环境变量覆盖） ----------
def spellbook_home():
    return os.environ.get(
        "SPELLBOOK_HOME", os.path.join(HOME, ".local", "share", "spellbook-skills")
    )


def codex_hooks_file():
    return os.path.join(os.environ.get("CODEX_HOME", os.path.join(HOME, ".codex")), "hooks.json")


def copilot_instructions_file():
    return os.path.join(
        os.environ.get("COPILOT_HOME", os.path.join(HOME, ".copilot")), "copilot-instructions.md"
    )


def installed_hooks_dir():
    return os.path.join(spellbook_home(), "hooks")


def installed_script():
    return os.path.join(installed_hooks_dir(), "session-start")


def installed_rules():
    return os.path.join(installed_hooks_dir(), "project-context.md")


def manifest_path():
    return os.path.join(spellbook_home(), ".install-state.json")


# ---------- 原子写 / JSON ----------
def _atomic_write(path, content):
    """临时文件 + fsync + os.replace 原子替换，避免中断留下截断文件。"""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-spellbook-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _write_json(path, data):
    _atomic_write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _load_json_strict(path, default):
    """读取 JSON；损坏时报清晰错误并中止（不破坏用户文件）。"""
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"❌ {path} 不是合法 JSON（{exc}）；未做任何修改，请手动修复或备份后重试。")


def _read_manifest():
    path = manifest_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _update_manifest(**kw):
    data = _read_manifest()
    data.update(kw)
    _write_json(manifest_path(), data)


# ---------- 稳定位置 payload ----------
def copy_payload():
    dst = installed_hooks_dir()
    os.makedirs(dst, exist_ok=True)
    for name in ("session-start", "project-context.md"):
        shutil.copy2(os.path.join(HERE, name), os.path.join(dst, name))
    os.chmod(installed_script(), 0o755)
    with open(os.path.join(dst, SENTINEL), "w", encoding="utf-8") as handle:
        handle.write("spellbook-skills project-context hook payload\n")


def remove_payload():
    """只删带哨兵文件的稳定目录——绝不递归删除非本工具创建的目录。"""
    hooks_dir = installed_hooks_dir()
    if not os.path.isfile(os.path.join(hooks_dir, SENTINEL)):
        if os.path.isdir(hooks_dir):
            print(f"⚠️  跳过删除 {hooks_dir}：未找到本工具哨兵文件，可能非本工具创建，请手动检查。")
        return
    shutil.rmtree(hooks_dir)
    if os.path.isfile(manifest_path()):
        os.remove(manifest_path())
    root = spellbook_home()
    if os.path.isdir(root) and not os.listdir(root):
        os.rmdir(root)


# ---------- Codex ----------
def _quote_command_arg(arg):
    if os.name == "nt":
        quoted = subprocess.list2cmdline([arg])
        return quoted if quoted.startswith('"') else f'"{quoted}"'
    return shlex.quote(arg)


def _command(args):
    return " ".join(_quote_command_arg(arg) for arg in args)


def _codex_entry():
    return {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
            {
                "type": "command",
                "timeout": 5,
                "command": _command([sys.executable, installed_script()]),
            }
        ],
    }


def _is_our_codex(entry):
    """保守类型判断 + 脚本路径识别，异常结构一律视为非本工具、保留不动。"""
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    markers = (installed_script(), "spellbook-skills/hooks/session-start")
    for hook in hooks:
        if isinstance(hook, dict):
            cmd = hook.get("command", "")
            if isinstance(cmd, str) and any(marker in cmd for marker in markers):
                return True
    return False


def _require_codex_session_start(data, path):
    """校验并返回 (hooks_dict, session_start_list)；结构异常则中止，不破坏文件。"""
    if not isinstance(data, dict):
        raise SystemExit(f"❌ {path} 顶层不是 JSON 对象；未修改，请手动检查。")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"❌ {path} 的 hooks 不是对象；未修改，请手动检查。")
    session_start = hooks.setdefault("SessionStart", [])
    if not isinstance(session_start, list):
        raise SystemExit(f"❌ {path} 的 SessionStart 不是数组；未修改，请手动检查。")
    return hooks, session_start


def codex_install():
    path = codex_hooks_file()
    data = _load_json_strict(path, {})
    _, session_start = _require_codex_session_start(data, path)
    session_start[:] = [e for e in session_start if not _is_our_codex(e)]  # 幂等
    session_start.append(_codex_entry())
    _write_json(path, data)


def codex_uninstall():
    path = codex_hooks_file()
    if not os.path.exists(path):
        return
    data = _load_json_strict(path, {})
    if not isinstance(data, dict):
        return
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return
    session_start = hooks.get("SessionStart")
    if not isinstance(session_start, list):
        return
    session_start[:] = [e for e in session_start if not _is_our_codex(e)]
    if not session_start:
        del hooks["SessionStart"]
    _write_json(path, data)


def codex_status():
    path = codex_hooks_file()
    if not os.path.exists(path):
        return False
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict) or not isinstance(data.get("hooks"), dict):
        return False
    session_start = data["hooks"].get("SessionStart")
    return isinstance(session_start, list) and any(_is_our_codex(e) for e in session_start)


# ---------- Copilot（instructions + marker 块） ----------
def _render_block():
    with open(installed_rules(), encoding="utf-8") as handle:
        rules = handle.read().rstrip()
    return f"{MARKER_BEGIN}\n{rules}\n{MARKER_END}"


def _strip_blocks(text):
    """移除所有完整 MARKER_BEGIN..MARKER_END 块；遇残缺标记保守停止。"""
    while True:
        begin = text.find(MARKER_BEGIN)
        if begin == -1:
            break
        end = text.find(MARKER_END, begin)
        if end == -1:
            break
        end += len(MARKER_END)
        text = (text[:begin].rstrip("\n") + "\n" + text[end:].lstrip("\n")).strip("\n")
    return text


def _markers_balanced(text):
    """MARKER_BEGIN/END 数量相等且顺序配对则返回 True。"""
    begins = text.count(MARKER_BEGIN)
    if begins != text.count(MARKER_END):
        return False
    pos = 0
    for _ in range(begins):
        begin = text.find(MARKER_BEGIN, pos)
        end = text.find(MARKER_END, begin)
        if begin == -1 or end == -1 or end < begin:
            return False
        pos = end + len(MARKER_END)
    return True


def _assert_markers_balanced(text, path):
    """残缺/不配对的 marker 会让安装卸载状态不闭环，发现即中止、提示手动修复。"""
    if not _markers_balanced(text):
        raise SystemExit(
            f"❌ {path} 的 spellbook-skills marker 残缺或不配对"
            f"（BEGIN={text.count(MARKER_BEGIN)}, END={text.count(MARKER_END)}）；"
            f"未做任何修改，请手动修复成对的 marker"
            f"（{MARKER_BEGIN} ... {MARKER_END}）后重试。"
        )


def _check_copilot_markers():
    path = copilot_instructions_file()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as handle:
            _assert_markers_balanced(handle.read(), path)


def copilot_install():
    path = copilot_instructions_file()
    pre_existed = os.path.exists(path)
    existing = ""
    if pre_existed:
        with open(path, encoding="utf-8") as handle:
            existing = handle.read()
    existing = _strip_blocks(existing)  # 幂等：去掉所有旧块
    block = _render_block()
    new = (existing.rstrip("\n") + "\n\n" + block) if existing.strip() else block
    _atomic_write(path, new + "\n")
    created = _read_manifest().get("copilot_created", False) or (not pre_existed)
    _update_manifest(copilot_created=created)


def copilot_uninstall():
    path = copilot_instructions_file()
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    stripped = _strip_blocks(text)
    if stripped.strip():
        _atomic_write(path, stripped + "\n")
    elif _read_manifest().get("copilot_created"):
        os.remove(path)  # 文件由本工具创建且已空 → 删除
    else:
        _atomic_write(path, "")  # 用户原有文件，保守保留为空，不删整文件


def copilot_status():
    path = copilot_instructions_file()
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as handle:
        return MARKER_BEGIN in handle.read()


# ---------- 子命令 ----------
def _preflight():
    """安装前校验：Codex hooks.json 结构合法、Copilot marker 配对，避免中途失败留半成品。"""
    path = codex_hooks_file()
    if os.path.exists(path):
        data = _load_json_strict(path, {})
        if not isinstance(data, dict):
            raise SystemExit(f"❌ {path} 顶层不是 JSON 对象；未修改。")
        hooks = data.get("hooks")
        if hooks is not None and not isinstance(hooks, dict):
            raise SystemExit(f"❌ {path} 的 hooks 不是对象；未修改。")
        if isinstance(hooks, dict):
            session_start = hooks.get("SessionStart")
            if session_start is not None and not isinstance(session_start, list):
                raise SystemExit(f"❌ {path} 的 SessionStart 不是数组；未修改。")
    _check_copilot_markers()


def cmd_install():
    _preflight()  # 校验失败时尚未 copy 任何文件，无半成品
    copy_payload()
    codex_install()
    copilot_install()
    print("✅ 安装完成")
    print(f"   稳定位置: {installed_hooks_dir()}")
    print(f"   Codex:    已合并进 {codex_hooks_file()} 的 SessionStart")
    print(f"   Copilot:  已写入 {copilot_instructions_file()}（marker 块）")
    print()
    print("⚠️  Codex 首次需信任：启动 Codex 后运行 /hooks 审核并信任本 hook（一次即可，无法脚本预信任）。")
    print("    Claude Code 无需本脚本——插件已自动加载 hooks/hooks.json。")


def cmd_uninstall():
    _check_copilot_markers()  # 残缺 marker 先中止，避免半卸载
    codex_uninstall()
    copilot_uninstall()  # 需在 remove_payload 之前读 manifest
    remove_payload()
    print("✅ 卸载完成：已从 Codex hooks.json、Copilot instructions 移除，并删除稳定位置文件。")
    print("   注：Codex config.toml 的 [hooks.state] 残留条目无害（hash 对不上会被忽略），如需可手动清理含 session_start 的段。")


def cmd_status():
    print(f"稳定位置:     {'已安装' if os.path.isdir(installed_hooks_dir()) else '未安装'}  ({installed_hooks_dir()})")
    print(f"Codex hook:   {'已安装' if codex_status() else '未安装'}  ({codex_hooks_file()})")
    cpath = copilot_instructions_file()
    broken = False
    if os.path.exists(cpath):
        with open(cpath, encoding="utf-8") as handle:
            broken = not _markers_balanced(handle.read())
    if broken:
        print(f"Copilot 指令: ⚠️ marker 残缺/不配对，需手动修复  ({cpath})")
    else:
        print(f"Copilot 指令: {'已安装' if copilot_status() else '未安装'}  ({cpath})")


def main():
    actions = {"install": cmd_install, "uninstall": cmd_uninstall, "status": cmd_status}
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        print(__doc__)
        print(f"用法: python3 {os.path.basename(__file__)} {{install|uninstall|status}}")
        sys.exit(2)
    actions[sys.argv[1]]()


if __name__ == "__main__":
    main()
