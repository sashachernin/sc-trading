# Sunday discussions

The same four roles meet Sunday at 12:00 America/New_York. Meetings are distinct records keyed by experiment/scheduled Sunday, referencing prior and upcoming weeks separately. Skipped weeks still have meetings; a first-ever meeting uses kickoff state. Meetings do not allocate capital or formally activate lessons.

Default agenda: manager opening; Avery/Morgan/Riley updates; three manager questions each followed by a different participant; manager closing. Each accepted utterance comes from a fresh role-specific runner invocation with `purpose=MEETING_TURN`. The manager chooses the three follow-up recipients; code checks routing, unique participation, speaker/phase/sequence, evidence and prior-turn references. The synthetic executable is a deterministic test double, not real AI speech.

At start, freeze verified source status, canonical P&L/cash, available review, evidence IDs, role overlays and last recap. Subsequent retries use this same packet. The initial source packet contains summary-level verified records; fuller per-role proposal/fill context can be added within the hard budget when the deployed evidence provider supports it.

Accepted turns and cursor progression commit atomically. Retry reads existing turns and resumes the first missing sequence, using deterministic role-run IDs. Publishing reads accepted speech exactly, producing JSON, Markdown and a statically rendered article from the same records. Raw HTML/executable links are rejected; React renders strings as text. Metadata includes cutoff, actual generation date, run IDs, models, overlay versions and usage availability.

Budgets: 11 accepted contributions, <=180 words/1400 characters each, <=2000 dialogue words, <=2800 article words. <=12,000 input tokens; at most two additional transient attempts across the meeting. A manager failure preserves draft for retry. A non-manager failure records unavailable participation and can produce a labeled partial article; unavailable notices are application records, not fabricated agent speech. Publication status is independent of CONTENT_READY.

Pause gates new discussion. Cron provides the scheduled invocation; missed meetings and historical reconstruction should be handled explicitly by the operator. The native trigger does not silently create old speech and pretend it ran on time. Reconstructed historical meetings must retain a historical frozen packet and actual generation time; the initial CLI does not offer automatic historical reconstruction.
