"""Convert a successful raw AppAgent trace into a portable YAML test case."""

from __future__ import annotations

import json
import os
import re

import yaml


def normalize_successful_trace(trace_path):
    """Create a replay case only for a fully successful exploration run.

    This deliberately uses simple, inspectable heuristics.  Coordinates and
    screenshot-local component indexes remain in the raw trace, never in the
    generated case.
    """
    with open(trace_path, encoding="utf-8") as handle:
        trace = json.load(handle)
    if not trace.get("completed"):
        return None

    actions_by_step = {}
    for action in trace.get("actions", []):
        actions_by_step.setdefault(action["step_id"], []).append(action)

    steps = []
    for step in trace.get("steps", []):
        if step.get("status") != "satisfied":
            return None
        for action in actions_by_step.get(step["id"], []):
            item = _normalise_action(action, step["description"])
            if item:
                steps.append(item)

    if not steps:
        return None
    case = {
        "schema_version": "appagent-replay/0.1",
        "id": _safe_id(trace.get("objective", "generated_case")),
        "app": trace.get("app", ""),
        "app_description": trace.get("app_description", ""),
        "objective": trace.get("objective", ""),
        "generated_from": os.path.basename(trace_path),
        "preconditions": ["首次探索运行已成功；重放前请将应用置于等价初始状态。"],
        "steps": steps,
        "final_oracle": {"task_completed": True},
    }
    output = os.path.join(os.path.dirname(trace_path), "normalized_test_case.yaml")
    with open(output, "w", encoding="utf-8") as handle:
        yaml.safe_dump(case, handle, allow_unicode=True, sort_keys=False)
    return output


def _normalise_action(action, description):
    name = action.get("action")
    params = action.get("params", [])
    if name == "search" and len(params) >= 4:
        return {
            "action": "search",
            "target": {"semantic_role": "search_entry", "text": "搜索"},
            "value": params[3],
            "expected_effect": {"input_value": params[3]},
            "source_step": description,
        }
    if name == "text" and len(params) >= 2:
        return {"action": "input", "value": params[1],
                "expected_effect": {"input_value": params[1]},
                "source_step": description}
    if name in ("tap", "long_press", "clear", "swipe", "back"):
        item = {"action": name, "source_step": description}
        target = action.get("target")
        if target:
            text = target.get("text", "")
            role = _role_hint(description, text)
            item["target"] = {"semantic_role": role}
            # OCR text such as "之沈A人心" is not a portable locator for a result.
            if text and role != "search_result":
                item["target"]["text"] = text
            resource_id = target.get("resource_id", "")
            if resource_id:
                item["target"]["resource_id"] = resource_id
            content_desc = target.get("content_desc", "")
            if content_desc:
                item["target"]["content_desc"] = content_desc
            if role == "search_result":
                item["target"]["position"] = "first"
        if name == "swipe" and len(params) >= 4:
            item["direction"] = params[2]
            item["distance"] = params[3]
        return item
    return None


def _role_hint(description, text):
    value = (description + " " + text).lower()
    if "search" in value or "搜索" in value:
        if "result" in value or "结果" in value:
            return "search_result"
        return "search_entry"
    if "cart" in value or "购物车" in value:
        return "add_to_cart"
    if "product" in value or "商品" in value:
        return "product_item"
    return "ui_element"


def _safe_id(value):
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return value[:80] or "generated_case"
