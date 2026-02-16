from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "consumers_catalog.csv"
OUT = ROOT / "docs" / "NORMATIVE_AUDIT.md"


def _f(v: str) -> float:
    try:
        return float(v or 0.0)
    except Exception:
        return 0.0


def run() -> None:
    rows = list(csv.DictReader(CATALOG.open(encoding="utf-8")))
    issues: list[str] = []
    lines: list[str] = []
    lines.append("# Аудит нормативных строк (таблица А.2)")
    lines.append("")
    lines.append("Проверки:")
    lines.append("- обязательные ссылки на норматив (`source_doc`, `source_item`)")
    lines.append("- непротиворечивость: `q_u_hot <= q_u_total`, `q_hr_hot <= q_hr_total`")
    lines.append("- расчетные значения для U=1: `Qсут`, `Qч`, `qсек`")
    lines.append("")
    lines.append("| № | Потребитель | Qсут, м3/сут | Qч, м3/ч | qсек, л/с | Статус |")
    lines.append("|---|---|---:|---:|---:|---|")

    for i, r in enumerate(rows, start=1):
        name = r.get("name", "").strip()
        q_u_tot = _f(r.get("q_u_total_l_day", "0"))
        q_u_hot = _f(r.get("q_u_hot_l_day", "0"))
        q_hr_tot = _f(r.get("q_hr_total_l_h", "0"))
        q0_tot = _f(r.get("q0_total_l_s", "0"))
        src_doc = (r.get("source_doc") or "").strip()
        src_item = (r.get("source_item") or "").strip()

        status = []
        if not src_doc or not src_item:
            status.append("нет ссылки")
            issues.append(f"{i}. {name}: пустой source_doc/source_item")
        if q_u_hot > q_u_tot + 1e-9:
            status.append("q_u_hot>q_u_total")
            issues.append(f"{i}. {name}: q_u_hot > q_u_total")
        if _f(r.get("q_hr_hot_l_h", "0")) > q_hr_tot + 1e-9 and q_hr_tot > 0:
            status.append("q_hr_hot>q_hr_total")
            issues.append(f"{i}. {name}: q_hr_hot > q_hr_total")

        q_day_m3 = q_u_tot / 1000.0
        q_hour_m3 = q_hr_tot / 1000.0
        q_sec_ls = q0_tot if q0_tot > 0 else q_hr_tot / 3600.0
        mark = "OK" if not status else ", ".join(status)
        lines.append(f"| {i} | {name} | {q_day_m3:.3f} | {q_hour_m3:.3f} | {q_sec_ls:.3f} | {mark} |")

    lines.append("")
    lines.append(f"Итого строк: **{len(rows)}**")
    lines.append(f"Проблем найдено: **{len(issues)}**")
    lines.append("")
    if issues:
        lines.append("## Замечания")
        for issue in issues:
            lines.append(f"- {issue}")
    else:
        lines.append("Замечаний нет.")

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"written: {OUT}")
    print(f"rows={len(rows)} issues={len(issues)}")


if __name__ == "__main__":
    run()

