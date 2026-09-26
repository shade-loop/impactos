/**
 * graphData.ts
 *
 * Static graph topology (nodes + edges).
 * Keep this file separate from rendering so it can be replaced
 * with a backend payload without touching any component.
 */

import type { Node, Edge } from "@xyflow/react";
import type { ServiceNodeData } from "../types/graphTypes";

export const GRAPH_NODES: Node<ServiceNodeData>[] = [
  { id: "auth",            position: { x: 60,  y: 40  }, data: { label: "Auth",            type: "Gateway",  impactState: "unaffected" } },
  { id: "profileService",  position: { x: 60,  y: 160 }, data: { label: "ProfileService",  type: "Service",  impactState: "unaffected" } },
  { id: "userService",     position: { x: 300, y: 100 }, data: { label: "UserService",     type: "Service",  impactState: "unaffected" } },
  { id: "ordersService",   position: { x: 540, y: 40  }, data: { label: "OrdersService",   type: "Service",  impactState: "unaffected" } },
  { id: "checkoutService", position: { x: 540, y: 160 }, data: { label: "CheckoutService", type: "Service",  impactState: "unaffected" } },
  { id: "paymentService",  position: { x: 780, y: 160 }, data: { label: "PaymentService",  type: "Service",  impactState: "unaffected" } },
  { id: "database",        position: { x: 780, y: 40  }, data: { label: "Database",        type: "Database", impactState: "unaffected" } },
];

export const GRAPH_EDGES: Edge[] = [
  { id: "e-auth-user",      source: "auth",            target: "userService",     animated: true },
  { id: "e-profile-user",   source: "profileService",  target: "userService",     animated: true },
  { id: "e-user-orders",    source: "userService",     target: "ordersService",   animated: true },
  { id: "e-user-checkout",  source: "userService",     target: "checkoutService", animated: true },
  { id: "e-checkout-pay",   source: "checkoutService", target: "paymentService",  animated: true },
  { id: "e-orders-db",      source: "ordersService",   target: "database",        animated: true },
  { id: "e-pay-db",         source: "paymentService",  target: "database",        animated: true },
];
