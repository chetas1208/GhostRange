from ghostrange_contracts.enums import ReasonCode
from ghostrange_contracts.scheduler_v3 import SchedulerPolicyId
from ghostrange_scheduler.simulator.engine import GhostSchedulerSimulator, synthetic_mixed_branch_context
from ghostrange_scheduler.v3.critical_path import analyze_critical_path
from ghostrange_scheduler.v3.plan import plan


def test_critical_path_mixed_branch():
    ctx = synthetic_mixed_branch_context()
    task_ids = [str(t.id) for t in ctx.tasks]
    edges = [(str(a), str(b)) for a, b in ctx.dependency_edges]
    task_types = {str(t.id): t.task_type.value for t in ctx.tasks}
    cp = analyze_critical_path(task_ids, edges, ctx.latency_model, task_types)
    assert len(cp) == 3
    # remediation is sole root; attack + regression are parallel children — both on critical path
    critical = [tid for tid, t in cp.items() if t.on_critical_path]
    assert len(critical) >= 2


def test_plan_places_ready_task():
    ctx = synthetic_mixed_branch_context()
    p = plan(ctx)
    place = [a for a in p.actions if a.action.value == "PLACE_TASK"]
    assert place
    assert place[0].reason_codes


def test_scale_out_on_high_ready_count():
    ctx = synthetic_mixed_branch_context()
    ctx.ready_task_ids = [t.id for t in ctx.tasks] * 4  # inflate ready queue
    ctx.queue_state.ready_count = 20
    p = plan(ctx)
    scale = [a for a in p.actions if a.action.value == "PROVISION_WORKER"]
    assert scale
    assert ReasonCode.SCALE_OUT_QUEUE_PRESSURE in scale[0].reason_codes


def test_simulator_records_overhead():
    ctx = synthetic_mixed_branch_context()
    ctx.policy_id = SchedulerPolicyId.GHOSTSCHEDULER_V3
    sim = GhostSchedulerSimulator(seed=0)
    result = sim.run_policy(ctx, ticks=2)
    assert result.scheduler_overhead_ms >= 0
    assert len(result.plans) == 2
