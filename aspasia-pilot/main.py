from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional, Literal, Union
from dataclasses import dataclass
import yaml
import textwrap
import json

# ==========================================
# 1. THE LOGIC ENGINE (AST & COMPILER)
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
# 2. SERVER & DATA CONFIG
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

- name: flag_virtual_asset_transfer
  when:
    field: context
    op: eq
    value: "Virtual_Asset_Transfer"
  action: flag
  priority: 8

- name: default_allow
  when: {}
  action: allow
  priority: 0
"""

app = FastAPI(title="ASPASIA Intelligence Layer", version="1.0.0")

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
    trace_id: str
    trace: List[Dict[str, Any]]

# Init Engine
rules_objects = load_rules_from_yaml(DEFAULT_RULES)
engine = PolicyEngine(rules_objects)
STATS = {"total_processed": 0, "decisions": {"BLOCK": 0, "FLAG": 0, "ALLOW": 0}}

# ==========================================
# 3. HTML FRONTEND (Single File)
# ==========================================
# This HTML replaces the Streamlit UI. It talks to the API below.

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ASPASIA | Protocol-Embedded Policy</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background: #f8fafc; }
        .sidebar { background: #1e293b; color: white; min-height: 100vh; }
        .nav-link { display: block; padding: 12px 20px; color: #94a3b8; text-decoration: none; cursor: pointer; }
        .nav-link:hover, .nav-link.active { background: #0f172a; color: white; border-left: 3px solid #0ea5e9; }
        .code-block { background: #1e293b; color: #a5b4fc; padding: 15px; border-radius: 6px; font-family: monospace; overflow-x: auto; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .badge-block { background: #fee2e2; color: #991b1b; }
        .badge-flag { background: #fef3c7; color: #92400e; }
        .badge-allow { background: #dcfce7; color: #166534; }
    </style>
    <script>
        // Data for scenarios
        const scenarios = {
            "tx_high": { "id": "tx_high", "originator": {"kyc": true}, "beneficiary": {}, "amount": 250000, "currency": "EUR" },
            "tx_norm": { "id": "tx_norm", "originator": {"kyc": true}, "beneficiary": {}, "amount": 15000, "currency": "EUR" },
            "tx_bad":  { "id": "tx_bad",  "originator": {"kyc": false}, "beneficiary": {}, "amount": 5000,  "currency": "EUR", "context": "Virtual_Asset_Transfer" }
        };

        function loadScenario(key) {
            document.getElementById('txInput').value = JSON.stringify(scenarios[key], null, 2);
        }

        async function runCheck() {
            const raw = document.getElementById('txInput').value;
            try {
                const tx = JSON.parse(raw);
                const res = await fetch('/enforce', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: raw
                });
                const data = await res.json();
                
                // Visual Updates
                const statusDiv = document.getElementById('statusResult');
                let badgeClass = data.decision === 'BLOCK' ? 'badge-block' : (data.decision === 'FLAG' ? 'badge-flag' : 'badge-allow');
                statusDiv.innerHTML = `<span class="badge ${badgeClass} text-xl">DECISION: ${data.decision}</span>`;
                
                document.getElementById('ruleResult').innerText = data.rule_applied || "None";
                document.getElementById('traceResult').innerText = JSON.stringify(data.trace, null, 2);
                
                // Refresh Stats
                loadStats();
                
            } catch (e) {
                alert("Invalid JSON or API Error: " + e);
            }
        }

        async function loadStats() {
            const res = await fetch('/stats');
            const data = await res.json();
            document.getElementById('statTotal').innerText = data.total_processed;
            document.getElementById('statBlock').innerText = data.decisions.BLOCK;
        }

        function showPage(id) {
            document.querySelectorAll('.page').forEach(el => el.style.display = 'none');
            document.getElementById(id).style.display = 'block';
            document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
            event.target.classList.add('active');
        }
        
        window.onload = loadStats;
    </script>
</head>
<body class="flex">

    <!-- Sidebar -->
    <div class="sidebar w-64 flex-none hidden md:block">
        <div class="p-6">
            <h1 class="text-xl font-bold tracking-wider">ASPASIA <span class="text-sky-400 text-xs">v1.0</span></h1>
            <p class="text-xs text-slate-400 mt-1">Intelligence Layer</p>
        </div>
        <nav>
            <a onclick="showPage('page-sim')" class="nav-link active">🚀 Live Simulator</a>
            <a onclick="showPage('page-ast')" class="nav-link">🧠 AST vs. Agents</a>
            <a onclick="showPage('page-conflict')" class="nav-link">⚔️ Conflict Resolution</a>
            <a href="/docs" target="_blank" class="nav-link">🔌 API Docs (Swagger)</a>
        </nav>
        <div class="p-6 mt-10">
            <div class="text-xs text-slate-500 uppercase font-bold">Live Stats</div>
            <div class="mt-2 text-sm">Processed: <span id="statTotal" class="text-white">0</span></div>
            <div class="text-sm">Blocked: <span id="statBlock" class="text-red-400">0</span></div>
        </div>
    </div>

    <!-- Main Content -->
    <div class="flex-1 p-8 h-screen overflow-y-auto">
        
        <!-- PAGE 1: SIMULATOR -->
        <div id="page-sim" class="page">
            <h2 class="text-3xl font-bold text-slate-800 mb-6">Transaction Simulator</h2>
            <p class="text-slate-600 mb-8">Test the <strong>Ex-Ante Enforcement</strong> engine. Send a transaction JSON to the API and see the deterministic result instantly.</p>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <!-- Input Column -->
                <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div class="flex justify-between items-center mb-4">
                        <h3 class="font-bold text-slate-700">1. Transaction Payload</h3>
                        <div class="space-x-2">
                            <button onclick="loadScenario('tx_norm')" class="text-xs bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded">Normal</button>
                            <button onclick="loadScenario('tx_high')" class="text-xs bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded">High Val</button>
                            <button onclick="loadScenario('tx_bad')" class="text-xs bg-red-50 hover:bg-red-100 text-red-600 px-2 py-1 rounded">Unhosted</button>
                        </div>
                    </div>
                    <textarea id="txInput" class="w-full h-64 font-mono text-sm p-4 bg-slate-50 border rounded-lg focus:ring-2 ring-sky-500 outline-none">
{
  "id": "tx_demo_01",
  "originator": {
    "kyc": true,
    "id": "BANK_001"
  },
  "beneficiary": {},
  "amount": 15000,
  "currency": "EUR"
}</textarea>
                    <button onclick="runCheck()" class="mt-4 w-full bg-sky-600 hover:bg-sky-700 text-white font-bold py-3 rounded-lg transition">
                        POST /enforce (Run Check)
                    </button>
                </div>

                <!-- Output Column -->
                <div class="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 class="font-bold text-slate-700 mb-4">2. API Response</h3>
                    
                    <div class="mb-6 p-4 bg-slate-50 rounded-lg border border-slate-100 flex justify-between items-center">
                        <div>
                            <div class="text-xs text-slate-500 uppercase">Status</div>
                            <div id="statusResult" class="mt-1"><span class="text-slate-400">Waiting...</span></div>
                        </div>
                        <div class="text-right">
                            <div class="text-xs text-slate-500 uppercase">Winning Rule</div>
                            <div id="ruleResult" class="font-mono text-sm text-slate-700 mt-1">-</div>
                        </div>
                    </div>

                    <div class="text-xs text-slate-500 uppercase mb-2">Cryptographic Audit Trace</div>
                    <div id="traceResult" class="code-block h-64 text-xs">
// The JSON audit log will appear here...
                    </div>
                </div>
            </div>
        </div>

        <!-- PAGE 2: AST DESIGN -->
        <div id="page-ast" class="page" style="display:none;">
            <h2 class="text-3xl font-bold text-slate-800 mb-6">Why ASTs beat Agents</h2>
            <div class="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
                <div class="grid grid-cols-2 gap-8 mb-8">
                    <div class="p-4 bg-red-50 rounded-lg border border-red-100">
                        <h4 class="font-bold text-red-800 mb-2">❌ Stochastic Agents (LLMs)</h4>
                        <ul class="list-disc list-inside text-sm text-red-700 space-y-2">
                            <li><strong>Probabilistic:</strong> Ask twice, get different answers.</li>
                            <li><strong>Hallucinations:</strong> Can invent rules.</li>
                            <li><strong>Black Box:</strong> Hard to audit specific logic paths.</li>
                        </ul>
                    </div>
                    <div class="p-4 bg-green-50 rounded-lg border border-green-100">
                        <h4 class="font-bold text-green-800 mb-2">✅ ASPASIA (Deterministic AST)</h4>
                        <ul class="list-disc list-inside text-sm text-green-700 space-y-2">
                            <li><strong>Deterministic:</strong> 100% reproducible results.</li>
                            <li><strong>Strict Liability:</strong> Code executes exactly as written.</li>
                            <li><strong>Traversable:</strong> We walk the tree and record every step.</li>
                        </ul>
                    </div>
                </div>
                <h3 class="font-bold text-slate-700 mb-4">The Recursive Logic Tree</h3>
                <pre class="code-block">
@dataclass
class CompositeCondition:
    mode: Literal["all", "any"]
    children: List["Node"]  # <-- Recursive Definition

    def eval(self, tx):
        # We walk this tree recursively
        if self.mode == "all": return all(c.eval(tx) for c in self.children)
</pre>
            </div>
        </div>

        <!-- PAGE 3: CONFLICT RESOLUTION -->
        <div id="page-conflict" class="page" style="display:none;">
            <h2 class="text-3xl font-bold text-slate-800 mb-6">Explicit Conflict Resolution</h2>
            <div class="bg-white p-8 rounded-xl shadow-sm border border-slate-200">
                <p class="text-lg text-slate-600 mb-6">
                    In banking, rules collide. A "VIP Allow" rule might conflict with a "Sanctions Block".
                    ASPASIA solves this via <strong>Tuple Sorting</strong>.
                </p>
                
                <div class="p-6 bg-slate-50 border border-slate-200 rounded-lg mb-6">
                    <h4 class="font-mono text-sm text-slate-500 mb-2">ALGORITHM</h4>
                    <pre class="text-sm font-mono text-slate-700">chosen = max(matched, key=lambda r: (self.action_rank[r.action], r.priority))</pre>
                </div>

                <h3 class="font-bold text-slate-700 mb-4">The Hierarchy of Severity</h3>
                <div class="space-y-3">
                    <div class="flex items-center p-3 bg-red-50 border border-red-100 rounded">
                        <span class="badge badge-block mr-4">BLOCK (Rank 2)</span>
                        <span class="text-sm text-red-800">The "Nuclear Option". Overrides everything.</span>
                    </div>
                    <div class="flex items-center p-3 bg-amber-50 border border-amber-100 rounded">
                        <span class="badge badge-flag mr-4">FLAG (Rank 1)</span>
                        <span class="text-sm text-amber-800">Overrides 'Allow', but yields to 'Block'.</span>
                    </div>
                    <div class="flex items-center p-3 bg-green-50 border border-green-100 rounded">
                        <span class="badge badge-allow mr-4">ALLOW (Rank 0)</span>
                        <span class="text-sm text-green-800">The default state. Weakest priority.</span>
                    </div>
                </div>
            </div>
        </div>

    </div>
</body>
</html>
"""

# ==========================================
# 4. API ENDPOINTS
# ==========================================

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serves the Single-Page Application (SPA) dashboard."""
    return HTML_TEMPLATE

@app.get("/stats")
def live_stats():
    return STATS

@app.post("/enforce", response_model=PolicyResponse)
def enforce_policy(tx: TransactionRequest):
    tx_data = tx.dict()
    try:
        # Run the Engine
        result = engine.evaluate(tx_data)
        
        # Update Stats
        decision_key = result["decision"].upper()
        STATS["total_processed"] += 1
        STATS["decisions"][decision_key] += 1

        return {
            "decision": decision_key,
            "rule_applied": result["rule"],
            "trace_id": f"trace_{tx.id}_secure",
            "trace": result["trace"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
