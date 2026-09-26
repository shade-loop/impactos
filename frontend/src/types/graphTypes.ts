/**
 * graphTypes.ts
 *
 * Shared types used by both graphData.ts and DependencyGraph.tsx.
 * No component or utility code lives here — types only.
 */

import type { ImpactState } from "../utils/blastRadius";

export interface ServiceNodeData extends Record<string, unknown> {
  label: string;
  /** Component type used for the badge (Gateway / Service / Database) */
  type: string;
  /** Impact classification injected by the parent on each selection change */
  impactState: ImpactState;
}
