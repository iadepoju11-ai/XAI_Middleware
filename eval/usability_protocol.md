# Usability Study Protocol
## XAI Compliance Middleware Dashboard — Phase 8 Qualitative Evaluation

**Target participants:** 5 mock compliance officers (peers, colleagues, or supervisor)  
**Session length:** ~30 minutes per participant  
**Format:** Think-aloud, moderated, in-person or screen-share  
**SUS target:** ≥ 70 (Good usability)  
**Explanation clarity target:** ≥ 3.5 / 5.0  

---

## Pre-Session Setup

1. Start Flask API: `cd backend && python app.py`
2. Start frontend: `cd frontend && npm start`
3. Open browser at `http://localhost:3000`
4. Ensure audit database is fresh (or has ≥50 records for realistic data)
5. Prepare consent/information sheet (dissertation research context)

---

## Introduction Script (Read verbatim)

> "Thank you for taking part in this usability study. I am evaluating a prototype dashboard
> designed to help compliance officers understand AI credit decisions under the EU AI Act.
> This is a test of the system, not of you — there are no wrong answers.
> Please think aloud as you work through the tasks. I may take notes but will not guide you.
> After the tasks, I'll ask you to complete a short questionnaire."

---

## Task Scenarios

### Task 1 — Submit a Credit Application (5 min)
> "A customer named Alex has applied for a loan. Enter these details and submit:
> Credit amount: £8,000 | Duration: 24 months | Age: 45 | Purpose: car |
> Employment: 4 <= X < 7 years | Monthly installments: 3 | Existing credits: 1 | Sex: male (1)"

**Observe:**
- [ ] Can participant find and complete the form without help?
- [ ] Does the decision result render correctly?
- [ ] Does the participant notice the SHAP waterfall chart?
- [ ] Can they explain *why* the system reached its decision?

**Success criteria:** Decision displayed + SHAP chart visible within 2 minutes

---

### Task 2 — Retrieve an Audit Record (5 min)
> "Retrieve the full audit record for the application you just submitted.
> Confirm that the SHAP values shown match what was on the scoring page."

**Observe:**
- [ ] Does participant navigate to Audit Trail without prompting?
- [ ] Can they find the record by application ID?
- [ ] Do they notice the expandable row and SHAP values?

**Success criteria:** Record retrieved + SHAP values inspected within 3 minutes

---

### Task 3 — Identify a Fairness Alert (5 min)
> "Go to the Fairness Monitor page. Is the current model making fair decisions?
> What would you tell a regulator about its demographic parity?"

**Observe:**
- [ ] Does participant understand the parity ratio KPI?
- [ ] Can they interpret the bar chart (acceptance rate by sex)?
- [ ] Do they correctly read the alert banner (if present)?

**Success criteria:** Participant can state whether alert is present and what it means

---

### Task 4 — Export Audit Data (3 min)
> "A regulator has requested a full export of all credit decisions.
> Download the data in CSV format."

**Observe:**
- [ ] Participant finds export buttons without help

**Success criteria:** CSV file downloaded within 2 minutes

---

### Task 5 — Describe the System (2 min)
> "In one or two sentences, describe what this system does and how it helps with compliance."

**Record response verbatim.**

---

## Post-Task Questionnaires

### System Usability Scale (SUS) — 10 items, 5-point Likert

Rate each from 1 (Strongly Disagree) to 5 (Strongly Agree):

| # | Statement |
|---|---|
| 1 | I think that I would like to use this system frequently. |
| 2 | I found the system unnecessarily complex. |
| 3 | I thought the system was easy to use. |
| 4 | I think that I would need the support of a technical person to use this system. |
| 5 | I found the various functions in this system were well integrated. |
| 6 | I thought there was too much inconsistency in this system. |
| 7 | I would imagine that most people would learn to use this system very quickly. |
| 8 | I found the system very cumbersome to use. |
| 9 | I felt very confident using the system. |
| 10 | I needed to learn a lot of things before I could get going with this system. |

**SUS scoring:** For odd items: score − 1. For even items: 5 − score. Sum × 2.5.

---

### Explanation Clarity Scale — 5 items, 5-point Likert

Rate each from 1 (Strongly Disagree) to 5 (Strongly Agree):

| # | Statement |
|---|---|
| EC1 | The SHAP chart clearly showed which factors most influenced the credit decision. |
| EC2 | I understood why the system accepted or rejected the application. |
| EC3 | The fairness metrics were presented in a way I could understand. |
| EC4 | I would feel confident explaining this decision to a customer using this dashboard. |
| EC5 | The information provided would satisfy EU AI Act transparency requirements. |

**Score:** Mean of EC1–EC5. Target ≥ 3.5.

---

### Open-Ended Questions

1. What was most confusing about the dashboard?
2. What would you add or change to make it more useful for compliance work?
3. Would you trust this system's explanations in a real regulatory audit? Why / why not?

---

## Facilitator Notes Template

| Participant | Role | SUS | Clarity | Task 1 ✓ | Task 2 ✓ | Task 3 ✓ | Task 4 ✓ | Notes |
|---|---|---|---|---|---|---|---|---|
| P1 | | | | | | | | |
| P2 | | | | | | | | |
| P3 | | | | | | | | |
| P4 | | | | | | | | |
| P5 | | | | | | | | |
| **Mean** | | | | | | | | |

---

## Thematic Analysis Codes (post-session)

Use these codes when transcribing post-task interview responses:

- `EXPLAIN` — comments about explanation quality
- `NAVIGATE` — comments about navigation / findability
- `TRUST` — comments about trusting the system
- `COMPLY` — comments about regulatory compliance readiness
- `IMPROVE` — suggested improvements
