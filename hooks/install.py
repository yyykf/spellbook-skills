#!/usr/bin/env python3
"""安装/卸载 .project_context 规则注入到 Copilot 与旧 Codex fallback。

Claude Code 靠插件自动加载本目录的 hooks.json，无需本脚本。
Codex 0.137.0+ 也会自动加载插件包内 hooks/hooks.json；首次仍需 /hooks 信任。
本脚本现在只处理：
  - Copilot：把规则写进 ~/.copilot/copilot-instructions.md（personal 级，抗 compact）
  - 旧 Codex / fallback：显式选择时，把 SessionStart/SubagentStart hooks 合并进 ~/.codex/hooks.json

注入脚本与规则正文会先 copy 到稳定位置（默认 ~/.local/share/spellbook-skills/hooks/）。

健壮性保障：
  - 稳定目录写哨兵文件，卸载只删带哨兵的目录（绝不误删用户目录）
  - 所有配置文件原子写入（临时文件 + os.replace），中断不留半成品
  - 合并/卸载前做 JSON 解析与类型校验，异常结构不破坏用户配置
  - Copilot instructions 用 manifest 记录创建来源，只删本工具建的文件

用法：
  python3 install.py install                         安装 Copilot instructions（默认）
  python3 install.py install --target auto           自动判断是否需要旧 Codex fallback
  python3 install.py install --target codex-fallback 安装旧 Codex fallback
  python3 install.py install --target all            同时安装 Copilot + Codex fallback
  python3 install.py uninstall                       卸载全部（精确移除自己加的部分）
  python3 install.py uninstall --target copilot      只卸载 Copilot 部分
  python3 install.py status                          查看全部安装状态

环境变量覆盖路径（主要用于测试）：
  SPELLBOOK_HOME / CODEX_HOME / COPILOT_HOME
"""
import argparse
import json
import os
import re
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

TARGET_COPILOT = "copilot"
TARGET_CODEX_FALLBACK = "codex-fallback"
TARGET_ALL = "all"
TARGET_AUTO = "auto"
TARGET_NONE = "none"
TARGET_CHOICES = (TARGET_COPILOT, TARGET_CODEX_FALLBACK, TARGET_ALL, TARGET_AUTO)
CODEX_PLUGIN_HOOK_MIN_VERSION = (0, 137, 0)
CODEX_CONTEXT_HOOK_EVENTS = ("SessionStart", "SubagentStart")


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


def _codex_entry(event_name):
    entry = {
        "hooks": [
            {
                "type": "command",
                "timeout": 5,
                "command": _command([sys.executable, installed_script()]),
            }
        ],
    }
    if event_name == "SessionStart":
        entry["matcher"] = "startup|resume|clear|compact"
    return entry


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


def _require_codex_event(hooks, event_name, path):
    entries = hooks.setdefault(event_name, [])
    if not isinstance(entries, list):
        raise SystemExit(f"❌ {path} 的 {event_name} 不是数组；未修改，请手动检查。")
    return entries


def _require_codex_context_events(data, path):
    """校验并返回 hooks_dict；结构异常则中止，不破坏文件。"""
    if not isinstance(data, dict):
        raise SystemExit(f"❌ {path} 顶层不是 JSON 对象；未修改，请手动检查。")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SystemExit(f"❌ {path} 的 hooks 不是对象；未修改，请手动检查。")
    for event_name in CODEX_CONTEXT_HOOK_EVENTS:
        _require_codex_event(hooks, event_name, path)
    return hooks


def codex_install():
    path = codex_hooks_file()
    data = _load_json_strict(path, {})
    hooks = _require_codex_context_events(data, path)
    for event_name in CODEX_CONTEXT_HOOK_EVENTS:
        entries = hooks[event_name]
        entries[:] = [e for e in entries if not _is_our_codex(e)]  # 幂等
        entries.append(_codex_entry(event_name))
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
    for event_name in CODEX_CONTEXT_HOOK_EVENTS:
        entries = hooks.get(event_name)
        if not isinstance(entries, list):
            continue
        entries[:] = [e for e in entries if not _is_our_codex(e)]
        if not entries:
            del hooks[event_name]
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
    return any(
        isinstance(data["hooks"].get(event_name), list)
        and any(_is_our_codex(e) for e in data["hooks"][event_name])
        for event_name in CODEX_CONTEXT_HOOK_EVENTS
    )


def codex_installed_events():
    path = codex_hooks_file()
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    return [
        event_name
        for event_name in CODEX_CONTEXT_HOOK_EVENTS
        if isinstance(hooks.get(event_name), list)
        and any(_is_our_codex(e) for e in hooks[event_name])
    ]


def _parse_codex_version(text):
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def _format_version(version):
    return ".".join(str(part) for part in version)


def _detect_codex_version():
    codex = shutil.which("codex")
    if not codex:
        return None, "未找到 PATH 上的 codex 命令"
    try:
        proc = subprocess.run(
            [codex, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"运行 codex --version 失败：{exc}"
    output = "\n".join(part for part in (proc.stdout, proc.stderr) if part).strip()
    if proc.returncode != 0:
        return None, f"codex --version 退出码 {proc.returncode}：{output or '无输出'}"
    version = _parse_codex_version(output)
    if version is None:
        return None, f"无法从 codex --version 输出解析版本：{output or '无输出'}"
    return version, None


def resolve_auto_install_target():
    version, reason = _detect_codex_version()
    if version is None:
        raise SystemExit(
            "❌ 无法自动判断 Codex 版本，未写入任何 Codex fallback 配置。\n"
            f"   原因：{reason}\n"
            "   如果你确认这是旧 Codex，或明确需要固定写入 ~/.codex/hooks.json，"
            "请改用：--target codex-fallback"
        )
    if version < CODEX_PLUGIN_HOOK_MIN_VERSION:
        print(
            "ℹ️  检测到 Codex "
            f"{_format_version(version)} < {_format_version(CODEX_PLUGIN_HOOK_MIN_VERSION)}，"
            "将安装 Codex fallback。"
        )
        return TARGET_CODEX_FALLBACK
    print(
        "ℹ️  检测到 Codex "
        f"{_format_version(version)} >= {_format_version(CODEX_PLUGIN_HOOK_MIN_VERSION)}，"
        "Codex 使用插件 hooks/hooks.json；不写 ~/.codex/hooks.json fallback。"
    )
    return TARGET_NONE


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
def _target_includes(target, selected):
    return target == TARGET_ALL or target == selected


def _target_label(target):
    if target == TARGET_ALL:
        return "Copilot + Codex fallback"
    if target == TARGET_CODEX_FALLBACK:
        return "Codex fallback"
    if target == TARGET_NONE:
        return "Codex auto (no fallback needed)"
    return "Copilot"


def _preflight(target):
    """安装前校验目标配置结构，避免中途失败留半成品。"""
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        path = codex_hooks_file()
        if os.path.exists(path):
            data = _load_json_strict(path, {})
            if not isinstance(data, dict):
                raise SystemExit(f"❌ {path} 顶层不是 JSON 对象；未修改。")
            hooks = data.get("hooks")
            if hooks is not None and not isinstance(hooks, dict):
                raise SystemExit(f"❌ {path} 的 hooks 不是对象；未修改。")
            if isinstance(hooks, dict):
                for event_name in CODEX_CONTEXT_HOOK_EVENTS:
                    entries = hooks.get(event_name)
                    if entries is not None and not isinstance(entries, list):
                        raise SystemExit(f"❌ {path} 的 {event_name} 不是数组；未修改。")
    if _target_includes(target, TARGET_COPILOT):
        _check_copilot_markers()


def _remove_payload_if_unused():
    if codex_status() or copilot_status():
        return
    remove_payload()


def cmd_install(target):
    if target == TARGET_NONE:
        print("✅ 无需安装 Codex fallback")
        print("   Codex:    0.137.0+ 使用插件 hooks/hooks.json；启用插件后运行 /hooks 信任即可。")
        print("   Copilot:  未写入（如需 Copilot instructions，请运行不带 --target 的 install）")
        return
    _preflight(target)  # 校验失败时尚未 copy 任何文件，无半成品
    copy_payload()
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        codex_install()
    if _target_includes(target, TARGET_COPILOT):
        copilot_install()
    print("✅ 安装完成")
    print(f"   目标:     {_target_label(target)}")
    print(f"   稳定位置: {installed_hooks_dir()}")
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        print(f"   Codex:    已合并进 {codex_hooks_file()} 的 SessionStart/SubagentStart")
    else:
        print("   Codex:    未写入 fallback（Codex 0.137.0+ 使用插件 hooks/hooks.json）")
    if _target_includes(target, TARGET_COPILOT):
        print(f"   Copilot:  已写入 {copilot_instructions_file()}（marker 块）")
    else:
        print("   Copilot:  未写入")
    print()
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        print("⚠️  Codex fallback 首次需信任：启动 Codex 后运行 /hooks 审核并信任本 hook（一次即可，无法脚本预信任）。")
    else:
        print("ℹ️  Codex 0.137.0+ 无需本脚本写 hooks.json；启用插件后通过 /hooks 信任插件 hook 即可。")
    print("    Claude Code 无需本脚本——插件已自动加载 hooks/hooks.json。")


def cmd_uninstall(target):
    if _target_includes(target, TARGET_COPILOT):
        _check_copilot_markers()  # 残缺 marker 先中止，避免半卸载
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        codex_uninstall()
    if _target_includes(target, TARGET_COPILOT):
        copilot_uninstall()  # 需在 remove_payload 之前读 manifest
    _remove_payload_if_unused()
    print(f"✅ 卸载完成：已从 {_target_label(target)} 精确移除本工具写入的配置。")
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        print("   注：Codex config.toml 的 [hooks.state] 残留条目无害（hash 对不上会被忽略），如需可手动清理含 session_start/subagent_start 的段。")


def cmd_status(target):
    print(f"稳定位置:     {'已安装' if os.path.isdir(installed_hooks_dir()) else '未安装'}  ({installed_hooks_dir()})")
    if _target_includes(target, TARGET_CODEX_FALLBACK):
        installed_events = codex_installed_events()
        if installed_events == list(CODEX_CONTEXT_HOOK_EVENTS):
            label = "已安装"
        elif installed_events:
            label = "部分安装: " + ",".join(installed_events)
        else:
            label = "未安装"
        print(f"Codex fallback: {label}  ({codex_hooks_file()})")
    if _target_includes(target, TARGET_COPILOT):
        cpath = copilot_instructions_file()
        broken = False
        if os.path.exists(cpath):
            with open(cpath, encoding="utf-8") as handle:
                broken = not _markers_balanced(handle.read())
        if broken:
            print(f"Copilot 指令:  ⚠️ marker 残缺/不配对，需手动修复  ({cpath})")
        else:
            print(f"Copilot 指令:  {'已安装' if copilot_status() else '未安装'}  ({cpath})")


def _parse_args(argv):
    parser = argparse.ArgumentParser(
        description="安装/卸载 Spellbook Project Context Hook。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("action", choices=("install", "uninstall", "status"))
    parser.add_argument(
        "--target",
        choices=TARGET_CHOICES,
        default=None,
        help=(
            "目标平台。install 默认 copilot；uninstall/status 默认 all。auto 仅支持 install。"
            "codex-fallback 仅用于旧 Codex 或明确需要 ~/.codex/hooks.json 的场景。"
        ),
    )
    return parser.parse_args(argv)


def main():
    args = _parse_args(sys.argv[1:])
    target = args.target
    if target is None:
        target = TARGET_COPILOT if args.action == "install" else TARGET_ALL
    elif target == TARGET_AUTO:
        if args.action != "install":
            raise SystemExit("❌ --target auto 仅支持 install；uninstall/status 请使用 all、copilot 或 codex-fallback。")
        target = resolve_auto_install_target()
    actions = {"install": cmd_install, "uninstall": cmd_uninstall, "status": cmd_status}
    actions[args.action](target)


if __name__ == "__main__":
    main()
