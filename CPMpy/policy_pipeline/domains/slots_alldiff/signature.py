import cpmpy as cp

# Sections 2–3: slots must take distinct codes (0..2) for this toy domain.
slot_a = cp.intvar(0, 2, name="slot_a")
slot_b = cp.intvar(0, 2, name="slot_b")
slot_c = cp.intvar(0, 2, name="slot_c")

# Optional shared globals (empty here; the rule itself uses cp.AllDifferent).
GLOBAL_CONSTRAINTS: list = []

TOOL_DEPENDENCIES = {
    "apply_refund": ["slot_a", "slot_b", "slot_c"],
}
