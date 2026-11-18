# Resolve web: visual system

World: **security-printed cheque.** The site is cheque stock; every payout renders as a cheque the policy engine draws. The model writes the letter, never the cheque. Engineering design decisions live in `docs/DESIGN.md`; this file is only the visual system.

## Themes

Picked from the use scene (a hiring manager on a laptop in daylight), light is the default; dark is the **carbon copy**. Tokens live in `src/app/globals.css` on `:root`, overridden under `prefers-color-scheme: dark` and `[data-theme="dark"]`.

| Token | Paper (light) | Carbon (dark) | Job |
|---|---|---|---|
| `--paper` | `#e8ece3` | `#0d1520` | page ground |
| `--paper-hi` | `#f3f5ef` | `#131e2d` | cheque face, panels, fields |
| `--paper-lo` | `#dce2d6` | `#0a111a` | hover wash, status strip |
| `--ink` | `#13261f` | `#e6eaf0` | text |
| `--ink-2` / `--ink-3` | `#3d5047` / `#536459` | `#b4becd` / `#93a0b2` | secondary / captions (AA on paper) |
| `--blue` | `#1e3d8c` | `#9db8ff` | primary action, code-owned, signatures, "paid" |
| `--amber` | `#7d4c00` | `#ecb955` | human-owned, awaiting signature |
| `--void` | `#b42d1b` | `#ff8670` | VOID and failures only |
| `--g` | `#7f9c8c` | `#3a5576` | guilloche stroke |

Colour strategy: restrained. Ink on security paper, with blue, amber and vermilion each owning one meaning (code, human, void). Never decorate with them.

## Type

Self-hosted through `next/font` (variables set on `<html>`; never redefine them in CSS):

- **Bodoni Moda** (`--f-display`): headings, wordmark, bank name. Italic for the second clause of a statement.
- **Public Sans** (`--f-ui`): all UI and body.
- **JetBrains Mono** (`--f-mono`): only data: IDs, amounts, keys, metrics, trace lines, typed cheque fields.
- **Herr Von Muellerhoff** (`--f-script`): only signatures.

## Materials and components

- `Guilloche`: parametric harmonic bands drawn as SVG paths from a seed; quiet (`--g-opacity` ~0.5). Never an image.
- `Microprint`: the tagline at 4.6px as signature rules.
- `Cheque`: kinds `specimen | drawn | pending | void | declined | escalated`. The amount is set only from the policy decision. Amount in figures and words; MICR line = ticket ⑆ customer ⑈ item paid for (authored SVG symbols). `pending` shows the amber stamp and Approve & sign; `void` raises the VOID pantograph.
- Ledgers (`.ledger`): ruled tables, uppercase micro headers, tabular numerals right-aligned, `is-chosen` row wash.
- Owners: `.owner--code` (filled square, blue), `.owner--model` (open circle, ink), `.owner--human` (filled square, amber).
- Trace (`.trace`): steps print as mono lines, not cards.
- No kickers above headings, no card grids, no gradients or glass; corners 3–4px; shadows are offset and soft.

## Motion

One authored moment: the printing of a cheque when the API answers. Figures stamp in, typed lines reveal left to right, the code signature writes itself, VOID rises through the pantograph, and stamps press down. All of it sits behind `prefers-reduced-motion: no-preference`.

## Layout

Max width 1240px, gutter `clamp(16px, 4vw, 40px)`. Landing hero: 5/12 copy, 7/12 fanned cheque stack, then a ruled terms strip with the live numbers. App pages: `split` 5/7 or `grid2`. Below 640px the stack becomes a vertical list and the nav scrolls horizontally under the wordmark.
