import argparse
import json
import sys

from .simulator import ProductionRolloutSimulator, SimScenario


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ghostrange-ghostwatch")
    sub = p.add_subparsers(dest="cmd", required=True)
    sim = sub.add_parser("simulate")
    sim.add_argument("scenario", choices=[s.value for s in SimScenario])
    args = p.parse_args(argv)
    if args.cmd == "simulate":
        results = ProductionRolloutSimulator().run_scenario(SimScenario(args.scenario))
        print(json.dumps([r.__dict__ for r in results], indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
