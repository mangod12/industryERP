# KBSteel ERP — Product Context

## Register
product

## Product Purpose
Production tracking and inventory management system for a real steel fabrication plant. Tracks raw materials from receipt through fabrication, painting, dispatch, and scrap recovery. Used daily by plant floor operators, store keepers, QA inspectors, and management.

## Users

### Boss / Management
- Views dashboard for production status, stock value, scrap rates
- Manages system settings, user accounts, naming series
- Reviews and approves GRNs, dispatches
- Checks reports for business decisions
- Uses: desktop, sometimes tablet in office

### Store Keeper
- Manages raw material inventory, stock lots
- Creates GRNs when materials arrive at gate
- Records weighbridge data
- Most frequent user, 8+ hours daily
- Uses: desktop at store counter, sometimes mobile for quick checks

### QA Inspector
- Inspects incoming materials, approves/rejects lots
- Checks production quality at stage gates
- Uses: tablet on plant floor

### Dispatch Operator
- Creates dispatch notes when goods leave
- Records vehicle/transporter details, weighbridge data
- Prints delivery challans for drivers
- Uses: desktop at dispatch office

### Production Floor Supervisor
- Tracks items through fabrication → painting → dispatch stages
- Uploads Excel sheets with production data
- Manages scrap records and reusable stock
- Uses: desktop, occasionally mobile

## Brand Voice
- Functional, not flashy. This is a tool people use all day
- Clear labels, no ambiguity. Steel plant operators are not tech-savvy
- Hindi-English bilingual context (Hinglish). Keep labels in English but expect users who think in Hindi
- Numbers are sacred: weights in tons/kg, quantities, rates. Must be prominent and scannable
- Status must be visible at a glance: what stage, what's pending, what needs attention

## Anti-references
- Generic SaaS dashboards with meaningless gradient cards
- Over-designed admin panels that prioritize aesthetics over function
- Dark themes that look "techy" — this is a bright, dusty plant office with sunlight
- Tiny text optimized for designers, not plant workers on 15-inch monitors

## Strategic Principles
1. **Scannable over beautiful** — A supervisor glancing at the screen should know status in 2 seconds
2. **Dense but organized** — Lots of data, but grouped logically with clear hierarchy
3. **Forgiving inputs** — Operators make typos. Fuzzy matching, confirmations, undo where possible
4. **Print-ready** — Many workflows end with printing (GRN, dispatch challan). Print output matters
5. **Works on slow connections** — Plant may have unreliable internet. No heavy JS frameworks, minimize requests
