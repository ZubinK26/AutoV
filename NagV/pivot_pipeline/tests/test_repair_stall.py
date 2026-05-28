from pivot_pipeline.repair_stall import RepairStallTracker, normalize_error_message


def test_normalize_strips_line_numbers() -> None:
    a = normalize_error_message("Expecting ',' delimiter: line 66 column 24 (char 2131)")
    b = normalize_error_message("Expecting ',' delimiter: line 99 column 24 (char 9999)")
    assert a == b


def test_stall_after_repeated_registry_error() -> None:
    t = RepairStallTracker(threshold=2)
    msg = "Expecting ',' delimiter: line 66 column 24 (char 2131)"
    assert not t.record("registry_json", msg)
    assert t.record("registry_json", msg)
    assert t.stall_detected
