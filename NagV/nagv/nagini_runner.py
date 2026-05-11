"""Run Nagini as subprocess; classify failures."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class NaginiResult:
    ok: bool
    exit_code: int
    stdout: str
    stderr: str
    kind: str  # success | frontend | verification | tool_failure | timeout | missing


def resolve_nagini_exe() -> Path | None:
    env = os.environ.get("NAGV_NAGINI_EXE", "").strip()
    if env:
        p = Path(env)
        return p if p.is_file() else None
    # NagV/.venv next to nagv package
    nagv_dir = Path(__file__).resolve().parents[1]
    cand = nagv_dir / ".venv" / "Scripts" / "nagini.exe"
    if cand.is_file():
        return cand
    cand = nagv_dir / ".venv" / "bin" / "nagini"
    if cand.is_file():
        return cand
    return None


def _jdk_major_from_home(java_home: Path) -> int | None:
    """Read ``JAVA_VERSION`` major from ``release`` (OpenJDK layout)."""
    rel = java_home / "release"
    if not rel.is_file():
        return None
    try:
        text = rel.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("JAVA_VERSION="):
            raw = line.split("=", 1)[1].strip().strip('"')
            head = raw.split(".")[0].split("+")[0].strip()
            if head.isdigit():
                return int(head)
    return None


def _collect_jvm_dirs_under_vendor(base: Path) -> list[Path]:
    """List jdk* / jre* install folders (glob + iterdir — naming varies by vendor)."""
    if not base.is_dir():
        return []
    out: list[Path] = []
    seen: set[str] = set()

    def add(p: Path) -> None:
        if not p.is_dir():
            return
        try:
            k = str(p.resolve())
        except OSError:
            k = str(p)
        if k in seen:
            return
        seen.add(k)
        out.append(p)

    for pattern in ("jdk-*", "jre-*", "jdk*", "jre*"):
        try:
            for p in base.glob(pattern):
                add(p)
        except OSError:
            continue
    try:
        for p in base.iterdir():
            pl = p.name.lower()
            if p.is_dir() and (pl.startswith("jdk") or pl.startswith("jre")):
                add(p)
    except OSError:
        pass
    return out


def discover_windows_jdk_home() -> Path | None:
    """
    Find a JDK/JRE 11+ under common Windows install locations (Temurin, Microsoft, etc.).

    Prefer major 17, then 21, then 11, then other 11+. Skip Java 8.
    Set ``NAGV_DISABLE_JAVA_DISCOVERY=1`` to skip (use only JAVA_HOME / ``which java``).
    """
    if os.name != "nt":
        return None
    if os.environ.get("NAGV_DISABLE_JAVA_DISCOVERY", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return None

    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    w6432 = os.environ.get("ProgramW6432", pf)
    local = os.environ.get("LOCALAPPDATA", "").strip()

    roots: list[Path] = []
    for r in (
        Path(w6432) / "Eclipse Adoptium",
        Path(pf) / "Eclipse Adoptium",
        Path(pf) / "Microsoft",
        Path(pf) / "Java",
        Path(pf) / "Amazon Corretto",
        Path(pf86) / "Eclipse Adoptium",
        Path(pf86) / "Microsoft",
    ):
        roots.append(r)
    if local:
        roots.append(Path(local) / "Programs" / "Eclipse Adoptium")

    scored: list[tuple[int, int, Path]] = []
    rank_map = {17: 300, 21: 200, 11: 100}
    seen_home: set[str] = set()

    for base in roots:
        for p in _collect_jvm_dirs_under_vendor(base):
            try:
                key = str(p.resolve())
            except OSError:
                key = str(p)
            if key in seen_home:
                continue
            seen_home.add(key)
            maj = _jdk_major_from_home(p)
            if maj is None or maj < 11 or maj == 8:
                continue
            tier = rank_map.get(maj, maj)
            scored.append((tier, maj, p))

    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], -t[1], str(t[2])))
    return scored[0][2].resolve()


def resolve_java_home_hint() -> None:
    """
    Set ``JAVA_HOME`` for this process (and thus Nagini's child env).

    Priority:
    1. ``NAGV_JAVA_HOME`` if set.
    2. Existing ``JAVA_HOME`` if it parses as JDK/JRE 11+ (via ``release`` file).
    3. On Windows: auto-discover 11+ under standard dirs; **replaces** JAVA_HOME if it is
       8, unknown, or missing (so a stale Java 8 system install does not win).
    4. Derive from ``which java`` only if discovery found nothing (may be Java 8).
    """
    override = os.environ.get("NAGV_JAVA_HOME", "").strip()
    if override:
        os.environ["JAVA_HOME"] = override
        return

    cur = os.environ.get("JAVA_HOME", "").strip()
    if cur:
        maj = _jdk_major_from_home(Path(cur))
        if maj is not None and maj >= 11:
            return
        discovered = discover_windows_jdk_home()
        if discovered:
            os.environ["JAVA_HOME"] = str(discovered)
        return

    discovered = discover_windows_jdk_home()
    if discovered:
        os.environ["JAVA_HOME"] = str(discovered)
        return

    which = shutil.which("java")
    if not which:
        return
    p = Path(which).resolve()
    if p.name.lower() == "java" and p.parent.name.lower() == "bin":
        os.environ["JAVA_HOME"] = str(p.parent.parent)


def _normalize_path_with_java_first(path_str: str, java_home: Path) -> str:
    """Put ``JAVA_HOME\\bin`` and ``bin\\server`` first; drop duplicate occurrences."""
    jb = java_home / "bin"
    jsv = java_home / "bin" / "server"
    try:
        jb_r = jb.resolve()
    except OSError:
        jb_r = jb
    jsv_r: Path | None = None
    if jsv.is_dir():
        try:
            jsv_r = jsv.resolve()
        except OSError:
            jsv_r = jsv

    parts: list[str] = []
    seen: set[str] = set()
    for raw in path_str.split(os.pathsep):
        if not raw:
            continue
        try:
            key = str(Path(raw).resolve())
        except OSError:
            key = raw
        if key in seen:
            continue
        if key == str(jb_r) or (jsv_r and key == str(jsv_r)):
            continue
        seen.add(key)
        parts.append(raw)

    front: list[str] = [str(jb)]
    if jsv.is_dir():
        front.append(str(jsv))
    return os.pathsep.join(front + parts)


def child_env_for_nagini() -> dict[str, str]:
    """
    Environment for the Nagini subprocess.

    - Sets ``JAVA_HOME`` explicitly and puts ``JAVA_HOME\\bin`` and ``JAVA_HOME\\bin\\server``
      at the **front** of ``PATH`` (single consistent JVM for JPype / ``jvm.dll`` on Windows).
    - Merges ``JAVA_TOOL_OPTIONS`` with NagV defaults unless ``NAGV_JAVA_TOOL_OPTIONS``
      is set (empty string = no NagV-added flags).
    """
    env = os.environ.copy()
    jh_raw = env.get("JAVA_HOME", "").strip()
    if jh_raw:
        jh = Path(jh_raw).resolve()
        env["JAVA_HOME"] = str(jh)
        env["PATH"] = _normalize_path_with_java_first(env.get("PATH", ""), jh)

    raw_extra = os.environ.get("NAGV_JAVA_TOOL_OPTIONS")
    if raw_extra is None:
        extra = "-Xmx4g -Djava.awt.headless=true"
    else:
        extra = raw_extra.strip()

    if extra:
        existing = env.get("JAVA_TOOL_OPTIONS", "").strip()
        env["JAVA_TOOL_OPTIONS"] = f"{extra} {existing}".strip() if existing else extra

    return env


def run_nagini(py_file: Path, *, timeout_sec: int = 600) -> NaginiResult:
    resolve_java_home_hint()
    jh = os.environ.get("JAVA_HOME", "").strip()
    if jh:
        maj = _jdk_major_from_home(Path(jh))
        if maj is not None and maj <= 8:
            print(
                "warning: JAVA_HOME appears to be Java 8; JPype+Nagini on Windows often "
                "needs JDK 11+. Install Temurin 17 (default path) or set NAGV_JAVA_HOME.",
                file=sys.stderr,
            )

    exe = resolve_nagini_exe()
    if exe is None:
        return NaginiResult(
            ok=False,
            exit_code=-1,
            stdout="",
            stderr="Nagini executable not found; set NAGV_NAGINI_EXE or install nagini in NagV/.venv",
            kind="missing",
        )
    child_env = child_env_for_nagini()
    try:
        proc = subprocess.run(
            [str(exe), "-v", str(py_file)],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        return NaginiResult(
            ok=False,
            exit_code=-124,
            stdout="",
            stderr=f"Nagini timed out after {timeout_sec}s",
            kind="timeout",
        )
    out = proc.stdout or ""
    err = proc.stderr or ""
    combined = (out + "\n" + err).lower()
    ok = proc.returncode == 0 and "verification successful" in combined
    if ok:
        return NaginiResult(True, proc.returncode, out, err, "success")
    if (
        "syntaxerror" in combined
        or "parse error" in combined
        or "indentationerror" in combined
        or "translation failed" in combined
        or "type error" in combined
    ):
        kind = "frontend"
    elif (
        "fatal error has been detected by the java runtime" in combined
        or ("fatal error has been detected" in combined and "jre version:" in combined)
        or "hs_err_pid" in combined
        or "there is insufficient memory for the java runtime" in combined
        or "outofmemoryerror" in combined
        or "could not create the java virtual machine" in combined
        or "java vm failed to start" in combined
        or "a java exception has been" in combined
    ):
        kind = "tool_failure"
    elif (
        "verification failed" in combined
        or "might not hold" in combined
        or "postcondition might not hold" in combined
        or "exhale might fail" in combined
        or "inhale might fail" in combined
    ):
        kind = "verification"
    elif proc.returncode != 0:
        kind = "tool_failure"
    else:
        kind = "frontend"
    return NaginiResult(False, proc.returncode, out, err, kind)


def nagini_translation_passed(nag: NaginiResult) -> bool:
    """True if Nagini completed translation (verification may still fail)."""
    return nag.kind in ("success", "verification")
