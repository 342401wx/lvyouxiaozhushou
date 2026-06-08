import argparse

from _bootstrap import SRC  # noqa: F401

from education_qa.web_app import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the tourism planning web app.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
