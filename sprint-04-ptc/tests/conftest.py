"""pytest conftest for Sprint 4 mutation testing compatibility.

When mutmut runs, the mutated `temperature_node.py` includes a
`_mutmut_trampoline` that imports `mutmut.__main__`. Because mutmut was
launched via `python -m mutmut`, that module lives in `sys.modules` as
`__main__`, not as `mutmut.__main__` — so the trampoline's import re-executes
the top-level code, including `multiprocessing.set_start_method('fork')`,
which raises `RuntimeError: context has already been set`.

Fix: in mutation-test runs only, replace `multiprocessing.set_start_method`
with a tolerant version that swallows the duplicate-context error. No-op in
normal pytest runs.
"""
import os

if os.environ.get("MUTANT_UNDER_TEST"):
    import multiprocessing as _mp

    _orig_set_start_method = _mp.set_start_method

    def _tolerant_set_start_method(*args, **kwargs):
        try:
            _orig_set_start_method(*args, **kwargs)
        except RuntimeError:
            pass

    _mp.set_start_method = _tolerant_set_start_method
