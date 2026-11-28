"""Default offline. --live explicitly sends only bundled synthetic requirements."""
import argparse
import asyncio
from contextlib import redirect_stdout
import io
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from teacher_intent_benchmark import evaluate


async def main(args):
    generate = None
    if args.live:
        if not args.model_label:
            raise SystemExit("--live requires --model-label (configured model name/version, never a credential)")
        from config import settings
        from xunfei.spark_api import ask_spark, is_spark_available
        if not settings.ALLOW_EXTERNAL_AI or not settings.ALLOW_TEACHER_TASK_PLANNER_AI or not is_spark_available():
            raise SystemExit("Live evaluation requires both AI flags and configured credentials; flags were not changed")
        async def generate(*call_args, **call_kwargs):
            # Legacy client prints provider failures; never include them in evidence.
            with redirect_stdout(io.StringIO()):
                reply = await ask_spark(*call_args, **call_kwargs)
            if not reply:
                raise RuntimeError("provider_unavailable")
            return reply
    if args.suite == "new-phrasing":
        from teacher_intent_validation_set import CASES, VERSION
        report = await evaluate(generate, args.model_label, CASES, VERSION, allow_format_retry=args.format_retry)
    else:
        report = await evaluate(generate, args.model_label, allow_format_retry=args.format_retry)
    report["source_sha256"] = {name: hashlib.sha256((BACKEND / name).read_bytes()).hexdigest() for name in ("teacher_task_intent.py", "teacher_intent_guard.py", "teacher_task_planner.py", "teacher_intent_benchmark.py", "teacher_intent_validation_set.py", "scripts/evaluate_teacher_intent.py", "xunfei/spark_api.py")}
    try:
        report["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=BACKEND, stderr=subprocess.DEVNULL, text=True).strip()
        report["worktree_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=BACKEND, stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        report["git_commit"], report["worktree_dirty"] = None, None
    data = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        # Never overwrite an earlier measurement. Parent directory must exist.
        with Path(args.output).open("x", encoding="utf-8") as destination:
            destination.write(data + "\n")
    else:
        print(data)
    return 0 if not args.live or report["passed"] == report["total"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model-label")
    parser.add_argument("--suite", choices=["baseline", "new-phrasing"], default="baseline")
    parser.add_argument("--format-retry", action="store_true", help="Experimental: one JSON-syntax retry within the same timeout budget")
    parser.add_argument("--output")
    arguments = parser.parse_args()
    if arguments.output and Path(arguments.output).exists():
        parser.error("output exists; choose a new file")
    raise SystemExit(asyncio.run(main(arguments)))
