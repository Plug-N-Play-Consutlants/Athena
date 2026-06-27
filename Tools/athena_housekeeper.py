"""
Athena Housekeeper - Safe Cleanup Utility

Place this file at:
    F:/Development/Athena/Tools/athena_housekeeper.py

Run in Spyder:
    %runfile F:/Development/Athena/Tools/athena_housekeeper.py --wdir

Default mode is DRY RUN. Review the output first.
To actually delete files/folders, set APPLY = True below and rerun.
"""

from pathlib import Path
import hashlib
import shutil


###############################################################################
# CONFIGURATION
###############################################################################

ROOT = Path(r"F:/Development/Athena")

APPLY = True  # False = dry run, True = actually delete

DELETE_PYCACHE = True
DELETE_PYC_FILES = True
DELETE_EMPTY_DIRS = True
DELETE_KNOWN_WRAPPER_DIRS = True
DELETE_DUPLICATE_ROOT_ATHENA_PACKAGE_FILES = True

# Keep generated output by default. Set True only if you want to clear generated
# reports/exports/outputs and rebuild them later.
DELETE_GENERATED_OUTPUT = False


###############################################################################
# HELPERS
###############################################################################

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def remove_file(path: Path, actions: list[str]) -> None:
    actions.append(f"DELETE FILE: {path}")
    if APPLY:
        path.unlink(missing_ok=True)


def remove_dir(path: Path, actions: list[str]) -> None:
    actions.append(f"DELETE DIR : {path}")
    if APPLY:
        shutil.rmtree(path, ignore_errors=True)


def safe_empty_dir_delete(root: Path, actions: list[str]) -> None:
    for path in sorted(root.rglob("*"), key=lambda p: len(str(p)), reverse=True):
        if path.is_dir():
            try:
                if not any(path.iterdir()):
                    remove_dir(path, actions)
            except OSError:
                pass


###############################################################################
# CLEANUP STEPS
###############################################################################

def clean_pycache(actions: list[str]) -> None:
    if not DELETE_PYCACHE:
        return
    for path in ROOT.rglob("__pycache__"):
        if path.is_dir():
            remove_dir(path, actions)


def clean_pyc(actions: list[str]) -> None:
    if not DELETE_PYC_FILES:
        return
    for path in ROOT.rglob("*.pyc"):
        if path.is_file():
            remove_file(path, actions)


def clean_wrapper_dirs(actions: list[str]) -> None:
    if not DELETE_KNOWN_WRAPPER_DIRS:
        return

    # These are accidental patch-wrapper patterns, not valid project packages.
    prefixes = (
        "Athena_4E",
        "Athena_4D",
        "Athena_cleanup",
        "Athena_cleaned",
    )

    for path in ROOT.iterdir():
        if path.is_dir() and path.name.startswith(prefixes):
            remove_dir(path, actions)

    # This is the bad triple-nested accidental path. Do NOT delete ROOT/Athena.
    bad_nested = ROOT / "Athena" / "Athena"
    if bad_nested.exists() and bad_nested.is_dir():
        remove_dir(bad_nested, actions)


def clean_duplicate_root_package_files(actions: list[str]) -> None:
    """
    Removes duplicate root-level package files only when they are byte-for-byte
    identical to the intentional Athena/ package copy.

    Example:
        ROOT/connect.py
        ROOT/Athena/connect.py

    If identical, ROOT/connect.py is removed.
    If different, it is left untouched.
    """
    if not DELETE_DUPLICATE_ROOT_ATHENA_PACKAGE_FILES:
        return

    internal_pkg = ROOT / "Athena"
    if not internal_pkg.exists() or not internal_pkg.is_dir():
        return

    candidates = [
        "capabilities.py",
        "connect.py",
        "debug_export.py",
        "exceptions.py",
        "operation_result.py",
        "orchestrator.py",
        "status.py",
        "sync.py",
        "workspace.py",
    ]

    for name in candidates:
        root_file = ROOT / name
        pkg_file = internal_pkg / name
        if root_file.exists() and pkg_file.exists():
            try:
                if sha256(root_file) == sha256(pkg_file):
                    remove_file(root_file, actions)
                else:
                    actions.append(f"KEEP DIFF : {root_file} differs from {pkg_file}")
            except OSError as ex:
                actions.append(f"SKIP ERROR: {root_file} ({ex})")


def clean_generated_output(actions: list[str]) -> None:
    if not DELETE_GENERATED_OUTPUT:
        return

    candidates = [
        ROOT / "Output",
        ROOT / "Reports",
        ROOT / "Logs",
    ]

    for path in candidates:
        if path.exists() and path.is_dir():
            remove_dir(path, actions)


def clean_empty_dirs(actions: list[str]) -> None:
    if DELETE_EMPTY_DIRS:
        safe_empty_dir_delete(ROOT, actions)


###############################################################################
# MAIN
###############################################################################

def main() -> None:
    print("Athena Housekeeper")
    print("==================")
    print(f"Root : {ROOT}")
    print(f"Mode : {'APPLY' if APPLY else 'DRY RUN'}")
    print()

    if not ROOT.exists():
        raise RuntimeError(f"Root does not exist: {ROOT}")

    expected = ["Core", "Knowledge", "Tests"]
    missing = [name for name in expected if not (ROOT / name).exists()]
    if missing:
        print("[WARN] Missing expected root folders:", ", ".join(missing))
    else:
        print("[PASS] Project root looks valid")

    actions: list[str] = []

    clean_pycache(actions)
    clean_pyc(actions)
    clean_wrapper_dirs(actions)
    clean_duplicate_root_package_files(actions)
    clean_generated_output(actions)
    clean_empty_dirs(actions)

    print()
    print("Planned actions" if not APPLY else "Actions applied")
    print("---------------")

    if not actions:
        print("No cleanup actions needed.")
    else:
        for line in actions:
            print(line)

    print()
    print("Summary")
    print("-------")
    print(f"Total actions: {len(actions)}")
    print("Status:", "APPLIED" if APPLY else "DRY RUN ONLY")
    print()
    if not APPLY:
        print("Review the list above. To delete, set APPLY = True and rerun.")


if __name__ == "__main__":
    main()
