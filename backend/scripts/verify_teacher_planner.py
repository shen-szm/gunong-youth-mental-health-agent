"""Contract smoke suite. --live explicitly calls configured LoRA using synthetic enums only."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from teacher_task_planner import PlanningRequest, TaskContract, fallback_plan, preview_task


async def run(live=False):
    generate = None
    if live:
        from config import settings
        from xunfei.spark_api import ask_spark, is_spark_available
        if not settings.ALLOW_EXTERNAL_AI or not settings.ALLOW_TEACHER_TASK_PLANNER_AI or not is_spark_available():
            raise SystemExit("Live probe requires both external-AI flags and configured credentials")
        generate = ask_spark
    rows = []
    for objective in ("weekly_followup", "conversation_preparation"):
        for resource in ("not_needed", "approved_only"):
            for output in ("checklist", "one_page_brief"):
                contract = TaskContract(objective=objective, resource_policy=resource, output_format=output)
                result = await preview_task(PlanningRequest(contract=contract, confirmed=True), generate)
                rows.append({"contract": contract.model_dump(), "source": result["source"], "model_attempts": result["model_attempts"], "fallback_reason": result["fallback_reason"], "contract_passed": [s["tool"] for s in result["steps"]] == fallback_plan(contract).tools})
    report = {"data_origin": "synthetic_contracts", "mode": "live_lora" if live else "local_contract_only", "cases": len(rows), "contract_passed": sum(r["contract_passed"] for r in rows), "model_selected": sum(r["source"] == "model_selected" for r in rows), "limitations": "Tests bounded JSON planning only; not autonomous execution, human utility or clinical effectiveness", "results": rows}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(r["contract_passed"] and (not live or r["source"] == "model_selected") for r in rows) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.live)))
