"""G9 — warm-registry two-run script."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from registry_stage.warm_registry_two_run import _parse_args, run_warm_two_phase


def test_run_warm_two_phase_calls_run_main_twice(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    reuse = tmp_path / "reuse.json"
    reg = tmp_path / "warm.json"
    seed.write_text("{}")
    reuse.write_text("{}")

    calls: list[list[str] | None] = []

    def fake_main(argv: list[str] | None) -> int:
        calls.append(argv)
        return 0

    rc = run_warm_two_phase(
        seed_bundle=seed,
        reuse_bundle=reuse,
        registry_out=reg,
        index="stub",
        no_llm=True,
        run_main=fake_main,
    )
    assert rc == 0
    assert len(calls) == 2
    assert calls[0] is not None
    assert "--save-registry" in calls[0]
    assert str(reg) in calls[0]
    assert calls[1] is not None
    assert "--registry" in calls[1]
    assert str(reg) in calls[1]


def test_run_warm_two_phase_stops_on_first_failure(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    reuse = tmp_path / "reuse.json"
    reg = tmp_path / "warm.json"
    seed.write_text("{}")
    reuse.write_text("{}")

    def fake_main(argv: list[str] | None) -> int:
        return 3

    rc = run_warm_two_phase(
        seed_bundle=seed,
        reuse_bundle=reuse,
        registry_out=reg,
        run_main=fake_main,
    )
    assert rc == 3


def test_parse_args_defaults():
    args = _parse_args([])
    assert args.seed_bundle.name == "m4_warm_seed_bundle.json"
    assert args.reuse_bundle.name == "m4_warm_reuse_bundle.json"
    assert "warm_after_seed_registry.json" in str(args.registry_out)


def test_main_requires_existing_bundles(tmp_path: Path) -> None:
    from registry_stage import warm_registry_two_run as mod

    missing = tmp_path / "nope.json"
    rc = mod.main(
        [
            "--seed-bundle",
            str(missing),
            "--reuse-bundle",
            str(missing),
            "--registry-out",
            str(tmp_path / "r.json"),
        ]
    )
    assert rc == 2


@patch("registry_stage.warm_registry_two_run.run_warm_two_phase", return_value=0)
def test_main_delegates_to_run_warm_two_phase(mock_run, tmp_path: Path) -> None:
    from registry_stage import warm_registry_two_run as mod

    s = tmp_path / "s.json"
    r = tmp_path / "r.json"
    s.write_text("x")
    r.write_text("x")
    # Use non-default bundles so we do not depend on repo fixtures path.
    out = tmp_path / "out.json"
    assert mod.main(["--seed-bundle", str(s), "--reuse-bundle", str(r), "--registry-out", str(out)]) == 0
    assert mock_run.called
