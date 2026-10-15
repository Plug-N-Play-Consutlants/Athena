# v0.7.10.2.7 Inquiry Correction Pass

Source findings: the public identity registry lacked William Nylander and the resolver required nationality/position for a complete unique name embedded in a question. The economic specialist returned 0.96 confidence despite missing a cap ledger and failing to answer the roster-needs component. The standings presentation omitted the baseline period even when the investigation calculated it. The current-season team performance legacy branch remains an explicit evidence gap and is NOT fixed by this overlay.

Changes: add Nylander public identity and minimally factual profile; accept a unique complete name in a sentence without demanding qualifiers; retain ambiguity for nonunique names; report missing current-season observation; lower incomplete economic answer confidence and acknowledge unanswered roster needs; expose the standings comparison baseline; add hermetic tests. No synthetic season statistics or payroll totals.

Local PASS: validate_inquiry_completion_071027.py, validate_inquiry_trace_contract.py, validate_general_inquiry_071025.py, compileall. Existing validate_public_inquiry_pathways.py is blocked by missing Athena.inquiry_execution in the reconstructed repository; this is NOT a passing suite.

Studio verification pending. Do not lock. The requested full four-inquiry acceptance is not achieved: current-season team performance acquisition and actual roster-needs investigation require further implementation.
