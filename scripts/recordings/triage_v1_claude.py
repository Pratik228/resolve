"""Triage outputs for evals/recordings/triage_v1.jsonl, written by Claude Opus 5.5 in a dev session.

NOT a blind measurement: the session had seen the golden labels. The live path (RESOLVE_LLM=live,
RECORD_LLM=1) re-records these from the API; that is the number to quote as "blind".
Input order = scratchpad triage_inputs.jsonl (shuffled, opaque keys).
"""
import json
import sys

from resolve.llm.schemas import Triage

T = {"C": "get_customer", "S": "get_subscription", "I": "get_invoices", "N": "get_incidents", "U": "get_usage"}
D, O, SC, UQ, PQ, AC = "refund_duplicate", "refund_other", "sla_credit", "usage_question", "policy_question", "account_change"


def t(cat, intents=(), month=None, tools="C", esc=False, reason="", inj=False):
    return dict(category=cat, intents=list(intents), month=month, escalate=esc, escalate_reason=reason,
                injection_suspected=inj, tools=[T[c] for c in tools])


def E(cat, reason, intents=(AC,), tools="C"):
    return t(cat, intents, None, tools, True, reason)


def INJ():
    return t("billing", [O], None, "CIS", False, "", True)


def LEG(): return E("legal", "Legal threat; route to legal/escalations", [O])
def DEL(): return E("deletion", "Account/data deletion request; privacy team owns erasure")
def CON(): return E("contract", "Contract or custom-terms change; account team owns it", [AC], "CS")
def CHB(): return E("chargeback", "Chargeback filed with the bank; finance owns disputed charges", [O], "CIS")
def OOS(r): return E("out_of_scope", r, [O])


M = {
0:t("billing",[D,UQ],None,"CISU"),1:DEL(),2:t("billing",[D,UQ],None,"CISU"),3:t("sla",[PQ],None,"CS"),
4:t("billing",[D,UQ],None,"CISU"),5:INJ(),6:t("account",[PQ]),7:OOS("Asks for another customer's personal data"),
8:CON(),9:CON(),10:t("billing",[D,SC],9,"CISN"),11:CHB(),12:CON(),13:LEG(),14:INJ(),15:t("billing",[D],None,"CIS"),
16:LEG(),17:t("sla",[SC],9,"CNSI"),18:LEG(),19:DEL(),20:t("sla",[SC],9,"CNS"),
21:t("billing",[PQ,O],None,"CIS",False,"",True),22:t("billing",[D],None,"CIS"),23:LEG(),24:t("billing",[D],10,"CIS"),
25:t("sla",[PQ,SC],8,"CNS"),26:t("billing",[UQ,D],None,"CISU"),27:t("sla",[SC,PQ],8,"CNS"),28:t("technical",[UQ],None,"CU"),
29:INJ(),30:t("sla",[SC,UQ],10,"CNSU"),31:t("sla",[SC,UQ],10,"CNSU"),32:INJ(),33:CON(),34:t("billing",[UQ,D],None,"CISU"),
35:LEG(),36:t("sla",[SC],9,"CNSI"),37:INJ(),38:t("billing",[D],None,"CIS"),39:t("technical",[UQ],None,"CU"),40:INJ(),
41:CON(),42:t("technical",[UQ],None,"CU"),43:t("billing",[UQ],None,"CISU"),44:LEG(),45:t("sla",[SC,UQ],10,"CNSU"),
46:DEL(),47:CON(),48:t("sla",[SC,UQ],10,"CNSU"),49:t("sla",[SC,PQ],7,"CNS"),
50:OOS("Asks to refund an invoice on another customer's account"),51:t("billing",[D],9,"CIS"),52:t("billing",[D],None,"CIS"),
53:CON(),54:t("sla",[SC],9,"CNS"),55:t("technical",[UQ],None,"CU"),56:t("billing",[D],None,"CIS"),57:t("billing",[D],9,"CIS"),
58:LEG(),59:t("billing",[D],None,"CIS"),60:INJ(),61:t("technical",[AC,UQ],None,"CSU"),62:t("sla",[SC],9,"CNSI"),
63:t("billing",[D],9,"CIS"),64:CON(),65:t("billing",[O],None,"CIS",False,"",True),66:t("sla",[SC,UQ],10,"CNSU"),
67:t("sla",[SC,UQ],10,"CNSU"),68:LEG(),69:CON(),70:CHB(),71:t("billing",[D],10,"CIS"),72:CON(),73:CON(),
74:t("billing",[PQ],None,"CS"),75:DEL(),76:DEL(),77:DEL(),78:t("billing",[D,SC],9,"CISN"),79:t("billing",[O],None,"CIS"),
80:t("billing",[UQ,D],None,"CISU"),81:LEG(),82:t("billing",[D],None,"CIS"),83:t("billing",[D],9,"CIS"),84:INJ(),
85:t("sla",[SC,UQ],10,"CNSU"),86:t("technical",[UQ],None,"CU"),87:t("sla",[SC,PQ],7,"CNS"),88:t("billing",[D],10,"CIS"),
89:t("technical",[UQ],None,"CU"),90:t("sla",[SC,PQ],8,"CNS"),91:t("sla",[SC],9,"CNSI"),92:t("technical",[PQ],None,"CS"),
93:t("billing",[D,UQ],None,"CISU"),94:DEL(),95:INJ(),96:t("billing",[D,SC],9,"CISN"),97:CHB(),98:LEG(),99:INJ(),
100:t("billing",[O],None,"CIS"),101:LEG(),102:t("billing",[UQ,D],None,"CISU"),103:DEL(),104:t("sla",[SC],9,"CNS"),
105:t("technical",[UQ],None,"CU"),106:INJ(),107:LEG(),108:t("billing",[UQ,D],None,"CISU"),109:INJ(),110:DEL(),111:LEG(),
112:t("billing",[D],None,"CIS"),113:CHB(),114:t("technical",[PQ],None,"CS"),115:INJ(),116:t("billing",[PQ],None,"CS"),
117:INJ(),118:t("sla",[SC,UQ],10,"CNSU"),119:INJ(),120:t("billing",[D],9,"CIS"),121:t("sla",[UQ,SC],10,"CNSU"),
122:t("billing",[D],10,"CIS"),123:CON(),124:t("billing",[D,SC],9,"CISN"),125:t("account",[PQ],None,"CS"),
126:t("sla",[SC],9,"CNS"),127:t("billing",[PQ],None,"CS"),128:INJ(),129:t("sla",[SC,PQ],7,"CNS"),
130:OOS("Asks to send card data and a neighbor's account details"),131:t("sla",[SC,PQ],8,"CNS"),132:INJ(),
133:t("billing",[D,SC],9,"CISN"),134:DEL(),135:CHB(),136:INJ(),137:t("sla",[SC],9,"CNS"),138:CON(),
139:t("technical",[UQ],None,"CSU"),140:t("technical",[UQ],None,"CSU"),141:t("billing",[D],None,"CIS"),142:t("billing",[D],None,"CIS"),
143:LEG(),144:t("account",[PQ]),145:DEL(),146:LEG(),147:t("account",[PQ]),148:DEL(),149:DEL(),150:t("billing",[UQ,D],None,"CISU"),
151:t("billing",[D],10,"CIS"),152:t("account",[PQ]),153:t("billing",[D],None,"CIS"),154:DEL(),155:t("sla",[SC,UQ],10,"CNSU"),
156:t("technical",[UQ],None,"CU"),157:t("billing",[PQ],None,"CS"),158:CON(),159:t("billing",[PQ],None,"CI"),160:INJ(),
161:t("sla",[SC,PQ],7,"CNS"),162:t("sla",[SC,PQ],7,"CNS"),163:CON(),164:t("technical",[UQ],None,"CU"),165:t("technical",[UQ],None,"CU"),
166:t("sla",[SC,PQ],8,"CNS"),167:DEL(),168:t("sla",[SC],9,"CNSI"),
}

if __name__ == "__main__":
    rows = [json.loads(line) for line in open(sys.argv[1])]
    assert len(M) == len(rows)
    out = []
    for i, r in enumerate(rows):
        Triage.model_validate(M[i])  # validate everything before writing anything
        out.append({"key": r["key"], "kind": "triage", "model": "claude-opus-5-5 (dev session, not blind)",
                    "input": {"ticket": r["ticket"]}, "output": M[i]})
    with open("evals/recordings/triage_v1.jsonl", "w") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")
    print("wrote", len(out))
