"""
Clean & self-contained RAG pipeline (NO faiss, NO new OpenAI SDK)
===============================================================

Features:
- XML task parsing
- Intent extraction
- Embedding construction (OpenAI old SDK compatible)
- Pure NumPy cosine similarity retrieval
- Few-shot prompt construction
- Task step generation
- Quality filtering + deduplication
- Append new examples to XML

This file is intentionally verbose but ZERO undefined functions.
"""

# =========================
# Imports
# =========================

import os
import re
from config import load_config
from app_description_helper import app_desc_index
import xml.etree.ElementTree as ET
from typing import List, Dict

import cv2
import numpy as np
import dashscope
from dashscope.embeddings import TextEmbedding

from model import QwenModel
from prompts import assert_template

# =========================
# Qwen (DashScope) Config
# =========================

dashscope.api_key = load_config()["DASHSCOPE_API_KEY"]

# =========================
# XML Parsing
# =========================

def parse_task_xml(xml_path: str):
    """
        Parse a <tasks> XML file and return a list of task dicts.
        """
    xml_path = os.path.expanduser(xml_path)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    tasks = []

    for task_node in root.findall("task"):
        app_name = task_node.findtext("app_name", "").strip().lower()

        task_desc = task_node.findtext("task_desc", "")
        task_desc = " ".join(task_desc.split()).lower()

        task_steps = []
        steps_node = task_node.find("task_steps")
        if steps_node is not None:
            for step in steps_node.findall("task_step"):
                if step.text:
                    step_content = " ".join(step.text.split())
                    step_content = step_content.replace("%_left", "<")
                    step_content = step_content.replace("%_right", ">")
                    task_steps.append(step_content)

        # 基本防御：没有描述就跳过
        if not app_name or not task_desc:
            continue

        tasks.append({
            "app_name": app_name,
            "app_desc": app_desc_index.get(app_name),
            "task_desc": task_desc,
            "task_steps": task_steps,
        })

    return tasks


# =========================
# Intent Extraction
# =========================

INTENT_KEYWORDS = {
    "navigation": ["navigate", "navigation", "direction", "route", "drive", "walk"],
    "search": ["search", "find", "look for"],
    "booking": ["book", "reserve", "order"],
    "payment": ["pay", "payment", "checkout"],
    "login": ["login", "sign in", "log in"],
}


def extract_intents(task_desc: str) -> List[str]:
    intents = []
    for intent, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if kw in task_desc:
                intents.append(intent)
                break
    return intents or ["general"]


# =========================
# Embedding Helpers
# =========================


def build_embedding_text(task: Dict) -> str:
    intents = extract_intents(task["task_desc"])
    return (
        f"App Description: {task['app_desc']}\n"
        f"Task Intent: {', '.join(intents)}\n"
        f"Task Description: {task['task_desc']}\n"
        f"App Name: {task['app_name']}"
    )


def build_query_embedding_text(app_name: str, app_desc: str, task_desc: str) -> str:
    intents = extract_intents(task_desc.lower())
    return (
        f"App Description: {app_desc.lower()}\n"
        f"Task Intent: {', '.join(intents)}\n"
        f"Task Description: {task_desc.lower()}\n"
        f"App Name: {app_name.lower()}"
    )


def get_embedding(text: str) -> np.ndarray:
    resp = TextEmbedding.call(
        model="text-embedding-v2",
        input=text
    )
    vec = resp.output["embeddings"][0]["embedding"]
    return np.array(vec, dtype="float32")


# =========================
# Vector Retrieval (NumPy)
# =========================


def l2_normalize(x: np.ndarray) -> np.ndarray:
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def build_embedding_matrix(tasks: List[Dict]) -> np.ndarray:
    texts = [build_embedding_text(t) for t in tasks]
    emb = np.vstack([get_embedding(t) for t in texts])
    return l2_normalize(emb)


def retrieve_top_k_tasks(
    embeddings: np.ndarray,
    tasks: List[Dict],
    app_name: str,
    app_desc: str,
    task_desc: str,
    k: int = 3,
    query_text: str = None,
) -> List[Dict]:
    # A structured task representation can be supplied by UTP-SRM.  Existing
    # callers retain the original query construction.
    q_text = query_text or build_query_embedding_text(app_name, app_desc, task_desc)
    q_emb = get_embedding(q_text).reshape(1, -1)
    q_emb = l2_normalize(q_emb)[0]

    scores = embeddings @ q_emb
    idx = np.argsort(scores)[-k:][::-1]

    return [{"score": float(scores[i]), "task": tasks[i]} for i in idx]

# =========================
# Quality Filter & Dedup
# =========================


def is_high_quality_example(task_steps: List[str]) -> bool:
    if len(task_steps) < 3:
        return False
    for s in task_steps:
        if len(s.split()) < 5:
            return False
        if any(x in s.lower() for x in ["maybe", "unknown", "not sure"]):
            return False
    return True


def task_desc_exists(root: ET.Element, app_name: str, task_desc: str) -> bool:
    for task in root.findall("task"):
        if (
            task.findtext("app_name", "").lower() == app_name.lower()
            and task.findtext("task_desc", "").lower() == task_desc.lower()
        ):
            return True
    return False


# =========================
# Write Example to XML
# =========================


def write_task_to_xml(
        xml_path: str,
        app_name: str,
        app_desc: str,
        task_desc: str,
        task_steps: List[str],
):
    """
    Append a new <task> to a <tasks> XML file.
    Creates file if not exists.
    """

    # ---------- load or create ----------
    if os.path.exists(xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
    else:
        root = ET.Element("tasks")
        tree = ET.ElementTree(root)

    # ---------- dedup (app_name + task_desc) ----------
    for task in root.findall("task"):
        existing_app = task.findtext("app_name", "").strip().lower()
        existing_desc = " ".join(
            task.findtext("task_desc", "").split()
        ).lower()

        if existing_app == app_name.lower() and existing_desc == task_desc.lower():
            print("[SKIP] duplicate task")
            return

    # ---------- create new task ----------
    task_node = ET.SubElement(root, "task")

    ET.SubElement(task_node, "app_name").text = app_name
    ET.SubElement(task_node, "task_desc").text = task_desc

    steps_node = ET.SubElement(task_node, "task_steps")
    for step in task_steps:
        step = step.replace("<", "%_left")
        step = step.replace(">", "%_right")
        ET.SubElement(steps_node, "task_step").text = step

    # ---------- write back ----------
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    app_desc_index.add_or_update(app_name, app_desc)
    print("[OK] task written to xml")


# =========================
# Minimal Demo
# =========================

if __name__ == "__main__":
    tasks = parse_task_xml(load_config()['TASK_STEPS_PATH'])
    count = 40
    for i in range(len(tasks)):
        print(f'当前轮次: {i}')
        if i < count:
            continue
        task = tasks[i]
        print(task)
        if input() != 'y':
            count += 1
            continue
        app_desc = task['app_desc']['description']
        task_desc = task['task_desc']
        app_name = task['app_name']
        image = '../test_images/' + str(count) + '.png'

        configs = load_config()
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"], model=configs["QWEN_MODEL_MLLM"])

        prompt = assert_template
        prompt = re.sub(r"<task_description>", task_desc, prompt)
        prompt = re.sub(r"<app_description>", app_desc, prompt)
        prompt = re.sub(r"<app_name>", app_name, prompt)

        status, rsp = mllm.get_model_response(prompt=prompt, images=[image])
        print(rsp)
        count += 1
    # embeddings = build_embedding_matrix(tasks)
    #
    # query = {
    #     "app_name": "baidu map",
    #     "app_desc": "travel",
    #     "task_desc": "find west lake and start walking navigation",
    # }
    #
    # retrieved = retrieve_top_k_tasks(
    #     embeddings,
    #     tasks,
    #     query["app_name"],
    #     query["app_desc"],
    #     query["task_desc"],
    #     k=2,
    # )
    #
    # print(retrieved)
