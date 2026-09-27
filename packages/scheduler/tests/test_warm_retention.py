from ghostrange_contracts.enums import ResourceClass
from ghostrange_scheduler.warm_retention import decide_warm_retention


def test_reuse_cheaper_inside_quantum():
    d = decide_warm_retention(
        resource_class=ResourceClass.CPU_SMALL,
        idle_seconds=120,
        seconds_into_billing_quantum=600,
        predicted_next_task_seconds=300,
    )
    assert d.incremental_reuse_usd <= d.incremental_new_worker_usd
