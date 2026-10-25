from runtime.space_mission import build_mission_swarm_plan, orbital_period_minutes, size_satellite


def test_orbital_period_leo_range():
    period = orbital_period_minutes(550)
    assert 90 < period < 100


def test_satellite_margin_passes():
    result = size_satellite(payload_mass_kg=50, payload_power_w=800, launch_capacity_kg=500)
    assert result["launch_margin_kg"] > 0


def test_space_swarm_plan_builds():
    plan = build_mission_swarm_plan(
        mission_name="XUNIA Demo Mission",
        target_latitude_deg=37.54,
        payload_mass_kg=50,
        payload_power_w=800,
        launch_capacity_kg=500,
        parallel_agents=9,
    )
    assert plan["constraint_pass"] is True
    assert plan["candidate_count"] >= 4
    assert len(plan["workers"]) == 9
    assert plan["best_orbit"]["score"] > 0
