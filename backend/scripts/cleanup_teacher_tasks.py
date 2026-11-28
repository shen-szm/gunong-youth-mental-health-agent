"""Preview local checkpoint retention; --apply explicitly commits deletion."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_cleanup import cleanup_expired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True, help="Exact existing task runtime directory")
    parser.add_argument("--apply", action="store_true", help="Delete eligible expired checkpoints; irreversible without a backup")
    args = parser.parse_args()
    try:
        result = cleanup_expired(args.directory, apply=args.apply)
    except Exception:
        # Do not print deserialized data or database/provider exception text.
        print("Cleanup stopped. Check the directory, schema, task metadata and execution lock.", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
