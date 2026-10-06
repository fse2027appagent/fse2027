"""Backward-compatible AppAgent facade over the complete SRM module chain."""

from __future__ import annotations

from typing import Dict, Optional
from .downstream import ExistingWorkflowAdapter
from .translator import RequirementTranslator, TranslationRequest


class RequirementPipeline:
    """Translate a task and expose retrieval/planning-friendly views.

    Rules deliberately favour faithful extraction over guessing.  An unmatched
    clause remains a ``generic_interaction`` and is visible in diagnostics.
    """

    def build(self, task_id: str, app_name: str, task_description: str,
              app_description: Optional[str] = None) -> Dict[str, Any]:
        model = RequirementTranslator().translate(TranslationRequest(task_id, app_name, task_description, app_description))
        bundle = ExistingWorkflowAdapter().build(model).to_dict()
        bundle["model"] = model.to_dict()
        return bundle

    def _match(self, requirement_id: str, clause: str):
        lower = clause.lower()
        quoted = re.findall(r'[“"]([^”"]+)[”"]|[‘\']([^’\']+)[’\']', clause)
        quoted_value = next((a or b for a, b in quoted), None)
        if re.search(r"验证|检查|确认|verify|check|ensure", lower):
            comparison = re.search(r"(?:低于|小于|less than|below)\s*[¥￥$]?\s*(\d+(?:\.\d+)?)", lower)
            if comparison:
                value = float(comparison.group(1)); value = int(value) if value.is_integer() else value
                return Requirement(requirement_id, "ExpectedOutcome", "verify", clause, "displayed_value", value, "less_than", ["threshold"]), {"threshold": value}
            return Requirement(requirement_id, "ExpectedOutcome", "verify", clause, "task_outcome", quoted_value), {}
        if re.search(r"搜索|search|find", lower):
            value = quoted_value or self._after(clause, ("搜索", "search for", "search", "find"))
            return Requirement(requirement_id, "Interaction", "search", clause, "search_query", value, parameters=["query"] if value else []), ({"query": value} if value else {})
        if re.search(r"导航|navigate|directions", lower):
            value = quoted_value or self._after(clause, ("导航到", "前往", "navigate to"))
            return Requirement(requirement_id, "Interaction", "navigate", clause, "destination", value, parameters=["destination"] if value else []), ({"destination": value} if value else {})
        if re.search(r"登录|log\s*in|sign\s*in", lower):
            value = self._after(clause, ("登录账号", "登录", "log in", "sign in"))
            return Requirement(requirement_id, "Interaction", "login", clause, "account", value, parameters=["account"] if value else []), ({"account": value} if value else {})
        if re.search(r"排序|sort", lower):
            value = "sales_descending" if re.search(r"销量|sales", lower) else "specified_order"
            return Requirement(requirement_id, "Interaction", "sort", clause, "result_list", value, parameters=["sort_mode"]), {"sort_mode": value}
        if re.search(r"打开|open", lower):
            rank = 1 if re.search(r"第一个|首个|first", lower) else None
            return Requirement(requirement_id, "Interaction", "open", clause, "ranked_result" if rank else "described_target", rank, parameters=["result_rank"] if rank else []), ({"result_rank": rank} if rank else {})
        if re.search(r"播放|\bplay\b", lower):
            return Requirement(requirement_id, "Interaction", "play", clause, "favorite_video" if "收藏" in clause or "favorite" in lower else "described_media"), {}
        if re.search(r"弹幕|bullet comment|danmaku", lower):
            return Requirement(requirement_id, "Interaction", "send_comment", clause, "bullet_comment", quoted_value, parameters=["comment"] if quoted_value else []), ({"comment": quoted_value} if quoted_value else {})
        if re.search(r"创建.*闹钟|设置.*闹钟|新建.*闹钟|create.*alarm|set.*alarm", lower):
            alarm_time = self._alarm_time(clause)
            data = {"alarm_time": alarm_time} if alarm_time else {}
            return Requirement(requirement_id, "Interaction", "set_alarm", clause, "alarm", alarm_time,
                               parameters=["alarm_time"] if alarm_time else []), data
        return Requirement(requirement_id, "Interaction", "generic_interaction", clause, "described_target"), {}

    @staticmethod
    def _after(text: str, keywords) -> Optional[str]:
        lowered = text.lower()
        for keyword in keywords:
            position = lowered.find(keyword.lower())
            if position >= 0:
                value = text[position + len(keyword):].strip(" ：:到")
                return value or None
        return None

    @staticmethod
    def _alarm_time(text: str) -> Optional[str]:
        """Normalise common Clock-task expressions without inferring a date."""
        chinese = re.search(r"(上午|早上|下午|晚上).*?([一二三四五六七八九十])点", text)
        if chinese:
            hours = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
                     "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            hour = hours[chinese.group(2)]
            if chinese.group(1) in ("下午", "晚上"):
                hour = hour % 12 + 12
            return "%02d:00" % hour
        match = re.search(r"(?:上午|早上|am\s*)(\d{1,2})(?:[:：](\d{2}))?", text, re.I)
        if match:
            return "%02d:%s" % (int(match.group(1)), match.group(2) or "00")
        match = re.search(r"(?:下午|晚上|pm\s*)(\d{1,2})(?:[:：](\d{2}))?", text, re.I)
        if match:
            hour = int(match.group(1)) % 12 + 12
            return "%02d:%s" % (hour, match.group(2) or "00")
        return None
