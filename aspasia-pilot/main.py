from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal, Union
from dataclasses import dataclass
import yaml
import textwrap

# ==========================================
# 1. DATA MODELS & ENGINE LOGIC
# ==========================================

Decision = Literal["allow", "block", "flag"]

@dataclass
class Condition:
    field: str
    op: str
    value: Any

    def _get_nested(self, tx: Dict[str, Any]) -> Any:
        current: Any = tx
        for part in self.field.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def eval(self, tx: Dict[str, Any]) -> bool:
        v = self._get_nested(tx)
        if v is None: return False
        if self.op == "gt": return v > self.value
        if self.op == "lt": return v < self.value
        if self.op == "eq": return v == self.value
        if self.op == "in": return v in self.value
        raise ValueError(f"Unknown operator: {self.op!r}")

@dataclass
class CompositeCondition:
    mode: Literal["all", "any"]
    children: List["Node"]

    def eval(self, tx: Dict[str, Any]) -> bool:
        if self.mode == "all": return all(child.eval(tx) for child in self.children)
        else: return any(child.eval(tx) for child in self.children)

Node = Union[Condition, CompositeCondition]

@dataclass
class Rule:
    name: str
    root: Node
    action: Decision
    priority: int

def build_node(spec: Dict[str, Any]) -> Node:
    if "all" in spec or "any" in spec:
        mode = "all" if "all" in spec else "any"
        children = [build_node(child) for child in spec[mode]]
        return CompositeCondition(mode=mode, children=children)
    return Condition(field=spec["field"], op=spec["op"], value=spec["value"])

def load_rules_from_yaml(yaml_text: str) -> List[Rule]:
    raw = yaml.safe_load(textwrap.dedent(yaml_text))
    rules: List[Rule] = []
    for r in raw:
        when_spec = r.get("when") or {"field": "__always__", "op": "eq", "value": True}
        rules.append(Rule(
            name=r["name"],
            root=build_node(when_spec),
            action=r["action"],
            priority=int(r.get("priority", 0)),
        ))
    return rules

class PolicyEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = rules
        self.action_rank = {"block": 2, "flag": 1, "allow": 0}

    def evaluate(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        trace = []
        matched = []
        ordered = sorted(self.rules, key=lambda r: (-r.priority, r.name))

        for rule in ordered:
            result = rule.root.eval(tx)
            trace.append({"rule": rule.name, "result": bool(result)})
            if result: matched.append(rule)

        if not matched:
            decision, chosen = "allow", None
        else:
            chosen = max(matched, key=lambda r: (self.action_rank[r.action], r.priority))
            decision = chosen.action

        return {
            "decision": decision,
            "rule": chosen.name if chosen else None,
            "matched_rules": [r.name for r in matched],
            "trace": trace,
        }

# ==========================================
# 2. SERVER CONFIGURATION
# ==========================================

DEFAULT_RULES = """
- name: block_unhosted_wallets
  when:
    field: originator.kyc
    op: eq
    value: false
  action: block
  priority: 20

- name: flag_high_value_eur
  when:
    all:
      - field: amount
        op: gt
        value: 100000
      - field: currency
        op: eq
        value: "EUR"
  action: flag
  priority: 10

- name: default_allow
  when: {}
  action: allow
  priority: 0
"""

# API Models
class TransactionRequest(BaseModel):
    id: str
    originator: Dict[str, Any]
    beneficiary: Dict[str, Any]
    amount: float
    currency: str
    context: Optional[str] = "Standard"

class PolicyResponse(BaseModel):
    decision: str
    rule_applied: Optional[str]
    timestamp: str = "2025-10-27T10:00:00Z"
    trace_id: str

# Global Variables
app = FastAPI(title="ASPASIA Intelligence Layer", version="1.0.0")
STATS = {"total_processed": 0, "decisions": {"BLOCK": 0, "FLAG": 0, "ALLOW": 0}}

# Initialize Engine
rules_objects = load_rules_from_yaml(DEFAULT_RULES)
engine = PolicyEngine(rules_objects)

# ==========================================
# 3. API ENDPOINTS
# ==========================================

@app.get("/")
def health_check():
    return {"status": "active", "system": "ASPASIA Pilot Core"}

@app.get("/stats")
def live_stats():
    """Returns real-time performance metrics."""
    return STATS

@app.post("/enforce", response_model=PolicyResponse)
def enforce_policy(tx: TransactionRequest):
    tx_data = tx.dict()
    try:
        result = engine.evaluate(tx_data)
        
        # Update Stats
        decision_key = result["decision"].upper()
        STATS["total_processed"] += 1
        STATS["decisions"][decision_key] += 1

        return {
            "decision": decision_key,
            "rule_applied": result["rule"],
            "trace_id": f"trace_{tx.id}_secure",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/update_policy")
def update_policy(yaml_rules: str):
    global engine
    try:
        new_rules = load_rules_from_yaml(yaml_rules)
        engine = PolicyEngine(new_rules)
        return {"status": "Policy updated successfully", "rule_count": len(new_rules)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")