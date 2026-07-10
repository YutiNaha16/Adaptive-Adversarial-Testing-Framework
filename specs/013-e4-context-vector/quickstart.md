# Quickstart: Context Vector Builder (F13)

## Import

```python
from aatf.context_vector import EpisodeState, build_context, CONTEXT_DIM
import time
```

## Fresh episode — first step

```python
state = EpisodeState(
    completed_actions=set(),
    detection_history={},
    alert_history=[],
    step=0,
    start_time=time.time(),
    fired_categories=set(),
)
vec = build_context(state)
print(vec.shape)   # (50,)
print(vec.dtype)   # float32
print(vec)         # all zeros at step 0
```

## After a few steps

```python
import time

start = time.time()
state = EpisodeState(
    completed_actions={"tcp_port_scan", "ssh_brute_force"},
    detection_history={
        "tcp_port_scan": [False, False],      # 0/2 detected — evaded both times
        "ssh_brute_force": [True, False, True], # 2/3 detected
    },
    alert_history=[False, False, True, False, True],  # last 5 steps
    step=5,
    start_time=start,
    fired_categories={"ET SCAN"},
)

vec = build_context(state, current_time=start + 30)

# Interpret
alert_window   = vec[0:10]    # [0,0,0,0,0, 0,0,1,0,1] — last 5 steps
progress       = vec[10:25]   # 1.0 for tcp_port_scan, ssh_brute_force
technique      = vec[25:40]   # 0.0 for tcp_port_scan, 0.667 for ssh_brute_force
timing         = vec[40:42]   # [0.05, 0.0083]  (step=5/100, 30s/3600s)
rule_cats      = vec[42:50]   # [1,0,0,0,0,0,0,0]  ET SCAN fired
```

## Inject current_time for deterministic tests

```python
def test_timing_half_episode():
    t = 1000.0
    state = EpisodeState(
        completed_actions=set(), detection_history={},
        alert_history=[], step=50, start_time=t,
        fired_categories=set(),
    )
    vec = build_context(state, current_time=t + 1800)  # 30 minutes elapsed
    assert vec[40] == pytest.approx(0.5)   # step 50 / 100
    assert vec[41] == pytest.approx(0.5)   # 1800s / 3600s
```

## Downstream RL usage

```python
# The RL policy expects a fixed-length observation
assert CONTEXT_DIM == 50
policy_input = build_context(state)  # shape (50,) float32 — ready for LinUCB or DQN
```
