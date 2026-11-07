"""Prometheus text exposition without a client library."""

from __future__ import annotations

import threading
from collections import defaultdict

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)


def _labels(d: dict) -> str:
    return "{" + ",".join(f'{k}="{v}"' for k, v in sorted(d.items())) + "}" if d else ""


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.requests = defaultdict(int)  # (route, status)
        self.latency = defaultdict(lambda: [0] * len(BUCKETS))  # route -> bucket counts
        self.latency_sum = defaultdict(float)
        self.latency_count = defaultdict(int)
        self.events = defaultdict(int)  # (event, outcome), e.g. override set, summary generated

    def observe(self, route: str, status: int, seconds: float) -> None:
        with self.lock:
            self.requests[(route, str(status))] += 1
            for i, b in enumerate(BUCKETS):
                if seconds <= b:
                    self.latency[route][i] += 1
            self.latency_sum[route] += seconds
            self.latency_count[route] += 1

    def event(self, name: str, outcome: str) -> None:
        with self.lock:
            self.events[(name, outcome)] += 1

    def render(self, gauges: dict[str, tuple[str, list[tuple[dict, float]]]]) -> str:
        lines = [
            "# HELP migplan_requests_total HTTP requests by route and status",
            "# TYPE migplan_requests_total counter",
        ]
        with self.lock:
            for (route, status), n in sorted(self.requests.items()):
                lines.append(f"migplan_requests_total{_labels({'route': route, 'status': status})} {n}")
            lines += ["# HELP migplan_request_seconds Request latency", "# TYPE migplan_request_seconds histogram"]
            for route in sorted(self.latency_count):
                for b, n in zip(BUCKETS, self.latency[route], strict=True):
                    lines.append(f"migplan_request_seconds_bucket{_labels({'route': route, 'le': b})} {n}")
                lines.append(
                    f"migplan_request_seconds_bucket{_labels({'route': route, 'le': '+Inf'})} "
                    f"{self.latency_count[route]}"
                )
                lines.append(f"migplan_request_seconds_sum{_labels({'route': route})} {self.latency_sum[route]:.6f}")
                lines.append(f"migplan_request_seconds_count{_labels({'route': route})} {self.latency_count[route]}")
            lines += ["# HELP migplan_events_total Plan events by outcome", "# TYPE migplan_events_total counter"]
            for (name, outcome), n in sorted(self.events.items()):
                lines.append(f"migplan_events_total{_labels({'event': name, 'outcome': outcome})} {n}")
        for name, (help_text, samples) in gauges.items():
            lines += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge"]
            for labels, value in samples:
                lines.append(f"{name}{_labels(labels)} {value}")
        return "\n".join(lines) + "\n"
