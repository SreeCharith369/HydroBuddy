"""HydroBuddy application entry point."""

from core.app_controller import run_app


def main() -> int:
    """Run the HydroBuddy desktop shell."""

    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
