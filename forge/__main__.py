import sys
from .cli import main as task_main
from .corpus_cli import main as corpus_main


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "corpus":
        sys.exit(corpus_main(sys.argv[2:]))
    sys.exit(task_main())


if __name__ == "__main__":
    main()