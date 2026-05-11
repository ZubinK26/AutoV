import cpmpy as cp

DOMAIN_DIMENSIONS = {"LINE_LEN": 4}
TEST_SHAPE_BOUNDS = {"LINE_LEN": 4}

LINE_LEN = 4
line_flags = cp.boolvar(shape=(LINE_LEN,), name="line_flags")

TOOL_DEPENDENCIES = {"apply_refund": ["line_flags"]}
