"""Golden-path Z3 driver on a minimal satisfiable candidate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nagv.z3_runner import run_z3, z3_feasibility_passed


TOY_SAT = '''
def run_z3_check():
    import z3
    s = z3.Solver()
    x = z3.Int("x")
    s.add(x > 0, x < 3)
    r = s.check()
    st = str(r).lower()
    m = None
    if st == "sat":
        m = str(s.model())[:500]
    return {"status": st, "model_excerpt": m}
'''


class TestZ3DriverToy(unittest.TestCase):
    def test_feasibility_and_verify_sat(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(TOY_SAT)
            p = Path(f.name)
        try:
            zf = run_z3(p, timeout_sec=60, phase="feasibility")
            self.assertTrue(z3_feasibility_passed(zf), msg=(zf.stdout, zf.stderr, zf.payload))
            zv = run_z3(p, timeout_sec=60, phase="verify")
            self.assertTrue(zv.ok, msg=(zv.stdout, zv.stderr, zv.payload))
            self.assertEqual(zv.z3_status, "sat")
        finally:
            p.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
