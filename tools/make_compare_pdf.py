#!/usr/bin/env python3
"""生成「原版报告 vs AI 生成报告」左右对比 PDF。"""
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "output" / "pdf" / "对比报告_原版vs生成.pdf"
GEN_MD = BASE / "output" / "20260601-1XXXX_解析报告.md"

FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT = "CJK"
pdfmetrics.registerFont(TTFont(FONT, FONT_PATH))
pdfmetrics.registerFontFamily(
    FONT,
    normal=FONT,
    bold=FONT,
    italic=FONT,
    boldItalic=FONT,
)

CHAR_FIX = {"⌀": "φ"}


def norm_line(line: str):
    s = line.strip()
    if not s:
        return None
    if re.match(r"^\|?[\s:|-]+\|?$", s):
        return None
    if s.startswith("# "):
        return None
    s = s.replace("**", "")
    if s.startswith("- "):
        s = "· " + s[2:]
    if s.startswith("|") and s.endswith("|"):
        cells = [c.strip() for c in s.strip("|").split("|")]
        s = " ｜ ".join(cells)
    for k, v in CHAR_FIX.items():
        s = s.replace(k, v)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s


def clean_lines(lines):
    out = []
    for line in lines:
        n = norm_line(line)
        if n:
            out.append(n)
    return out


def parse_generated():
    text = GEN_MD.read_text(encoding="utf-8")
    lines = text.splitlines()
    pre, sections, cur = [], {}, None
    footnote = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            break
        if line.strip() and not line.startswith("# "):
            pre.append(line)
        i += 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("## "):
            cur = line[3:].strip()
            sections[cur] = []
        elif cur is not None:
            sections[cur].append(line)
        i += 1
    for key in sections:
        kept = []
        for line in sections[key]:
            if line.strip().startswith("注："):
                footnote = line.strip()
            else:
                kept.append(line)
        sections[key] = kept
    return clean_lines(pre), {k: clean_lines(v) for k, v in sections.items()}, footnote


ORIG_HEAD = [
    "来源文件：20260601-1XXXX.pdf。名称：CSP_箱体组件；编码：20204036；重量：6.06 kg；图纸比例：1:2。",
    "范围限制：源 PDF 实际仅含 1 页，标题栏标注“第 1 页，共 7 页”。以下为该总览页的图面识别结果，完整加工尺寸须结合其余图页及引用的 3D 数据。",
]

ORIG = {
    "一、尺寸及公差": [
        "吊耳孔：直径 12，3 处",
        "拉涨堵头：直径 16 mm × 1 件；直径 18 mm × 5 件",
        "绝缘膜厚度：PI 基材 0.075 mm；胶厚 0.025 mm；总厚 T=0.1 mm",
        "未注倒圆角：R0.5",
        "顶针位置：必须低于产品可见平面，图纸标注 ≤0.2 mm",
        "螺纹精度：按 6H 加工；本页未标具体螺纹规格",
        "绝缘膜未注尺寸公差：GB/T 1804-2008，m 级",
        "本页未给出箱体长、宽、高及完整孔位尺寸；未注特征和尺寸要求参考 3D。",
    ],
    "二、材料及组成": [
        "SIT20201766：CSP_箱体零件 / AlSi12Fe 铝合金，1",
        "SIT20253690：PI 绝缘膜，0.075 mm 基材 + 0.025 mm 胶，1",
        "SIT20253691：PI 绝缘膜，0.075 mm 基材 + 0.025 mm 胶，1",
        "21020582：水嘴保护套；未注明材质，1",
        "SIT32010523：直径 16 mm 拉涨堵头；未注明材质，1",
        "SIT32010718：直径 18 mm 拉涨堵头；未注明材质，5",
        "组件标题栏“材料”为“/”，具体材料以明细表为准。",
    ],
    "三、工艺及检验要求": [
        "箱体压铸及加工：按《SIT0045004 压铸件通用供货技术协议》执行；外观要求抛丸，不允许周边毛刺、利边。孔隙率等未尽要求按该协议执行。",
        "堵头装配：采用拉胀式堵头装配工艺，装配及检验按《SIT00060545 拉胀式堵头装配工艺技术协议》执行。",
        "密封检测：水道采用氦检，按《SIT0045003》；壳体密封检测按《SIT0045010》执行。",
        "密封面：不得有油污、脱模剂等有机杂质；表面能要求按《SIT0045011 点胶件表面能通用供货技术协议》执行。",
        "螺纹检验：前三个螺牙不得破牙，全螺纹允许一个破牙，并须满足通止规检验要求。",
        "绝缘膜性能：阻燃等级 UL94 V0；长期耐热 ≥135℃ 不变形；击穿电压 >5000 V；体积电阻 50 MΩ·cm；吸水率 <2%。其他要求按《SIT0070003 绝缘材料检验规范》。",
        "绝缘膜外观：表面平整，无破损、水渍、开裂褶皱、明显可见霉斑及脏污，不得出现烧焦或发黄痕迹。",
        "清洁度：按《SIT0045015 清洁度检测通用技术协议》执行。",
        "环保：按《SIT0070104 汽车禁用物质要求》；箱体及堵头要求满足 A02 版并提供 ELV（按 2000/53/EC）检测报告，其他部分提供符合性声明；绝缘膜材料须满足最新版的“全部市场”要求。",
        "追溯标识：二维码按《SIT00060522 联合动力来料标识要求规范》执行。",
        "特性标记：★ 为关键特性；◇ 为重要特性。",
    ],
    "四、待补充确认": [
        "1. 补齐其余 6 页及 3D 数据，确认完整外形、孔位、水道、螺纹规格与对应公差。",
        "2. 本页引用的企业标准正文未随文件提供，密封、表面能、清洁度等具体检测阈值无法由本页补全。",
        "3. 绝缘膜技术要求写明设计厚度 0.075 mm，明细表另列基材 0.075 mm、胶厚 0.025 mm、总厚 0.1 mm；验收时需区分基材厚度与含胶总厚度。",
    ],
}


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    gen_head, gen_sections, footnote = parse_generated()

    st_title = ParagraphStyle("title", fontName=FONT, fontSize=16, leading=22, spaceAfter=2 * mm)
    st_sub = ParagraphStyle("sub", fontName=FONT, fontSize=9, leading=13, textColor=colors.HexColor("#666666"), spaceAfter=4 * mm)
    st_section = ParagraphStyle("section", fontName=FONT, fontSize=12, leading=16, spaceBefore=3 * mm, spaceAfter=1.5 * mm)
    st_colhead = ParagraphStyle("colhead", fontName=FONT, fontSize=10, leading=14, alignment=1)
    st_cell = ParagraphStyle("cell", fontName=FONT, fontSize=8.5, leading=12.5)

    doc = SimpleDocTemplate(str(OUT), pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm, leftMargin=14 * mm, rightMargin=14 * mm)
    col_w = (A4[0] - 28 * mm - 2 * mm) / 2
    story = [
        Paragraph("图纸识别报告 — 原版 vs AI 生成", st_title),
        Paragraph("左栏为参考报告（原版），右栏为系统按提示词生成的报告。", st_sub),
    ]

    def add_block(title, left_lines, right_lines):
        story.append(Paragraph(title, st_section))
        header = [Paragraph("原版报告", st_colhead), Paragraph("AI 生成报告", st_colhead)]
        row = [Paragraph("<br/>".join(left_lines), st_cell), Paragraph("<br/>".join(right_lines), st_cell)]
        t = Table([header, row], colWidths=[col_w, col_w], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9cdd4")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f3f5")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 1.5 * mm))

    add_block("头部信息 / 范围限制", ORIG_HEAD, gen_head)
    for title in ["一、尺寸及公差", "二、材料及组成", "三、工艺及检验要求", "四、待补充确认"]:
        add_block(title, ORIG[title], gen_sections.get(title, []))
    if footnote:
        story.append(Paragraph(norm_line(footnote) or footnote, st_cell))

    doc.build(story)
    print("已生成:", OUT)


if __name__ == "__main__":
    main()
