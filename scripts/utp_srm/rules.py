"""Deterministic extraction rules. They are intentionally conservative."""
import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple
from .models import RequirementKind

ALLOWED_OPERATIONS = ("login", "search", "navigate", "open", "play", "select", "sort", "send_comment", "input", "tap", "verify", "set_alarm", "generic_interaction")
@dataclass(frozen=True)
class Clause: text: str; start: int; end: int
@dataclass(frozen=True)
class RuleMatch:
    kind: RequirementKind; operation: str; target: Optional[str] = None; value: Any = None; operator: Optional[str] = None; arguments: Optional[dict] = None; data: Tuple[Tuple[str, Any, str], ...] = ()

_BOUNDARY = re.compile(r"(?:，|。|；|;|,|\bthen\b|\band then\b|然后|随后|接着|并且|并(?=(?:开始|发送|打开|选择|验证|检查)))", re.I)
def split_clauses(text):
    result=[]; cursor=0
    for match in _BOUNDARY.finditer(text):
        _append(result, text, cursor, match.start()); cursor=match.end()
    _append(result, text, cursor, len(text)); return result
def _append(result, text, start, end):
    raw=text[start:end]; left=len(raw)-len(raw.lstrip()); right=len(raw.rstrip())
    if right > left: result.append(Clause(text[start+left:start+right], start+left, start+right))
def extract_quoted(text): return [a or b for a,b in re.findall(r'[“"]([^”"]+)[”"]|[‘\']([^’\']+)[’\']', text)]
def match_clause(clause):
    lowered=clause.lower(); quoted=extract_quoted(clause)
    if re.search(r"验证|检查|确认|verify|check|ensure", lowered):
        comparison=re.search(r"(?:低于|小于|less than|below)\s*[¥￥$]?\s*(\d+(?:\.\d+)?)", lowered)
        if comparison:
            value=float(comparison.group(1)); value=int(value) if value.is_integer() else value
            return RuleMatch(RequirementKind.EXPECTED_OUTCOME,"verify","displayed_value",value,"less_than",data=(("threshold",value,"number"),))
        return RuleMatch(RequirementKind.EXPECTED_OUTCOME,"verify","task_outcome",quoted[0] if quoted else None)
    if re.search(r"创建.*闹钟|设置.*闹钟|新建.*闹钟|create.*alarm|set.*alarm", lowered):
        value=_alarm_time(clause); return RuleMatch(RequirementKind.INTERACTION,"set_alarm","alarm",value,data=(("alarm_time",value,"string"),) if value else ())
    if re.search(r"登录|log\s*in|sign\s*in", lowered):
        value=_after(clause,("登录账号","登录","log in","sign in")); return RuleMatch(RequirementKind.INTERACTION,"login","account",value,data=(("account",value,"string"),) if value else ())
    if re.search(r"搜索|search|find", lowered):
        value=quoted[0] if quoted else _after(clause,("搜索","search for","search","find")); return RuleMatch(RequirementKind.INTERACTION,"search","search_query",value,data=(("query",value,"string"),) if value else ())
    if re.search(r"导航|navigate|directions", lowered):
        value=quoted[0] if quoted else _after(clause,("导航到","前往","navigate to")); return RuleMatch(RequirementKind.INTERACTION,"navigate","destination",value,data=(("destination",value,"string"),) if value else ())
    if re.search(r"排序|sort", lowered):
        value="sales_descending" if re.search(r"销量|sales",lowered) else "specified_order"; return RuleMatch(RequirementKind.INTERACTION,"sort","result_list",value,data=(("sort_mode",value,"enum"),))
    if re.search(r"打开|open", lowered):
        rank=1 if re.search(r"第一个|首个|first",lowered) else None; return RuleMatch(RequirementKind.INTERACTION,"open","ranked_result" if rank else "described_target",rank,data=(("result_rank",rank,"integer"),) if rank else ())
    if re.search(r"播放|\bplay\b",lowered): return RuleMatch(RequirementKind.INTERACTION,"play","favorite_video" if "收藏" in clause or "favorite" in lowered else "described_media")
    if re.search(r"弹幕|bullet comment|danmaku",lowered):
        value=quoted[0] if quoted else None; return RuleMatch(RequirementKind.INTERACTION,"send_comment","bullet_comment",value,data=(("comment",value,"string"),) if value else ())
    return RuleMatch(RequirementKind.INTERACTION,"generic_interaction","described_target",arguments={"raw_clause":clause})
def _after(text, keywords):
    lowered=text.lower()
    for keyword in keywords:
        i=lowered.find(keyword.lower())
        if i>=0: return text[i+len(keyword):].strip(" ：:到") or None
    return None
def _alarm_time(text):
    match=re.search(r"(上午|早上|下午|晚上).*?([一二三四五六七八九十])点", text)
    if match:
        hour={"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}[match.group(2)]; return "%02d:00" % (hour % 12 + 12 if match.group(1) in ("下午","晚上") else hour)
    match=re.search(r"(?:上午|早上|am\s*)(\d{1,2})(?:[:：](\d{2}))?", text, re.I)
    if match:return "%02d:%s"%(int(match.group(1)),match.group(2) or "00")
    return None
