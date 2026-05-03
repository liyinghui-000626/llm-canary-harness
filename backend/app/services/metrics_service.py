from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil
from typing import Any

from app.core.exceptions import AppError
from app.core.repository_provider import get_repository
from app.services.experiment_service import ExperimentService
from app.utils.time_utils import utcnow_iso


class MetricsService:
    def __init__(self) -> None:
        self.experiment_service = ExperimentService()

    def get_experiment_metrics(
        self,
        experiment_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, Any]:
        experiment = self.experiment_service.get_experiment(experiment_id)
        traces = self._filter_traces(experiment_id, start_time, end_time)
        control_traces = [item for item in traces if item["version_id"] == experiment["control_version_id"]]
        treatment_traces = [item for item in traces if item["version_id"] == experiment["treatment_version_id"]]
        return {
            "experiment_id": experiment_id,
            "control": self._aggregate(experiment["control_version_id"], control_traces),
            "treatment": self._aggregate(experiment["treatment_version_id"], treatment_traces),
            "generated_at": utcnow_iso(),
        }

    def get_timeseries(
        self,
        experiment_id: str,
        metric: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict[str, Any]:
        experiment = self.experiment_service.get_experiment(experiment_id)
        delta = self._parse_interval(interval)
        traces = self._filter_traces(experiment_id, start_time, end_time)

        control = self._timeseries_for_version(
            traces, experiment["control_version_id"], metric, delta, start_time, end_time
        )
        treatment = self._timeseries_for_version(
            traces, experiment["treatment_version_id"], metric, delta, start_time, end_time
        )
        return {
            "metric": metric,
            "interval": interval,
            "control": control,
            "treatment": treatment,
        }

    def _filter_traces(
        self,
        experiment_id: str,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list[dict[str, Any]]:
        traces = [
            trace
            for trace in get_repository().list_request_traces({"experiment_id": experiment_id})
            if trace.get("experiment_id") == experiment_id
        ]
        if start_time:
            traces = [trace for trace in traces if self._parse(trace["created_at"]) >= start_time]
        if end_time:
            traces = [trace for trace in traces if self._parse(trace["created_at"]) <= end_time]
        return traces

    def _aggregate(self, version_id: str, traces: list[dict[str, Any]]) -> dict[str, Any]:
        request_count = len(traces)
        success_count = sum(1 for item in traces if item["status"] == "success")
        error_count = request_count - success_count
        latency_values = [item["latency_ms"] for item in traces]
        cost_values = [item["cost"] for item in traces]
        input_tokens = [item["input_tokens"] for item in traces]
        output_tokens = [item["output_tokens"] for item in traces]
        sorted_latency = sorted(latency_values)
        p95_index = ceil(0.95 * len(sorted_latency)) - 1 if sorted_latency else 0
        p95_latency = sorted_latency[p95_index] if sorted_latency else 0
        return {
            "version_id": version_id,
            "request_count": request_count,
            "success_count": success_count,
            "error_count": error_count,
            "error_rate": round(error_count / request_count, 4) if request_count else 0,
            "avg_latency_ms": round(sum(latency_values) / request_count, 2) if request_count else 0,
            "p95_latency_ms": p95_latency,
            "avg_cost": round(sum(cost_values) / request_count, 6) if request_count else 0,
            "avg_input_tokens": round(sum(input_tokens) / request_count, 2) if request_count else 0,
            "avg_output_tokens": round(sum(output_tokens) / request_count, 2) if request_count else 0,
        }

    def _timeseries_for_version(
        self,
        traces: list[dict[str, Any]],
        version_id: str,
        metric: str,
        delta: timedelta,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        buckets: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
        for trace in traces:
            if trace["version_id"] != version_id:
                continue
            created_at = self._parse(trace["created_at"])
            bucket = self._floor_time(created_at, delta, start_time)
            buckets[bucket].append(trace)

        points = []
        cursor = start_time
        while cursor <= end_time:
            batch = buckets.get(cursor, [])
            aggregate = self._aggregate(version_id, batch)
            points.append({"timestamp": cursor.isoformat().replace("+00:00", "Z"), "value": aggregate.get(metric, 0)})
            cursor += delta
        return points

    def _parse_interval(self, interval: str) -> timedelta:
        if interval.endswith("m"):
            return timedelta(minutes=int(interval[:-1]))
        if interval.endswith("h"):
            return timedelta(hours=int(interval[:-1]))
        raise AppError("unsupported interval", code=40006, status_code=400)

    def _floor_time(self, current: datetime, delta: timedelta, start_time: datetime) -> datetime:
        seconds = int((current - start_time).total_seconds())
        bucket_size = int(delta.total_seconds())
        aligned_seconds = (seconds // bucket_size) * bucket_size
        return start_time + timedelta(seconds=aligned_seconds)

    def _parse(self, value: str) -> datetime:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
