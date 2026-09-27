import uuid

from ghostrange_contracts.source_model import SourceModelV1, SourceType
from ghostrange_contracts.system_graph import NormalizedSystemGraphV1
from ghostrange_contracts.ghost_ir import GhostIRV1
from ghostrange_contracts.fidelity_m5 import FidelityProfileV1, InvestigationObjectiveV1
from ghostrange_contracts.twin_compiler import TwinBlueprintV1, CompilerState


def test_source_model_minimal():
    m = SourceModelV1(source_type=SourceType.DOCKER_COMPOSE, parser_id="test", parser_version="0")
    assert m.schema_version == "1"


def test_compiler_state_enum():
    assert CompilerState.READY.value == "READY"


def test_ghost_ir_links_graph():
    gid = uuid.uuid4()
    ir = GhostIRV1(normalized_graph_id=gid)
    assert ir.normalized_graph_id == gid
