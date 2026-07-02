import json
import pathlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aatf.contracts import (
    Action,
    ContextVector,
    DetectionResult,
    EpisodeRecord,
    RunManifest,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(UTC)


def _action(**kwargs) -> Action:
    defaults = dict(
        action_id="act-001",
        category="scan",
        parameters={"rate": 10},
        timestamp=_now(),
    )
    return Action.model_validate({**defaults, **kwargs})


def _detection(**kwargs) -> DetectionResult:
    defaults = dict(
        alerted=False,
        rule_ids=[],
        anomaly_score=0.0,
        coverage="uncovered",
    )
    return DetectionResult.model_validate({**defaults, **kwargs})


def _ctx(**kwargs) -> ContextVector:
    defaults = dict(
        alert_history=[0.0, 1.0],
        attack_progress=0.25,
        current_stage=1,
        technique_detection_rates={"scan": 0.5},
        time_since_last_alert=5.0,
    )
    return ContextVector.model_validate({**defaults, **kwargs})


def _episode(**kwargs) -> EpisodeRecord:
    ctx = _ctx()
    defaults = dict(
        episode_id="ep-001",
        step=0,
        action=_action(),
        detection=_detection(),
        reward=-1.0,
        context_before=ctx,
        context_after=ctx,
        timestamp=_now(),
    )
    return EpisodeRecord.model_validate({**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Action — T-A1 through T-A5
# ---------------------------------------------------------------------------


def test_action_valid():
    a = _action()
    assert a.action_id == "act-001"
    assert a.category == "scan"
    assert a.parameters == {"rate": 10}


def test_action_missing_action_id():
    with pytest.raises(ValidationError) as exc:
        Action.model_validate({"category": "scan", "parameters": {}, "timestamp": _now()})
    assert "action_id" in str(exc.value)


def test_action_missing_category():
    with pytest.raises(ValidationError) as exc:
        Action.model_validate({"action_id": "x", "parameters": {}, "timestamp": _now()})
    assert "category" in str(exc.value)


def test_action_empty_parameters():
    a = _action(parameters={})
    assert a.parameters == {}


def test_action_is_frozen():
    a = _action()
    with pytest.raises(ValidationError):
        a.category = "exfil"


# ---------------------------------------------------------------------------
# DetectionResult — T-DR1 through T-DR7
# ---------------------------------------------------------------------------


def test_detection_binary_mode():
    d = DetectionResult.model_validate(
        dict(alerted=True, rule_ids=["SID:2100498"], anomaly_score=0.0, coverage="covered")
    )
    assert d.alerted is True
    assert d.rule_ids == ["SID:2100498"]


def test_detection_continuous_mode():
    d = DetectionResult.model_validate(
        dict(alerted=True, rule_ids=[], anomaly_score=0.87, coverage="covered")
    )
    assert d.anomaly_score == pytest.approx(0.87)


def test_detection_both_modes():
    d = DetectionResult.model_validate(
        dict(alerted=True, rule_ids=["SID:1234"], anomaly_score=0.91, coverage="covered")
    )
    assert d.alerted is True
    assert d.rule_ids == ["SID:1234"]
    assert d.anomaly_score == pytest.approx(0.91)


def test_detection_undetected():
    d = _detection()
    assert d.alerted is False
    assert d.coverage == "uncovered"


def test_detection_score_too_high():
    with pytest.raises(ValidationError) as exc:
        _detection(anomaly_score=1.5)
    assert "anomaly_score" in str(exc.value)


def test_detection_bad_coverage():
    with pytest.raises(ValidationError) as exc:
        _detection(coverage="maybe")
    assert "coverage" in str(exc.value)


def test_detection_score_negative():
    with pytest.raises(ValidationError) as exc:
        _detection(anomaly_score=-0.1)
    assert "anomaly_score" in str(exc.value)


# ---------------------------------------------------------------------------
# ContextVector — T-CV1 through T-CV8
# ---------------------------------------------------------------------------


def test_context_vector_valid():
    cv = _ctx()
    assert cv.current_stage == 1
    assert cv.attack_progress == pytest.approx(0.25)


def test_context_vector_alert_history_valid():
    cv = _ctx(alert_history=[0.0, 1.0, 0.0])
    assert cv.alert_history == [0.0, 1.0, 0.0]


def test_context_vector_alert_history_out_of_range():
    with pytest.raises(ValidationError) as exc:
        _ctx(alert_history=[0.0, 1.5, 0.0])
    assert "alert_history" in str(exc.value)


def test_context_vector_attack_progress_negative():
    with pytest.raises(ValidationError) as exc:
        _ctx(attack_progress=-0.1)
    assert "attack_progress" in str(exc.value)


def test_context_vector_current_stage_out_of_range():
    with pytest.raises(ValidationError) as exc:
        _ctx(current_stage=4)
    assert "current_stage" in str(exc.value)


def test_context_vector_technique_rates_out_of_range():
    with pytest.raises(ValidationError) as exc:
        _ctx(technique_detection_rates={"ssh": 1.7})
    assert "technique_detection_rates" in str(exc.value)


def test_context_vector_time_negative():
    with pytest.raises(ValidationError) as exc:
        _ctx(time_since_last_alert=-1.0)
    assert "time_since_last_alert" in str(exc.value)


def test_context_vector_empty_technique_rates():
    cv = _ctx(technique_detection_rates={})
    assert cv.technique_detection_rates == {}


# ---------------------------------------------------------------------------
# EpisodeRecord — T-ER1 through T-ER7
# ---------------------------------------------------------------------------


def test_episode_record_valid():
    er = _episode()
    assert er.episode_id == "ep-001"
    assert er.step == 0


def test_episode_record_negative_step():
    with pytest.raises(ValidationError) as exc:
        _episode(step=-1)
    assert "step" in str(exc.value)


def test_episode_record_any_reward():
    er = _episode(reward=999.9)
    assert er.reward == pytest.approx(999.9)


def test_episode_record_bad_reward_type():
    with pytest.raises(ValidationError) as exc:
        _episode(reward="high")
    assert "reward" in str(exc.value)


def test_episode_record_jsonl_roundtrip():
    er = _episode()
    data = er.model_dump(mode="json")
    line = json.dumps(data)
    restored = EpisodeRecord.model_validate(json.loads(line))
    assert restored == er


def test_episode_record_jsonl_multi_line(tmp_path):
    records = [_episode(episode_id=f"ep-{i}", step=i) for i in range(3)]
    log_file = tmp_path / "episode.jsonl"
    log_file.write_text("\n".join(json.dumps(r.model_dump(mode="json")) for r in records) + "\n")
    restored = [
        EpisodeRecord.model_validate(json.loads(line)) for line in log_file.read_text().splitlines()
    ]
    assert restored == records


def test_episode_record_missing_episode_id():
    with pytest.raises(ValidationError) as exc:
        EpisodeRecord.model_validate(
            dict(
                step=0,
                action=_action().model_dump(mode="json"),
                detection=_detection().model_dump(mode="json"),
                reward=0.0,
                context_before=_ctx().model_dump(mode="json"),
                context_after=_ctx().model_dump(mode="json"),
                timestamp=_now().isoformat(),
            )
        )
    assert "episode_id" in str(exc.value)


# ---------------------------------------------------------------------------
# RunManifest — T-RM1 through T-RM6
# ---------------------------------------------------------------------------


def _manifest_data(**kwargs) -> dict:
    defaults = dict(
        seed=42,
        python_version="3.12.3",
        packages={"pydantic": "2.13.4"},
        suricata_version="unknown",
        ruleset_version="unknown",
        git_commit="abc1234",
        config_snapshot={"episodes": 100, "seed": 42},
        timestamp="2026-07-02T04:00:00Z",
    )
    return {**defaults, **kwargs}


def test_run_manifest_valid():
    m = RunManifest.model_validate(_manifest_data())
    assert m.seed == 42
    assert m.suricata_version == "unknown"


def test_run_manifest_negative_seed():
    with pytest.raises(ValidationError) as exc:
        RunManifest.model_validate(_manifest_data(seed=-1))
    assert "seed" in str(exc.value)


def test_run_manifest_unknown_suricata():
    m = RunManifest.model_validate(_manifest_data(suricata_version="unknown"))
    assert m.suricata_version == "unknown"


def test_run_manifest_empty_packages():
    m = RunManifest.model_validate(_manifest_data(packages={}))
    assert m.packages == {}


def test_run_manifest_roundtrip():
    m = RunManifest.model_validate(_manifest_data())
    data = m.model_dump(mode="json")
    restored = RunManifest.model_validate(data)
    assert restored == m


def test_run_manifest_from_f02_file(tmp_path):
    from aatf.config import ExperimentConfig
    from aatf.manifest import write_manifest

    cfg = ExperimentConfig.model_validate(
        dict(
            episodes=10,
            seed=42,
            output_dir=str(tmp_path / "out"),
            ruleset_path="/etc/suricata/rules",
            detection_threshold=0.5,
        )
    )
    path = write_manifest(cfg, 42)
    m = RunManifest.model_validate(json.loads(path.read_text()))
    assert m.seed == 42
    assert "pydantic" in m.packages


# ---------------------------------------------------------------------------
# Static isolation guard — FR-010
# ---------------------------------------------------------------------------


def test_no_forbidden_imports():
    source = pathlib.Path("src/aatf/contracts.py").read_text()
    # Check for import statements only — field names like "suricata_version" are fine
    forbidden_imports = [
        "import aatf.defender",
        "from aatf.defender",
        "import aatf.attacker",
        "from aatf.attacker",
        "import aatf.environment",
        "from aatf.environment",
        "import suricata",
        "from suricata",
    ]
    for term in forbidden_imports:
        assert term not in source, f"Forbidden import found in contracts.py: {term}"
