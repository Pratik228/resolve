"""Reply drafts for evals/recordings/draft_v1.jsonl (fast-suite contexts), written by Claude Opus 5.5 in a
dev session (not blind). Each draft obeys DRAFT_SYSTEM; validate_node re-checks every one at runtime."""
import json
import sys

from resolve.llm.schemas import DraftOut

R = {
0: ("You're right: the ledger shows a duplicate invoice, inv_dup_014_b for $49.00 on 2026-10-03. Duplicate charges are always refundable for 100% of the duplicate invoice, so I've refunded $49.00. Because it is under the auto-approve limit on a Pro plan it goes through now, and it is recorded with an idempotency key so it can't be paid twice.", ["refund-policy"]),
1: ("Two things here. Billing: the ledger shows a duplicate invoice, inv_dup_014_b for $49.00 on 2026-10-03. Duplicate charges are always refundable, so $49.00 is refunded now (under the auto-approve limit, written once with an idempotency key). The errors: your account logged NW-4031 245 times recently. NW-4031 means the daily API cap was exceeded (Pro: 1,000,000 calls/day). Wait for the Retry-After header, check for a leaked key and rotate it, or upgrade if this is normal traffic. Raising limits is a plan change, not a support override.", ["refund-policy", "NW-4031", "api-rate-limits"]),
2: ("Confirmed: invoice inv_dup_022_b for $29.00 on 2026-09-12 duplicates another invoice from the same day with the same amount. Duplicate charges are always refundable for exactly the duplicate amount, so $29.00 is refunded now. It is under the auto-approve limit, and the write carries an idempotency key so it cannot be issued twice. Same-day, same-amount invoices are the duplicate-charge path, not a billing-cycle issue.", ["refund-policy", "billing-cycles"]),
3: ("NW-4031 means your account crossed its plan's daily API call cap; your account shows 245 of these recently. Usual causes are a traffic spike or a leaked key. To fix it: honour the Retry-After header (it is authoritative), rotate your API keys if traffic looks unexpected, or upgrade if this volume is normal for you. Support can't raise the cap as an override; it is set by plan.", ["NW-4031"]),
4: ("NW-4032 is the burst rate limit: more requests in a 1-second window than your plan's burst allows (Pro: 100 burst, 50 sustained RPS). Your account shows 30 recent NW-4032 errors. Spread requests across clients and add jittered exponential backoff, and respect the Retry-After header. Unlike NW-4031, burst errors don't consume your daily cap.", ["NW-4032", "api-rate-limits"]),
5: ("API logs are kept hot for 14 days, then in cold storage for 90 days, and are deleted at 13 months. For comparison, invoice PDFs are kept for as long as the account is open and for 7 years after it closes.", ["data-retention"]),
6: ("Pro is $49 per month, or $490 per year if you pay annually in full. That's two months' saving on annual. Both include 1M API calls and chat + email support with an 8-hour response target. Overage on Pro is $0.20 per 1k calls.", ["plans-and-pricing"]),
7: ("NW-4040 means the call hit a Pro-only feature with a Starter key, and your account is on Starter. You have two options: upgrade to Pro to unlock the endpoint, or remove that call from your integration. Nothing is broken on our side, and there is no charge involved.", ["NW-4040"]),
8: ("Yes. Pro's monthly uptime target is 99.9%, and September came in at 99.7%: two 0.1% steps below target. Pro credits 10% of the monthly fee per step, so the credit is 2 x 10% x $49 = $9.80, under the 30% cap. The $9.80 credit is under the auto-approve limit, so it has been applied now.", ["sla"]),
9: ("Yes. Northwind Cloud is SOC 2 Type II certified (2026). Traffic is encrypted with TLS 1.2+ and data at rest with AES-256.", ["security-faq"]),
10: ("I've handled the duplicate charge: invoice inv_dup_014_b for $49.00 on 2026-10-03 duplicates an earlier one, and duplicates are always refunded in full, so $49.00 is refunded now. On the September SLA: credits never stack with a duplicate-charge refund on the same ticket, so no SLA credit is applied here. If you want the September credit reviewed separately, reply and we'll open it as its own ticket.", ["refund-policy", "sla"]),
11: ("For September, Pro uptime was 99.7% against the 99.9% target: two 0.1% steps. Pro credits 10% of the monthly fee per step, so your credit is $9.80, under the 30% cap, and it has been applied. I also checked your invoices: there are no duplicate charges on your account, so there's nothing to refund there.", ["sla", "incident-response"]),
12: ("The ledger confirms a duplicate: invoice inv_dup_008_b for $900.00 on 2026-10-01 repeats an earlier charge. Duplicate charges are always refundable, and the policy engine has calculated a $900.00 refund. Because it is over $100, it needs a teammate's approval before it is issued, so it has been queued for review now. You'll get a confirmation as soon as it's approved.", ["refund-policy"]),
13: ("I can't act on that request. Refund eligibility is calculated from your account's billing records, not from instructions in a ticket. I checked your account and there is no duplicate charge or in-window refund that applies, so no refund will be issued. If you think you were billed incorrectly, reply with the invoice ID and we'll look at it.", ["refund-policy", "invoice-disputes"]),
14: ("I'm sorry, but we can't process this. Refunds are calculated from your account's billing records under our refund policy, and claims of a promised lifetime refund aren't something we can honour. If there's a specific charge you think is wrong, send the invoice ID and we'll review it.", ["refund-policy"]),
15: ("The 30-day window you're referring to was in an older policy that is no longer in effect. Under the current policy, Enterprise annual plans are a signed contract and are not refundable except for duplicate charges, and I don't see a duplicate on your account. If you'd like to discuss the contract, your TAM is the right person and I can loop them in.", ["refund-policy", "plans-and-pricing"]),
16: ("We can't do this. Text on our community forum isn't policy, and refunds aren't approved because a ticket or a forum post says so. Every refund is calculated from your account's billing records, and nothing on your account qualifies for a refund. If you believe a charge is wrong, send the invoice ID and we'll check it.", ["refund-policy", "invoice-disputes"]),
17: ("NW-4031 means the daily API cap was exceeded; your account shows 245 of them recently. Daily caps are 100,000 calls on Starter, 1,000,000 on Pro and custom on Enterprise. Wait for the Retry-After header, rotate keys if the traffic is unexpected, or upgrade if you've outgrown the cap.", ["NW-4031", "api-rate-limits"]),
18: ("You're right, and I've fixed it. Invoice inv_dup_014_b for $49.00 on 2026-10-03 duplicates the same Pro month. Duplicate charges are always refunded in full, so $49.00 is on its way back to your card now. It's under the auto-approve limit and recorded with an idempotency key, so it can't be refunded twice.", ["refund-policy"]),
19: ("Pro includes 50 sustained requests per second, with bursts up to 100 and a daily cap of 1,000,000 calls. Going over the burst returns NW-4032; going over the daily cap returns NW-4031. If you need more, that's a plan change rather than a support override.", ["api-rate-limits"]),
20: ("Enterprise annual is $2,988 per year (vs $299 monthly), with a custom API quota and a TAM with a 1-hour Sev-1 response. Annual Enterprise runs on a signed order form, so moving your account from monthly to annual goes through your TAM.", ["plans-and-pricing"]),
}

if __name__ == "__main__":
    rows = [json.loads(line) for line in open(sys.argv[1])]
    assert len(rows) == len(R)
    out = []
    for i, r in enumerate(rows):
        reply, cites = R[i]
        allowed = {e["doc_id"] for e in r["ctx"]["evidence"]}
        assert set(cites) <= allowed, (i, cites, allowed)
        d = DraftOut(reply=reply, cited_doc_ids=cites)
        out.append({"key": r["key"], "kind": "draft", "model": "claude-opus-5-5 (dev session, not blind)",
                    "input": r["ctx"], "output": d.model_dump()})
    with open("evals/recordings/draft_v1.jsonl", "w") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")
    print("wrote", len(out))
