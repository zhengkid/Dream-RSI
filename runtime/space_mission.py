from __future__ import annotations

from dataclasses import dataclass, asdict
from math import pi, sqrt
from typing import Any

MU_EARTH_KM3_S2 = 398600.4418
EARTH_RADIUS_KM = 6378.137


@dataclass
class OrbitCandidate:
    altitude_km: float
    inclination_deg: float
    period_minutes: float
    score: float


@dataclass
class SatelliteCandidate:
    bus_mass_kg: float
    payload_mass_kg: float
    power_w: float
    total_mass_kg: float
    launch_margin_kg: float
    score: float


def orbital_period_minutes(altitude_km: float) -> float:
    if altitude_km < 120:
        raise ValueError("altitude_km must be at least 120 km")
    semi_major_axis = EARTH_RADIUS_KM + altitude_km
    period_seconds = 2 * pi * sqrt((semi_major_axis ** 3) / MU_EARTH_KM3_S2)
    return period_seconds / 60.0


def _orbit_score(altitude_km: float, inclination_deg: float, target_latitude_deg: float) -> float:
    access_fit = max(0.0, 1.0 - abs(abs(inclination_deg) - abs(target_latitude_deg)) / 90.0)
    altitude_fit = max(0.0, 1.0 - abs(altitude_km - 550.0) / 1500.0)
    return round((0.65 * access_fit + 0.35 * altitude_fit) * 100.0, 3)


def generate_orbit_candidates(target_latitude_deg: float, altitudes_km: list[float] | None = None) -> list[dict[str, Any]]:
    altitudes = altitudes_km or [400.0, 500.0, 550.0, 650.0, 800.0]
    inclinations = sorted({round(abs(target_latitude_deg), 3), 51.6, 70.0, 97.4})
    candidates: list[OrbitCandidate] = []
    for altitude in altitudes:
        for inclination in inclinations:
            candidates.append(
                OrbitCandidate(
                    altitude_km=altitude,
                    inclination_deg=inclination,
                    period_minutes=round(orbital_period_minutes(altitude), 3),
                    score=_orbit_score(altitude, inclination, target_latitude_deg),
                )
            )
    candidates.sort(key=lambda c: c.score, reverse=True)
    return [asdict(c) for c in candidates]


def size_satellite(
    payload_mass_kg: float,
    payload_power_w: float,
    launch_capacity_kg: float,
    bus_mass_fraction: float = 0.62,
) -> dict[str, Any]:
    if payload_mass_kg <= 0 or payload_power_w <= 0 or launch_capacity_kg <= 0:
        raise ValueError("payload mass, payload power, and launch capacity must be positive")
    if not 0.2 <= bus_mass_fraction <= 0.9:
        raise ValueError("bus_mass_fraction must be between 0.2 and 0.9")

    total_mass = payload_mass_kg / (1.0 - bus_mass_fraction)
    bus_mass = total_mass - payload_mass_kg
    margin = launch_capacity_kg - total_mass
    mass_fit = max(0.0, min(1.0, margin / launch_capacity_kg + 0.5))
    power_fit = max(0.0, min(1.0, 1.0 - payload_power_w / 5000.0))
    score = round((0.7 * mass_fit + 0.3 * power_fit) * 100.0, 3)

    return asdict(
        SatelliteCandidate(
            bus_mass_kg=round(bus_mass, 3),
            payload_mass_kg=round(payload_mass_kg, 3),
            power_w=round(payload_power_w, 3),
            total_mass_kg=round(total_mass, 3),
            launch_margin_kg=round(margin, 3),
            score=score,
        )
    )


def build_mission_swarm_plan(
    mission_name: str,
    target_latitude_deg: float,
    payload_mass_kg: float,
    payload_power_w: float,
    launch_capacity_kg: float,
    parallel_agents: int,
) -> dict[str, Any]:
    orbits = generate_orbit_candidates(target_latitude_deg)
    satellite = size_satellite(payload_mass_kg, payload_power_w, launch_capacity_kg)
    best_orbit = orbits[0]
    constraint_pass = satellite["launch_margin_kg"] >= 0
    composite_score = round((best_orbit["score"] * 0.55) + (satellite["score"] * 0.45), 3)

    roles = [
        "OrbitAgent",
        "AccessAgent",
        "SatelliteAgent",
        "PayloadAgent",
        "LaunchAgent",
        "MappingAgent",
        "CostAgent",
        "MissionCritic",
        "EvolutionAgent",
    ]
    workers = [
        {"agent_id": f"space-{i + 1:03d}", "role": roles[i % len(roles)]}
        for i in range(max(1, parallel_agents))
    ]

    return {
        "mission": mission_name,
        "best_orbit": best_orbit,
        "satellite": satellite,
        "constraint_pass": constraint_pass,
        "composite_score": composite_score,
        "workers": workers,
        "candidate_count": len(orbits),
        "evolution_loop": [
            "generate_candidates",
            "evaluate",
            "retain_winners",
            "record_lineage",
            "dream_replay",
            "mutate_next_generation",
        ],
        "note": "Educational mission-design planner; real mission operations require validated engineering models and human review.",
    }
