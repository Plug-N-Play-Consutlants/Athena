"""
Simple shared logging utilities.
"""


def log(message: str = "") -> None:
    print(message)


def log_header(title: str, width: int = 60) -> None:
    print(title)
    print("=" * width)


def log_section(title: str, width: int = 60) -> None:
    print("")
    print(title)
    print("-" * width)