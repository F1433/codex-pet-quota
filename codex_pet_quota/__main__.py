import argparse
import json
import sys

from .pet_locator import diagnostics_as_dicts
from .service import QuotaService


def _once() -> int:
    service = QuotaService()
    try:
        view, decision = service.refresh()
        payload = {
            "state": view.state,
            "source": view.source,
            "remainingPercent": view.remaining_percent,
            "resetsAt": view.resets_at,
            "fetchedAt": view.fetched_at,
            "lowQuota": decision.badge_visible,
            "newAlert": decision.should_notify,
            "message": view.message,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if view.state in ("ready", "unavailable") else 2
    except Exception as exc:
        print(json.dumps({"state": "error", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    finally:
        service.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex 宠物周额度伴随卡片")
    parser.add_argument("--once", action="store_true", help="只读一次周额度并输出脱敏 JSON")
    parser.add_argument("--diagnose-windows", action="store_true", help="列出候选 Codex 窗口，不读取额度")
    parser.add_argument("--background", action="store_true", help="静默后台等待宠物交互")
    parser.add_argument("--supervisor", action="store_true", help="随 Codex 启停并自动恢复后台监听")
    args = parser.parse_args()
    if args.once:
        return _once()
    if args.diagnose_windows:
        print(json.dumps(diagnostics_as_dicts(), ensure_ascii=False, indent=2))
        return 0
    from .instance_lock import SingleInstance

    if args.supervisor:
        from .supervisor import run_supervisor

        with SingleInstance("Local\\CodexPetQuotaSupervisor") as instance:
            if not instance.acquired:
                return 0
            run_supervisor()
        return 0

    from .ui import QuotaWindow

    with SingleInstance() as instance:
        if not instance.acquired:
            return 0
        QuotaWindow().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
