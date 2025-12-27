from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Union

import json
import textwrap

import streamlit as st
import yaml


# ----------------- Demo rules & transactions ----------------- #
RULE_DESCRIPTIONS = {
    "block_unhosted_wallets": "Block transfers where the originator wallet has no KYC.",
    "flag_high_value_eur": "Flag high-value EUR transfers above the configured threshold.",
    "flag_virtual_asset_transfer": "Flag virtual asset transfers for extra review.",
    "default_allow": "Allow everything not caught by stricter rules.",
}

RULES_YAML_DEFAULT = """
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
""".strip()


tx_high_value = {
    "id": "tx_high_value",
    "originator": {
        "id": "BANK_001",
        "name": "Tier 1 Bank",
        "centrality": 0.15,
        "kyc": True,
    },
    "beneficiary": {
        "id": "CORP_042",
        "name": "Corporate Account",
        "centrality": 0.05,
        "kyc": True,
    },
    "amount": 250000,
    "currency": "EUR",
    "context": "MiCA_Title_III_Settlement",
}

tx_normal = {
    "id": "tx_normal",
    "originator": {
        "id": "BANK_002",
        "name": "Tier 2 Bank",
        "centrality": 0.08,
        "kyc": True,
    },
    "beneficiary": {
        "id": "SME_123",
        "name": "Small Merchant",
        "centrality": 0.03,
        "kyc": True,
    },
    "amount": 15000,
    "currency": "EUR",
    "context": "Standard_EU_Transfer",
}

tx_unhosted = {
    "id": "tx_unhosted",
    "originator": {
        "id": "WALLET_X",
        "name": "Anonymous Wallet",
        "centrality": 0.02,
        "kyc": False,
    },
    "beneficiary": {
        "id": "EXCHANGE_Y",
        "name": "Registered VASP",
        "centrality": 0.10,
        "kyc": True,
    },
    "amount": 5000,
    "currency": "EUR",
    "context": "Virtual_Asset_Transfer",
}

TXS = {
    "High-value EUR transfer": tx_high_value,
    "Normal SME payment": tx_normal,
    "Unhosted wallet transfer": tx_unhosted,
}


# ----------------- Engine (same semantics as notebook) ----------------- #

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
        if v is None:
            return False

        if self.op == "gt":
            return v > self.value
        if self.op == "lt":
            return v < self.value
        if self.op == "eq":
            return v == self.value
        if self.op == "in":
            return v in self.value

        raise ValueError(f"Unknown operator: {self.op!r}")


@dataclass
class CompositeCondition:
    mode: Literal["all", "any"]
    children: List["Node"]

    def eval(self, tx: Dict[str, Any]) -> bool:
        if self.mode == "all":
            return all(child.eval(tx) for child in self.children)
        else:
            return any(child.eval(tx) for child in self.children)


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
        children_specs = spec[mode]
        children = [build_node(child) for child in children_specs]
        return CompositeCondition(mode=mode, children=children)

    return Condition(
        field=spec["field"],
        op=spec["op"],
        value=spec["value"],
    )


def load_rules_from_yaml(yaml_text: str) -> List[Rule]:
    raw = yaml.safe_load(textwrap.dedent(yaml_text))

    rules: List[Rule] = []
    for r in raw:
        when_spec = r.get("when") or {}
        if not when_spec:
            when_spec = {"field": "__always__", "op": "eq", "value": True}
        root = build_node(when_spec)
        rules.append(
            Rule(
                name=r["name"],
                root=root,
                action=r["action"],
                priority=int(r.get("priority", 0)),
            )
        )
    return rules


class PolicyEngine:
    def __init__(self, rules: List[Rule]):
        self.rules = rules
        self.action_rank = {"block": 2, "flag": 1, "allow": 0}

    def evaluate(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        matched: List[Rule] = []

        ordered = sorted(self.rules, key=lambda r: (-r.priority, r.name))

        for rule in ordered:
            result = rule.root.eval(tx)
            trace.append({"rule": rule.name, "result": bool(result)})
            if result:
                matched.append(rule)

        if not matched:
            decision: Decision = "allow"
            chosen = None
        else:
            chosen = max(
                matched,
                key=lambda r: (self.action_rank[r.action], r.priority),
            )
            decision = chosen.action

        return {
            "decision": decision,
            "rule": chosen.name if chosen else None,
            "matched_rules": [r.name for r in matched],
            "trace": trace,
        }


# ----------------- Streamlit UI ----------------- #

st.set_page_config(
    page_title="Encoding Regulation – Minimal Policy Engine",
    layout="wide",
)

st.title("Encoding Regulation – Minimal Policy-as-Code Engine")
st.markdown(
    "Tiny workbench: edit YAML rules on the left, pick a transaction on the right, "
    "and see the decision + evaluation trace."
)

col_rules, col_tx = st.columns([2, 3])

with col_rules:
    st.subheader("Policy (YAML DSL)")
    rules_text = st.text_area(
        label="Rules",
        value=RULES_YAML_DEFAULT,
        height=350,
        label_visibility="collapsed",
        help="Edit policy rules here; the engine will reparse them on each run.",
    )

    st.caption(
        "Schema: name, when, action ∈ {allow, block, flag}, priority ∈ ℤ. "
        "`when` supports `field / op / value` and `all / any` composites."
    )

with col_tx:
    st.subheader("Transaction & Result")

    choice = st.selectbox(
        "Transaction:",
        options=list(TXS.keys()),
    )
    tx = TXS[choice]

    # optional live tweak: let them change amount
    new_amount = st.number_input(
        "Amount",
        min_value=0.0,
        value=float(tx["amount"]),
        step=1000.0,
    )
    tx = {**tx, "amount": new_amount}  # shallow copy with updated amount

    if st.button("Evaluate", type="primary"):
        try:
            rules = load_rules_from_yaml(rules_text)
            engine = PolicyEngine(rules)
            result = engine.evaluate(tx)

            st.markdown(
                f"### Decision: **{result['decision']}**"
                + (f"  (winning rule: `{result['rule']}`)" if result["rule"] else "")
            )
            st.markdown(
                "**Matched rules:** "
                + (", ".join(result["matched_rules"]) or "_none_")
            )

            with st.expander("Transaction JSON", expanded=False):
                st.code(json.dumps(tx, indent=2), language="json")

            with st.expander("Evaluation trace", expanded=True):
                st.code(json.dumps(result["trace"], indent=2), language="json")

        except Exception as e:
            st.error(f"Error while parsing rules or evaluating: {e}")
    else:
        st.info("Pick a transaction, optionally tweak the amount, then click **Evaluate**.")

explanation = RULE_DESCRIPTIONS.get(result["rule"], "No specific rule explanation available.")
st.markdown(f"**Explanation:** {explanation}")
