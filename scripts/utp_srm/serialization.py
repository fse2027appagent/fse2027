import json
from pathlib import Path
def write_json(path,payload):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True); target.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def write_jsonl(path,payloads):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    with target.open("w",encoding="utf-8") as handle:
        for payload in payloads: handle.write(json.dumps(payload,ensure_ascii=False)+"\n")
