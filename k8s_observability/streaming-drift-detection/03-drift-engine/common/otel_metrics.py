"""OTLP metrics emitter shared by batch and streaming drift checks, so a
drift score computed by either mode lands in Prometheus under the exact same
metric name/labels (`mode` is the only thing that differs) — see
../README.md's "batch vs. streaming" section.

Uses observable (callback-based) gauges rather than the newer synchronous
Gauge instrument: it's the OTel Python API surface that's been stable the
longest, lowest risk for a stage that hasn't been run against a real
collector yet (see ../../04-metrics-export/, also unverified).
"""

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.metrics import Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource

_latest: dict[tuple[str, str], dict] = {}  # (feature, mode) -> {"drift_score", "drift_detected"}


def _observe_drift_score(_options):
    for (feature, mode), values in _latest.items():
        yield Observation(values["drift_score"], {"feature": feature, "mode": mode})


def _observe_drift_detected(_options):
    for (feature, mode), values in _latest.items():
        yield Observation(values["drift_detected"], {"feature": feature, "mode": mode})


def init_meter(otlp_endpoint: str) -> MeterProvider:
    resource = Resource.create({"service.name": "drift-engine"})
    exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)

    meter = metrics.get_meter("drift-engine")
    meter.create_observable_gauge(
        "drift_score",
        callbacks=[_observe_drift_score],
        description="Evidently drift score for one feature (higher = more drifted)",
    )
    meter.create_observable_gauge(
        "drift_detected",
        callbacks=[_observe_drift_detected],
        description="1 if the feature crossed DRIFT_THRESHOLD, else 0",
    )
    return provider


def record(feature: str, mode: str, drift_score: float, drift_detected: bool) -> None:
    _latest[(feature, mode)] = {
        "drift_score": drift_score,
        "drift_detected": 1 if drift_detected else 0,
    }
