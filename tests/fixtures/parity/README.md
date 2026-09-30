# Parity fixtures — one per registered adapter

One file per adapter in `tests/contract/adapter_registry.py`'s `REGISTRY`, named `<adapter>.<ext>`.
`scripts/adapter_parity_report.py` runs each adapter's `--file` mode over its own file here and
prints the table `docs/ADAPTER_PLAYBOOK.md` §7 must equal (`tests/test_adapter_parity.py`).
A second set, `references_construct.<ext>`, drives `tests/test_references_construct_agreement.py`.

Each file encodes **the same construct set in its own language's spelling** (R2) — a type, a class
holding a typed property, a callable taking and returning that type, a `private static` member, a
class-level constant, and a call passing a string and a number. Where a language has no such
construct the file simply omits it, and the probe reports `0/0`: *nothing to find*, which is a
measurement and not a judgement. That distinction is the whole point — `0/1` means the construct
was there and the adapter dropped it.

**Adding adapter #5 means adding a file here.** A registered adapter with no parity file makes the
report fail rather than quietly print a short table (R6.5).
