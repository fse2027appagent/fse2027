"""Stable adapters from SRM to AppAgent's RAG, planning, and runtime stages."""
from dataclasses import asdict, dataclass
from typing import Any, Dict, Tuple
from .models import RequirementKind
@dataclass(frozen=True)
class RetrievalInput: app_name:str; app_description:str; intent_labels:Tuple[str,...]; task_query:str; composite_text:str
@dataclass(frozen=True)
class PlanningInput: task_description:str; structured_objective:str; ordered_requirements:Tuple[Dict[str,Any],...]; test_data:Dict[str,Any]; hard_constraints:Tuple[str,...]; expected_outcomes:Tuple[Dict[str,Any],...]
@dataclass(frozen=True)
class RuntimeObligation: requirement_id:str; kind:str; completion_specification:Dict[str,Any]
@dataclass(frozen=True)
class DownstreamBundle:
    retrieval:RetrievalInput; planning:PlanningInput; runtime_obligations:Tuple[RuntimeObligation,...]; requirement_order:Tuple[str,...]
    def to_dict(self): return asdict(self)
class ExistingWorkflowAdapter:
    def build(self,model):
        order=tuple(_topological_order(model)); by_id={item.id:item for item in model.requirements}; ordered=[by_id[item_id] for item_id in order]
        intents=tuple(dict.fromkeys(item.specification.operation for item in ordered)); app_desc=model.context.app_description or ""
        composite="\n".join(["App Name: %s"%model.context.test_item,"App Description: %s"%app_desc,"Intent: %s"%", ".join(intents),"Objective: %s"%model.objective.specification,"Requirements:"]+["- [%s] %s"%(item.id,item.description) for item in ordered])
        payloads=tuple({"requirement_id":item.id,"kind":item.kind.value,"description":item.description,"specification":asdict(item.specification),"parameters":list(item.parameters)} for item in ordered)
        expected=tuple(item for item in payloads if item["kind"]==RequirementKind.EXPECTED_OUTCOME.value)
        return DownstreamBundle(RetrievalInput(model.context.test_item,app_desc,intents,model.original_description,composite),PlanningInput(model.original_description,model.objective.specification,payloads,{item.name:item.value for item in model.test_data},tuple("Preserve and cover requirement %s"%item_id for item_id in order),expected),tuple(RuntimeObligation(item.id,item.kind.value,asdict(item.specification)) for item in ordered),order)
def _topological_order(model):
    index={item.id:i for i,item in enumerate(model.requirements)}; adjacent={item.id:[] for item in model.requirements}; degree={item.id:0 for item in model.requirements}
    for edge in model.dependencies: adjacent[edge.predecessor].append(edge.successor); degree[edge.successor]+=1
    ready=sorted((node for node,value in degree.items() if value==0),key=index.get); result=[]
    while ready:
        node=ready.pop(0); result.append(node)
        for successor in adjacent[node]:
            degree[successor]-=1
            if degree[successor]==0: ready.append(successor); ready.sort(key=index.get)
    return result
