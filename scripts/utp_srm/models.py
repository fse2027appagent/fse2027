"""Immutable UTP-SRM domain model used by the AppAgent front end."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "utp-srm/0.1"

class RequirementKind(str, Enum):
    CONTEXT_CONDITION = "ContextCondition"
    INTERACTION = "Interaction"
    EXPECTED_OUTCOME = "ExpectedOutcome"

class Provenance(str, Enum):
    EXPLICIT = "explicit"
    DETERMINISTIC = "deterministic"
    LLM_INFERRED = "llm_inferred"

@dataclass(frozen=True)
class SourceSpan:
    text: str; start: int; end: int; provenance: Provenance = Provenance.EXPLICIT
    def validate_against(self, original: str) -> List[str]:
        if not 0 <= self.start <= self.end <= len(original): return ["invalid source span [%d, %d)" % (self.start, self.end)]
        return [] if original[self.start:self.end] == self.text else ["source text mismatch"]

@dataclass(frozen=True)
class TestDataItem: name: str; value: Any; data_type: str = "string"; source: Optional[SourceSpan] = None
@dataclass(frozen=True)
class RequirementSpecification:
    operation: str; target: Optional[str] = None; value: Any = None; operator: Optional[str] = None; arguments: Dict[str, Any] = field(default_factory=dict)
@dataclass(frozen=True)
class AtomicTestRequirement:
    id: str; kind: RequirementKind; specification: RequirementSpecification; source: SourceSpan; description: str; parameters: Tuple[str, ...] = ()
@dataclass(frozen=True)
class RequirementDependency: predecessor: str; successor: str; relation: str = "precedes"; rationale: str = "explicit_or_semantically_required_order"
@dataclass(frozen=True)
class TestContext: id: str; test_item: str; test_level: str = "system"; test_type: str = "functional"; app_description: Optional[str] = None
@dataclass(frozen=True)
class TestObjective: id: str; specification: str; source: SourceSpan
@dataclass
class TranslationDiagnostics:
    warnings: List[str] = field(default_factory=list); unresolved: List[Dict[str, str]] = field(default_factory=list); unsupported_inferences: List[str] = field(default_factory=list); extraction_backend: str = "deterministic"
@dataclass
class StructuredRequirementModel:
    task_id: str; original_description: str; context: TestContext; objective: TestObjective; requirements: List[AtomicTestRequirement]; test_data: List[TestDataItem] = field(default_factory=list); dependencies: List[RequirementDependency] = field(default_factory=list); diagnostics: TranslationDiagnostics = field(default_factory=TranslationDiagnostics); schema_version: str = SCHEMA_VERSION
    def to_dict(self) -> Dict[str, Any]: return _enum_values(asdict(self))

def _enum_values(value):
    if isinstance(value, Enum): return value.value
    if isinstance(value, dict): return {key: _enum_values(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)): return [_enum_values(item) for item in value]
    return value
