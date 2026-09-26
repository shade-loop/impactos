/**
 * blastRadius.ts
 *
 * Pure utility module — no React, no side-effects.
 *
 * Exports:
 *   computeImpactMap   – BFS downstream traversal over any edge list
 *   getMockImpactData  – deterministic mock metrics per node
 *
 * Builder A: replace getMockImpactData with a real API call and keep
 * computeImpactMap as-is. The graph component and ImpactPanel are already
 * wired to consume the same ImpactData shape.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

/** Per-node impact classification produced by computeImpactMap. */
export type ImpactState =
  | "selected"
  | "direct"
  | "indirect"
  | "unaffected";

/** Map from node id → its ImpactState for the current selection. */
export type ImpactMap = Record<string, ImpactState>;

/** Structured risk / metric data shown in the Change Impact panel. */
export interface ImpactData {
  risk: "HIGH" | "MEDIUM" | "LOW";
  directDeps: number;
  indirectDeps: number;
  affectedApis: number;
  affectedTests: number;
  /** Components reachable in exactly 1 hop — shown under "Direct impact". */
  directImpact: string[];
  /** Components reachable in 2+ hops — shown under "Indirect impact". */
  indirectImpact: string[];
  /** Flat list kept for backward-compat (union of direct + indirect). */
  affectedComponents: string[];
  /** Short bullets for the Risk Analysis section. */
  riskReasons: string[];
  /** Checklist items the engineer should verify before merging. */
  verificationSteps: string[];
  /** One-sentence recommended action shown at the bottom. */
  recommendedAction: string;
  explanation: string;
}

// ─── Graph traversal ──────────────────────────────────────────────────────────

interface GraphEdge {
  source: string;
  target: string;
}

/**
 * BFS from `sourceId` following directed edges (source → target).
 * Returns an ImpactMap for all node ids supplied.
 *
 * @param sourceId   The clicked / selected node id.
 * @param allNodeIds Every node id in the graph (so unaffected ones are included).
 * @param edges      Directed edges — only `source` and `target` are consumed.
 */
export function computeImpactMap(
  sourceId: string,
  allNodeIds: string[],
  edges: GraphEdge[],
): ImpactMap {
  // Build adjacency list (source → set of direct targets)
  const adj = new Map<string, Set<string>>();
  for (const { source, target } of edges) {
    if (!adj.has(source)) adj.set(source, new Set());
    adj.get(source)!.add(target);
  }

  const directNeighbours = adj.get(sourceId) ?? new Set<string>();

  // BFS — level 1 = direct, level 2+ = indirect
  const visited = new Map<string, number>(); // id → BFS depth
  const queue: Array<{ id: string; depth: number }> = [{ id: sourceId, depth: 0 }];

  while (queue.length > 0) {
    const { id, depth } = queue.shift()!;
    if (visited.has(id)) continue;
    visited.set(id, depth);
    for (const neighbour of adj.get(id) ?? []) {
      if (!visited.has(neighbour)) {
        queue.push({ id: neighbour, depth: depth + 1 });
      }
    }
  }

  const map: ImpactMap = {};
  for (const id of allNodeIds) {
    if (id === sourceId) {
      map[id] = "selected";
    } else if (directNeighbours.has(id)) {
      map[id] = "direct";
    } else if (visited.has(id)) {
      map[id] = "indirect";
    } else {
      map[id] = "unaffected";
    }
  }
  return map;
}

// ─── Deterministic mock impact data ───────────────────────────────────────────

/**
 * Returns deterministic mock ImpactData for a node.
 * Replace this function with a backend call when Builder A ships the API.
 *
 * Exact values for UserService are spec-mandated; all others are derived
 * deterministically from the node id and ImpactMap so the UI is always
 * consistent across re-renders.
 */
export function getMockImpactData(
  nodeId: string,
  nodeLabel: string,
  nodeType: string,
  impactMap: ImpactMap,
): ImpactData {
  // Spec-mandated exact values for UserService
  if (nodeId === "userService") {
    return {
      risk: "HIGH",
      directDeps: 8,
      indirectDeps: 21,
      affectedApis: 4,
      affectedTests: 7,
      directImpact:  ["OrdersService", "CheckoutService"],
      indirectImpact: ["PaymentService", "Database"],
      affectedComponents: ["OrdersService", "CheckoutService", "PaymentService", "Database"],
      riskReasons: [
        "High downstream dependency count",
        "Multiple services depend on this component",
        "Production APIs may be affected",
        "Multiple tests require verification",
      ],
      verificationSteps: [
        "Run OrdersService tests",
        "Run CheckoutService tests",
        "Verify API contracts",
        "Verify database interactions",
      ],
      recommendedAction:
        "Review downstream dependencies and run the affected test suite before merging.",
      explanation:
        "UserService is a central hub: Auth and ProfileService both depend on it " +
        "as an entry point, while OrdersService, CheckoutService, PaymentService, " +
        "and Database are all reachable downstream. A breaking change here propagates " +
        "across the entire order and payment flow.",
    };
  }

  // For all other nodes, derive sensible values from the impact map
  const affected = Object.entries(impactMap).filter(
    ([id, s]) => id !== nodeId && (s === "direct" || s === "indirect"),
  );
  const directAffected   = affected.filter(([, s]) => s === "direct");
  const indirectAffected = affected.filter(([, s]) => s === "indirect");
  const directCount   = directAffected.length;
  const indirectCount = indirectAffected.length;

  // Deterministic pseudo-values seeded by node id character codes
  const seed = nodeId.split("").reduce((a, c) => a + c.charCodeAt(0), 0);
  const affectedApis  = (seed % 3) + 1;
  const affectedTests = (seed % 5) + 1;

  const risk: ImpactData["risk"] =
    directCount >= 2 ? "MEDIUM" : directCount === 1 ? "LOW" : "LOW";

  // Camel-case id → "Title Case" label
  const toLabel = (id: string) =>
    id.replace(/([A-Z])/g, " $1").trim().replace(/^./, (c) => c.toUpperCase());

  const directImpact   = directAffected.map(([id]) => toLabel(id));
  const indirectImpact = indirectAffected.map(([id]) => toLabel(id));
  const affectedComponents = [...directImpact, ...indirectImpact];

  const riskReasons =
    directCount > 0
      ? [
          `${directCount} service${directCount > 1 ? "s" : ""} directly depend on this component`,
          ...(indirectCount > 0
            ? [`${indirectCount} additional service${indirectCount > 1 ? "s" : ""} indirectly affected`]
            : []),
          ...(affectedApis > 0 ? ["Production APIs may be affected"] : []),
          ...(affectedTests > 0 ? ["Tests require verification before merge"] : []),
        ]
      : ["No downstream dependents detected — change is isolated"];

  const verificationSteps = [
    ...directImpact.map((name) => `Run ${name} tests`),
    ...(affectedApis > 0 ? ["Verify API contracts"] : []),
    ...(indirectCount > 0 ? ["Verify database interactions"] : []),
  ];

  const recommendedAction =
    directCount > 0
      ? "Review downstream dependencies and run the affected test suite before merging."
      : "No downstream impact detected. Proceed with standard review.";

  const explanations: Record<string, string> = {
    auth:
      "Auth is an upstream gateway. Changes here affect all clients that " +
      "authenticate before reaching UserService.",
    profileService:
      "ProfileService feeds user profile data into UserService. Changes to " +
      "its interface may break downstream consumer expectations.",
    ordersService:
      "OrdersService depends on UserService for user context. Changes here " +
      "impact Database writes and order-lifecycle operations.",
    checkoutService:
      "CheckoutService sits between UserService and PaymentService. " +
      "Changes here directly risk payment flow integrity.",
    paymentService:
      "PaymentService is a leaf-adjacent node writing final state to Database. " +
      "Changes here can silently corrupt payment records.",
    database:
      "Database is the terminal node. Changes to its schema or access patterns " +
      "propagate back through all services that read or write to it.",
  };

  return {
    risk,
    directDeps: directCount,
    indirectDeps: indirectCount,
    affectedApis,
    affectedTests,
    directImpact,
    indirectImpact,
    affectedComponents,
    riskReasons,
    verificationSteps,
    recommendedAction,
    explanation:
      explanations[nodeId] ??
      `Changes to ${nodeLabel} (${nodeType}) may affect ${directCount} direct and ` +
        `${indirectCount} indirect downstream components.`,
  };
}
