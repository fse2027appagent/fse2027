"""Replay a normalised case with text-based UI relocation and assertions."""

from __future__ import annotations

import argparse
import json
import os
import time
import xml.etree.ElementTree as ET

import yaml


def _find_component(page, target):
    expected = (target or {}).get("text", "").strip().lower()
    role = (target or {}).get("semantic_role", "")
    aliases = {
        "search_entry": ("搜索", "search"),
        "add_to_cart": ("加入购物车", "add to cart"),
    }
    if not expected:
        expected_values = aliases.get(role, ())
    else:
        expected_values = (expected,)
    for index, component in enumerate(page.get_components(), 1):
        text = (component.get_desc() or "").strip().lower()
        if any(value == text or value in text for value in expected_values):
            return index
    return None


def _find_xml_bounds(controller, root_dir, target):
    """Use Android accessibility metadata when vision cannot read an icon."""
    xml_path = controller.get_xml("replay_locator", root_dir)
    if xml_path == "ERROR" or not os.path.exists(xml_path):
        return None
    expected = (target or {}).get("text", "").lower()
    role = (target or {}).get("semantic_role", "")
    resource_id = (target or {}).get("resource_id", "").lower()
    content_desc = (target or {}).get("content_desc", "").lower()
    try:
        nodes = list(ET.parse(xml_path).iter("node"))
    except ET.ParseError:
        return None

    # 1) A recorded resource-id is the strongest portable locator: match on any node.
    if resource_id:
        for node in nodes:
            node_resource_id = node.attrib.get("resource-id", "").lower()
            if node_resource_id == resource_id or node_resource_id.endswith(resource_id):
                box = _parse_bounds(node.attrib.get("bounds", ""))
                if box is not None:
                    return box

    # 2) content-desc / text / role keywords.  Prefer clickable nodes but fall back
    #    to non-clickable ones: Compose often puts the label on a sibling of the
    #    clickable element (e.g. a bottom tab whose content-desc is non-clickable).
    candidates = []
    for node in nodes:
        clickable = node.attrib.get("clickable") == "true"
        node_text = node.attrib.get("text", "").lower()
        node_desc = node.attrib.get("content-desc", "").lower()
        node_resource_id = node.attrib.get("resource-id", "").lower()
        haystack = " ".join((node_text, node_desc, node_resource_id))

        if content_desc and content_desc in node_desc:
            candidates.append((clickable, node))
        elif expected and expected in haystack:
            candidates.append((clickable, node))
        elif role == "search_entry" and ("search" in haystack or "搜索" in haystack):
            candidates.append((clickable, node))
        elif role == "search_result":
            # Search results are normally the first clickable row below the header.
            bounds = _parse_bounds(node.attrib.get("bounds", ""))
            if bounds and 150 < bounds[1] < 1600 and (node.attrib.get("text") or node.attrib.get("content-desc")):
                candidates.append((clickable, node))
    if not candidates:
        return None
    candidates.sort(key=lambda item: 0 if item[0] else 1)  # clickable first
    return _parse_bounds(candidates[0][1].attrib.get("bounds", ""))


def _parse_bounds(value):
    try:
        first, second = value[1:-1].split("][")
        x1, y1 = map(int, first.split(","))
        x2, y2 = map(int, second.split(","))
        return x1, y1, x2, y2
    except (AttributeError, ValueError):
        return None


def replay(case_path, root_dir):
    # Imported here so YAML validation can run without loading CV/ML packages.
    from and_controller import AndroidController, list_all_devices
    from object.page import Page

    with open(case_path, encoding="utf-8") as handle:
        case = yaml.safe_load(handle)
    devices = list_all_devices()
    if not devices:
        raise RuntimeError("未发现 ADB 设备")
    os.makedirs(root_dir, exist_ok=True)
    controller = AndroidController(devices[0])
    report = {"case": case.get("id"), "steps": [], "passed": False}

    # TRACE: allow a freshly launched Android application to leave its splash screen.
    time.sleep(3)

    for number, step in enumerate(case.get("steps", []), 1):
        screenshot = controller.get_screenshot("replay_%02d" % number, root_dir)
        action = step.get("action")
        # TRACE: XML is fast and sees icon/resource-id targets that OCR misses.
        xml_bounds = _find_xml_bounds(controller, root_dir, step.get("target"))
        page = None
        target_index = None
        if xml_bounds is None:
            # Vision remains a fallback for canvas-only applications.
            page = Page(screenshot)
            target_index = _find_component(page, step.get("target"))
        ok, reason = True, ""
        if action == "input":
            controller.text(str(step.get("value", "")))
        elif action == "search":
            if target_index is None and xml_bounds is None:
                ok, reason = False, "TARGET_NOT_FOUND"
            else:
                if xml_bounds:
                    x1, y1, x2, y2 = xml_bounds
                else:
                    bounds = page.get_components()[target_index - 1].get_bounds()
                    x1, y1, x2, y2 = bounds.x1, bounds.y1, bounds.x2, bounds.y2
                controller.search((x1 + x2) / 2, (y1 + y2) / 2,
                                  str(step.get("value", "")))
        elif action == "back":
            controller.back()
        elif action in ("tap", "long_press", "clear"):
            if target_index is None and xml_bounds is None:
                ok, reason = False, "TARGET_NOT_FOUND"
            else:
                if xml_bounds:
                    x1, y1, x2, y2 = xml_bounds
                else:
                    bounds = page.get_components()[target_index - 1].get_bounds()
                    x1, y1, x2, y2 = bounds.x1, bounds.y1, bounds.x2, bounds.y2
                x, y = (x1 + x2) / 2, (y1 + y2) / 2
                getattr(controller, action)(x, y) if action != "clear" else controller.clear(x, y)
        elif action == "swipe":
            if target_index is None and xml_bounds is None:
                ok, reason = False, "TARGET_NOT_FOUND"
            else:
                if xml_bounds:
                    x1, y1, x2, y2 = xml_bounds
                else:
                    bounds = page.get_components()[target_index - 1].get_bounds()
                    x1, y1, x2, y2 = bounds.x1, bounds.y1, bounds.x2, bounds.y2
                controller.swipe((x1 + x2) / 2, (y1 + y2) / 2,
                                 step.get("direction", "up"), step.get("distance", "medium"))
        else:
            ok, reason = False, "UNSUPPORTED_ACTION"
        report["steps"].append({"number": number, "action": action, "passed": ok, "reason": reason})
        if not ok:
            break
        time.sleep(1)
    report["passed"] = bool(report["steps"]) and all(item["passed"] for item in report["steps"])
    path = os.path.join(root_dir, "replay_result.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Replay a normalised AppAgent trace case.")
    parser.add_argument("--case", required=True)
    parser.add_argument("--root_dir", default="./result/replay")
    arguments = parser.parse_args()
    print(json.dumps(replay(arguments.case, arguments.root_dir), ensure_ascii=False, indent=2))
