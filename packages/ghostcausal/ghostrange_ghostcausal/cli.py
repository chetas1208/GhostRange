import json

from .simulator import run_m14_flagship_demo


def main() -> None:
    print(json.dumps(run_m14_flagship_demo(), indent=2))
