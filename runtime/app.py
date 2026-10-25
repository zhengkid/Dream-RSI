import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from runtime.space_mission import build_mission_swarm_plan

APP_ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY_PATH = APP_ROOT / "ecosystem" / "ontology" / "gptdoug-all-kinds.yaml"
SPACE_ONTOLOGY_PATH = APP_ROOT / "ecosystem" / "space" / "stellarxplorers-swarm.yaml"

app = FastAPI(
    title="GPTDoug ALL KINDS Swarm",
    version="0.2.0",
    description="Governed swarm orchestration surface for Dream-RSI + Zyra + XUNIA + Palantir-compatible ontology adapters + space mission swarm.",
)

MAX_AGENTS = max(1, int(os.getenv("GPTDOUG_MAX_PARALLEL_AGENTS", "32")))
RULE = "gptdougALLKINDSFOREVERRULE"
PARENT_RULE = "ForeverRuleGPTDOUGLLMMAXMIMIXK"

ROLES = [
    "ontology_mapper",
    "repository_mapper",
    "documentation_agent",
    "compliance_mapper",
    "evaluator",
    "critic",
    "provenance_agent",
    "security_reviewer",
    "integration_agent",
]


class SwarmRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=4000)
    requested_agents: int | None = Field(default=None, ge=1, le=10000)
    repositories: list[str] = []
    jurisdictions: list[str] = []


class ComplianceRequest(BaseModel):
    system_name: str
    jurisdictions: list[str] = []
    use_case: str
    risk_tier: str | None = None


class SpaceMissionRequest(BaseModel):
    mission_name: str = Field(min_length=3, max_length=200)
    target_latitude_deg: float = Field(ge=-90, le=90)
    payload_mass_kg: float = Field(gt=0, le=100000)
    payload_power_w: float = Field(gt=0, le=1000000)
    launch_capacity_kg: float = Field(gt=0, le=1000000)
    requested_agents: int | None = Field(default=None, ge=1, le=10000)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "gptdoug-all-kinds-swarm",
        "rule": RULE,
        "parent_rule": PARENT_RULE,
        "status": "online",
        "max_parallel_agents": MAX_AGENTS,
        "palantir_adapter": "configured-by-environment",
        "space_mission_swarm": "enabled",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ontology")
def ontology() -> dict[str, Any]:
    if not ONTOLOGY_PATH.exists():
        raise HTTPException(status_code=404, detail="ontology manifest missing")
    return {
        "name": RULE,
        "format": "yaml",
        "source": str(ONTOLOGY_PATH.relative_to(APP_ROOT)),
        "content": ONTOLOGY_PATH.read_text(encoding="utf-8"),
    }


@app.get("/space/ontology")
def space_ontology() -> dict[str, Any]:
    if not SPACE_ONTOLOGY_PATH.exists():
        raise HTTPException(status_code=404, detail="space ontology manifest missing")
    return {
        "name": "gptdoug-stellarxplorers-space-swarm",
        "format": "yaml",
        "source": str(SPACE_ONTOLOGY_PATH.relative_to(APP_ROOT)),
        "content": SPACE_ONTOLOGY_PATH.read_text(encoding="utf-8"),
    }


@app.post("/swarm/plan")
def swarm_plan(request: SwarmRequest) -> dict[str, Any]:
    requested = request.requested_agents or MAX_AGENTS
    count = min(requested, MAX_AGENTS)
    workers = [
        {
            "agent_id": f"agent-{i+1:03d}",
            "role": ROLES[i % len(ROLES)],
            "authority": "proposal-and-evaluation-only",
        }
        for i in range(count)
    ]
    return {
        "run_id": str(uuid.uuid4()),
        "rule": RULE,
        "objective": request.objective,
        "repositories": request.repositories,
        "jurisdictions": request.jurisdictions,
        "parallel_agents": count,
        "workers": workers,
        "pipeline": [
            "ingest_context",
            "branch_candidates",
            "parallel_exploration",
            "evaluate_candidates",
            "security_and_compliance_review",
            "retain_diverse_winners",
            "record_lineage",
            "dream_replay",
            "improve_policy",
        ],
        "promotion": "review-required",
    }


@app.post("/space/mission-plan")
def space_mission_plan(request: SpaceMissionRequest) -> dict[str, Any]:
    requested = request.requested_agents or MAX_AGENTS
    count = min(requested, MAX_AGENTS)
    try:
        plan = build_mission_swarm_plan(
            mission_name=request.mission_name,
            target_latitude_deg=request.target_latitude_deg,
            payload_mass_kg=request.payload_mass_kg,
            payload_power_w=request.payload_power_w,
            launch_capacity_kg=request.launch_capacity_kg,
            parallel_agents=count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "run_id": str(uuid.uuid4()),
        "rule": RULE,
        "source_domain": "StellarXplorers public training concepts",
        "parallel_agents": count,
        **plan,
    }


@app.post("/compliance/map")
def compliance_map(request: ComplianceRequest) -> dict[str, Any]:
    return {
        "system": request.system_name,
        "use_case": request.use_case,
        "risk_tier": request.risk_tier or "unassessed",
        "jurisdictions": request.jurisdictions,
        "status": "scope-required-before-compliance-claim",
        "workflow": [
            "identify_applicable_authorities",
            "retrieve_current_official_rules",
            "map_obligations_to_controls",
            "collect_evidence",
            "evaluate_controls",
            "human_review_when_required",
            "release_or_block",
            "continuous_change_monitoring",
        ],
    }


@app.get("/palantir/deployment-plan")
def palantir_deployment_plan() -> dict[str, Any]:
    host = os.getenv("PALANTIR_FOUNDRY_HOST")
    ontology_rid = os.getenv("PALANTIR_ONTOLOGY_RID")
    configured = bool(host and ontology_rid)
    return {
        "configured": configured,
        "host_present": bool(host),
        "ontology_rid_present": bool(ontology_rid),
        "secret_present": bool(os.getenv("PALANTIR_TOKEN")),
        "required_objects": [
            "AI_System", "Agent", "Swarm", "Organization", "Agency", "Repository",
            "Production", "Model", "Dataset", "Document", "Policy", "Regulation",
            "Control", "Evaluation", "Evidence", "Incident", "HumanApproval",
            "SpaceMission", "OrbitCandidate", "SatelliteDesign", "Payload",
            "LaunchVehicle", "GroundTarget", "AccessWindow", "CoverageRegion",
            "MissionEvaluation", "MissionLineage"
        ],
        "note": "Actual Foundry ontology mutation requires a connected authorized Palantir session or deployment credentials supplied outside source control.",
    }
