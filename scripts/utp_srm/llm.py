"""Provider-neutral optional semantic-extraction boundary."""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol, Tuple
@dataclass(frozen=True)
class LLMExtractionRequest:
    app_name:str; app_description:Optional[str]; task_description:str; allowed_requirement_kinds:Tuple[str,...]; allowed_operations:Tuple[str,...]; output_schema:Dict[str,Any]
class LLMExtractor(Protocol):
    name: str
    def extract(self, request:LLMExtractionRequest)->Dict[str,Any]: ...
class CallableLLMExtractor:
    def __init__(self, callback, name="custom-llm"): self.callback=callback; self.name=name
    def extract(self, request): return self.callback(request)
LLM_OUTPUT_SCHEMA={"type":"object","required":["objective","requirements","test_data","dependencies"],"properties":{"objective":{"type":"object","required":["specification","source_start","source_end"]},"requirements":{"type":"array"},"test_data":{"type":"array"},"dependencies":{"type":"array"},"unresolved":{"type":"array"}}}
