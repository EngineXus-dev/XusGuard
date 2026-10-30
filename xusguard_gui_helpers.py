"""Headless GUI helpers: persistent multi-selection and readable test results."""
import re

ANSI_PATTERN = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07]*(?:\x07|\x1b\\)")


def clean_terminal_output(value):
    """Remove ANSI/terminal control sequences before showing text in Tk widgets."""
    if not isinstance(value, str):
        value = str(value)
    value = ANSI_PATTERN.sub("", value).replace("\r\n", "\n").replace("\r", "\n")
    return "".join(char for char in value if char in "\n\t" or ord(char) >= 32)


def selected_keys(ordered_keys, indices):
    """Map any number of selected rows to unique stable model keys."""
    result = []
    for raw in indices:
        index = int(raw)
        if 0 <= index < len(ordered_keys) and ordered_keys[index] not in result:
            result.append(ordered_keys[index])
    return result


def summarize_recovery_drill(stdout, stderr, returncode):
    """Keep expected negative-test log messages out of the success summary."""
    full_log = clean_terminal_output((stdout or "") + "\n" + (stderr or ""))
    lines = full_log.splitlines()
    status_lines = [line.strip() for line in lines
                    if line.startswith("test_") and " ... " in line]
    pass_count = sum(line.endswith(" ... ok") for line in status_lines)
    skip_count = sum(" ... skipped" in line for line in status_lines)
    failure_count = sum(line.endswith((" ... FAIL", " ... ERROR"))
                        for line in status_lines)
    match = re.search(r"^Ran (\d+) tests? in ([\d.]+)s$", full_log, re.MULTILINE)
    total = int(match.group(1)) if match else 0
    passed = (returncode == 0 and bool(match)
              and failure_count == 0 and "OK" in lines[-15:])
    # unittest may put stdout after stderr; rely on its terminating OK status,
    # not the position of the status line in combined captured streams.
    ok_line = next((line.strip() for line in lines
                    if line.strip() == "OK" or line.strip().startswith("OK (skipped=")), None)
    passed = (returncode == 0 and bool(match) and bool(ok_line)
              and failure_count == 0 and pass_count + skip_count == total)
    if passed:
        summary = (
            "RECOVERY DRILL PASSED\n\n"
            f"{total} tests executed  |  {pass_count} passed  |  {skip_count} skipped\n\n"
            "Backups, rollback, tamper rejection and simulated failure handling "
            "were checked against disposable hosts files.\n"
            "Expected internal error messages are hidden from this summary.\n\n"
            "No real Windows system hosts file was changed.\n"
        )
        if skip_count:
            summary += (
                "\nNote: Symlink-related tests can be skipped on Windows when "
                "the runner lacks permission to create symbolic links.\n"
            )
    else:
        summary = (
            "RECOVERY DRILL FAILED\n\n"
            f"{total or '?'} tests reported  |  {pass_count} passed"
            f"  |  {skip_count} skipped  |  {failure_count} failures/errors\n\n"
            "Review the full test output. No real system hosts file was changed.\n"
        )
    return {"passed": passed, "summary": summary, "details": full_log,
            "total": total, "passed_count": pass_count,
            "skipped": skip_count, "failure_count": failure_count}
