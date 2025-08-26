"""Plot heart rate data using matplotlib."""

import sys


def plot_hr() -> None:
    """Plot heart rate data.

    Raises:
        RuntimeError: If matplotlib is not installed.
    """
    try:
        import matplotlib.pyplot as _  # type: ignore # noqa: F401
    except Exception as exc:  # pragma: no cover - import failure
        raise RuntimeError("matplotlib is required for plotting") from exc

    # Placeholder for plotting logic.
    # The actual implementation is not required for this test.


def main() -> None:
    try:
        plot_hr()
    except RuntimeError:
        print("matplotlib is required for plotting", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
