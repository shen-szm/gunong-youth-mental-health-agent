"""Export the latest completed synthetic guardian case as a local preview PDF."""

import json
from pathlib import Path
import sys
import argparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from database import SessionLocal
from guardian_pdf import generate_guardian_pdf
from guardian_schemas import SupportPlanOutput
from models import EvidenceSource, GuardianCase, SupportPlan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-code")
    parser.add_argument("--output")
    args = parser.parse_args()
    output_path = Path(args.output).resolve() if args.output else (
        Path(__file__).resolve().parents[2]
        / "output"
        / "pdf"
        / "咕哝-守护者支持方案-5.1.0-alpha.4.pdf"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        query = db.query(GuardianCase).filter(GuardianCase.status == "completed")
        if args.case_code:
            query = query.filter(GuardianCase.case_code == args.case_code)
        else:
            query = query.filter(GuardianCase.risk_level != "urgent")
        case = query.order_by(GuardianCase.id.desc()).first()
        if case is None:
            raise RuntimeError("没有可导出的已完成合成工单")
        plan_row = db.query(SupportPlan).filter(SupportPlan.case_id == case.id).first()
        if plan_row is None:
            raise RuntimeError("工单缺少支持方案")
        plan = SupportPlanOutput.model_validate(json.loads(plan_row.plan_json))
        evidence = (
            db.query(EvidenceSource)
            .filter(EvidenceSource.source_code.in_(plan.evidence_codes))
            .all()
        )
        output_path.write_bytes(generate_guardian_pdf(case, plan, evidence))
        print(output_path)
    finally:
        db.close()


if __name__ == "__main__":
    main()
