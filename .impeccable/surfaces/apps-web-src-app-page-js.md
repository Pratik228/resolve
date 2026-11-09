---
version: 1
slug: "apps-web-src-app-page-js"
primary_target: "apps/web/src/app/page.js"
related_targets: ["apps/web/src"]
---

# Surface: Resolve web (explainer + app)

Scope: apps/web. Explainer landing is Persuade; console, trace, approvals, evals and Break the refund are Operate inside the same world.
Audience: hiring managers/recruiters with ~90 seconds, then engineers. Job: see that the model cannot move money, with proof.
Action: run the three demo tickets live from the landing page. Proof: live API results and evals/results/*.json only.
Constraints: no invented claims; replay numbers labelled "recorded, not blind"; WCAG AA in light and dark; keyboard demo path; reduced motion respected.

## Direction contract

THESIS: The site is printed on security paper and every payout is a cheque the policy engine draws; the model writes the letter, never the cheque. Refuses the category default: a dark AI dashboard of glowing cards around a chat box.

OWN-WORLD: Sage-grey security paper ground with a fine generative guilloche and microprint rules; deep green-black intaglio ink; cheque-blue for live/primary; amber "awaiting signature" stamp; vermilion only for VOID. Engraved Didone display, sober public-document grotesk for UI, MICR-like mono strictly for IDs, keys and figures, copperplate script only on signature lines. Dark theme is the carbon copy: blue-black carbon with pale ink.

STORY: The visitor sees three cheques: one drawn and signed by code ($49), one waiting for a human signature ($900), one voided by a prompt injection. They believe amounts come from the ledger, not the model, and they press Run to watch it happen live, then open the trace, evals or the forge challenge.

FIRST VIEWPORT: Left column, ~5/12: the tagline as an engraved headline, two lines of plain explanation, the primary "Run the three demo tickets" button, and a one-line link to the repo. Right ~7/12: the cheque stack at life size, front cheque fully legible with payee, amount in figures and words, memo, signature line and MICR line; the two others fanned behind it. A printed terms strip along the bottom edge carries pass^5, unsafe writes and red-team breaches from the API.

FORM: Security-printed cheque, candidate 7 of 7 on the ordered list. seed:65a968e507b9b946. Signature interaction: Run prints each cheque live from the API response: figures stamp in, the auto-approval signature draws itself, the $900 cheque waits for an Approve & sign control, the injected one has VOID rise through its pantograph.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
