"""Small, append-only recorder for a natural-language AppAgent run."""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime


def _parse_node_bounds(node):
    raw = node.attrib.get("bounds", "")
    try:
        first, second = raw[1:-1].split("][")
        x1, y1 = map(int, first.split(","))
        x2, y2 = map(int, second.split(","))
        return x1, y1, x2, y2
    except (AttributeError, ValueError):
        return None


def _box_area(box):
    return (box[2] - box[0]) * (box[3] - box[1])


def _box_contains(box, x, y):
    return box[0] <= x <= box[2] and box[1] <= y <= box[3]


class TraceRecorder:
    """Persist raw execution evidence without participating in agent decisions."""

    def __init__(self, task_dir, app, app_description, task, controller=None):
        self.task_dir = task_dir
        self.controller = controller
        self.path = os.path.join(task_dir, "execution_trace.json")
        self.data = {
            "schema_version": "appagent-trace/0.1",
            "app": app,
            "app_description": app_description or "",
            "objective": task or "",
            "started_at": datetime.now().isoformat(),
            "actions": [],
            "steps": [],
            "completed": False,
        }
        self._flush()

    def record_action(self, step_id, step_description, action, params, summary,
                      screenshot, components, xml_path=None):
        """Record the volatile UI index plus portable text/bounds evidence."""
        target = None
        if action in ("tap", "long_press", "swipe", "clear") and len(params) > 1:
            try:
                index = int(params[1]) - 1
                component = components[index]
                bounds = component.get_bounds().to_list()
                target = {
                    "component_index": index + 1,
                    "text": component.get_desc() or "",
                    "bounds": bounds,
                    "component_type": component.get_type(),
                }
                # TRACE: resource-id/content-desc/text from the hierarchy are the
                # portable locators that survive OCR-empty icon buttons and rows.
                xml_node = self._locate_xml_node(bounds, xml_path)
                if xml_node is not None:
                    resource_id = xml_node.attrib.get("resource-id", "")
                    content_desc = xml_node.attrib.get("content-desc", "")
                    node_text = xml_node.attrib.get("text", "")
                    if resource_id:
                        target["resource_id"] = resource_id
                    if content_desc:
                        target["content_desc"] = content_desc
                    if node_text and not target.get("text"):
                        target["text"] = node_text
            except (IndexError, TypeError, ValueError):
                target = {"component_index": params[1]}
        self.data["actions"].append({
            "step_id": step_id,
            "step_description": step_description,
            "action": action,
            "params": list(params),
            "summary": summary or "",
            "before_screenshot": self._relative(screenshot),
            "target": target,
        })
        self._flush()

    def record_step(self, step_id, description, succeeded, evidence_screenshot):
        self.data["steps"].append({
            "id": step_id,
            "description": description,
            "status": "satisfied" if succeeded else "failed",
            "evidence_screenshot": self._relative(evidence_screenshot),
        })
        self._flush()

    def finish(self, completed):
        self.data["completed"] = bool(completed)
        self.data["finished_at"] = datetime.now().isoformat()
        self._flush()

    def _locate_xml_node(self, bounds, xml_path=None):
        """Map a vision-detected box to the smallest XML node containing its centre.

        Prefers clickable nodes (their resource-id/content-desc identify an icon),
        then falls back to the smallest text node so text-only rows such as search
        results still yield a portable locator.  ``xml_path`` must be the hierarchy
        captured *before* the action ran; otherwise the target has already navigated
        away and no node will contain the box.
        """
        if xml_path is None:
            if self.controller is None:
                return None
            xml_path = self.controller.get_xml("trace_locator", self.task_dir)
        if xml_path == "ERROR" or not os.path.exists(xml_path):
            return None
        centre_x = (bounds[0] + bounds[2]) / 2
        centre_y = (bounds[1] + bounds[3]) / 2
        try:
            nodes = list(ET.parse(xml_path).iter("node"))
        except ET.ParseError:
            return None

        # Pass 1: smallest clickable node containing the centre.
        best = None
        best_area = None
        for node in nodes:
            box = _parse_node_bounds(node)
            if box is None or not _box_contains(box, centre_x, centre_y):
                continue
            if node.attrib.get("clickable") != "true":
                continue
            area = _box_area(box)
            if best_area is None or area < best_area:
                best, best_area = node, area
        if best is not None:
            return best

        # Pass 2: smallest node carrying a readable locator (text or content-desc).
        for node in nodes:
            if not (node.attrib.get("text", "").strip() or
                    node.attrib.get("content-desc", "").strip()):
                continue
            box = _parse_node_bounds(node)
            if box is None or not _box_contains(box, centre_x, centre_y):
                continue
            area = _box_area(box)
            if best_area is None or area < best_area:
                best, best_area = node, area
        return best

    def _relative(self, path):
        if not path or path == "ERROR":
            return None
        return os.path.relpath(path, self.task_dir)

    def _flush(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)
