import argparse
import ast
import datetime
import json
import logging
import os
import re
import sys
import time

import prompts
from config import load_config
from rag_task_steps_pipeline import write_task_to_xml, retrieve_top_k_tasks, parse_task_xml, build_embedding_matrix
from and_controller import list_all_devices, AndroidController
from model import parse_explore_rsp, parse_divide_rsp, OpenAIModel, QwenModel
from app_description_helper import app_desc_index
from object.page import Page
from utils import draw_bbox_multi
from utp_srm import RequirementPipeline
# TRACE: capture successful natural-language runs and export replayable cases.
from trace import TraceRecorder, normalize_successful_trace

USE_RAG = True

# 启用子步骤执行后的纠错：失败走强纠错，成功后走弱纠错。
CORRECT_SWITCH = True

USE_RULE = True

# token 用量统计的字段
_USAGE_FIELDS = ("calls", "input_tokens", "cached_tokens", "fresh_tokens",
                 "output_tokens", "total_tokens", "elapsed_sec")

# === 日志配置类 ===
class LoggerFactory:
    @staticmethod
    def create_logger(log_file: str):
        logger = logging.getLogger("app_executor")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # 关键

        if logger.handlers:
            return logger

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        formatter = logging.Formatter(
            "%(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger


# === 模型管理 ===
class ModelManager:
    def __init__(self, configs, logger):
        self.configs = configs
        self.logger = logger
        self.mllm, self.llm = self._init_models()

    def _init_models(self):
        model_type = self.configs["MODEL"]
        self.logger.info(f"Initializing model: {model_type}")
        if model_type == "OpenAI":
            mllm = OpenAIModel(
                base_url=self.configs["OPENAI_API_BASE"],
                api_key=self.configs["OPENAI_API_KEY"],
                model=self.configs["OPENAI_API_MODEL"],
                temperature=self.configs["TEMPERATURE"],
                max_tokens=self.configs["MAX_TOKENS"],
            )
            llm = None
        elif model_type == "DeepSeek":
            mllm = OpenAIModel(
                base_url=self.configs["DEEPSEEK_API_BASE"],
                api_key=self.configs["DEEPSEEK_API_KEY"],
                model=self.configs["DEEPSEEK_API_MODEL"],
                temperature=self.configs["TEMPERATURE"],
                max_tokens=self.configs["MAX_TOKENS"],
            )
            llm = None
        elif model_type == "Qwen":
            mllm = QwenModel(api_key=self.configs["DASHSCOPE_API_KEY"],
                             model=self.configs["QWEN_MODEL_MLLM"],
                             logger=self.logger)
            llm = QwenModel(api_key=self.configs["DASHSCOPE_API_KEY"],
                            model=self.configs["QWEN_MODEL_LLM"],
                            logger=self.logger)
        else:
            self.logger.error(f"Unsupported model type: {model_type}")
            sys.exit()
        return mllm, llm


# === 设备管理 ===
class DeviceManager:
    def __init__(self, logger):
        self.logger = logger
        self.device = self._select_device()
        self.controller = AndroidController(self.device)
        self.width, self.height = self.controller.get_device_size()
        if not self.width or not self.height:
            self.logger.error("Invalid device size!")
            sys.exit()
        self.logger.info(f"Screen resolution of {self.device}: {self.width}x{self.height}")

    def _select_device(self):
        device_list = list_all_devices()
        if not device_list:
            self.logger.error("No device found!")
            sys.exit()
        self.logger.info(f"Devices attached: {device_list}")
        if len(device_list) == 1:
            return device_list[0]
        self.logger.info("Please choose a device by entering its ID:")
        return input()

    def execute_action(self, action, params, page):
        try:
            components = page.get_components()
            if action in ["tap", "long_press", "swipe", "clear"]:
                if len(components) == 0:
                    self.logger.error("No components detected on screen")
                    return "ERROR"
            if action == "tap":
                _, area = params
                if area < 1 or area > len(components):
                    self.logger.error(f"Component {area} out of range (1-{len(components)})")
                    return "ERROR"
                bounds = components[area - 1].get_bounds()
                x, y = (bounds.x1 + bounds.x2) / 2, (bounds.y1 + bounds.y2) / 2
                self.logger.info(f"tap <{x}, {y}>")
                return self.controller.tap(x, y)
            elif action == "text":
                _, text_input = params
                self.logger.info(f"text <{text_input}>")
                return self.controller.text(text_input)
            elif action == "long_press":
                _, area = params
                bounds = page.get_components()[area].get_bounds()
                x, y = (bounds.x1 + bounds.x2) / 2, (bounds.y1 + bounds.y2) / 2
                self.logger.info(f"long press <{x}, {y}>")
                return self.controller.long_press(x, y)
            elif action == "swipe":
                _, area, direction, dist = params
                bounds = page.get_components()[area].get_bounds()
                x, y = (bounds.x1 + bounds.x2) / 2, (bounds.y1 + bounds.y2) / 2
                self.logger.info(f"swip direction: {direction}, dist: {dist}")
                return self.controller.swipe(x, y, direction, dist)
            # 搜索操作
            elif action == "search":
                x, y, content = float(params[0]), float(params[1]), params[2]
                height, width = page.image.shape[:2]
                x = int(x * width)
                y = int(y * height)
                self.logger.info(f"tap <{x}, {y}> to search {content}")
                return self.controller.search(x, y, content)
            # 清除操作
            elif action == "clear":
                _, area = params
                bounds = page.get_components()[area - 1].get_bounds()
                x, y = (bounds.x1 + bounds.x2) / 2, (bounds.y1 + bounds.y2) / 2
                self.logger.info(f"tap <{x}, {y}> and clear")
                return self.controller.clear(x, y)
            # 回退操作
            elif action == "back":
                self.logger.info(f"do system back")
                return self.controller.back()
        except Exception as e:
            self.logger.error(f"Action execution failed: {e}")
        return "ERROR"


# === 文档管理 ===
class DocumentManager:
    def __init__(self, app_dir, app, logger):
        self.app_dir = app_dir
        self.app = app
        self.logger = logger
        self.docs_dir, self.no_doc = self._select_doc_source()

    def _select_doc_source(self):
        auto_docs = os.path.join(self.app_dir, "auto_docs")
        demo_docs = os.path.join(self.app_dir, "demo_docs")

        if not os.path.exists(auto_docs) and not os.path.exists(demo_docs):
            # self.logger.warning(f"No documentation found for {self.app}, continuing with none.")
            return None, True

        if os.path.exists(auto_docs) and os.path.exists(demo_docs):
            # self.logger.info("Both auto and demo docs found. Type 1 for auto, 2 for demo:")
            return (auto_docs if input() == "1" else demo_docs), False

        selected = auto_docs if os.path.exists(auto_docs) else demo_docs
        self.logger.info(f"Using documentation from {selected}")
        return selected, False

    def get_ui_docs(self, page):
        if self.no_doc or not self.docs_dir:
            return ""
        ui_doc = ""
        for i, elem in enumerate(page.get_components()):
            doc_path = os.path.join(self.docs_dir, f"{elem.uid}.txt")
            if not os.path.exists(doc_path):
                continue
            with open(doc_path, "r") as f:
                doc = ast.literal_eval(f.read())
            ui_doc += f"\nDocumentation for element {i + 1}:\n"
            for k, v in doc.items():
                if v:
                    ui_doc += f"{k}: {v}\n"
        return ui_doc


# === 任务管理 ===
class TaskManager:
    def __init__(self, app, app_desc, task_desc, work_dir):
        self.app = app
        if app_desc == "" or app_desc is None:
            self.app_desc = app_desc_index.get(app)
        else:
            self.app_desc = app_desc
            app_desc_index.add_or_update(app, app_desc)
        self.task_desc = task_desc
        self.task_steps = []
        self.requirement_bundle = None
        self.requirement_plan = []
        self.work_dir = work_dir
        self.task_dir, self.log_path = self._setup_task_dir()
        self.logger = None

    def _setup_task_dir(self):
        timestamp = int(time.time())
        dir_name = datetime.datetime.fromtimestamp(timestamp).strftime(f"task_{self.app}_%Y-%m-%d_%H-%M-%S")
        task_dir = os.path.join(self.work_dir, dir_name)
        os.makedirs(task_dir, exist_ok=True)
        log_path = os.path.join(task_dir, f"{self.app}_{dir_name}.log")
        return task_dir, log_path

    # 进行步骤拆分
    def divide_task_steps(self, llm):
        use_srm = bool(load_config().get("USE_UTP_SRM", False))
        if use_srm:
            self._build_requirement_bundle()

        # 采用rag技术
        task_steps_path = load_config()['TASK_STEPS_PATH']
        tasks = parse_task_xml(task_steps_path)

        # 将rag获得的example嵌入prompt
        # 考虑开关控制
        if USE_RAG and len(tasks) >= 2:
            embeddings = build_embedding_matrix(tasks)
            query = {
                "app_name": self.app,
                "app_desc": self.app_desc,
                "task_desc": self.task_desc,
            }
            retrieved = retrieve_top_k_tasks(
                embeddings,
                tasks,
                query["app_name"],
                query["app_desc"],
                query["task_desc"],
                k=2,
                query_text=(self.requirement_bundle["retrieval"]["composite_text"]
                            if self.requirement_bundle else None),
            )
            divide_prompt = re.sub(r"<app_name>", self.app, prompts.divide_task_template_with_rag)
            divide_prompt = self.build_rag(divide_prompt, retrieved)
        else:
            divide_prompt = re.sub(r"<app_name>", self.app, prompts.divide_task_template)

        if self.requirement_bundle:
            return self._divide_task_steps_with_requirements(llm)

        # app描述
        if self.app_desc == "" or self.app_desc is None:
            divide_prompt = re.sub(r"<app_description>", "", divide_prompt)
        else:
            divide_prompt = re.sub(r"<app_description>", "We simply describe this app: " + self.app_desc, divide_prompt)

        # 任务描述
        divide_prompt = re.sub(r"<task_description>", self.task_desc, divide_prompt)

        status, rsp = llm.get_model_response(prompt=divide_prompt, images=[]) \
            if llm else (True, [self.task_desc])
        if status:
            task_steps = parse_divide_rsp(rsp)
            if not task_steps:
                self.logger.warning(f"LLM failed to divide task into steps (response: {rsp[:200]}), using fallback")
                self.task_steps = [self.task_desc]
            else:
                self.task_steps = task_steps
        else:
            self.logger.warning(f"LLM call failed for task division: {rsp}, using fallback")
            self.task_steps = [self.task_desc]

        # if input() == "y":
        #     write_task_to_xml(task_steps_path, self.app, self.app_desc, self.task_desc, self.task_steps)

        return self.task_steps

    def _build_requirement_bundle(self):
        """Create immutable intent and mutable status artifacts for this run."""
        task_id = os.path.basename(self.task_dir)
        self.requirement_bundle = RequirementPipeline().build(
            task_id=task_id,
            app_name=self.app,
            app_description=self.app_desc if isinstance(self.app_desc, str) else "",
            task_description=self.task_desc,
        )
        self._write_json("requirement_model.json", self.requirement_bundle["model"])
        self._write_json("downstream_bundle.json", {
            key: value for key, value in self.requirement_bundle.items() if key != "model"
        })
        self._write_json("requirement_status.json", {
            "requirements": [
                {"requirement_id": item["requirement_id"], "status": "pending", "evidence_refs": []}
                for item in self.requirement_bundle["runtime_obligations"]
            ]
        })
        self.logger.info("UTP-SRM enabled: %d requirements extracted", len(self.requirement_bundle["requirement_order"]))

    def _divide_task_steps_with_requirements(self, llm):
        planning = self.requirement_bundle["planning"]
        prompt = prompts.divide_task_template_with_srm
        replacements = {
            "<app_name>": self.app,
            "<app_description>": self.app_desc if isinstance(self.app_desc, str) else "",
            "<task_description>": self.task_desc,
            "<structured_objective>": planning["structured_objective"],
            "<structured_requirements>": json.dumps(planning["ordered_requirements"], ensure_ascii=False),
            "<test_data>": json.dumps(planning["test_data"], ensure_ascii=False),
        }
        for marker, value in replacements.items():
            prompt = prompt.replace(marker, value)
        status, response = llm.get_model_response(prompt=prompt, images=[]) if llm else (False, "No planning LLM")
        plan = self._parse_requirement_plan(response) if status else []
        if not plan:
            self.logger.warning("UTP-SRM planner returned no valid covered plan; using one step per requirement")
            plan = [
                {"step_id": "S-%02d" % (index + 1), "description": item["description"],
                 "requirement_ids": [item["requirement_id"]], "status": "pending"}
                for index, item in enumerate(planning["ordered_requirements"])
            ]
        self.requirement_plan = plan
        self.task_steps = [item["description"] for item in plan]
        self._write_json("requirement_plan.json", {"steps": plan})
        return self.task_steps

    def _parse_requirement_plan(self, response):
        try:
            payload = json.loads(response)
            steps = payload["steps"]
            required = set(self.requirement_bundle["requirement_order"])
            covered = set()
            normalised = []
            for index, step in enumerate(steps, 1):
                identifiers = step.get("requirement_ids", [])
                if not isinstance(step.get("description"), str) or not isinstance(identifiers, list):
                    return []
                if any(item not in required for item in identifiers):
                    return []
                covered.update(identifiers)
                normalised.append({"step_id": step.get("step_id", "S-%02d" % index),
                                   "description": step["description"], "requirement_ids": identifiers,
                                   "status": "pending"})
            return normalised if covered == required else []
        except (TypeError, ValueError, KeyError):
            return []

    def _write_json(self, filename, payload):
        with open(os.path.join(self.task_dir, filename), "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def record_plan_step(self, step_index, succeeded, evidence_path=None):
        """Record execution evidence without ever mutating the intent model."""
        if not self.requirement_bundle or step_index >= len(self.requirement_plan):
            return
        step = self.requirement_plan[step_index]
        step["status"] = "satisfied" if succeeded else "uncertain"
        evidence_ref = os.path.basename(evidence_path) if evidence_path else None
        statuses = []
        for obligation in self.requirement_bundle["runtime_obligations"]:
            status = "pending"
            evidence_refs = []
            for plan_step in self.requirement_plan:
                if obligation["requirement_id"] not in plan_step["requirement_ids"]:
                    continue
                if plan_step["status"] == "satisfied":
                    status = "satisfied"
                elif plan_step["status"] == "uncertain" and status == "pending":
                    status = "uncertain"
            if obligation["requirement_id"] in step["requirement_ids"] and evidence_ref:
                evidence_refs.append(evidence_ref)
            statuses.append({"requirement_id": obligation["requirement_id"], "status": status,
                             "evidence_refs": evidence_refs})
        self._write_json("requirement_plan.json", {"steps": self.requirement_plan})
        self._write_json("requirement_status.json", {"requirements": statuses})

    def build_rag(self, prompt: str, tasks):
        inputs = []
        outputs = []
        for task in tasks:
            tmp_input = "Now we give a app called " + \
                        task['task']['app_name']
            if task['task']['app_desc'] != "" and task['task']['app_desc'] is not None:
                tmp_input = tmp_input + \
                            ". We simply describe this app: " + \
                            task['task']['app_desc']['description']
            tmp_input = tmp_input + \
                        ". You want to complete such task: " + \
                        task['task']['task_desc'] + '.'
            inputs.append(tmp_input)

            tmp_output = ""
            for i, step in enumerate(task['task']['task_steps']):
                tmp_output = tmp_output + "step" + str(i+1) + ": " + step + "\n"

            outputs.append(tmp_output)

        prompt = re.sub(r"<input1>", inputs[0], prompt)
        prompt = re.sub(r"<output1>", outputs[0], prompt)
        self.logger.info(f"top1 example input: \n{inputs[0]}")
        self.logger.info(f"top1 example output: \n{outputs[0]}")
        prompt = re.sub(r"<input2>", inputs[1], prompt)
        prompt = re.sub(r"<output2>", outputs[1], prompt)
        self.logger.info(f"top2 example input: \n{inputs[1]}")
        self.logger.info(f"top2 example output: \n{outputs[1]}")

        return prompt


# === 验证器 ===
class TaskAsserter:
    def __init__(self, configs, logger):
        self.logger = logger
        self.configs = configs
        self.step_records = []

    # ========== 强同步 ==========
    def strong_correct(self, task_desc, task_steps, current_step, screenshot, mllm):
        self.logger.info("start strong correct")
        prompt = prompts.strong_correct_template
        prompt = re.sub(r"<task_description>", task_desc, prompt)
        prompt = re.sub(r"<task_steps>", task_steps, prompt)
        prompt = re.sub(r"<current_step>", current_step, prompt)
        return mllm.get_model_response(prompt, [screenshot])

    # ========== 弱同步 ==========
    def weak_correct(self, task_desc, task_steps, current_step, screenshot, mllm):
        self.logger.info("start weak correct")
        prompt = prompts.weak_correct_template
        prompt = re.sub(r"<task_description>", task_desc, prompt)
        prompt = re.sub(r"<task_steps>", task_steps, prompt)
        prompt = re.sub(r"<current_step>", current_step, prompt)
        return mllm.get_model_response(prompt, [screenshot])

    # ========== 整体断言 ==========
    def task_assert(self, app, app_desc, task_desc, final_screenshot, mllm):
        """
        判断：整个任务是否完成
        return: dict 评估报告
        """
        prompt = prompts.assert_template
        prompt = re.sub(r"<app_name>", app, prompt)

        # app描述
        if app_desc == "" or app_desc is None:
            prompt = re.sub(r"<app_description>", "", prompt)
        else:
            prompt = re.sub(r"<app_description>", "We simply describe this app: " + app_desc, prompt)

        prompt = re.sub(r"<task_description>", task_desc, prompt)

        status, rsp = mllm.get_model_response(prompt, [final_screenshot])

        # todo: 解析rsp

        self.logger.info(f"[ASSERT-TASK] {rsp}")

        report = {
            "task": task_desc,
            "final_status": "success" if status and "YES" in rsp.upper() else "fail",
            "model_judge": rsp,
            "step_records": self.step_records
        }
        return report


# === 主执行器 ===
class AppExecutor:
    def __init__(self, args):
        self.args = args
        self.configs = load_config()
        self.app = self.args["app"].replace("%_space", "_") or input("Enter app name: ")
        self.root_dir = self.args["root_dir"]
        self.app_dir = os.path.join(self.root_dir, "apps", self.app)
        self.work_dir = os.path.join(self.root_dir, "tasks")
        self.actions = []
        os.makedirs(self.work_dir, exist_ok=True)

        # 初始化任务与日志
        self.task_mgr = TaskManager(
            self.app,
            self.args["app_description"].replace("%_space", " "),
            self.args["task"].replace("%_space", " "),
            self.work_dir,
        )
        self.logger = LoggerFactory.create_logger(self.task_mgr.log_path)
        self.logger.info(f"Starting AppExecutor for {self.app}")
        self.task_mgr.logger = self.logger
        # TRACE: recorder is observational only; it never changes agent planning.
        self.trace_recorder = TraceRecorder(
            self.task_mgr.task_dir, self.app, self.task_mgr.app_desc, self.task_mgr.task_desc
        )

        # 初始化核心模块
        self.model_mgr = ModelManager(self.configs, self.logger)
        self.device_mgr = DeviceManager(self.logger)
        # TRACE: let the recorder read the UI hierarchy so it can store
        # resource-id/content-desc locators for OCR-empty icon buttons.
        self.trace_recorder.controller = self.device_mgr.controller
        self.doc_mgr = DocumentManager(self.app_dir, self.app, self.logger)
        self.asserter = TaskAsserter(self.configs, self.logger)

    def execute_entire(self):
        llm, mllm = self.model_mgr.llm, self.model_mgr.mllm

        controller = self.device_mgr.controller
        round_count = 0
        task_complete = False
        task_desc = self.task_mgr.task_desc
        last_acts = ""
        screenshot = None

        while round_count < self.configs["MAX_ROUNDS"]:
            round_count += 1
            screenshot = controller.get_screenshot(f"{self.app}_{round_count}", self.task_mgr.task_dir)
            page = Page(screenshot)
            labeled_img = os.path.join(self.task_mgr.task_dir, f"{self.app}_{round_count}_labeled.png")
            draw_bbox_multi(screenshot, labeled_img, page.get_components(), dark_mode=self.configs["DARK_MODE"])

            ui_doc = self.doc_mgr.get_ui_docs(page)
            prompt = re.sub(r"<ui_document>", ui_doc, prompts.execute_task_template)

            prompt = re.sub(r"<task_description>", task_desc, prompt)

            if last_acts == "":
                prompt = re.sub(r"<last_act>", "None", prompt)
            else:
                prompt = re.sub(r"<last_act>", last_acts, prompt)
            prompt = re.sub(r"<max_index>", str(len(page.get_components())), prompt)

            self.logger.info(f"Round {round_count}: Generating next action...")
            status, rsp = mllm.get_model_response(prompt, [labeled_img])
            if not status:
                self.logger.error(rsp)
                break

            sts, res = parse_explore_rsp(self.logger, rsp)
            act_name = res[0]
            if act_name in ["FINISH", "ERROR"]:
                task_complete = (act_name == "FINISH")
                break

            if sts == "yes":
                task_complete = True
                break

            print("if do: ")
            if_do = "yes"

            if if_do == "yes":
                ret = self.device_mgr.execute_action(act_name, res[:-1], page)
                if ret == "ERROR":
                    self.logger.error(f"Failed to execute {act_name}")
                    break

            else:
                pass

            self.actions.append(res[:-1])

            last_act = res[-1]
            last_acts = last_acts + '\n' + last_act
            time.sleep(self.configs["REQUEST_INTERVAL"])

        if task_complete:
            self.logger.info("Step completed successfully.")
            return True, screenshot
        else:
            self.logger.warning("Step ended or max rounds reached.")
            return False, screenshot

    def _snapshot_usage(self):
        """任务某一时刻各模型累计 token 用量的快照"""
        snap = []
        for m in (self.model_mgr.llm, self.model_mgr.mllm):
            if m is None or not hasattr(m, "get_usage_summary"):
                continue
            s = m.get_usage_summary()
            snap.append({"model": s["model"],
                         **{k: s[k] for k in _USAGE_FIELDS},
                         "records": s["records"]})
        return snap

    @staticmethod
    def _sum_usage(snap):
        totals = {k: sum(s[k] for s in snap) for k in _USAGE_FIELDS}
        totals["elapsed_sec"] = round(totals["elapsed_sec"], 3)
        return totals

    @staticmethod
    def _diff_usage(after, before):
        return {k: round(after[k] - before[k], 3) for k in _USAGE_FIELDS}

    def _dump_token_usage(self):
        """对比任务执行前后的 token 快照，算出本次任务的消耗量"""
        before_snap = self.usage_before
        after_snap = self._snapshot_usage()
        before = self._sum_usage(before_snap)
        after = self._sum_usage(after_snap)
        delta = self._diff_usage(after, before)

        models = []
        for b, a in zip(before_snap, after_snap):
            models.append({
                "model": a["model"],
                "before": {k: b[k] for k in _USAGE_FIELDS},
                "after": {k: a[k] for k in _USAGE_FIELDS},
                "delta": self._diff_usage(a, b),
                "records": a["records"],
            })

        report = {
            "app": self.app,
            "task": self.task_mgr.task_desc,
            "before": before,
            "after": after,
            "delta": delta,
            "models": models,
        }
        path = os.path.join(self.task_mgr.task_dir, "token_usage.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        for label, t in (("BEFORE", before), ("AFTER", after), ("DELTA", delta)):
            self.logger.info(f"[TOKEN] {label} calls={t['calls']} "
                             f"in={t['input_tokens']} out={t['output_tokens']} "
                             f"total={t['total_tokens']} elapsed={t['elapsed_sec']}s")
        self.logger.info(f"[TOKEN] token usage saved to {path}")

    def execute(self):
        llm, mllm = self.model_mgr.llm, self.model_mgr.mllm
        # 记录任务执行前的 token 基线
        self.usage_before = self._snapshot_usage()
        self.task_mgr.divide_task_steps(llm)

        self.logger.info("\n".join(map(str, self.task_mgr.task_steps)))

        step_index = 0
        all_steps_satisfied = False

        all_time = 0
        time_count = 0

        while step_index < len(self.task_mgr.task_steps):
            task_steps = self.task_mgr.task_steps
            task_steps_str = "\n".join(map(str, task_steps))
            step = task_steps[step_index]

            self.logger.info(f"Executing step: {step}")
            flag, step_end_img, tmp_time = self._execute_step(step, step_index, mllm)
            self.task_mgr.record_plan_step(step_index, flag, step_end_img)
            # TRACE: persist each high-level natural-language subtask and its evidence.
            self.trace_recorder.record_step("S-%02d" % (step_index + 1), step, flag, step_end_img)
            if tmp_time > 0:
                all_time += tmp_time
                time_count += 1

            # 成功执行到了最后一步
            if step_index == len(task_steps) - 1 and flag is True:
                self.logger.info(f"the last step of the task is completed")
                all_steps_satisfied = True
                break

            # 开关控制是否进行同步
            elif CORRECT_SWITCH is False:
                step_index = step_index + 1
                continue

            # 进行强同步
            if flag is False:
                self.logger.warning("Task execute failed.")
                status, rsp \
                    = self.asserter.strong_correct(self.task_mgr.task_desc, task_steps_str, step, step_end_img, mllm)
                self.logger.info(f"the strong correct rsp: {rsp}")
                if status:
                    new_steps = parse_divide_rsp(rsp)
                    self.task_mgr.task_steps = task_steps[:step_index + 1] + new_steps

            # 进行弱同步
            else:
                status, rsp \
                    = self.asserter.weak_correct(self.task_mgr.task_desc, task_steps_str, step, step_end_img, mllm)
                self.logger.info(f"the weak correct rsp: {rsp}")
                if status:
                    if rsp == "finish":
                        break

                    elif rsp == "continue":
                        pass

                    else:
                        new_steps = parse_divide_rsp(rsp)
                        self.task_mgr.task_steps = task_steps[:step_index + 1] + new_steps

            step_index = step_index + 1

        self.logger.info(f"Task end")
        self.logger.info(f"action count: {len(self.actions)}")
        if time_count > 0:
            self.logger.info(f"average time: {all_time/time_count}")
        self._dump_token_usage()
        # TRACE: only a fully successful run is normalised into a standalone replay case.
        self.trace_recorder.finish(all_steps_satisfied)
        if all_steps_satisfied:
            case_path = normalize_successful_trace(self.trace_recorder.path)
            self.logger.info("[TRACE] normalized replay case: %s", case_path)

    def _execute_step(self, step, step_index, mllm):
        if "the search bar and search for" in step and USE_RULE:
            self.logger.info(f"do search step")
            return self._execute_search_step(step, step_index, mllm)
        else:
            self.logger.info(f"do normal step")
            return self._execute_normal_step(step, step_index, mllm)

    def _execute_normal_step(self, step, step_index, mllm):
        controller = self.device_mgr.controller
        round_count = 0
        task_complete = False
        task_desc = self.task_mgr.task_desc
        task_steps = self.task_mgr.task_steps
        last_acts = ""
        screenshot = None
        average_time = 0
        last_action_name = ""
        last_action_params = ""
        repeat_count = 0

        while round_count < self.configs["MAX_ROUNDS"]:
            start_time = time.time()
            round_count += 1
            screenshot = controller.get_screenshot(f"{self.app}_{step_index}_{round_count}", self.task_mgr.task_dir)
            if screenshot == "ERROR":
                self.logger.error("Screenshot capture failed; stopping this step before visual parsing.")
                break
            page = Page(screenshot)
            labeled_img = os.path.join(self.task_mgr.task_dir, f"{self.app}_{step_index}_{round_count}_labeled.png")
            draw_bbox_multi(screenshot, labeled_img, page.get_components(), dark_mode=self.configs["DARK_MODE"])

            ui_doc = self.doc_mgr.get_ui_docs(page)
            prompt = re.sub(r"<ui_document>", ui_doc, prompts.execute_task_template)

            prompt = re.sub(r"<task_description>", task_desc, prompt)
            prompt = re.sub(r"<task_steps>", "\n".join(map(str, task_steps)), prompt)
            prompt = re.sub(r"<current_step>", step, prompt)

            if last_acts == "":
                prompt = re.sub(r"<last_act>", "None", prompt)
            else:
                prompt = re.sub(r"<last_act>", last_acts, prompt)
            prompt = re.sub(r"<max_index>", str(len(page.get_components())), prompt)

            self.logger.info(f"Round {round_count}: Generating next action...")
            status, rsp = mllm.get_model_response(prompt, [labeled_img])
            if not status:
                self.logger.error(rsp)
                break

            sts, res = parse_explore_rsp(self.logger, rsp)
            act_name = res[0]
            if act_name in ["FINISH", "ERROR"]:
                task_complete = (act_name == "FINISH")
                break

            # 重复动作检测：连续3次相同 action 且参数一致则提前终止
            current_action_params = res[1:-1] if len(res) > 1 else []
            if act_name == last_action_name and current_action_params == last_action_params:
                repeat_count += 1
                if repeat_count >= 3:
                    self.logger.warning(f"Action '{act_name}' repeated {repeat_count} times without progress, breaking")
                    break
            else:
                repeat_count = 0
            last_action_name = act_name
            last_action_params = current_action_params

            if sts == "yes" and round_count > 1:
                task_complete = True
                break

            print("if do: ")
            if_do = "yes"

            if if_do == "yes":
                # TRACE: capture the hierarchy *before* the action runs, so the
                # recorder can map the tapped box to its resource-id on the
                # still-unchanged screen (not the post-action screen).
                xml_path = None
                if act_name in ("tap", "long_press", "swipe", "clear"):
                    xml_path = self.device_mgr.controller.get_xml(
                        "trace_locator", self.task_mgr.task_dir)
                ret = self.device_mgr.execute_action(act_name, res[:-1], page)
                if ret == "ERROR":
                    self.logger.error(f"Failed to execute {act_name}")
                    break
                # TRACE: save the original UI index as evidence; normalisation drops it.
                self.trace_recorder.record_action(
                    "S-%02d" % (step_index + 1), step, act_name, res[:-1], res[-1],
                    screenshot, page.get_components(), xml_path
                )

            else:
                pass

            self.actions.append(res[:-1])

            last_act = res[-1]
            last_acts = last_acts + '\n' + last_act
            time.sleep(self.configs["REQUEST_INTERVAL"])

            end_time = time.time()
            execution_time = int((end_time - start_time) * 1000)
            average_time = int((average_time * (round_count - 1) + execution_time) / round_count)

            self.logger.info(f"当前轮次: {round_count}; 执行时间为: {execution_time}")

        if task_complete:
            self.logger.info("Step completed successfully.")
            return True, screenshot, average_time
        else:
            self.logger.warning("Step ended or max rounds reached.")
            return False, screenshot, average_time

    def _execute_search_step(self, step, step_index, mllm):
        # 先走到有搜索框的地方
        # 要先确定到哪个有搜索框的界面。可以先不管
        # 对当前搜索框页面建模
        controller = self.device_mgr.controller
        screenshot = self.device_mgr.controller.get_screenshot(f"{self.app}_{step_index}_search",
                                                               self.task_mgr.task_dir)
        if screenshot == "ERROR":
            self.logger.error("Screenshot capture failed before search-step visual parsing.")
            return False, screenshot, 0
        page = Page(screenshot)
        # 提取搜索框位置
        prompt = prompts.find_search_bar_template
        status, rsp = mllm.get_model_response(prompt, [screenshot])
        self.logger.info(f"the search bar: {rsp}")
        if status:
            x, y = rsp.split(",")[0], rsp.split(",")[1]
            # 提取搜索内容
            match = re.search(r"<([^<>]+)>", step)
            if match:
                content = match.group(1)
                ret = self.device_mgr.execute_action("search", [x, y, content], page)
                if ret != "ERROR":
                    # TRACE: preserve rule-based search as a portable semantic action.
                    self.trace_recorder.record_action(
                        "S-%02d" % (step_index + 1), step, "search",
                        ["search", x, y, content], "Search for %s" % content,
                        screenshot, page.get_components()
                    )
                    time.sleep(self.configs["REQUEST_INTERVAL"])
                    screenshot = controller.get_screenshot(f"{self.app}_{step_index}_search_end",
                                                           self.task_mgr.task_dir)
                    return True, screenshot, 0
            else:
                self.logger.error(f"step has no content to search: {step}")

        time.sleep(self.configs["REQUEST_INTERVAL"])
        screenshot = controller.get_screenshot(f"{self.app}_{step_index}_search_end", self.task_mgr.task_dir)
        return False, screenshot, 0

    def _execute_smart_input_step(self, step, step_index, mllm):
        """
        模式二：基于问答参数填充的智能输入 (QA-Parameterized Input)
        逻辑：截图 -> 询问LLM四个参数(位置/清空/内容/确认) -> 规则引擎组装动作
        """
        import json
        import time

        # 1. 视觉感知：获取截图并绘制 SoM 标号
        controller = self.device_mgr.controller
        screenshot = controller.get_screenshot(f"{self.app}_{step_index}_input", self.task_mgr.task_dir)
        page = Page(screenshot)
        labeled_img = os.path.join(self.task_mgr.task_dir, f"{self.app}_{step_index}_input_labeled.png")
        # 绘制标号，供大模型识别 target_id 和 confirm_id
        draw_bbox_multi(screenshot, labeled_img, page.get_components(), dark_mode=self.configs["DARK_MODE"])

        # 2. 构造 Prompt：注入当前步骤描述
        # 注意：这里使用的是更新后的 smart_input_template，包含 input_content 问题
        prompt = prompts.smart_input_template
        prompt = re.sub(r"<step_description>", step, prompt)

        self.logger.info(f"[SmartInput] Querying LLM for parameters... Step: {step}")

        # 3. 大模型推理：获取参数
        status, rsp = mllm.get_model_response(prompt, [labeled_img])
        if not status:
            self.logger.error("LLM failed to respond for smart input.")
            return False, screenshot

        # 4. 解析 JSON 响应
        try:
            # 简单的 JSON 清洗逻辑
            json_str = rsp
            if "```json" in rsp:
                json_str = rsp.split("```json")[1].split("```")[0].strip()
            elif "```" in rsp:
                json_str = rsp.split("```")[1].split("```")[0].strip()

            params = json.loads(json_str)
            self.logger.info(f"[SmartInput] Parsed Params: {params}")
        except Exception as e:
            self.logger.error(f"Failed to parse JSON: {e}\nRSP: {rsp}")
            return False, screenshot

        # 5. 规则引擎：动态组装并执行动作序列
        try:
            # --- 参数提取 ---
            target_id = int(params.get("target_id", -1))
            input_content = params.get("input_content", "")
            need_clear = params.get("need_clear", False)
            confirm_info = params.get("confirm_action", {})

            if target_id == -1:
                self.logger.error("Invalid target_id from LLM")
                return False, screenshot

            # --- 原子动作 1: 清空 (Clear) ---
            # 如果大模型认为需要清空 (例如输入框有默认值)
            if need_clear:
                self.logger.info(f"[Rule] Clearing text in element {target_id}")
                # 1. 点击获取焦点
                # 2. 发送清除指令 (这里使用一种通用的长按删除逻辑，或者 ADB KEYCODE_CLEAR)
                # 模拟：移动光标到末尾 -> 长按删除键
                # 简单实现：多次发送删除键
                self.device_mgr.execute_action("clear", [target_id], page)

            # --- 原子动作 2: 输入 (Input) ---
            if input_content:
                self.logger.info(f"[Rule] Inputting content: '{input_content}'")
                # 1. 再次点击确保焦点 (防止清空操作丢失焦点)
                self.device_mgr.execute_action("tap", [target_id], page)
                time.sleep(0.5)
                # 2. 输入文本
                self.device_mgr.execute_action("text", [None, input_content], page)
            else:
                self.logger.warning("[Rule] LLM returned empty input_content, skipping text input.")

            # --- 原子动作 3: 确认 (Confirm) ---
            if confirm_info and confirm_info.get("need_confirm", False):
                confirm_id = confirm_info.get("confirm_id")

                # 情况 A: 点击屏幕上的按钮 (如"搜索"、"提交")
                if confirm_id is not None and confirm_id != -1:
                    self.logger.info(f"[Rule] Tapping confirm button {confirm_id}")
                    time.sleep(1)  # 等待UI响应
                    self.device_mgr.execute_action("tap", [confirm_id], page)

                # 情况 B: 点击键盘上的回车 (LLM返回需要确认但没有confirm_id)
                else:
                    self.logger.info(f"[Rule] Pressing Enter on keyboard")
                    time.sleep(0.5)
                    self.device_mgr.controller.device.shell("input keyevent 66")  # ENTER

            return True, screenshot

        except Exception as e:
            self.logger.error(f"Error executing smart input sequence: {e}")
            import traceback
            traceback.print_exc()
            return False, screenshot


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AppAgent Executor (OOP + Logging)")
    parser.add_argument("--app")
    parser.add_argument("--root_dir", default="./")
    parser.add_argument("--app_description")
    parser.add_argument("--task")
    args = vars(parser.parse_args())

    executor = AppExecutor(args)
    executor.execute()
