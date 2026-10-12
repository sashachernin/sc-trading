# Context and memory

Each role invocation starts fresh. The compiler reads a versioned fixed prompt, a clearly labeled ACTIVE LEARNING OVERLAY, current point-in-time records, at most eight recent completed-week summaries, older bounded aggregates and the output contract. Recent records are selected deterministically; archived meetings are excluded from Monday/Friday prompts.

Initial token budgets: rules 4,000; overlay 4,000; current data 14,000; recent 5,000; older 3,000; contract 2,000; total 32,000. `o200k_base` counts tokens when available; fallback uses UTF-8 bytes as a conservative upper bound. Section/total limits and a 256KB byte cap are checked before execution. Mandatory records/contracts that do not fit cause a visible error. Lower-priority recent/aggregate sections can be omitted deterministically, with reductions recorded.

Every run stores exact compiled input/hash and manifest: base version, exact overlay version, lesson IDs, recent week IDs, cutoff, estimate method/section sizes and reductions. At most 12 active lessons per role, each at most 700 characters. Expired lessons are excluded; new lessons are not retroactively included in the review cycle that created them.

Meeting inputs have a 12,000-token total, with at most 2,000 for instructions/overlay, 5,000 source, 4,000 transcript and 1,000 contract. The latest four complete accepted turns are selected deterministically; prior references must be among those supplied. The full accepted dialogue remains in the DB/article. Meeting source packets and role overlay contents/versions are frozen at start, so retrying after a later lesson update does not introduce future context. Only the latest <=1,500-character recap crosses meeting boundaries.

Token estimation is model-agnostic for explicitly configured models. A deployment using another tokenizer should adapt the counter and retain its provenance. Long historical audits are stored locally and do not grow active context indefinitely.
