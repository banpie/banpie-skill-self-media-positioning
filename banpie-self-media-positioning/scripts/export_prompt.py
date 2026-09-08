#!/usr/bin/env python3
"""从技能运行正文导出 Agent 与普通对话共用的自包含提示词。"""
import argparse
import hashlib
import re
from pathlib import Path

SOURCES = (
    "SKILL.md",
    "references/course-companion.md",
    "references/intake.md",
    "references/positioning-method.md",
    "references/scenarios.md",
    "references/research-and-validation.md",
    "references/account-diagnosis.md",
    "references/worked-example.md",
    "assets/account-positioning.md",
)


def render(root: Path) -> str:
    raw = [(name, (root / name).read_text(encoding="utf-8")) for name in SOURCES]
    version = re.search(r'version: "([^"]+)"', raw[0][1]).group(1)
    digest = hashlib.sha256()
    for name, body in raw:
        digest.update(name.encode() + b"\0" + body.encode() + b"\0")
    anchors = {name: f"source-{i}" for i, name in enumerate(SOURCES, 1)}
    sections = []
    for name, body in raw:
        if name == "SKILL.md":
            body = body.split("---", 2)[2].strip()

        def link(match):
            label, target = match.groups()
            if "://" in target or target.startswith("#"):
                return match.group(0)
            file_part = target.split("#", 1)[0]
            resolved = (root / name).parent.joinpath(file_part).resolve()
            relative = resolved.relative_to(root.resolve()).as_posix()
            if not resolved.is_file():
                raise ValueError(f"引用文件不存在：{name} -> {target}")
            if relative in anchors:
                return f"[{label}](#{anchors[relative]})"
            # 仅安装说明和维护来源留作外链，咨询流程所需正文全部嵌入。
            if relative not in {"README.md", "references/method-origins.md"}:
                raise ValueError(f"运行引用未嵌入：{relative}")
            return f"[{label}](https://github.com/banpie/banpie-skill-self-media-positioning/blob/main/banpie-self-media-positioning/{relative})"

        body = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, body)
        sections.append(f'<a id="{anchors[name]}"></a>\n\n<!-- 来源：{name} -->\n\n{body.strip()}')
    return (
        "# 自媒体定位统一提示词\n\n"
        f"> 自动导出版本：{version}；来源摘要：`{digest.hexdigest()}`。\n"
        "> 此文件同时用于 Agent 系统提示词与普通对话，不独立编辑；更新技能后重新导出。\n\n"
        "请按下面的完整流程担任自媒体定位顾问。普通对话使用时将本段及后续正文一起提供；"
        "若当前请求是开始定位，从第1步开始，并在资料核对处等待。仅要求审阅提示词时不启动咨询。"
        "本文件已包含入口、课程对照、信息模板、方法、场景、研究、诊断、示范与交付模板，"
        "文内参考链接指向本文件对应章节，无需寻找同名插件。"
        "引用的虚构案例用于示范，不作为当前用户资料，不自动运行完整案例。\n\n"
        + "\n\n---\n\n".join(sections) + "\n"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--check", action="store_true", help="只检查导出是否与源码一致")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.expanduser().resolve()
    # 防止误把输出指定为源码，或生成递归嵌入的技能内副本。
    if output == root or root in output.parents:
        parser.error("导出必须放在技能目录外，以免覆盖或重复载入源码")
    expected = render(root)
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != expected:
            parser.exit(1, "导出缺失或已过期，请重新生成。\n")
        print("导出与当前源码一致。")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(expected, encoding="utf-8")
        print(f"已导出：{output}")


if __name__ == "__main__":
    main()
