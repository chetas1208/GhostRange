"""ghostrange_range_iac: compiles a RangeSpecV1 (+ a PHYSICAL topology plan owned by
this package, not by ghostrange_contracts) into Vultr provisioning requests and real
cloud-init content.

See README.md for the package overview and docs/adr/ADR-M2-RANGE-PROVISIONING.md for
the design rationale (why direct provider calls rather than OpenTofu for M2, why
cloud-init rather than a custom Packer image, snapshot/fork strategy, teardown
behavior).
"""

from .cloud_init import render_cloud_init
from .compiler import CompileResult, EdgeCompilationRecord, TopologyMismatchError, compile_range
from .loader import load_range, load_rangespec, load_topology
from .models import INTERNET, PhysicalGroupV1, RangeTopologyPlanV1, ReachabilityEdgeV1
from .provider_interface import (
    AppliedRangeInfra,
    CompiledRangeInfra,
    FirewallGroupCreateRequest,
    FirewallRuleCreateRequest,
    InstanceCreateRequest,
    ProvisionedFirewallGroup,
    ProvisionedInstance,
    ProvisionedVPC,
    VPCCreateRequest,
    VultrProviderProtocol,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # models (physical/topology, range-iac-owned)
    "INTERNET",
    "PhysicalGroupV1",
    "ReachabilityEdgeV1",
    "RangeTopologyPlanV1",
    # loader
    "load_rangespec",
    "load_topology",
    "load_range",
    # compiler
    "compile_range",
    "CompileResult",
    "EdgeCompilationRecord",
    "TopologyMismatchError",
    # cloud-init
    "render_cloud_init",
    # provider interface
    "VultrProviderProtocol",
    "VPCCreateRequest",
    "FirewallGroupCreateRequest",
    "FirewallRuleCreateRequest",
    "InstanceCreateRequest",
    "CompiledRangeInfra",
    "ProvisionedVPC",
    "ProvisionedFirewallGroup",
    "ProvisionedInstance",
    "AppliedRangeInfra",
]
