from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[1]

TYPE_INFO: Dict[str, Dict[str, Any]] = {
    "M": {
        "name": "M型领导者",
        "en": "M-shaped Leader",
        "color": "#6C216D",
        "bg": "#F3E6F3",
        "desc": "你是AI时代组织变革的核心引领者，具备整合多领域资源、统筹AI战略落地的能力，能够推动团队从传统执行模式向人机协同模式转型，是企业AI转型的定向者与核心推动者。",
        "transform": "从经验决策 → AI驱动战略决策、组织变革管理、跨域资源统筹",
        "paths": [
            {"t": "近期（1个月）", "c": "完成AI通用底座学习，重点掌握绘制部门人机分工流程图、AI项目人效/成本测算方法"},
            {"t": "中期（1-3个月）", "c": "进入AI基础应用层：设计部门AI转型季度路径，学习组织变革阻力识别与应对话术"},
            {"t": "远期（3-6个月）", "c": "冲击AI专业深化层：主导AI项目全流程管控（需求→试点→复盘→推广），输出企业级AI战略"},
        ],
        "learns": [
            "识别企业可被AI替代的岗位/工作清单",
            "用AI生成会议纪要与任务拆解、跟进清单",
            "团队AI能力评估与成长路径规划",
            "AI项目全流程管控：需求→试点→复盘→推广",
            "企业AI治理体系：权限、合规、安全、迭代",
        ],
    },
    "A": {
        "name": "AI赋能者",
        "en": "AI Accomplisher",
        "color": "#E18C3F",
        "bg": "#FDF3E7",
        "desc": "你是企业AI工具的“训练师”与“优化师”，对AI有强烈的探索欲，已具备或有潜力具备业务知识库投喂、Prompt系统优化的能力，是连接AI能力与真实业务场景的关键节点。",
        "transform": "从普通工具使用者 → AI知识库投喂、指令优化、场景适配与模型调优",
        "paths": [
            {"t": "近期（1个月）", "c": "系统学习结构化Prompt设计与复用，完成首个业务场景的AI知识库搭建实操"},
            {"t": "中期（1-3个月）", "c": "完成业务知识库结构化整理，从0到1搭建企业专属AI智能体，并完成首次真实场景验证"},
            {"t": "远期（3-6个月）", "c": "建设企业10+可复用AI场景库，编制全员AI赋能标准化手册，成为内部AI推广核心负责人"},
        ],
        "learns": [
            "结构化Prompt设计：角色+任务+格式+示例+约束",
            "AI知识库投喂实操：上传、校验、校准、生效",
            "从0到1搭建企业专属AI智能体",
            "业务场景AI微调与适配：垂直场景效果提升",
            "企业级Prompt库搭建与持续维护",
        ],
    },
    "H": {
        "name": "H型员工",
        "en": "H-shaped Employee",
        "color": "#1A7A4A",
        "bg": "#EBF7F1",
        "desc": "你是AI时代人机协同的一线高效执行者，核心价值在于情感连接与高价值人际互动。AI将大幅解放你的重复性工作，让你专注于AI无法替代的真正高价值工作。",
        "transform": "从重复劳动执行 → 高价值人际互动、岗位AI化执行、人机协同提效",
        "paths": [
            {"t": "近期（1个月）", "c": "梳理本岗位80%可AI替代重复工作清单，制定个人人机分工SOP，掌握万能Prompt框架"},
            {"t": "中期（1-3个月）", "c": "用AI自动生成日/周报、资料分类整理，实现日常工作效率显著提升（目标提效30%以上）"},
            {"t": "远期（3-6个月）", "c": "从0到1搭建个人岗位AI工作流，编制《个人AI提效手册》，可担任团队AI小教员"},
        ],
        "learns": [
            "万能Prompt框架：背景+任务+要求+格式+示例",
            "用AI自动生成日报/周报/总结/话术",
            "用AI做资料提取、分类、汇总、排版",
            "高价值人际互动设计：AI执行，人做判断与情感沟通",
            "从0到1搭建个人岗位AI工作流",
        ],
    },
    "D": {
        "name": "数据管理者",
        "en": "Data Driver",
        "color": "#1A5276",
        "bg": "#EAF2FB",
        "desc": "你是AI时代数据资产的全周期管理者，对数据的价值定义、开发、整合与运维有专业敏感度，是企业AI模型训练的“燃料供应官”，保障AI系统稳定运行与持续迭代的关键人才。",
        "transform": "从基础数据处理 → 数据治理、数据价值定义、AI训练数据运维与资产管理",
        "paths": [
            {"t": "近期（1个月）", "c": "完成数据合规底座：掌握AI数据全流程（采集→清洗→标注→入库→使用），建立数据台账"},
            {"t": "中期（1-3个月）", "c": "完成数据整理与标注实操，掌握数据脱敏实操，用AI生成数据日报/周报看板"},
            {"t": "远期（3-6个月）", "c": "设计数据治理流程，构建AI训练数据供给体系，输出数据管理SOP与培训材料"},
        ],
        "learns": [
            "AI与数据关系：数据是AI系统的核心燃料",
            "数据合规：隐私、脱敏、授权、留存、销毁全流程",
            "AI训练数据标注规范与质量校验方法",
            "建立数据台账：来源、时间、用途、负责人",
            "数据治理流程设计：采集→清洗→校验→更新→退出",
        ],
    },
    "I": {
        "name": "I型解题者",
        "en": "Innovative Solver",
        "color": "#884400",
        "bg": "#FEF0E6",
        "desc": "你是AI时代处理复杂例外问题的核心专家，在某一专业领域的深厚积累让你成为组织的“深度判断节点”，AI将大幅放大你的专业影响力，帮你突破知识获取和方案输出的瓶颈。",
        "transform": "从单一领域专家 → 复杂问题AI化拆解、跨域协同、例外问题深度解决",
        "paths": [
            {"t": "近期（1个月）", "c": "掌握AI能力边界认知，学习复杂问题AI化拆解逻辑（结构、原因、影响、方案四维框架）"},
            {"t": "中期（1-3个月）", "c": "用AI辅助专业知识检索与方案框架生成，搭建个人专业领域AI知识库并完成首次调用"},
            {"t": "远期（3-6个月）", "c": "设计例外问题AI化解决路径，输出领域AI解题方法论，参与企业AI专业场景规划"},
        ],
        "learns": [
            "AI能力边界：能解决/不能解决的清晰区分",
            "用AI拆解复杂问题：结构、原因、影响、方案",
            "用AI检索并总结专业知识、案例、法规",
            "个人专业知识库搭建与AI调用方法",
            "例外问题AI化解决路径设计",
        ],
    },
}

MOTTOS = {
    "M": "用你的战略视野 × AI的执行效率，你将成为推动组织AI转型最不可缺少的掌舵人。",
    "A": "用你对AI的深度理解 × 业务场景洞察，你将成为企业最稀缺的AI赋能核心。",
    "H": "用你无可替代的情感连接 × AI释放出的时间，你将在真正高价值的工作中大放异彩。",
    "D": "用你对数据的专业敏感度 × AI的智能处理能力，你将成为企业AI燃料的关键守护者。",
    "I": "用你的专业深度 × AI的执行效率，你将成为组织里处理最复杂问题的核心专家。",
}

DIM_LABELS = {
    "E": "经验经历",
    "K": "AI专业知识",
    "I": "兴趣倾向",
    "L": "学习方式",
    "P": "发展潜能",
}

STYLE_INFO = {
    "social": {"name": "社交型", "desc": "倾向于通过与他人交流、请教来学习，善于在对话中获得启发。"},
    "practice": {"name": "实践型", "desc": "倾向于直接动手操作、在实践中摸索，从结果中积累经验。"},
    "structure": {"name": "结构型", "desc": "倾向于系统化、按步骤学习，喜欢先建立完整框架再深入。"},
    "research": {"name": "钻研型", "desc": "倾向于独立钻研、追根究底，喜欢从原理和本质理解问题。"},
}

LEVEL_INFO = [
    {"label": "AI通用底座", "desc": "尚未建立AI基础认知，需优先完成全员必修模块。"},
    {"label": "AI基础应用", "desc": "具备基本AI工具使用能力，可进入岗位专属学习路径。"},
    {"label": "AI专业深化", "desc": "能系统应用AI，可承担内部场景优化与赋能任务。"},
    {"label": "AI体系创新", "desc": "具备构建AI体系能力，可担任赋能者或领导者角色。"},
]


def as_number(value: Any, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp_pct(value: Any) -> int:
    return max(0, min(100, round(as_number(value))))


def text(value: Any) -> str:
    return escape("" if value is None else str(value), quote=True)


def score_percentages(result: Dict[str, Any]) -> Dict[str, int]:
    pcts = result.get("pcts") or {}
    if pcts:
        return {key: clamp_pct(pcts.get(key, 0)) for key in TYPE_INFO}
    final = result.get("final") or {}
    total = sum(as_number(final.get(key, 0)) for key in TYPE_INFO)
    if total <= 0:
        return {key: 0 for key in TYPE_INFO}
    return {key: clamp_pct(as_number(final.get(key, 0)) / total * 100) for key in TYPE_INFO}


def sorted_types(result: Dict[str, Any], pcts: Dict[str, int]) -> List[Tuple[str, int]]:
    raw_sorted = result.get("sorted") or []
    pairs: List[Tuple[str, int]] = []
    for item in raw_sorted:
        if isinstance(item, (list, tuple)) and len(item) >= 2 and item[0] in TYPE_INFO:
            pairs.append((str(item[0]), clamp_pct(item[1])))
    if pairs:
        return pairs
    return sorted(pcts.items(), key=lambda item: item[1], reverse=True)


def dim_scores(result: Dict[str, Any]) -> Dict[str, int]:
    dim_norm = result.get("dimNorm") or {}
    scores: Dict[str, int] = {}
    for key in DIM_LABELS:
        item = dim_norm.get(key, 0) if isinstance(dim_norm, dict) else 0
        if isinstance(item, dict) and item:
            scores[key] = clamp_pct(max(as_number(value) for value in item.values()))
        else:
            scores[key] = clamp_pct(item)
    return scores


def radar_svg(scores: Dict[str, int]) -> str:
    size = 240
    cx = cy = 120
    radius = 78
    keys = list(DIM_LABELS)

    def point(index: int, scale: float) -> Tuple[float, float]:
        import math

        angle = -math.pi / 2 + index * 2 * math.pi / len(keys)
        return cx + radius * scale * math.cos(angle), cy + radius * scale * math.sin(angle)

    rings = []
    for ring in (0.25, 0.5, 0.75, 1.0):
        rings.append(
            '<polygon points="{}" fill="none" stroke="#E7DFEA" stroke-width="1"/>'.format(
                " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, ring) for i in range(len(keys))))
            )
        )
    axes = []
    labels = []
    values = []
    for index, key in enumerate(keys):
        x, y = point(index, 1)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#EDE6EF" stroke-width="1"/>')
        lx, ly = point(index, 1.25)
        labels.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" dominant-baseline="middle" '
            f'fill="#6B6472" font-size="11">{text(DIM_LABELS[key])}</text>'
        )
        vx, vy = point(index, scores.get(key, 0) / 100)
        values.append((vx, vy))
    value_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in values)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#6C216D"/>' for x, y in values)
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" role="img" aria-label="MAHDI radar chart">'
        + "".join(rings)
        + "".join(axes)
        + f'<polygon points="{value_points}" fill="rgba(108,33,109,0.16)" stroke="#6C216D" stroke-width="2"/>'
        + dots
        + "".join(labels)
        + "</svg>"
    )


def bars(items: Iterable[Tuple[str, int]]) -> str:
    html = []
    for key, value in items:
        info = TYPE_INFO.get(key, TYPE_INFO["M"])
        html.append(
            f"""
            <div class="bar-row">
              <div class="bar-name"><span style="background:{info['bg']};color:{info['color']}">{text(key)}</span>{text(info['name'])}</div>
              <div class="bar-track"><div class="bar-fill" style="width:{clamp_pct(value)}%;background:{info['color']}"></div></div>
              <div class="bar-value" style="color:{info['color']}">{clamp_pct(value)}%</div>
            </div>
            """
        )
    return "".join(html)


def style_bars(result: Dict[str, Any]) -> str:
    style_pct = result.get("stylePct") or {}
    html = []
    for key, info in STYLE_INFO.items():
        value = clamp_pct(style_pct.get(key, 0))
        html.append(
            f"""
            <div class="bar-row">
              <div class="bar-name">{text(info['name'])}</div>
              <div class="bar-track"><div class="bar-fill purple" style="width:{value}%"></div></div>
              <div class="bar-value">{value}%</div>
            </div>
            """
        )
    return "".join(html)


def warning_block(result: Dict[str, Any]) -> str:
    warns = result.get("warns") or []
    if not warns:
        return '<div class="ok-note">未发现需要特别关注的方向，可按建议路径稳步推进。</div>'
    items = []
    for item in warns:
        if isinstance(item, dict):
            items.append(f"<li><strong>{text(item.get('name') or item.get('code'))}</strong>：{text(item.get('desc'))}</li>")
    if not items:
        return ""
    return '<div class="warn-box"><div class="section-title">需要关注的方向</div><ul>' + "".join(items) + "</ul></div>"


def path_block(info: Dict[str, Any]) -> str:
    items = []
    for index, item in enumerate(info.get("paths") or [], start=1):
        items.append(
            f"""
            <div class="path-item">
              <div class="path-num" style="background:{info['bg']};color:{info['color']}">{index}</div>
              <div>
                <h3 style="color:{info['color']}">{text(item.get('t'))}</h3>
                <p>{text(item.get('c'))}</p>
              </div>
            </div>
            """
        )
    if not items:
        return ""
    return f"""
    <section class="section path-section">
      <div class="section-title">个性化转型路径建议</div>
      <div class="muted-line">{text(info.get("transform"))}</div>
      {''.join(items)}
    </section>
    """


def learn_block(info: Dict[str, Any]) -> str:
    items = []
    for item in info.get("learns") or []:
        items.append(
            f"""
            <div class="learn-item">
              <span style="background:{info['color']}"></span>
              <div>{text(item)}</div>
            </div>
            """
        )
    if not items:
        return ""
    return f"""
    <section class="section learn-section">
      <div class="section-title">优先学习内容推荐</div>
      <div class="learn-grid">{''.join(items)}</div>
    </section>
    """


def motto_block(main_type: str) -> str:
    motto = MOTTOS.get(main_type)
    if not motto:
        return ""
    return f'<div class="motto"><p>{text(motto)}</p></div>'


def build_report_html(result: Dict[str, Any]) -> str:
    pcts = score_percentages(result)
    ranked = sorted_types(result, pcts)
    main_type = result.get("mainType") if result.get("mainType") in TYPE_INFO else ranked[0][0]
    second_type = result.get("secondType") if result.get("secondType") in TYPE_INFO else (ranked[1][0] if len(ranked) > 1 else "")
    info = TYPE_INFO[main_type]
    second_info = TYPE_INFO.get(second_type, {})
    level = max(1, min(4, int(as_number(result.get("level"), 1))))
    level_info = LEVEL_INFO[level - 1]
    k_rate = as_number(result.get("kRate"), 0)
    if 0 < k_rate <= 1:
        k_rate *= 100
    top_style = result.get("topStyle")
    top_style_name = result.get("topStyleName") or STYLE_INFO.get(top_style, {}).get("name") or "未识别"
    title = f"{info['name']} × {second_info.get('name', '')}".strip(" ×")
    created_at = text(result.get("createdAt") or "")
    user_name = text(result.get("userName") or result.get("email") or "学员")
    company = text(result.get("companyName") or "")
    job_title = text(result.get("jobTitle") or "")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
@page {{ size: A4; margin: 16mm 14mm; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; color: #1F1C2B; font-family: "Noto Sans SC", "Microsoft YaHei", Arial, sans-serif; background: #fff; font-size: 13px; line-height: 1.65; }}
.page {{ max-width: 760px; margin: 0 auto; }}
.header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; padding-bottom: 14px; border-bottom: 1px solid #E8DFEA; }}
.brand {{ display: flex; align-items: center; gap: 10px; color: #6C216D; font-weight: 700; }}
.logo {{ width: 34px; height: 34px; border-radius: 8px; background: #6C216D; color: #fff; display: flex; align-items: center; justify-content: center; }}
.meta {{ color: #8A8495; font-size: 11px; text-align: right; }}
.banner {{ margin: 18px 0 14px; padding: 12px 16px; color: #6C216D; background: #FAF5FB; border: 1px solid #E8DDEA; border-radius: 10px; text-align: center; }}
.hero {{ border: 1px solid #E3D9E7; border-top: 4px solid {info['color']}; border-radius: 12px; padding: 20px 22px; margin-bottom: 14px; }}
.hero-top {{ display: flex; gap: 16px; align-items: flex-start; }}
.avatar {{ width: 52px; height: 52px; flex: 0 0 52px; border-radius: 14px; background: {info['bg']}; color: {info['color']}; font-size: 24px; font-weight: 800; display: flex; align-items: center; justify-content: center; }}
h1 {{ margin: 0 0 3px; font-size: 23px; color: {info['color']}; line-height: 1.25; }}
.subtitle {{ color: #8D8796; font-size: 12px; margin-bottom: 8px; }}
.desc {{ color: #4F4A5C; }}
.transform {{ margin-top: 14px; padding: 10px 12px; border-radius: 8px; background: #FAFAFB; border-left: 3px solid {info['color']}; color: #4F4A5C; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }}
.section {{ border: 1px solid #E8DFEA; border-radius: 12px; padding: 16px; }}
.section-title {{ color: #8A8495; font-size: 12px; font-weight: 800; letter-spacing: .04em; margin-bottom: 10px; }}
.radar-wrap {{ display: flex; align-items: center; justify-content: center; }}
.bar-row {{ display: grid; grid-template-columns: 126px 1fr 42px; align-items: center; gap: 10px; margin: 9px 0; }}
.bar-name {{ display: flex; align-items: center; gap: 7px; color: #4F4A5C; font-size: 12px; }}
.bar-name span {{ display: inline-flex; width: 24px; height: 24px; border-radius: 7px; align-items: center; justify-content: center; font-weight: 800; }}
.bar-track {{ height: 7px; border-radius: 999px; background: #F0E8F1; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 999px; }}
.bar-fill.purple {{ background: #6C216D; }}
.bar-value {{ font-size: 12px; font-weight: 800; text-align: right; }}
.level-card {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 10px; }}
.level {{ padding: 10px 8px; text-align: center; border: 1px solid #E8DFEA; border-radius: 9px; color: #9B94A4; }}
.level.current {{ border-color: {info['color']}; background: {info['bg']}; color: {info['color']}; font-weight: 800; }}
.note {{ color: #4F4A5C; }}
.muted-line {{ color: #8A8495; font-size: 12px; margin-bottom: 12px; }}
.path-section, .learn-section {{ margin-bottom: 14px; }}
.path-item {{ display: grid; grid-template-columns: 28px 1fr; gap: 12px; margin-top: 12px; break-inside: avoid; }}
.path-num {{ width: 26px; height: 26px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 800; }}
.path-item h3 {{ margin: 0 0 3px; font-size: 13px; }}
.path-item p {{ margin: 0; color: #4F4A5C; font-size: 12.5px; line-height: 1.65; }}
.learn-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
.learn-item {{ display: grid; grid-template-columns: 7px 1fr; align-items: center; gap: 9px; padding: 9px 11px; background: #FAFAFB; border: 1px solid #EEE7EF; border-radius: 9px; color: #4F4A5C; font-size: 12.5px; break-inside: avoid; }}
.learn-item span {{ width: 6px; height: 6px; border-radius: 999px; }}
.ok-note {{ padding: 12px 14px; border-radius: 10px; background: #EEF8F2; color: #2F7441; border: 1px solid #D9EDDF; }}
.warn-box {{ border: 1px solid #F1D4D0; background: #FFF7F6; color: #8F332B; border-radius: 12px; padding: 14px 16px; break-inside: avoid; }}
.warn-box ul {{ margin: 8px 0 0 18px; padding: 0; }}
.motto {{ margin: 14px 0; padding: 18px 20px; text-align: center; border: 1px solid #E8DFEA; border-radius: 12px; background: linear-gradient(135deg, #FAF3FA, #FFFAF4); break-inside: avoid; }}
.motto p {{ margin: 0; color: #1F1C2B; font-size: 14px; font-weight: 700; line-height: 1.7; }}
.hero, .ok-note {{ break-inside: avoid; }}
.footer {{ margin-top: 16px; color: #9A94A4; font-size: 11px; text-align: center; }}
</style>
</head>
<body>
<main class="page">
  <header class="header">
    <div class="brand"><div class="logo">M</div><div>美太咨询 MA&T<br><span style="font-size:11px;color:#9A94A4;font-weight:500">Management Agent and Talent</span></div></div>
    <div class="meta">学员：{user_name}<br>{company} {job_title}<br>{created_at}</div>
  </header>

  <div class="banner">五维度评估结果不代表能力高低排序，仅反映你当前的特质组合与倾向方向，可作为自我认知和发展规划的参考。</div>

  <section class="hero">
    <div class="hero-top">
      <div class="avatar">{text(main_type)}</div>
      <div>
        <h1>{text(title)}</h1>
        <div class="subtitle">{text(info['en'])} · 第{level}层能力水位 · AI知识测试正确率 {clamp_pct(k_rate)}%</div>
        <div class="desc">{text(info.get("desc"))}</div>
      </div>
    </div>
    <div class="transform">转型方向：{text(info.get("transform"))}</div>
  </section>

  <div class="grid">
    <section class="section">
      <div class="section-title">五维能力雷达图</div>
      <div class="radar-wrap">{radar_svg(dim_scores(result))}</div>
    </section>
    <section class="section">
      <div class="section-title">MAHDI匹配度分析</div>
      {bars(ranked)}
    </section>
  </div>

  <section class="section">
    <div class="section-title">当前AI知识水位</div>
    <div class="note">你目前处于 <strong style="color:{info['color']}">第{level}层 · {text(level_info['label'])}</strong>：{text(level_info['desc'])}</div>
    <div class="level-card">
      {"".join(f'<div class="level {"current" if index + 1 == level else ""}"><strong>{index + 1}</strong><br>{text(item["label"])}</div>' for index, item in enumerate(LEVEL_INFO))}
    </div>
  </section>

  {path_block(info)}

  {learn_block(info)}

  <div class="grid">
    <section class="section">
      <div class="section-title">学习方式偏好</div>
      {style_bars(result)}
    </section>
    <section class="section">
      <div class="section-title">导出说明</div>
      <div class="note">本文件由系统根据你账号下最近一次测评记录生成。若你重新完成测评，再次导出时会使用新的最近记录。</div>
    </section>
  </div>

  {warning_block(result)}
  {motto_block(main_type)}
  <div class="footer">MAHDI AI智能力矩阵报告 · 仅供个人发展参考</div>
</main>
</body>
</html>"""


def render_result_pdf(result: Dict[str, Any]) -> bytes:
    if sys.platform == "win32" and os.environ.get("MAHDI_PDF_RENDER_MODE") != "direct":
        return _render_result_pdf_in_subprocess(result)
    return _render_result_pdf_direct(result)


def _render_result_pdf_direct(result: Dict[str, Any]) -> bytes:
    html = build_report_html(result)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is not installed. Run: python -m pip install playwright") from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": 900, "height": 1200})
            page.set_content(html, wait_until="networkidle")
            return page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "16mm", "right": "14mm", "bottom": "16mm", "left": "14mm"},
            )
        finally:
            browser.close()


def _render_result_pdf_in_subprocess(result: Dict[str, Any]) -> bytes:
    output_path = ""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        output_path = temp_file.name
    env = os.environ.copy()
    env["MAHDI_PDF_RENDER_MODE"] = "direct"
    command = [sys.executable, "-m", "backend.pdf_export", "--output", output_path]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        completed = subprocess.run(
            command,
            input=json.dumps(result, ensure_ascii=False).encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(ROOT),
            env=env,
            creationflags=creationflags,
            timeout=90,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout).decode("utf-8", "replace").strip()
            raise RuntimeError(message or "PDF subprocess failed")
        return Path(output_path).read_bytes()
    finally:
        if output_path:
            try:
                Path(output_path).unlink()
            except FileNotFoundError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    Path(args.output).write_bytes(_render_result_pdf_direct(payload))


if __name__ == "__main__":
    main()
