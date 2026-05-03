from __future__ import annotations

from app.tasks.canary_worker import CanaryWorker


def main() -> None:
    worker = CanaryWorker()
    results = worker.run_once()
    print(f"LLM Canary Harness worker bootstrap, evaluated={len(results)}")


if __name__ == "__main__":
    main()
