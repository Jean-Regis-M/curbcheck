# Pilot protocol: how to find out whether CurbCheck reduces contamination

**Status: designed, not run.** Nothing in this repository measures real-world contamination. The laboratory
false-accept rate predicts a safer answer per photo; it does not say how residents behave. This protocol is how
that question would be answered.

## Question
Does giving residents CurbCheck reduce the weight share of non-recyclable material in their recycling stream?

## Design
- **Units:** collection routes or multi-unit buildings, randomised to *tool* or *control* (cluster randomisation, so residents in
  one building do not contaminate each other's arms).
- **Outcome:** contamination by weight per bin audit (kilograms of non-recyclable material divided by total kilograms in a sampled
  load), measured by the same crew, blind to arm where possible, with the same sorting protocol before and after.
- **Timeline:** baseline audits, then an intervention period long enough to cover several collection cycles, then follow-up audits.
- **Analysis:** compare the log of contamination between arms, adjusting for the baseline audit of the same unit.
- **Secondary measures:** the "not sure" rate, wrong-answer reports received through the in-app report links, and the share of
  residents who used the tool at all (uptake decides the effect more than model accuracy does).

## How many audits
The table comes from [`scripts/pilot_power.py`](../scripts/pilot_power.py) and [`eval/pilot_power.json`](../eval/pilot_power.json).
It assumes bin-level contamination is lognormal with coefficient of variation CV, a two-sided test at 5%, and 80% power, and it
needs **no assumed baseline contamination rate**. A Monte Carlo simulation of 4,000 trials per row confirms the closed form
(simulated power 0.78 to 0.81 at the computed sizes).

| Bins audited per arm | CV 0.5 | CV 1.0 | CV 1.5 |
|---|---|---|---|
| Detect a 10% relative reduction | 316 | 981 | 1,667 |
| Detect a 20% relative reduction | 71 | 219 | 372 |
| Detect a 30% relative reduction | 28 | 86 | 146 |
| Detect a 50% relative reduction | 8 | 23 | 39 |

CV is not known for any real programme; the first step of a pilot is to estimate it from baseline audits and re-run the script.

## Ready to run
The analysis is already written and tested, so a pilot's data can be turned into an answer the day the audits finish:
fill [`pilot_audit_template.csv`](pilot_audit_template.csv) (one row per unit and period: `unit_id, arm, period, contaminant_kg, total_kg`) and run
`python scripts/analyze_pilot.py audits.csv`. It reports the relative reduction in contamination by weight with a 95% interval, adjusting
for each unit's own baseline. [`tests/test_pilot_analysis.py`](../tests/test_pilot_analysis.py) checks it on simulated pilots with a known effect:
it recovers a 30% reduction, its 95% interval covers the truth between 90% and 99% of the time over 200 simulated pilots, and it
flags no effect when there is none about as rarely as the nominal 5%.

## What would change the plan
- If uptake is low, the intervention is the outreach, not the model.
- If the tool's "not sure" rate is high for a city's common items, add rules and labelled photos for those items first.
- Any real pilot needs the city's agreement, a privacy review (the hosted demo keeps photos on the device; a collected-photo
  feedback path would not), and a decision rule agreed before the audits start.

## What this protocol does not give you
A cost estimate, a carbon figure or a tonnage claim. None of these exist for CurbCheck, and none are claimed anywhere.
