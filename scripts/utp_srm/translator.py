"""Hybrid compiler: deterministic by default, validated LLM drafts optionally."""
from dataclasses import dataclass
from typing import Any, Optional
from .llm import LLMExtractor, LLMExtractionRequest, LLM_OUTPUT_SCHEMA
from .models import AtomicTestRequirement, Provenance, RequirementDependency, RequirementKind, RequirementSpecification, SourceSpan, StructuredRequirementModel, TestContext, TestDataItem, TestObjective, TranslationDiagnostics
from .rules import ALLOWED_OPERATIONS, match_clause, split_clauses
from .validator import validate_model
@dataclass(frozen=True)
class TranslationRequest: task_id:str; app_name:str; task_description:str; app_description:Optional[str]=None; use_llm:bool=False
class RequirementTranslator:
    def __init__(self,llm_extractor=None): self.llm_extractor=llm_extractor
    def translate(self,request):
        if not request.task_description.strip(): raise ValueError("task_description must not be empty")
        if request.use_llm:
            if self.llm_extractor is None: raise ValueError("use_llm=True requires an LLMExtractor")
            model=self._from_llm(request,self.llm_extractor.extract(self._llm_request(request)))
        else: model=self._from_rules(request)
        validate_model(model); return model
    def _llm_request(self,request): return LLMExtractionRequest(request.app_name,request.app_description,request.task_description,tuple(kind.value for kind in RequirementKind),ALLOWED_OPERATIONS,LLM_OUTPUT_SCHEMA)
    def _from_rules(self,request):
        requirements=[]; data=[]; used=set(); diagnostics=TranslationDiagnostics(extraction_backend="deterministic-rules")
        for index,clause in enumerate(split_clauses(request.task_description),1):
            matched=match_clause(clause.text); names=[]
            for name,value,data_type in matched.data:
                unique=name; suffix=2
                while unique in used: unique="%s_%d"%(name,suffix); suffix+=1
                used.add(unique); names.append(unique); data.append(TestDataItem(unique,value,data_type,SourceSpan(clause.text,clause.start,clause.end)))
            if matched.operation=="generic_interaction": diagnostics.unresolved.append({"text":clause.text,"reason":"No deterministic semantic operation matched; optional LLM extraction can refine it."})
            requirements.append(AtomicTestRequirement("TR-%03d"%index,matched.kind,RequirementSpecification(matched.operation,matched.target,matched.value,matched.operator,matched.arguments or {}),SourceSpan(clause.text,clause.start,clause.end),clause.text,tuple(names)))
        description=request.task_description; full=SourceSpan(description,0,len(description)); deps=[RequirementDependency(requirements[i].id,requirements[i+1].id) for i in range(len(requirements)-1)]
        objective="On %s, complete the requested task: %s"%(request.app_name," -> ".join(item.description for item in requirements))
        return StructuredRequirementModel(request.task_id,description,TestContext("TCX-"+request.task_id,request.app_name,app_description=request.app_description),TestObjective("TO-"+request.task_id,objective,full),requirements,data,deps,diagnostics)
    def _from_llm(self,request,draft):
        description=request.task_description; diagnostics=TranslationDiagnostics(extraction_backend=getattr(self.llm_extractor,"name","llm"),unresolved=list(draft.get("unresolved",[]))); requirements=[]
        for index,item in enumerate(draft.get("requirements",[]),1):
            operation=item["operation"] if item["operation"] in ALLOWED_OPERATIONS else "generic_interaction"
            if operation!=item["operation"]: diagnostics.warnings.append("Unsupported LLM operation in TR-%03d"%index)
            source=SourceSpan(description[int(item["source_start"]):int(item["source_end"])],int(item["source_start"]),int(item["source_end"]),Provenance.LLM_INFERRED)
            requirements.append(AtomicTestRequirement("TR-%03d"%index,RequirementKind(item["kind"]),RequirementSpecification(operation,item.get("target"),item.get("value"),item.get("operator"),dict(item.get("arguments",{}))),source,item["description"],tuple(item.get("parameters",[]))))
        data=[TestDataItem(item["name"],item.get("value"),item.get("data_type","string")) for item in draft.get("test_data",[])]
        deps=[RequirementDependency(_ref(item["predecessor"]),_ref(item["successor"]),rationale=item.get("rationale","llm_extracted_order")) for item in draft.get("dependencies",[])]
        objective=draft["objective"]; source=SourceSpan(description[int(objective["source_start"]):int(objective["source_end"])],int(objective["source_start"]),int(objective["source_end"]),Provenance.LLM_INFERRED)
        return StructuredRequirementModel(request.task_id,description,TestContext("TCX-"+request.task_id,request.app_name,app_description=request.app_description),TestObjective("TO-"+request.task_id,objective["specification"],source),requirements,data,deps,diagnostics)
def _ref(value): return "TR-%03d"%value if isinstance(value,int) or not str(value).startswith("TR-") else value
