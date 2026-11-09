#!/usr/bin/env python3
"""Render supplied public school research without fetching, estimating or changing it.

Default output: this script's directory. Use --output-dir for isolated contract checks.
Only Python's standard library is used. Missing/invalid input never falls back to old data.
"""
from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CANONICAL = "https://tyhcch1234.github.io/sai-kung-primary-schools/"
TITLE = "西貢區小學全景資料｜實際人數・升中去向・社交平台・P5/P6招生策略"
DESCRIPTION = "按西貢行政區研究範圍分類整理小學資料：逐校實際學生人數與學年、完整公開升中去向、活動、社媒身份核實、來源及缺口；附暫定中學P5/P6招生策略，不以班數推算人數，亦非學校排名。"
UNKNOWN = "未公開／未核實"
LABELS = {
    "id": "ID", "name": "名稱", "english_name": "英文名稱", "category": "類別",
    "website": "學校網站", "profile_url": "學校概覽", "address": "地址", "school_net": "校網",
    "status": "狀態", "scope_note": "研究範圍備註", "checked_date": "核實日期",
    "academic_year": "學年", "total": "全校人數", "grades": "各年級", "grade": "年級",
    "students": "學生人數", "classes": "班數", "p6": "小六人數", "source_ids": "來源ID",
    "note": "備註", "enrolment": "實際人數", "enrolment_history": "歷年人數紀錄",
    "title": "標題", "description": "說明", "tags": "標籤", "year": "年份／學年",
    "activities": "課外與旗艦活動", "destinations": "公開升中去向", "cohort_total": "該屆總人數",
    "coverage": "公布覆蓋範圍", "schools": "學校紀錄", "count": "人數", "percentage": "公布百分比",
    "preferences": "升中取向", "observed": "可觀察證據", "inference": "策略推論（非志願事實）",
    "caveat": "限制", "school_links": "學校關係", "school": "學校", "relationship": "關係",
    "social": "社交平台", "platform": "平台", "account": "帳戶名稱", "url": "網址",
    "verification": "身份核實證據", "contact": "公開聯絡資料", "phone": "電話", "email": "電郵",
    "marketing": "每校宣傳切入建議", "segment": "分群", "priority_rationale": "接觸優先考量",
    "entry_offer": "切入活動／提案", "contact_role": "建議接洽角色", "message": "訊息",
    "channels": "渠道", "caveats": "限制與注意", "sources": "完整來源", "accessed_date": "查閱日期",
    "gaps": "研究缺口", "scope_notes": "涵蓋範圍", "failures": "研究未完成／失敗紀錄",
    "summary": "研究摘要（原始）", "context": "策略情境", "main_conclusion": "主要結論",
    "segments": "宣傳分群", "rationale": "理由", "school_ids": "相關學校", "offer": "切入提案",
    "priority": "接觸次序（非學校排名）", "school_id": "學校ID", "reason": "接觸理由",
    "evidence_gap": "證據缺口", "timeline": "時間線", "period": "時段", "action": "行動",
    "kpi": "量度指標", "content_plan": "渠道內容計劃", "channel": "渠道", "audience": "對象",
    "content": "內容", "cta": "下一步行動", "measurement": "成效量度", "limitations": "策略限制",
    "destinations_history": "歷年升中去向", "verification": "核實標記", "applicability": "小六適用性",
    "reported_students": "原報告人數", "reported_total": "原報告總數", "total_scope": "總數範圍",
    "total_verification": "總數核實狀態", "reported_classes": "來源列班數", "classes_scope": "班數口徑",
    "classes_academic_year": "班數來源學年", "classes_source_ids": "班數來源ID",
    "listed_count_sum": "公開列項人數小計（非全屆分母）",
    "reported_cohort_total": "原研究隊列值（未獨立核實，不採為全屆）",
    "cohort_total_verification": "全屆分母核實狀態",
}


def text(value):
    """Readable representation for every JSON value; retain false and zero."""
    if value is None:
        return UNKNOWN
    if isinstance(value, str):
        return value if value.strip() else "未提供"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def esc(value):
    return html.escape(text(value), quote=True)


def obj(value):
    return value if isinstance(value, dict) else {}


def items(value):
    """Accept a singleton but do not reinterpret/mutate irregular records."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def safe_url(value):
    if not isinstance(value, str) or not value or value != value.strip():
        return None
    if any(ord(char) <= 32 or ord(char) == 127 for char in value) or "\\" in value:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
            return None
        parsed.port  # validate malformed ports
        return value
    except ValueError:
        return None


def external(value, label=None):
    url = safe_url(value)
    caption = value if label is None else label
    if url:
        return f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(caption)}</a>'
    if value is None or value == "":
        return f'<span class="missing">{UNKNOWN}</span>'
    return f'<span>{esc(caption)}</span><small>未提供有效 HTTP(S) 連結：{esc(value)}</small>'


def rich(value):
    """Escape first, then render structured values without unsafe HTML or guesswork."""
    if isinstance(value, dict):
        if not value:
            return '<p class="missing">未提供</p>'
        return '<dl class="kv">' + ''.join(
            f'<dt>{esc(LABELS.get(str(key), str(key)))}</dt><dd class="rich">{rich(val)}</dd>'
            for key, val in value.items() if key not in {"raw_data", "integration"} and not str(key).endswith("_path")) + '</dl>'
    if isinstance(value, list):
        if not value:
            return '<p class="missing">未提供</p>'
        return '<ul>' + ''.join(f'<li class="rich">{rich(val)}</li>' for val in value) + '</ul>'
    if safe_url(value):
        return '<p>' + external(value) + '</p>'
    return f'<p>{esc(value)}</p>'


def number(value):
    """Known numeric counts for coverage/sorting only; never impute or sum."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, str):
        if not re.fullmatch(r"\d+(?:\.\d+)?", value.strip()):
            return None
        value = float(value)
    if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
        return value
    return None


def percentage_number(value):
    if isinstance(value, str) and re.fullmatch(r"\s*\d+(?:\.\d+)?\s*%\s*", value):
        return number(value.strip().removesuffix("%").strip())
    return number(value)


def scalar_id(value):
    if value is None or isinstance(value, (dict, list, bool)):
        return None
    # A numeric source id 7 resolves a reference "7", and vice versa.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def metric_value(value):
    if isinstance(value, dict):
        for key in ("students", "count", "total"):
            if key in value:
                return value[key]
        return None
    return value


def metric_parts(value, parent=None):
    parent = obj(parent)
    record = obj(value)
    return {
        "value": metric_value(value),
        "academic_year": record.get("academic_year", parent.get("academic_year")),
        "academic_year_normalized": record.get("academic_year_normalized"),
        "classes": record.get("classes"),
        "reported_students": record.get("reported_students"),
        "reported_classes": record.get("reported_classes"),
        "classes_scope": record.get("classes_scope"),
        "classes_academic_year": record.get("classes_academic_year", record.get("academic_year", parent.get("academic_year"))),
        "classes_source_ids": record.get("classes_source_ids", record.get("source_ids", parent.get("source_ids"))),
        "verification": record.get("verification"),
        "applicability": record.get("applicability"),
        "source_ids": record.get("source_ids", parent.get("source_ids")),
        "note": record.get("note", parent.get("note")),
    }


def total_parts(enrolment):
    parts = metric_parts(enrolment.get("total"), enrolment)
    parts.update({"verification": enrolment.get("total_verification", parts.get("verification")),
                  "reported_total": enrolment.get("reported_total"),
                  "total_scope": enrolment.get("total_scope")})
    return parts


def unresolved_total(parts):
    status = str(parts.get("verification") or "").lower()
    return "unresolved" in status and "conflict" in status


def normalized_year(parts):
    supplied = parts.get("academic_year_normalized")
    if supplied is not None:
        return text(supplied)
    year = parts.get("academic_year")
    if year is None:
        return None
    match = re.search(r"(?<!\d)(\d{4})\s*[/／–-]\s*(\d{4}|\d{2})(?!\d)", text(year))
    return match.group(1) + "/" + match.group(2)[-2:] if match else text(year).strip()


def p6_identity(parts):
    def canonical(value):
        numeric = number(value)
        return numeric if numeric is not None else text(value)
    return canonical(parts["value"]), normalized_year(parts), canonical(parts.get("classes"))


def observed_destination(destination):
    return obj(destination).get("record_type") != "policy_or_permission_not_observed_distribution"


def grade_code(value):
    """P/小 labels only. Do not equate international Grade/Year stages to P6."""
    if not isinstance(value, str):
        return None
    value = value.strip().upper().replace(" ", "")
    match = re.fullmatch(r"P([1-6])", value)
    if match:
        return "P" + match.group(1)
    chinese = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"}
    match = re.fullmatch(r"小([一二三四五六1-6])(?:年級)?", value)
    return "P" + chinese.get(match.group(1), match.group(1)) if match else None


class FaviconReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and "icon" in attrs.get("rel", "").split() and self.href is None:
            self.href = attrs.get("href")


def read_favicon():
    path = ROOT / "index.html"
    if not path.exists():
        raise ValueError("找不到原 index.html，無法保留原 favicon。")
    parser = FaviconReader()
    parser.feed(path.read_text(encoding="utf-8"))
    if not parser.href:
        raise ValueError("原 index.html 未找到 favicon；停止產生，請先恢復原頁。")
    return parser.href


class Renderer:
    def __init__(self, data, strategy):
        self.data = data
        self.strategy = strategy
        self.schools = data["schools"]
        self.index = []
        self.unresolved = []
        self.warnings = []
        self.source_cache = {}
        self.school_refs = {}
        self.used_slugs = set()
        for key, school in enumerate(self.schools):
            school_obj = obj(school)
            sid = scalar_id(school_obj.get("id"))
            slug = self.slug(school_obj.get("id"), key)
            if sid is not None:
                self.school_refs.setdefault(sid, []).append((slug, school_obj.get("name")))
            self.source_cache[key] = self.collect_sources(school_obj.get("sources"))
            grades = [obj(grade) for grade in items(obj(school_obj.get("enrolment")).get("grades"))]
            e = obj(school_obj.get("enrolment"))
            p6_entries = self.p6_entries(e)
            sort_values = [number(entry["value"]) for entry in p6_entries]
            known_values = [value for value in sort_values if value is not None]
            total = total_parts(e)
            destination = obj(school_obj.get("destinations"))
            destination_records = [destination] + items(school_obj.get("destinations_history"))
            names = list(dict.fromkeys(text(obj(receiver).get("name")) for d in destination_records if observed_destination(d) for receiver in items(obj(d).get("schools"))))
            self.index.append({
                "key": key, "id": school_obj.get("id"), "slug": slug,
                "name": text(school_obj.get("name")), "category": text(school_obj.get("category")),
                "search": " ".join([text(school_obj.get("name")), text(school_obj.get("english_name")),
                                      text(school_obj.get("activities")), " ".join(names)]),
                "p6_known": bool(known_values),
                "p6_sort": known_values[0] if len(p6_entries) == 1 and len(known_values) == 1 else None,
                "total_sort": None if unresolved_total(total) else number(total["value"]),
                "any_enrolment": (not unresolved_total(total) and number(total["value"]) is not None) or bool(known_values) or any(number(g.get("students")) is not None for g in grades),
                "any_grades": any(number(g.get("students")) is not None for g in grades),
                "any_destinations": observed_destination(destination) and any(number(obj(receiver).get("count")) is not None or percentage_number(obj(receiver).get("percentage")) is not None for receiver in items(destination.get("schools"))),
                "destination_counts": observed_destination(destination) and any(number(obj(receiver).get("count")) is not None for receiver in items(destination.get("schools"))),
                "destination_names": names,
            })
            if not isinstance(school, dict):
                self.warnings.append(f"學校紀錄 {key + 1} 不是物件，保留為不規則原始紀錄。")
            if len(p6_entries) > 1:
                self.warnings.append(f"{text(school_obj.get('name'))} 有多條獨立／年級小六紀錄；全部顯示，不合計，排序值保留未知。")

    def slug(self, sid, key):
        if scalar_id(sid) is None:
            stem = f"record-{key + 1}"
        else:
            raw = scalar_id(sid)
            stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-")[:72]
            if not stem or stem != raw:
                stem = (stem or "id") + "-" + hashlib.sha256(raw.encode()).hexdigest()[:10]
        slug = "school-" + stem
        if slug in self.used_slugs:
            slug += f"-record-{key + 1}"
            self.warnings.append(f"重複學校ID：{text(sid)}；保留各原始紀錄並建立不同錨點。")
        self.used_slugs.add(slug)
        return slug

    def collect_sources(self, value):
        sources = []
        if isinstance(value, dict) and "id" not in value and "url" not in value and "title" not in value:
            source_values = list(value.items())
        else:
            source_values = [(None, entry) for entry in items(value)]
        for fallback_id, source in source_values:
            source_obj = obj(source)
            sid = source_obj.get("id", fallback_id)
            sources.append({"id": sid, "record": source, "lookup": scalar_id(sid)})
        return sources

    def refs(self, key, refs, context=""):
        output = []
        for ref in items(refs):
            # Tolerate an object containing id, but never stringify it as an index key.
            sid = scalar_id(obj(ref).get("id")) if isinstance(ref, dict) else scalar_id(ref)
            matches = [(i, source) for i, source in enumerate(self.source_cache[key]) if sid is not None and source["lookup"] == sid]
            if not matches:
                output.append(f'<span class="source-missing">來源 {esc(ref)}：未能對應</span>')
                entry = {"school": self.index[key]["name"], "source_id": ref, "context": context}
                if entry not in self.unresolved:
                    self.unresolved.append(entry)
                continue
            for source_key, source in matches:
                source_obj = obj(source["record"])
                label = f"來源 {text(ref)}"
                title = text(source_obj.get("title"))
                url = safe_url(source_obj.get("url"))
                href = url or f"#source-{key}-{source_key}"
                output.append(f'<a class="source-ref" href="{esc(href)}" title="{esc(title)}"' +
                              (' target="_blank" rel="noopener noreferrer"' if url else '') + f'>{esc(label)}</a>')
        if not output:
            return '<span class="source-refs missing">未附來源ID</span>'
        return '<span class="source-refs">' + " ".join(output) + '</span>'

    def metric(self, key, parts, classes=False, extra_note=None):
        value = parts["value"]
        if parts.get("applicability") == "not_a_standard_primary_P6":
            rendered_value = "不適用（非標準小六學制）"
        elif unresolved_total(parts):
            reported = parts.get("reported_total")
            rendered_value = f'原表列{esc(value if reported is None else reported)}（總數有矛盾）'
        else:
            rendered_value = esc(value) if not isinstance(value, (dict, list)) else rich(value)
        output = f'<span class="value">{rendered_value}</span><small>學年：{esc(parts["academic_year"])}</small>'
        if classes:
            output += self.class_metric(key, parts, small=True)
        output += self.refs(key, parts.get("source_ids"), "人數／班數")
        for field, label in (("verification", "核實標記"), ("applicability", "小六適用性"), ("total_scope", "總數範圍"), ("reported_total", "原報告總數"), ("reported_students", "原報告人數")):
            if parts.get(field) is not None:
                output += f'<small class="metric-qualification">{label}：{esc(parts[field])}</small>'
        note = parts.get("note")
        if note is not None and note != "":
            output += '<div class="metric-note rich small">' + rich(note) + '</div>'
        if extra_note:
            output += f'<small>{esc(extra_note)}</small>'
        return output

    def class_metric(self, key, parts, small=False):
        year = parts.get("classes_academic_year")
        if parts.get("classes_scope") == "average_not_grade_actual":
            caption = f'來源列平均{esc(parts.get("reported_classes"))}班，非本級實際班數；' + ("班數年份未明" if year is None else f'班數學年：{esc(year)}')
        else:
            caption = f'班數：{esc(parts.get("classes"))}（獨立資料，不推算人數）；班數學年：{esc(year)}'
        output = f'<div class="class-count{" small" if small else ""}">{caption}'
        if parts.get("classes_scope") is not None:
            output += f'<small>班數口徑：{esc(parts["classes_scope"])}</small>'
        return output + self.refs(key, parts.get("classes_source_ids", parts.get("source_ids")), "年級班數") + '</div>'

    def grade_entries(self, enrolment, code):
        return [entry for entry in items(enrolment.get("grades")) if isinstance(entry, dict) and grade_code(entry.get("grade")) == code]

    def p6_entries(self, enrolment):
        output = []
        if enrolment.get("p6") is not None:
            output.append(metric_parts(enrolment["p6"], enrolment))
        for grade in self.grade_entries(enrolment, "P6"):
            parts = metric_parts({"students": grade.get("students"), **grade}, enrolment)
            # Same value/year/classes is one fact even if notes/sources differ; p6 wins.
            if not any(p6_identity(parts) == p6_identity(existing) for existing in output):
                output.append(parts)
        return output

    def roster_row(self, key):
        school = obj(self.schools[key])
        entry = self.index[key]
        e = obj(school.get("enrolment"))
        output = f'<tr data-school-key="{key}"><th scope="row"><a href="#{entry["slug"]}">{esc(school.get("name"))}</a><small>{esc(school.get("english_name"))}</small></th>'
        output += f'<td>{esc(school.get("category"))}<small>狀態：{esc(school.get("status"))}</small></td><td>{esc(e.get("academic_year"))}<small>各項如有另列學年，以該項為準</small></td>'
        output += '<td class="numeric">' + self.metric(key, total_parts(e)) + '</td>'
        for code in ("P1", "P2", "P3", "P4", "P5", "P6"):
            entries = self.p6_entries(e) if code == "P6" else [metric_parts(grade, e) for grade in self.grade_entries(e, code)]
            if not entries:
                entries = [metric_parts(None, {"academic_year": e.get("academic_year")})]
            output += f'<td class="numeric{" p6-cell" if code == "P6" else ""}">'
            output += '<hr>'.join(self.metric(key, parts, classes=True, extra_note="不同紀錄分開呈現，不相加" if len(entries) > 1 else None) for parts in entries)
            output += '</td>'
        return output + '</tr>'

    def sources(self, key):
        output = '<ol class="source-list">'
        for source_key, entry in enumerate(self.source_cache[key]):
            source = obj(entry["record"])
            output += f'<li id="source-{key}-{source_key}" tabindex="-1"><b>來源 {esc(entry["id"])}</b> — '
            if source:
                output += external(source.get("url"), source.get("title"))
                output += f'<small>學年：{esc(source.get("academic_year"))} · 查閱：{esc(source.get("accessed_date"))}</small>'
                extras = {k: v for k, v in source.items() if k not in {"id", "title", "url", "academic_year", "accessed_date"}}
                if extras:
                    output += rich(extras)
            else:
                output += rich(entry["record"])
            output += '</li>'
        if not self.source_cache[key]:
            output += '<li class="missing">未提供来源紀錄</li>'
        return output + '</ol>'

    def social_groups(self, school):
        grouped = {"Facebook": [], "Instagram": [], "小紅書": [], "其他平台": []}
        aliases = {"facebook": "Facebook", "fb": "Facebook", "instagram": "Instagram", "ig": "Instagram", "xiaohongshu": "小紅書", "xhs": "小紅書", "小紅書": "小紅書", "小红书": "小紅書", "rednote": "小紅書"}
        value = school.get("social")
        if isinstance(value, dict) and "platform" not in value:
            records = []
            for platform, record in value.items():
                for item in items(record):
                    if isinstance(item, dict):
                        records.append({"platform": platform, **item})
                    else:
                        # Legacy/malformed URL alone is never considered official.
                            records.append({"platform": platform, "url": item, "status": "原始紀錄未提供核實狀態", "verification": None})
        else:
            records = items(value)
        for record in records:
            platform = text(obj(record).get("platform_normalized") or obj(record).get("platform"))
            group = aliases.get(platform.strip().lower(), "其他平台")
            grouped[group].append(record)
        return grouped

    def social_entry(self, key, record, display_platform=False):
        if not isinstance(record, dict):
            return '<div class="social-entry rich">不規則社媒紀錄：' + rich(record) + '</div>'
        output = '<div class="social-entry">'
        if display_platform:
            output += f'<b>{esc(record.get("platform"))}</b><br>'
        output += external(record.get("url"), record.get("account") if record.get("account") is not None else record.get("url"))
        output += '<small>狀態：' + esc(record.get("status")) + '</small>'
        output += '<div class="identity rich">身份核實證據：' + rich(record.get("verification")) + '</div>'
        output += self.refs(key, record.get("source_ids"), "社媒身份")
        extras = {k: v for k, v in record.items() if k not in {"platform", "account", "url", "status", "verification", "source_ids"}}
        if extras:
            output += rich(extras)
        return output + '</div>'

    def social_cell(self, key, records, other=False):
        if not records:
            return '<span class="missing">未提供已核實帳戶／未找到紀錄</span><div class="identity">身份證據：未提供；不代表學校沒有帳戶。</div>'
        return ''.join(self.social_entry(key, record, other) for record in records)

    def social_row(self, key):
        school = obj(self.schools[key])
        groups = self.social_groups(school)
        output = f'<tr data-school-key="{key}"><th scope="row"><a href="#{self.index[key]["slug"]}">{esc(school.get("name"))}</a><small>核實：{esc(school.get("checked_date"))}</small></th>'
        for name, entries in groups.items():
            output += '<td>' + self.social_cell(key, entries, name == "其他平台") + '</td>'
        return output + '</tr>'

    def destination(self, key, overview=False):
        school = obj(self.schools[key])
        output = ''
        if overview:
            output += f'<article class="destination-block" data-school-key="{key}"><h3><a href="#{self.index[key]["slug"]}">{esc(school.get("name"))}</a></h3>'
        records = [("主要去向紀錄", school.get("destinations"))] + [("歷年獨立去向紀錄", record) for record in items(school.get("destinations_history"))]
        for label, record in records:
            output += '<section class="destination-cohort"><h4>' + label + '（各屆分開，不合計）</h4>' + self.destination_record(key, record) + '</section>'
        return output + ('</article>' if overview else '')

    def destination_record(self, key, destination_value):
        d = obj(destination_value)
        entries = items(d.get("schools"))
        observed = observed_destination(d)
        output = '' if observed else '<p class="note-box warning">政策／獲準升讀對象，非已觀察實際去向；不納入實際接收中學搜尋或數字覆蓋。</p>'
        output += '<div class="destination-meta">'
        output += f'<span>學年：<b>{esc(d.get("academic_year"))}</b></span><span>該屆總人數：<b>{esc(d.get("cohort_total"))}</b></span></div>'
        output += '<div class="note-box rich"><b>公布覆蓋範圍：</b>' + rich(d.get("coverage")) + '<b>資料備註：</b>' + rich(d.get("note")) + self.refs(key, d.get("source_ids"), "去向整體") + '</div>'
        output += '<div class="tablewrap" tabindex="0" role="region" aria-label="接收中學完整公開紀錄"><table><caption>全部已提供接收中學紀錄；不是第一志願或完整分佈的推定</caption><thead><tr><th scope="col">接收中學</th><th scope="col">學年</th><th scope="col">人數</th><th scope="col">公布百分比</th><th scope="col">備註與來源</th></tr></thead><tbody>'
        for receiver in entries:
            r = obj(receiver)
            name = r.get("name") if r else receiver
            row_attribute = f' data-destination="{esc(name)}"' + ('' if observed else ' data-observed="false"')
            output += f'<tr{row_attribute}><th scope="row">{esc(name)}</th><td>{esc(r.get("academic_year", d.get("academic_year")))}</td><td>{esc(r.get("count"))}</td><td>{esc(r.get("percentage"))}</td><td class="rich">{rich(r.get("note"))}{self.refs(key, r.get("source_ids"), "接收中學")}'
            extras = {k: v for k, v in r.items() if k not in {"name", "academic_year", "count", "percentage", "note", "source_ids"}}
            if extras:
                output += rich(extras)
            output += '</td></tr>'
        if not entries:
            output += f'<tr><td colspan="5" class="missing">{UNKNOWN}；未提供接收中學紀錄。</td></tr>'
        output += '</tbody></table></div>'
        extras = {k: v for k, v in d.items() if k not in {"academic_year", "cohort_total", "coverage", "note", "schools", "source_ids"}}
        if extras:
            output += rich(extras)
        if destination_value is not None and not isinstance(destination_value, dict):
            output += '<div class="rich">不規則原始去向紀錄：' + rich(destination_value) + '</div>'
        return output

    def enrolment_detail(self, key, history=False, override=None):
        school = obj(self.schools[key])
        value = override if history else school.get("enrolment")
        e = obj(value)
        heading = '歷年獨立紀錄：' + text(e.get('academic_year')) if history else '實際學生人數與班數'
        output = '<h3>' + esc(heading) + '</h3><div class="note-box">人數只使用研究輸入的實際紀錄。P1–P6 不涵蓋所有學制；其他年級按原標籤列出，不強行換算。班數不得乘班額估算人數。</div>'
        output += '<div class="grid2"><div class="card"><b>全校人數</b>' + self.metric(key, total_parts(e)) + '</div><div class="card p6-cell"><b>小六人數</b>'
        p6 = self.p6_entries(e) or [metric_parts(None, {"academic_year": e.get("academic_year")})]
        output += '<hr>'.join(self.metric(key, parts, True, "獨立紀錄，不合計" if len(p6) > 1 else None) for parts in p6) + '</div></div>'
        output += '<div class="tablewrap" tabindex="0" role="region" aria-label="所有原始年級的人數與班數"><table><caption>全部原始年級紀錄（不截斷、不轉換學制）</caption><thead><tr><th scope="col">原始年級</th><th scope="col">學生人數／學年／來源</th><th scope="col">班數／學年／來源</th><th scope="col">學制與備註</th></tr></thead><tbody>'
        grades = items(e.get("grades"))
        for grade in grades:
            g = obj(grade)
            year = g.get("academic_year", e.get("academic_year"))
            parts = metric_parts(g, e)
            parts["note"] = None
            output += f'<tr><th scope="row">{esc(g.get("grade") if g else grade)}</th><td>' + self.metric(key, parts) + '</td><td>'
            output += self.class_metric(key, parts) + '</td><td class="rich">' + rich(g.get("note"))
            extras = {k: v for k, v in g.items() if k not in {"grade", "students", "classes", "academic_year", "source_ids", "note"}}
            if extras:
                output += rich(extras)
            output += '</td></tr>'
        if not grades:
            output += '<tr><td colspan="4" class="missing">未提供各年級紀錄</td></tr>'
        output += '</tbody></table></div><div class="rich">全校人數備註：' + rich(e.get("note")) + self.refs(key, e.get("source_ids"), "人數整體") + '</div>'
        extras = {k: v for k, v in e.items() if k not in {"academic_year", "total", "grades", "p6", "source_ids", "note"}}
        if extras:
            output += rich(extras)
        if value is not None and not isinstance(value, dict):
            output += '<div class="rich">不規則人數紀錄：' + rich(value) + '</div>'
        if not history:
            output += '<h4>歷年紀錄（逐年分開，不跨年相加）</h4>'
            records = items(school.get("enrolment_history"))
            if records:
                output += ''.join(self.enrolment_detail(key, history=True, override=record) for record in records)
            else:
                output += '<p class="missing">未提供歷年人數紀錄</p>'
        return output

    def source_field(self, key, value, fields, context):
        """Render a sourced object; never hide malformed or additional fields."""
        if not isinstance(value, dict):
            return '<div class="rich">' + rich(value) + '</div>'
        output = '<dl class="kv">'
        for field in fields:
            output += f'<dt>{esc(LABELS.get(field, field))}</dt><dd class="rich">{rich(value.get(field))}</dd>'
        output += '</dl>' + self.refs(key, value.get("source_ids"), context)
        extras = {k: v for k, v in value.items() if k not in set(fields) | {"source_ids"}}
        return output + (rich(extras) if extras else '')

    def school_card(self, key):
        s = obj(self.schools[key])
        entry = self.index[key]
        output = f'<details class="school-card" id="{entry["slug"]}" data-school-key="{key}"><summary>{esc(s.get("name"))}<span class="summary-meta">{esc(s.get("english_name"))} · {esc(s.get("category"))} · 核實：{esc(s.get("checked_date"))}</span></summary><div class="school-body">'
        output += f'<a class="permalink" href="#{entry["slug"]}">此校深連結</a><div class="section-links">' + external(s.get("website"), "學校官網") + external(s.get("profile_url"), "學校概覽") + '</div>'
        output += '<dl class="kv">' + ''.join(f'<dt>{esc(LABELS[field])}</dt><dd class="rich">{rich(s.get(field))}</dd>' for field in ("address", "school_net", "status", "scope_note", "checked_date")) + '</dl>'
        output += self.enrolment_detail(key)
        output += '<h3>課外與旗艦活動</h3>'
        activities = items(s.get("activities"))
        for activity in activities:
            a = obj(activity)
            output += '<div class="activity">'
            if a:
                output += f'<h4>{esc(a.get("title"))}</h4><small>年份／學年：{esc(a.get("year"))}</small><div class="rich">' + rich(a.get("description")) + '</div><div class="tags">'
                output += ''.join(f'<span class="pill">{esc(tag)}</span>' for tag in items(a.get("tags"))) + '</div>' + self.refs(key, a.get("source_ids"), "課外活動")
                extras = {k: v for k, v in a.items() if k not in {"title", "year", "description", "tags", "source_ids"}}
                if extras:
                    output += rich(extras)
            else:
                output += rich(activity)
            output += '</div>'
        if not activities:
            output += '<p class="missing">未提供已核實活動紀錄</p>'
        output += '<h3>升中取向：觀察、推論與限制分開</h3>' + self.source_field(key, s.get("preferences"), ("observed", "inference", "caveat"), "升中取向")
        output += '<h3>一條龍／聯繫／其他學校關係</h3>'
        links = items(s.get("school_links"))
        output += ''.join('<div class="activity">' + self.source_field(key, link, ("school", "relationship", "note"), "學校關係") + '</div>' for link in links) if links else '<p class="missing">未提供已核實關係紀錄；不代表沒有關係。</p>'
        output += '<h3>公開升中去向</h3>' + self.destination(key)
        output += '<h3>社交平台與身份證據</h3>'
        output += '<p class="sub">保留研究原始狀態；官方已核實、校友會、第三方與待核實帳戶不可互相替代。</p>'
        for platform, records in self.social_groups(s).items():
            output += f'<h4>{esc(platform)}</h4>' + self.social_cell(key, records, platform == "其他平台")
        output += '<h3>公開聯絡資料</h3>' + self.source_field(key, s.get("contact"), ("phone", "email"), "聯絡資料")
        output += '<h3>每校宣傳切入建議（暫定中學P5/P6招生情境）</h3><p class="sub">研究建議不代表學校願意合作；接觸優先次序非學校質素排名，未對外聯絡。</p>'
        output += self.source_field(key, s.get("marketing"), ("segment", "priority_rationale", "entry_offer", "contact_role", "message", "channels", "caveats"), "每校宣傳建議")
        output += '<h3>完整來源</h3><p>此校來源列於<a href="#sources-' + str(key) + '">全站來源區</a>（所有來源，不截斷）。</p>'
        # Source anchors are owned by the central list; inline copy has no duplicate ids.
        output += '<ul class="source-list">'
        for source_key, source in enumerate(self.source_cache[key]):
            so = obj(source["record"])
            output += f'<li><a href="#source-{key}-{source_key}">來源 {esc(source["id"])}</a> — ' + (external(so.get("url"), so.get("title")) if so else rich(source["record"])) + f'<small>學年：{esc(so.get("academic_year"))} · 查閱：{esc(so.get("accessed_date"))}</small></li>'
        output += '</ul>' if self.source_cache[key] else '<li class="missing">未提供來源紀錄</li></ul>'
        output += '<h3>研究缺口</h3><div class="rich">' + rich(s.get("gaps")) + '</div>'
        known = {"id", "name", "english_name", "category", "website", "profile_url", "address", "school_net", "status", "scope_note", "checked_date", "enrolment", "enrolment_history", "activities", "preferences", "school_links", "destinations", "destinations_history", "social", "contact", "marketing", "sources", "gaps", "raw_data", "integration"}
        extras = {field: value for field, value in s.items() if field not in known and not field.endswith("_path")}
        if extras:
            output += '<h3>附加研究資料</h3><div class="rich">' + rich(extras) + '</div>'
        output += f'<details class="raw-record js-only" data-school-key="{key}"><summary>檢視此校完整原始JSON（包含額外／不規則欄位）</summary><pre></pre></details>'
        return output + '</div></details>'

    def school_links(self, value):
        output = []
        for sid in items(value):
            ref = scalar_id(sid)
            matches = self.school_refs.get(ref, [])
            if matches:
                output.extend(f'<a href="#{slug}">{esc(name)}</a>' for slug, name in matches)
            else:
                output.append(f'<span class="source-missing">學校ID {esc(sid)}：未能對應</span>')
                warning = f"策略中的學校ID {text(sid)} 未能對應；未擅自替換。"
                if warning not in self.warnings:
                    self.warnings.append(warning)
        return '、'.join(output) or '<span class="missing">未提供</span>'

    def strategy_html(self):
        s = self.strategy
        output = '<div class="note-box warning">暫定情境：中學面向P5/P6家庭及小學的招生／升中支援。以下是策略提案，不是學校排名，也不是對家長第一志願的判定；情境應由委託方確認。未對外聯絡。</div>'
        output += '<h3>情境與主要結論</h3><div class="rich">' + rich(s.get("context")) + rich(s.get("main_conclusion")) + '</div><h3>分群與切入</h3><div class="segments">'
        for segment in items(s.get("segments")):
            sg = obj(segment)
            output += '<article class="card">'
            if sg:
                output += f'<h4>{esc(sg.get("name"))}</h4><div class="rich">' + rich({LABELS[field]: sg.get(field) for field in ("rationale", "offer", "message", "channels")}) + '</div><p>相關學校：' + self.school_links(sg.get("school_ids")) + '</p>'
                extras = {k: v for k, v in sg.items() if k not in {"name", "rationale", "offer", "message", "channels", "school_ids"}}
                if extras:
                    output += rich(extras)
            else:
                output += rich(segment)
            output += '</article>'
        if not items(s.get("segments")):
            output += '<p class="missing">未提供策略分群</p>'
        output += '</div><h3>接觸優先考量（非學校排名）</h3><ol>'
        for priority in items(s.get("priority")):
            p = obj(priority)
            output += '<li>' + (self.school_links(p.get("school_id")) + '<div class="rich">' + rich({"reason": p.get("reason"), "evidence_gap": p.get("evidence_gap")}) + '</div>' if p else rich(priority)) + '</li>'
            extras = {k: v for k, v in p.items() if k not in {"school_id", "reason", "evidence_gap"}}
            if extras:
                output += '<li class="rich">' + rich(extras) + '</li>'
        output += '</ol><h3>時間線</h3>' + self.strategy_table(s.get("timeline"), ("period", "action", "kpi"), "timeline", "提案時間線與KPI")
        output += '<h3>渠道與內容</h3>' + self.strategy_table(s.get("content_plan"), ("channel", "audience", "content", "cta"), "content-table", "渠道、受眾、內容與下一步")
        output += '<h3>成效量度</h3><div class="rich">' + rich(s.get("measurement")) + '</div><h3>策略限制</h3><div class="rich">' + rich(s.get("limitations")) + '</div>'
        extras = {k: v for k, v in s.items() if k not in {"context", "main_conclusion", "segments", "priority", "timeline", "content_plan", "measurement", "limitations"}}
        if extras:
            output += '<h3>額外原始策略資料</h3><div class="rich">' + rich(extras) + '</div>'
        return output

    def strategy_table(self, values, fields, classname, caption):
        output = f'<div class="tablewrap" tabindex="0" role="region" aria-label="{esc(caption)}"><table class="{classname}"><caption>{esc(caption)}</caption><thead><tr>'
        output += ''.join(f'<th scope="col">{esc(LABELS[field])}</th>' for field in fields) + '<th scope="col">額外資料</th></tr></thead><tbody>'
        for value in items(values):
            record = obj(value)
            if record:
                output += '<tr>' + ''.join('<td class="rich">' + rich(record.get(field)) + '</td>' for field in fields)
                output += '<td class="rich">' + rich({k: v for k, v in record.items() if k not in fields}) + '</td></tr>'
            else:
                output += f'<tr><td colspan="{len(fields) + 1}" class="rich">{rich(value)}</td></tr>'
        if not items(values):
            output += f'<tr><td colspan="{len(fields) + 1}" class="missing">未提供</td></tr>'
        return output + '</tbody></table></div>'

    def coverage_kpis(self):
        summary = obj(self.data.get("summary"))
        definitions = obj(summary.get("definitions"))
        specs = [
            ("verified_total_count", "有已核實小學總數的學校", sum(entry["total_sort"] is not None for entry in self.index), "有全校實際人數的學校", "不同學年不能相加"),
            ("verified_grade_count", "有已核實年級實數的學校", sum(entry["any_grades"] for entry in self.index), "有年級實際人數的學校", "至少一級，不代表六級全齊"),
            ("verified_p6_count", "有已核實小六在籍實數的學校", sum(entry["p6_known"] for entry in self.index), "有已知小六人數的學校", "不等同畢業／派位人數"),
            ("verified_destinations_count", "有校名的已報道升學結果", sum(entry["any_destinations"] for entry in self.index), "有去向數字的學校", "含百分比，不代表逐校人數；非志願"),
            ("verified_destination_school_counts_count", "有接收中學逐校人數的學校", sum(entry["destination_counts"] for entry in self.index), "有接收中學逐校人數的學校", "百分比不是人數；非完整分佈"),
        ]
        output = [(len(self.schools), "輸入學校紀錄數", "依研究範圍，不等同95校網")]
        if not any(number(summary.get(spec[0])) is not None for spec in specs):
            output.append((sum(entry["any_enrolment"] for entry in self.index), "有任一實際人數的學校（僅主記錄）", "輸入未提供摘要核實統計；只計主記錄覆蓋校數，不合計學生"))
        for field, label, fallback, fallback_label, note in specs:
            if number(summary.get(field)) is not None:
                default = "至少一個保留學年有接收中學逐校實際人數；不把百分比當人數，不代表完整分佈。" if field == "verified_destination_school_counts_count" else note
                output.append((summary[field], label, definitions.get(field, default)))
            else:
                output.append((fallback, fallback_label + "（僅主記錄）", note + "；輸入未提供此摘要核實統計，僅按主記錄數值計算"))
        return output

    def build(self, favicon):
        roster = ''.join(self.roster_row(key) for key in range(len(self.schools)))
        cards = ''.join(self.school_card(key) for key in range(len(self.schools)))
        social = ''.join(self.social_row(key) for key in range(len(self.schools)))
        destinations = ''.join(self.destination(key, True) for key in range(len(self.schools)))
        strategy = self.strategy_html()
        source_groups = ''.join(f'<details class="source-index card" id="sources-{key}" data-school-key="{key}" open><summary>{esc(obj(school).get("name"))} — 全部來源（{len(self.source_cache[key])}項）</summary>' + self.sources(key) + '</details>' for key, school in enumerate(self.schools))
        categories = sorted({entry["category"] for entry in self.index})
        receivers = sorted({name for entry in self.index for name in entry["destination_names"] if name != UNKNOWN})
        overview = '<div class="kpis">' + ''.join(f'<div class="kpi"><div class="n">{esc(count)}</div><div class="l">{esc(label)}</div><small>{esc(note)}</small></div>' for count, label, note in self.coverage_kpis()) + '</div>'
        categories_options = ''.join(f'<option value="{esc(category)}">{esc(category)}</option>' for category in categories)
        receiver_options = ''.join(f'<option value="{esc(receiver)}">{esc(receiver)}</option>' for receiver in receivers)
        nav = [('overview', '總覽'), ('roster', '人數名冊'), ('profiles', '學校詳情'), ('destinations', '升中流向'), ('social', '社媒'), ('promo', '宣傳策略'), ('method', '來源')]
        nav_html = '<nav aria-label="主要導航"><div class="wrap"><a class="brand" href="../">← 返回全站</a><ul>' + ''.join(f'<li><a href="#{anchor}">{label}</a></li>' for anchor, label in nav) + '</ul></div></nav>'
        payload = json.dumps({"data": self.data, "index": self.index}, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        payload = payload.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        head = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="{esc(favicon)}">
<title>{esc(TITLE)}</title>
<meta name="description" content="{esc(DESCRIPTION)}">
<link rel="canonical" href="{CANONICAL}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="西貢區小學全景資料">
<meta property="og:title" content="{esc(TITLE)}">
<meta property="og:description" content="{esc(DESCRIPTION)}">
<meta property="og:url" content="{CANONICAL}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(TITLE)}">
<meta name="twitter:description" content="{esc(DESCRIPTION)}">
<link rel="stylesheet" href="styles.css">
<script src="app.js" defer></script>
</head>
<body>
<a class="skip" href="#main">跳至主要內容</a>
'''
        output = head + nav_html
        output += '<header class="hero"><div class="wrap"><div class="eyebrow">SAI KUNG DISTRICT · 按行政區研究範圍分類 · 公開資料</div><h1>西貢區小學全景：<em>實際資料</em>與升中支援</h1><p class="lede">逐校查看人數、學年、活動、接收中學、社媒身份與來源。未公開／未核實就是資料缺口，不以班數推算。策略以中學P5/P6招生為暫定情境，非學校排名。</p>'
        output += f'<div class="meta"><span class="badge">整體核實日期：{esc(self.data.get("checked_date"))}</span><span class="badge">不跨學年合計人數</span><span class="badge">官津／直資／私立／國際／特殊依輸入分類</span></div>'
        output += '<div class="downloads"><a href="data.json" download>完整學校JSON</a><a href="strategy.json" download>完整策略JSON</a><a href="report.md" download>研究報告Markdown</a></div></div></header><main id="main">'
        output += '<section id="overview"><div class="wrap"><h2>總覽：看資料覆蓋，不合計混年人數</h2><p class="sub">以下只計學校紀錄數及數字資料覆蓋校數，不代表研究母名單已完整、數字已同年或公布涵蓋全屆。資料完整性以來源與缺口為準。</p>' + overview
        output += '<div class="note-box rich"><b>研究範圍與邊界：</b>' + rich(self.data.get("scope_notes")) + '</div><details class="card"><summary>原始研究摘要（非跨年人數總計）</summary><div class="rich">' + rich(self.data.get("summary")) + '</div></details></div></section>'
        output += '<section id="roster"><div class="wrap"><span id="classes"></span><h2>人數名冊：實際數字、學年與逐項來源</h2><p class="sub">P6突出顯示；P1–P6無相應紀錄時標示未公開／未核實。國際／特殊學制請展開學校詳情閱讀全部原始年級及備註。班數另列為小字，不推算、不加總。</p><noscript><div class="note-box">JavaScript未啟用：以下仍有全部學校資料、可展開詳情及完整下載。互動篩選與當前篩選匯出需要JavaScript。</div></noscript>'
        output += '<div class="filters js-only"><label class="field" for="q">搜尋學校、活動或接收中學<input id="q" type="search" placeholder="學校名／活动／接收中學" autocomplete="off" aria-controls="rosterBody cards socialBody"></label><label class="field" for="fType">學校類別<select id="fType"><option value="">全部類別</option>' + categories_options + '</select></label>'
        output += '<label class="field" for="sortSchools">排序（數字未知放末）<select id="sortSchools"><option value="name">校名</option><option value="p6-desc">小六人數由多至少</option><option value="p6-asc">小六人數由少至多</option><option value="total-desc">全校人數由多至少</option><option value="total-asc">全校人數由少至多</option></select></label><div class="filter-footer"><label class="check"><input type="checkbox" id="knownP6">只看有已知小六人數</label><label class="check"><input type="checkbox" id="showClasses" checked>顯示班數小字</label><button type="button" id="clearFilters">清除全部篩選</button></div></div>'
        output += f'<p class="count" id="rosterCount" role="status" aria-live="polite" aria-atomic="true">顯示全部 {len(self.schools)} 間學校</p><p class="filter-note">數字排序僅為閱覽方便，學年不同不可直接比較，更不是學校質素排名。多條小六紀錄不相加，無單一排序值時放末。</p><div class="actions js-only"><button type="button" id="exportJSON">匯出目前篩選JSON</button><button type="button" id="exportCSV">匯出目前篩選人數CSV</button></div><p id="exportStatus" role="status" aria-live="polite" class="small"></p><p class="small">JSON保留所選學校完整原始資料及全研究背景；CSV為人數長表，逐項分學年，勿把獨立小六行重複相加。</p>'
        grade_headers = ''.join('<th scope="col"' + (' class="p6-cell"' if grade == 'P6' else '') + '>' + grade + '實數</th>' for grade in ('P1', 'P2', 'P3', 'P4', 'P5', 'P6'))
        output += '<div class="tablewrap" tabindex="0" role="region" aria-label="實際學生人數名冊，可橫向捲動"><table class="roster"><caption>全部學校的實際人數名冊（手機可橫向捲動）</caption><thead><tr><th scope="col">學校</th><th scope="col">類別</th><th scope="col">人數紀錄學年</th><th scope="col">全校實數</th>' + grade_headers + '</tr></thead><tbody id="rosterBody">' + roster + '</tbody></table></div><p class="empty" id="schoolEmpty" hidden>沒有符合條件的學校；可清除篩選重新查看。</p></div></section>'
        output += '<section id="profiles"><div class="wrap"><h2>學校詳情：事實、觀察與建議分開</h2><p class="sub">每校完整內容已在初始HTML中。點擊校名展開；人數缺口、社媒身份與接收中學名單的公布範圍請一併閱讀。</p><div class="actions js-only"><button type="button" id="expandAll">展開目前學校</button><button type="button" id="collapseAll">收起學校詳情</button></div><div class="cards" id="cards">' + cards + '</div></div></section>'
        output += '<section id="destinations"><div class="wrap"><h2>升中流向：公開接收中學紀錄</h2><p class="sub">全部已提供紀錄，不截取前幾名。不把去向當第一志願；部分公布、獲錄取、派位或一條龍關係需依每校備註區分。百分比不自行計算，也不由部分名單推定全屆。</p><div class="filters js-only"><label class="field" for="destinationQuery">搜尋接收中學<input id="destinationQuery" type="search" placeholder="接收中學名稱" aria-controls="destinationBlocks"></label><label class="field" for="destinationSchool">接收中學篩選<select id="destinationSchool"><option value="">全部接收中學</option>' + receiver_options + '</select></label><div class="filter-footer"><button id="clearDestinations" type="button">清除接收中學條件</button><span class="small">同時受上方學校篩選控制；不改動各校原始資料。</span></div></div><p id="destinationCount" class="count" role="status" aria-live="polite" aria-atomic="true">全部學校公開去向紀錄</p><p id="destinationEmpty" class="empty" hidden>沒有符合條件的去向紀錄。</p><div id="destinationBlocks">' + destinations + '</div></div></section>'
        output += '<section id="social"><div class="wrap"><h2>社媒總覽：連結、原始狀態與身份證據</h2><p class="sub">每校固定列Facebook、Instagram及小紅書，其他平台另列。未找到／未核實不代表不存在；校友會、第三方與官方已核實分開識讀，不混合統計帳戶數。</p><div class="tablewrap" tabindex="0" role="region" aria-label="全部學校社媒身份總覽，可橫向捲動"><table class="social-table"><caption>各平台保留帳戶原始狀態與證據</caption><thead><tr><th scope="col">學校</th><th scope="col">Facebook</th><th scope="col">Instagram</th><th scope="col">小紅書</th><th scope="col">其他平台</th></tr></thead><tbody id="socialBody">' + social + '</tbody></table></div></div></section>'
        output += '<section id="promo"><div class="wrap"><h2>宣傳策略：分群、切入、時間線与量度</h2>' + strategy + '</div></section>'
        output += '<section id="method"><div class="wrap"><h2>來源、研究缺口與使用限制</h2><div class="note-box warning">本頁不作選校排名。所有数字只反映來源指定學年；未公開／未核實並非0。班數、人數、屆別總人數及去向公布覆蓋不可互相替代。研究資料與策略均應以最新官方發布再核對。</div><h3>研究未完成／失敗紀錄</h3><div class="rich">' + rich(self.data.get("failures")) + '</div>'
        output += '<h3>資料聯結與格式提醒</h3><div class="rich">' + (rich(self.warnings) if self.warnings else '<p>沒有產生器格式提醒；這不代表研究事實已由產生器核實。</p>') + '</div>'
        output += '<h4>未能對應來源ID</h4><div class="rich">' + (rich(self.unresolved) if self.unresolved else '<p>所有已提供來源ID可對應；未提供來源ID者仍標示缺口。</p>') + '</div><h3>逐校完整來源</h3><div id="sourceGroups">' + source_groups + '</div>'
        extras = {k: v for k, v in self.data.items() if k not in {"checked_date", "scope_notes", "schools", "failures", "summary", "raw_data", "integration"} and not k.endswith("_path")}
        if extras:
            output += '<h3>其他研究原始欄位</h3><div class="rich">' + rich(extras) + '</div>'
        output += '</div></section></main><footer><div class="wrap"><b>西貢區小學全景資料</b> · 整體核實日期：' + esc(self.data.get("checked_date")) + '<br>保留原GitHub Pages網址。沒有登入、追蹤碼、網路字型、外部JavaScript／CDN；未對外聯絡。<br><a href="../">返回全站</a> · <a href="data.json" download>完整資料</a> · <a href="strategy.json" download>策略</a> · <a href="report.md" download>報告</a></div></footer>\n'
        output += '<script id="site-data" type="application/json">' + payload + '</script>\n</body>\n</html>\n'
        return output

    def report(self):
        def md(value):
            value = html.escape(text(value), quote=False)
            return re.sub(r"([\\`*_{}\[\]()#+.!|>-])", r"\\\1", value)

        def readable_lines(value, depth=0):
            indent = "  " * depth
            if isinstance(value, dict):
                output = []
                for field, child in value.items():
                    if field in {"raw_data", "integration"} or field.endswith("_path"):
                        continue
                    label = md(LABELS.get(field, field))
                    if isinstance(child, (dict, list)):
                        output += [indent + "- " + label + "："] + readable_lines(child, depth + 1)
                    else:
                        output += [indent + "- " + label + "：" + md(child)]
                return output or [indent + "- 未提供"]
            if isinstance(value, list):
                output = []
                for child in value:
                    if isinstance(child, (dict, list)):
                        output += [indent + "- 紀錄："] + readable_lines(child, depth + 1)
                    else:
                        output += [indent + "- " + md(child)]
                return output or [indent + "- 未提供"]
            return [indent + "- " + md(value)]

        lines = ["# 西貢區小學公開資料研究報告", "", f"核實日期：{md(self.data.get('checked_date'))}", "",
                 "本報告由所提供研究JSON靜態產生，產生器不搜尋、核實或補完事實。西貢行政區不等同95校網。", "",
                 "暫定策略情境為中學P5/P6招生及升中支援；接觸次序不是學校排名，公開接收中學亦非第一志願。", "",
                 "## 範圍與摘要", ""]
        lines += readable_lines(self.data.get("scope_notes")) + [""] + readable_lines(self.data.get("summary"))
        lines += ["", "## 資料覆蓋（只計學校紀錄）", ""]
        lines += [f"- {md(label)}：{count}校。{md(note)}" for count, label, note in self.coverage_kpis()]
        lines += ["", "未跨學年合計學生人數；沒有班額推算。", "", "## 研究未完成／失敗紀錄", ""] + readable_lines(self.data.get("failures")) + ["", "## 逐校紀錄", ""]
        for key, school in enumerate(self.schools):
            s = obj(school)
            lines += [f"### {md(s.get('name'))}", "", f"[网页深連結]({CANONICAL}#{self.index[key]['slug']})", ""]
            for field, value in (s.items() if s else [("原始紀錄", school)]):
                if field in {"raw_data", "integration"} or field.endswith("_path"):
                    continue
                lines += [f"#### {md(LABELS.get(field, field))}", ""]
                if field == "sources":
                    for source in self.source_cache[key]:
                        source_obj = obj(source["record"])
                        url = safe_url(source_obj.get("url"))
                        lines += [f"- 來源 {md(source['id'])}：{md(source_obj.get('title'))}"]
                        if url:
                            lines += [f"  - 網址：<{html.escape(url, quote=True).replace('>', '%3E').replace('<', '%3C')}>"]
                        lines += readable_lines(source["record"], 1) + [""]
                else:
                    lines += readable_lines(value) + [""]
        lines += ["## 完整宣傳策略", ""]
        for field, value in self.strategy.items():
            if field not in {"raw_data", "integration"} and not field.endswith("_path"):
                lines += ["### " + md(LABELS.get(field, field)), ""] + readable_lines(value) + [""]
        lines += ["## 產生器資料聯結提醒", ""] + readable_lines(self.warnings) + [""] + readable_lines(self.unresolved) + ["",
                  "## 使用限制", "", "來源ID對應只保證資料聯結，不代表來源內容已核實。來源ID不存在不崩潰，會在頁面與此報告保留提醒。", "",
                  "國際／特殊學制按原始年級與備註呈現，不強行換算P1–P6。公布去向可能只是部分名單，百分比不自行推算。", "",
                  "官方社媒、校友會、第三方及待核實帳戶不可混合統計。任何公開資料仍需最新官方資料覆核；本頁未對外聯絡。", "",
                  "完整可機讀資料見 data.json；策略見 strategy.json。CSV按當前學校篩選匯出人數長表，完整研究欄位請用JSON。", ""]
        return "\n".join(lines)


def load_json(path):
    def reject_constant(value):
        raise ValueError(f"JSON不得包含非有限數字：{value}")

    return json.loads(path.read_text(encoding="utf-8-sig"), parse_constant=reject_constant)


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(temp, path)
    except Exception:
        Path(temp).unlink(missing_ok=True)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="完整 all-schools.json")
    parser.add_argument("--strategy", type=Path, required=True, help="完整 strategy.json")
    parser.add_argument("--report", type=Path, help="逐位元組複製已完成的可讀報告為report.md；不改寫來源")
    parser.add_argument("--output-dir", type=Path, default=ROOT, help="預設產生於脚本所在儲存庫；測試可指定/tmp")
    args = parser.parse_args(argv)
    try:
        data = load_json(args.data)
        strategy = load_json(args.strategy)
        if not isinstance(data, dict) or not isinstance(data.get("schools"), list):
            raise ValueError("資料最上層必須是物件，schools必須是陣列；拒絕舊資料fallback。")
        if not data["schools"]:
            raise ValueError("schools為空；為避免空資料覆蓋真實首頁，停止產生。")
        if not isinstance(strategy, dict):
            raise ValueError("strategy最上層必須是物件。")
        favicon = read_favicon()
        renderer = Renderer(data, strategy)
        page = renderer.build(favicon)
        report = args.report.read_bytes() if args.report is not None else renderer.report().encode("utf-8")
        # Validate everything before touching the output, and copy JSON byte-for-byte.
        contents = {
            "index.html": page.encode("utf-8"),
            "data.json": args.data.read_bytes(),
            "strategy.json": args.strategy.read_bytes(),
            "report.md": report,
            "styles.css": (ROOT / "styles.css").read_bytes(),
            "app.js": (ROOT / "app.js").read_bytes(),
            "manus-routes.json": json.dumps({"routes": [{"path": "/sai-kung-primary-schools/", "title": "西貢區小學資料與中學招生研究"}]}, ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
        }
        output = args.output_dir.resolve()
        output.mkdir(parents=True, exist_ok=True)
        for filename, content in contents.items():
            atomic_write(output / filename, content)
        print(f"產生完成：{output / 'index.html'}（{len(data['schools'])}校；初始HTML包含完整資料）")
        print(f"來源ID未能對應：{len(renderer.unresolved)}項；格式／策略提醒：{len(renderer.warnings)}項。詳見report.md。")
        print("沒有搜尋、估算、登入、對外聯絡或部署。")
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(f"產生失敗：{exc}；沒有使用舊數據fallback。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
