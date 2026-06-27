"""
Athena cleanup utility
Run from anywhere.

Default behavior is DRY RUN. Nothing is deleted unless --apply is passed.

Recommended:
    python cleanup_athena_leftovers.py --root F:\Development\Athena
    python cleanup_athena_leftovers.py --root F:\Development\Athena --apply

Optional:
    --remove-generated-output  Remove Logs/Reports/Diagnostics contents.
    --remove-pdfs             Remove rule-source PDFs if any remain.
"""

ROOT = r"F:\Development\Athena"

APPLY = False          # True = delete files
REMOVE_GENERATED = False


ROOT_DUPLICATE_PACKAGE_FILES = [
    "__init__.py",
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

CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
}

JUNK_FILE_NAMES = {
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
}

COMPILED_SUFFIXES = {
    ".pyc",
    ".pyo",
}

TEMP_PATCH_PREFIXES = (
    "Athena_4E",
    "Athena_4D",
    "Athena_4C",
    "Athena_4B",
    "Athena_4A",
)

GENERATED_OUTPUT_DIRS = [
    "Logs",
    "Reports",
    "Diagnostics",
]


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def remove_path(path: Path, root: Path, apply: bool, reason: str) -> None:
    print(f"[{'DELETE' if apply else 'DRY'}] {rel(path, root)}  -- {reason}")
    if not apply:
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


def cleanup_cache(root: Path, apply: bool) -> None:
    for path in sorted(root.rglob("*"), key=lambda p: len(str(p)), reverse=True):
        if path.is_dir() and path.name in CACHE_DIR_NAMES:
            remove_path(path, root, apply, "cache directory")
        elif path.is_file() and (path.name in JUNK_FILE_NAMES or path.suffix.lower() in COMPILED_SUFFIXES):
            remove_path(path, root, apply, "compiled/cache/junk file")


def cleanup_nested_accidental_package(root: Path, apply: bool) -> None:
    accidental = root / "Athena" / "Athena"
    if accidental.exists():
        remove_path(accidental, root, apply, "accidental nested Athena/Athena package")


def cleanup_patch_wrapper_dirs(root: Path, apply: bool) -> None:
    for path in root.iterdir():
        if path.is_dir() and path.name.startswith(TEMP_PATCH_PREFIXES):
            remove_path(path, root, apply, "temporary extracted patch wrapper directory")


def cleanup_duplicate_root_package_files(root: Path, apply: bool) -> None:
    """
    Athena/Athena is intentional.
    This removes duplicate files at repo root only when they are byte-for-byte
    identical to Athena/<same file>.
    """
    package_root = root / "Athena"
    if not package_root.is_dir():
        print("[WARN] Internal package folder missing: Athena/")
        return

    for filename in ROOT_DUPLICATE_PACKAGE_FILES:
        root_file = root / filename
        package_file = package_root / filename

        if not root_file.is_file() or not package_file.is_file():
            continue

        try:
            same = filecmp.cmp(root_file, package_file, shallow=False)
        except OSError:
            same = False

        if same:
            remove_path(
                root_file,
                root,
                apply,
                "root duplicate identical to intentional Athena/ package file",
            )
        else:
            print(
                f"[KEEP] {rel(root_file, root)} -- not identical to {rel(package_file, root)}"
            )


def cleanup_pdfs(root: Path, apply: bool) -> None:
    for pdf in sorted(root.rglob("*.pdf")):
        remove_path(pdf, root, apply, "PDF source not required for runtime rule pack")


def cleanup_generated_output(root: Path, apply: bool) -> None:
    for dirname in GENERATED_OUTPUT_DIRS:
        path = root / dirname
        if path.exists():
            remove_path(path, root, apply, "generated runtime output directory")


def remove_empty_dirs(root: Path, apply: bool) -> None:
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(str(p)), reverse=True):
        if path == root:
            continue
        try:
            if not any(path.iterdir()):
                remove_path(path, root, apply, "empty directory")
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean Athena repo leftovers safely.")
    parser.add_argument("--root", default=".", help="Path to Athena repository root.")
    parser.add_argument("--apply", action="store_true", help="Actually delete files. Default is dry-run.")
    parser.add_argument("--remove-pdfs", action="store_true", help="Remove remaining PDFs.")
    parser.add_argument(
        "--remove-generated-output",
        action="store_true",
        help="Remove Logs, Reports, and Diagnostics directories.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Root does not exist: {root}")

    expected = ["Core", "Knowledge", "Tests"]
    missing = [name for name in expected if not (root / name).exists()]
    if missing:
        print(f"[WARN] Root does not look like Athena repo root. Missing: {missing}")
        print(f"       Root: {root}")

    print("Athena Cleanup")
    print("==============")
    print(f"Root : {root}")
    print(f"Mode : {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    cleanup_cache(root, args.apply)
    cleanup_nested_accidental_package(root, args.apply)
    cleanup_patch_wrapper_dirs(root, args.apply)
    cleanup_duplicate_root_package_files(root, args.apply)

    if args.remove_pdfs:
        cleanup_pdfs(root, args.apply)

    if args.remove_generated_output:
        cleanup_generated_output(root, args.apply)

    remove_empty_dirs(root, args.apply)

    print()
    print("Cleanup complete." if args.apply else "Dry run complete. Re-run with --apply to delete.")


if __name__ == "__main__":
    main()
