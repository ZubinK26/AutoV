import cpmpy as cp

# Slice 7 second domain: vector + global constraint (AllDistinct bins).

DOMAIN_DIMENSIONS = {"N_BINS": 3}
TEST_SHAPE_BOUNDS = {"N_BINS": 3}

N_BINS = 3
bin_counts = cp.intvar(0, 5, shape=(N_BINS,), name="bin_counts")

GLOBAL_CONSTRAINTS = [cp.AllDifferent(bin_counts)]

TOOL_DEPENDENCIES = {
    "apply_refund": ["bin_counts"],
}
