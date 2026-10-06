import re
import time
from abc import abstractmethod
from typing import List
from http import HTTPStatus

import cv2
import requests
import dashscope

from utils import print_with_color, encode_image


class BaseModel:
    def __init__(self):
        pass

    @abstractmethod
    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        pass


class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        for img in images:
            base64_img = encode_image(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            })
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "models": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        response = requests.post(self.base_url, headers=headers, json=payload).json()
        if "error" not in response:
            usage = response["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            print_with_color(f"Request cost is "
                             f"${'{0:.2f}'.format(prompt_tokens / 1000 * 0.01 + completion_tokens / 1000 * 0.03)}",
                             "yellow")
        else:
            return False, response["error"]["message"]
        return True, response["choices"][0]["message"]["content"]


class QwenModel(BaseModel):
    def __init__(self, api_key: str, model: str, logger=None):
        super().__init__()
        self.model = model
        self.logger = logger
        # 不能仅依赖 "vl"：新版 qwen3.7-plus 名称不含该字符串，但仍支持
        # 图像输入，必须通过 MultiModalConversation 调用。
        self.is_multimodal = (
            "vl" in model.lower()
            or model.lower() in {"qwen3.7-plus", "qwen3.7-plus-2026-05-26"}
        )
        dashscope.api_key = api_key
        self.usage_records = []

    def _record_usage(self, response, multimodal: bool, elapsed: float):
        """从 DashScope 响应中提取 token 用量并记入 usage_records"""
        usage = getattr(response, "usage", None)
        if usage is None:
            return
        input_tokens = _usage_get(usage, "input_tokens") or 0
        output_tokens = _usage_get(usage, "output_tokens") or 0
        total_tokens = _usage_get(usage, "total_tokens") or input_tokens + output_tokens
        # 命中缓存的 token 数，DashScope 放在 prompt_tokens_details 里
        cached_tokens = _usage_get(_usage_get(usage, "prompt_tokens_details", {}), "cached_tokens") or 0
        fresh_tokens = input_tokens - cached_tokens
        record = {
            "model": self.model,
            "api": "multimodal" if multimodal else "text",
            "input_tokens": input_tokens,
            "cached_tokens": cached_tokens,
            "fresh_tokens": fresh_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "elapsed_sec": round(elapsed, 3),
        }
        self.usage_records.append(record)
        if self.logger:
            self.logger.info(
                f"[TOKEN] {record['model']} ({record['api']}) "
                f"in={input_tokens} (cached={cached_tokens}, fresh={fresh_tokens}) "
                f"out={output_tokens} total={total_tokens} "
                f"elapsed={record['elapsed_sec']}s"
            )

    def get_usage_summary(self):
        """返回该模型实例的累计用量与每次调用明细"""
        return {
            "model": self.model,
            "calls": len(self.usage_records),
            "input_tokens": sum(r["input_tokens"] for r in self.usage_records),
            "cached_tokens": sum(r["cached_tokens"] for r in self.usage_records),
            "fresh_tokens": sum(r["fresh_tokens"] for r in self.usage_records),
            "output_tokens": sum(r["output_tokens"] for r in self.usage_records),
            "total_tokens": sum(r["total_tokens"] for r in self.usage_records),
            "elapsed_sec": round(sum(r["elapsed_sec"] for r in self.usage_records), 3),
            "records": self.usage_records,
        }

    def get_model_response(self, prompt: str, images: List[str]) -> (bool, str):
        if not images and not self.is_multimodal:
            # 纯文本模型（如 qwen-plus）不支持多模态接口，走 Generation
            start = time.time()
            response = dashscope.Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            if response.status_code == HTTPStatus.OK:
                self._record_usage(response, multimodal=False, elapsed=time.time() - start)
                return True, response.output.text
            else:
                return False, response.message

        content = [{
            "text": prompt
        }]
        for img in images:
            img_path = f"file://{img}"
            content.append({
                "image": img_path
            })
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        start = time.time()
        response = dashscope.MultiModalConversation.call(model=self.model, messages=messages)
        if response.status_code == HTTPStatus.OK:
            self._record_usage(response, multimodal=True, elapsed=time.time() - start)
            return True, response.output.choices[0].message.content[0]["text"]
        else:
            return False, response.message


def _usage_get(obj, key, default=0):
    """读取 DashScope usage 字段：usage 是 dict 子类，但 prompt_tokens_details 是纯 dict"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _safe_findall(pattern, text, default=""):
    """安全地从文本中提取第一个匹配项，未匹配时返回默认值"""
    matches = re.findall(pattern, text, re.MULTILINE)
    return matches[0] if matches else default


def parse_explore_rsp(logger, rsp):
    try:
        observation = _safe_findall(r"Observation: (.*?)$", rsp)
        think = _safe_findall(r"Thought: (.*?)$", rsp)
        step_sts = _safe_findall(r"Subtask Status: (.*?)$", rsp, "none")
        act = _safe_findall(r"Action: (.*?)$", rsp)
        last_act = _safe_findall(r"Summary: (.*?)$", rsp)

        info = "Observation: \n" + observation + "\n" \
               + "Thought: \n" + think + "\n" \
               + "Subtask Status: \n" + step_sts + "\n" \
               + "Action: \n" + act + "\n" \
               + "Summary: \n" + last_act

        logger.info(f"mllm response: \n{info}")
        if "FINISH" in act:
            return step_sts, ["FINISH"]

        act_name = act.split("(")[0]
        if act_name == "tap":
            area = int(re.findall(r"tap\((.*?)\)", act)[0])
            return step_sts, [act_name, area, last_act]
        elif act_name == "text":
            input_str = re.findall(r"text\((.*?)\)", act)[0][1:-1]
            return step_sts, [act_name, input_str, last_act]
        elif act_name == "long_press":
            area = int(re.findall(r"long_press\((.*?)\)", act)[0])
            return step_sts, [act_name, area, last_act]
        elif act_name == "back":
            return step_sts, [act_name, "", last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0]
            area, swipe_dir, dist = params.split(",")
            area = int(area)
            swipe_dir = swipe_dir.strip()[1:-1]
            dist = dist.strip()[1:-1]
            return step_sts, [act_name, area, swipe_dir, dist, last_act]
        else:
            logger.error(f"ERROR: Undefined act {act_name}!", "red")
            return step_sts, ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the models response: {e}", "red")
        print_with_color(rsp, "red")
        return step_sts, ["ERROR"]


def parse_grid_rsp(rsp):
    try:
        observation = re.findall(r"Observation: (.*?)$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        act = re.findall(r"Action: (.*?)$", rsp, re.MULTILINE)[0]
        last_act = re.findall(r"Summary: (.*?)$", rsp, re.MULTILINE)[0]
        print_with_color("Observation:", "yellow")
        print_with_color(observation, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        print_with_color("Action:", "yellow")
        print_with_color(act, "magenta")
        print_with_color("Summary:", "yellow")
        print_with_color(last_act, "magenta")
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            params = re.findall(r"tap\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "long_press":
            params = re.findall(r"long_press\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0].split(",")
            start_area = int(params[0].strip())
            start_subarea = params[1].strip()[1:-1]
            end_area = int(params[2].strip())
            end_subarea = params[3].strip()[1:-1]
            return [act_name + "_grid", start_area, start_subarea, end_area, end_subarea, last_act]
        elif act_name == "grid":
            return [act_name]
        else:
            print_with_color(f"ERROR: Undefined act {act_name}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the models response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_reflect_rsp(rsp):
    try:
        decision = re.findall(r"Decision: (.*?)\s*$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        print_with_color("Decision:", "yellow")
        print_with_color(decision, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        if decision == "INEFFECTIVE":
            return [decision, think]
        elif decision == "BACK" or "CONTINUE" == decision or "SUCCESS" == decision:
            doc = re.findall(r"Documentation: (.*?)$", rsp, re.MULTILINE)[0]
            print_with_color("Documentation:", "yellow")
            print_with_color(doc, "magenta")
            return [decision, think, doc]
        else:
            print_with_color(f"ERROR: Undefined decision {decision}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the models response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_divide_rsp(rsp):
    try:
        task_steps = []
        for step in re.findall(r"step\d+:\s*(.*)", rsp):
            task_steps.append(step.strip())
        return task_steps
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the models response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_assert_rsp(logger, rsp):
    try:
        type = re.findall(r"Type: (.*?)$", rsp, re.MULTILINE)[0]
        impact = re.findall(r"Impact: (.*?)$", rsp, re.MULTILINE)[0]
        reason = re.findall(r"Reason: (.*?)$", rsp, re.MULTILINE)[0]
        steps = re.findall(r"Check Steps: (.*?)$", rsp, re.MULTILINE)[0]
        info = "Type: \n" + type + "\n" \
               + "Impact: \n" + impact + "\n" \
               + "Reason: \n" + reason + "\n" \
               + "Check Steps: \n" + steps + "\n" \

        logger.info(f"mllm response: \n{info}")
        return type, impact, reason, steps
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the models response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


if __name__ == '__main__':
    from config import load_config
    import prompts
    configs = load_config()

    llm = None
    mllm = None
    if configs["MODEL"] == "Qwen":
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                         model=configs["QWEN_MODEL_MLLM"])
        llm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                        model=configs["QWEN_MODEL_LLM"])

    prompt = re.sub(r"<app_name>", "Baidu Map", prompts.divide_task_template)
    prompt = re.sub(r"<app_description>", "a commonly used map app", prompt)
    prompt = re.sub(r"<task_description>", "find nearby cafes, arrange them by distance, and navigate to the nearest "
                                           "one", prompt)

    prompt2 = "在你看来这张图的长宽各是多少个像素？"

    status, rsp = mllm.get_model_response(prompt=prompt2, images=["../0.png"])

    # print(prompt)
    print(rsp)
    # print(parse_divide_rsp(rsp))
