"""Deterministic model validation, including dependency-DAG validation."""
from collections import defaultdict, deque
from .rules import ALLOWED_OPERATIONS
class ModelValidationError(ValueError):
    def __init__(self, errors): self.errors=errors; super().__init__("Invalid structured requirement model:\n- "+"\n- ".join(errors))
def validate_model(model):
    errors=[]
    if not model.original_description.strip(): errors.append("original_description must not be empty")
    if not model.requirements: errors.append("at least one test requirement is required")
    ids=[item.id for item in model.requirements]
    if len(ids)!=len(set(ids)): errors.append("requirement IDs must be unique")
    names={item.name for item in model.test_data}
    for item in model.requirements:
        errors.extend("%s: %s"%(item.id,error) for error in item.source.validate_against(model.original_description))
        if item.specification.operation not in ALLOWED_OPERATIONS: errors.append("%s: unsupported operation"%item.id)
        for parameter in item.parameters:
            if parameter not in names: errors.append("%s: undefined parameter %r"%(item.id,parameter))
    errors.extend("objective: %s"%error for error in model.objective.source.validate_against(model.original_description))
    errors.extend(_validate_graph(ids,model.dependencies))
    if errors: raise ModelValidationError(errors)
def _validate_graph(ids, dependencies):
    errors=[]; nodes=set(ids); adjacency=defaultdict(list); indegree={node:0 for node in nodes}; seen=set()
    for edge in dependencies:
        pair=(edge.predecessor,edge.successor)
        if pair in seen: errors.append("duplicate dependency %r"%(pair,)); continue
        seen.add(pair)
        if pair[0] not in nodes or pair[1] not in nodes: errors.append("dependency references unknown requirement: %r"%(pair,)); continue
        if pair[0]==pair[1]: errors.append("self dependency is not allowed: %r"%(pair,)); continue
        adjacency[pair[0]].append(pair[1]); indegree[pair[1]]+=1
    queue=deque(node for node,degree in indegree.items() if degree==0); seen_nodes=0
    while queue:
        node=queue.popleft(); seen_nodes+=1
        for successor in adjacency[node]:
            indegree[successor]-=1
            if indegree[successor]==0: queue.append(successor)
    if seen_nodes!=len(nodes): errors.append("requirement dependency graph must be acyclic")
    return errors
