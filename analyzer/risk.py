def assess_risk(impact_result: dict) -> dict:
    """Augment impact_result with risk_level, impact_score, evidence, and recommendations."""
    affected_count: int = impact_result.get("affected_count", 0)
    direct_count: int = impact_result.get("direct_count", 0)
    indirect_count: int = impact_result.get("indirect_count", 0)
    max_depth: int = impact_result.get("max_depth", 0)
    changed_modules: list[str] = impact_result.get("changed_modules", [])
    direct_affected: list[str] = impact_result.get("direct_affected", [])

    # Risk level
    if affected_count == 0:
        risk_level = "LOW"
    elif affected_count <= 2 and max_depth <= 2:
        risk_level = "MEDIUM"
    elif affected_count <= 5:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    # Impact score (clamped to [0.0, 1.0])
    # Weights: 1 direct + 1 indirect + depth 2 = 0.3 (matches spec)
    impact_score = min(
        1.0,
        direct_count * 0.2 + indirect_count * 0.05 + max_depth * 0.025,
    )

    # Evidence bullets
    evidence: list[str] = []
    for mod in changed_modules:
        evidence.append(f"Module {mod} is changed")
    evidence.append(
        f"{direct_count} module(s) directly depend on the changed code"
    )
    if indirect_count:
        evidence.append(f"{indirect_count} modules are indirectly affected")
    if max_depth:
        evidence.append(
            f"Change propagates {max_depth} level(s) deep through the dependency tree"
        )

    # Recommendations
    recommendations: list[str] = []
    for mod in direct_affected:
        recommendations.append(
            f"REVIEW: {mod} directly depends on changed code — review for breaking changes"
        )
    if direct_count:
        recommendations.append(
            f"TEST: Run tests for all {direct_count} directly affected module(s)"
        )
    for mod in impact_result.get("indirect_affected", []):
        recommendations.append(
            f"TEST: Verify {mod} still works end-to-end"
        )

    impact_result["risk_level"] = risk_level
    impact_result["impact_score"] = round(impact_score, 4)
    impact_result["evidence"] = evidence
    impact_result["recommendations"] = recommendations

    return impact_result
