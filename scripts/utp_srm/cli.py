"""Standalone translation utility, matching the preappagent batch boundary."""
import argparse
import json
from pathlib import Path
from .downstream import ExistingWorkflowAdapter
from .serialization import write_json, write_jsonl
from .translator import RequirementTranslator, TranslationRequest

def _parser():
    parser=argparse.ArgumentParser(description="Translate mobile tasks into UTP-SRM")
    commands=parser.add_subparsers(dest="command",required=True)
    one=commands.add_parser("translate"); one.add_argument("--task-id",required=True); one.add_argument("--app",required=True); one.add_argument("--description",required=True); one.add_argument("--app-description"); one.add_argument("--model-out",required=True); one.add_argument("--handoff-out")
    batch=commands.add_parser("batch"); batch.add_argument("--input",required=True); batch.add_argument("--model-out",required=True); batch.add_argument("--handoff-out")
    return parser
def main():
    args=_parser().parse_args(); translator=RequirementTranslator(); adapter=ExistingWorkflowAdapter()
    if args.command=="translate":
        model=translator.translate(TranslationRequest(args.task_id,args.app,args.description,args.app_description)); write_json(args.model_out,model.to_dict())
        if args.handoff_out: write_json(args.handoff_out,adapter.build(model).to_dict())
        return
    models=[]; handoffs=[]
    for line_number,line in enumerate(Path(args.input).read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        item=json.loads(line)
        try: model=translator.translate(TranslationRequest(str(item["task_id"]),item["app_name"],item["task_description"],item.get("app_description")))
        except Exception as exc: raise RuntimeError("input line %d: %s"%(line_number,exc))
        models.append(model.to_dict()); handoffs.append(adapter.build(model).to_dict())
    write_jsonl(args.model_out,models)
    if args.handoff_out: write_jsonl(args.handoff_out,handoffs)
if __name__=="__main__": main()
