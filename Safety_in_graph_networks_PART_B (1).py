#!/usr/bin/env python3
# ==========================================
# Networks Safety (Final Project) - Part B
# Simulation: Online Routing & Scheduling with Deadlines
# Based on paper:
# "Online Routing and Scheduling With Capacity Redundancy for Timely Delivery Guarantees in Multihop Networks"
#
# This script provides a *course-level* simulator that lets you:
#   - Build two topologies: small network and 5x5 grid
#   - Generate packet arrivals with deadlines
#   - Run scheduling policies and measure delivery ratio
#   - Sweep redundancy factor R and plot results
#
# Policies implemented:
#   1) EDF        : Earliest-Deadline-First per link
#   2) PRICED_EDF : EDF with simple dual-price congestion penalty (PD-inspired heuristic)
#   3) RANDOM     : Random per link (baseline)
#
# Output:
#   - PNG plots (delivery ratio vs R)
#
# Run examples:
#   python3 partB_sim.py --topo small --traffic light --runs 20 --out small_light.png
#   python3 partB_sim.py --topo grid  --traffic heavy --runs 20 --out grid_heavy.png
#
# Notes:
#   - Time is slotted. Each hop transmission takes 1 slot.
#   - Each directed link has capacity C_l * R packets/slot (integer).
#   - Packets follow a shortest path (hop count). This keeps routing simple and reproducible.
# ==========================================

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import argparse
import random
import math
import statistics

# ----------------------------
# Graph utilities (no networkx)
# ----------------------------

Node = int
Edge = Tuple[Node, Node]

def bfs_shortest_path(adj: Dict[Node, List[Node]], s: Node, t: Node) -> Optional[List[Node]]:
    """Return one shortest path from s to t using BFS (unweighted)."""
    if s == t:
        return [s]
    q = [s]
    parent = {s: None}
    for u in q:
        for v in adj.get(u, []):
            if v not in parent:
                parent[v] = u
                if v == t:
                    # reconstruct
                    path = [t]
                    cur = t
                    while parent[cur] is not None:
                        cur = parent[cur]
                        path.append(cur)
                    path.reverse()
                    return path
                q.append(v)
    return None

def make_grid_5x5() -> Tuple[Dict[Node, List[Node]], List[Edge]]:
    """Undirected 5x5 grid, represented as bidirectional directed edges."""
    W = 5
    H = 5
    def nid(r,c): return r*W + c
    adj: Dict[Node, List[Node]] = {nid(r,c): [] for r in range(H) for c in range(W)}
    edges: List[Edge] = []
    for r in range(H):
        for c in range(W):
            u = nid(r,c)
            for dr, dc in [(1,0), (-1,0), (0,1), (0,-1)]:
                rr, cc = r+dr, c+dc
                if 0 <= rr < H and 0 <= cc < W:
                    v = nid(rr,cc)
                    adj[u].append(v)
                    edges.append((u,v))
    return adj, edges

def make_small_topology() -> Tuple[Dict[Node, List[Node]], List[Edge]]:
    """
    A small connected topology (10 nodes) with multiple paths.
    This is a *reasonable* 'small network' for class simulation.
    """
    adj: Dict[Node, List[Node]] = {i: [] for i in range(10)}
    undirected = [
        (0,1),(1,2),(2,3),(3,4),
        (0,5),(5,6),(6,7),(7,4),
        (1,6),(2,7),
        (5,8),(8,9),(9,4),
        (3,9)
    ]
    edges: List[Edge] = []
    for a,b in undirected:
        adj[a].append(b); adj[b].append(a)
        edges.append((a,b)); edges.append((b,a))
    return adj, edges

# ----------------------------
# Simulation model
# ----------------------------

@dataclass
class Packet:
    pid: int
    src: Node
    dst: Node
    arrival: int
    deadline: int
    path: List[Node]          # nodes along path
    hop_idx: int = 0          # next hop is path[hop_idx] -> path[hop_idx+1]
    delivered: bool = False
    dropped: bool = False     # expired

    def next_edge(self) -> Optional[Edge]:
        if self.delivered or self.dropped:
            return None
        if self.hop_idx >= len(self.path)-1:
            return None
        return (self.path[self.hop_idx], self.path[self.hop_idx+1])

    def remaining_hops(self) -> int:
        return max(0, (len(self.path)-1) - self.hop_idx)

    def slack(self, now: int) -> int:
        # slots remaining until deadline after including remaining hops
        return (self.deadline - now) - self.remaining_hops()

def cap_scale(base: int, R: int) -> int:
    return max(0, base * R)

class Scheduler:
    name: str = "BASE"
    def select(self, now: int, link: Edge, queue: List[Packet], cap: int, lambdas: Dict[Edge, float]) -> List[Packet]:
        raise NotImplementedError

class EDFScheduler(Scheduler):
    name = "EDF"
    def select(self, now: int, link: Edge, queue: List[Packet], cap: int, lambdas: Dict[Edge, float]) -> List[Packet]:
        # earliest absolute deadline first; tie-breaker smaller slack, then pid
        q = [p for p in queue if (not p.dropped and not p.delivered)]
        q.sort(key=lambda p: (p.deadline, p.slack(now), p.pid))
        return q[:cap]

class RandomScheduler(Scheduler):
    name = "RANDOM"
    def select(self, now: int, link: Edge, queue: List[Packet], cap: int, lambdas: Dict[Edge, float]) -> List[Packet]:
        q = [p for p in queue if (not p.dropped and not p.delivered)]
        random.shuffle(q)
        return q[:cap]

class PricedEDFScheduler(Scheduler):
    """
    PD-inspired heuristic:
      score(packet) = urgency - price_penalty
      urgency = 1/(slack+1)  (bigger is more urgent)
      price_penalty = sum of link prices on remaining path (approx congestion)
    """
    name = "PRICED_EDF"
    def select(self, now: int, link: Edge, queue: List[Packet], cap: int, lambdas: Dict[Edge, float]) -> List[Packet]:
        q = [p for p in queue if (not p.dropped and not p.delivered)]
        def score(p: Packet) -> float:
            s = max(0, p.slack(now))
            urgency = 1.0 / (s + 1.0)
            # approximate remaining-path price by summing lambdas along remaining edges
            price = 0.0
            for i in range(p.hop_idx, len(p.path)-1):
                e = (p.path[i], p.path[i+1])
                price += lambdas.get(e, 0.0)
            return urgency - 0.15 * price  # 0.15 is a mild penalty
        q.sort(key=lambda p: (-score(p), p.deadline, p.pid))
        return q[:cap]

def simulate_once(
    topo: str,
    traffic: str,
    R: int,
    horizon: int,
    seed: int,
    scheduler: Scheduler,
    base_cap: int = 1,
    eta: float = 0.08,
    broadcast_period: int = 1,   # if >1, prices are "broadcast" every Tb slots (PDD-like)
) -> float:
    """
    Returns delivery ratio in one run.
    """
    random.seed(seed)

    if topo == "small":
        adj, edges = make_small_topology()
        rel_deadline_min, rel_deadline_max = 2, 6
    elif topo == "grid":
        adj, edges = make_grid_5x5()
        rel_deadline_min, rel_deadline_max = 2, 10
    else:
        raise ValueError("topo must be small or grid")

    nodes = list(adj.keys())
    # directed edges list
    edge_set = set(edges)

    # link capacities (homogeneous). You can make heterogeneous by randomizing base_cap per edge if needed.
    cap = {e: cap_scale(base_cap, R) for e in edge_set}

    # dual prices (link "congestion" prices)
    lambdas = {e: 0.0 for e in edge_set}
    lambdas_stale = dict(lambdas)

    # Per-link queue: packets waiting to traverse that link as their next hop
    link_queues: Dict[Edge, List[Packet]] = {e: [] for e in edge_set}

    pid = 0
    packets: List[Packet] = []

    # traffic model: arrivals per slot
    # Light: ~20 packets/slot on average, Heavy: ~150 packets/slot on average (mirrors the paper description)
    if traffic == "light":
        # with prob 0.95 -> 0 arrivals, with prob 0.05 -> 1 "batch" of 400 arrivals? That's too spiky.
        # We use a smoother model but keep average ~20.
        lam = 20
    elif traffic == "heavy":
        lam = 150
    else:
        raise ValueError("traffic must be light or heavy")

    def poisson(lmb: float) -> int:
        # Knuth poisson for moderate lmb; for larger, use normal approx
        if lmb > 60:
            # normal approx
            return max(0, int(random.gauss(lmb, math.sqrt(lmb))))
        L = math.exp(-lmb)
        k = 0
        p = 1.0
        while p > L:
            k += 1
            p *= random.random()
        return k - 1

    for now in range(horizon):
        # Possibly refresh prices (PDD-style with stale broadcasts)
        if now % broadcast_period == 0:
            lambdas_stale = dict(lambdas)

        # 1) Generate arrivals
        k = poisson(lam)
        for _ in range(k):
            src = random.choice(nodes)
            dst = random.choice(nodes)
            while dst == src:
                dst = random.choice(nodes)
            path = bfs_shortest_path(adj, src, dst)
            if path is None or len(path) < 2:
                continue
            rel_dl = random.randint(rel_deadline_min, rel_deadline_max)
            p = Packet(
                pid=pid, src=src, dst=dst,
                arrival=now, deadline=now + rel_dl,
                path=path
            )
            pid += 1
            packets.append(p)
            # enqueue on its first edge
            e0 = p.next_edge()
            if e0 in link_queues:
                link_queues[e0].append(p)

        # 2) Drop expired packets (deadline missed) before scheduling
        for p in packets:
            if (not p.delivered) and (not p.dropped) and (now > p.deadline):
                p.dropped = True

        # 3) Schedule transmissions per link
        #    We use the scheduler's selection based on current queues.
        #    Packets selected traverse one hop.
        utilization: Dict[Edge, int] = {e: 0 for e in edge_set}

        for e in edge_set:
            c = cap[e]
            if c <= 0:
                continue
            q = link_queues[e]
            if not q:
                continue
            chosen = scheduler.select(now, e, q, c, lambdas_stale)
            if not chosen:
                continue
            utilization[e] = len(chosen)

            # remove chosen from queue (stable remove by id)
            chosen_ids = set(p.pid for p in chosen)
            link_queues[e] = [p for p in q if p.pid not in chosen_ids]

            # advance each chosen packet by one hop
            for p in chosen:
                if p.dropped or p.delivered:
                    continue
                p.hop_idx += 1
                if p.hop_idx >= len(p.path)-1:
                    # arrived at destination (at end of this slot)
                    if now <= p.deadline:
                        p.delivered = True
                    else:
                        p.dropped = True
                else:
                    # enqueue to next edge for future slot
                    ne = p.next_edge()
                    if ne in link_queues:
                        link_queues[ne].append(p)

        # 4) Update dual prices (simple gradient ascent on overload)
        #    lambda <- [lambda + eta*(util - cap)]_+
        for e in edge_set:
            overload = utilization[e] - cap[e]
            if overload > 0:
                lambdas[e] += eta * overload
            else:
                # mild decay to avoid prices exploding forever
                lambdas[e] = max(0.0, lambdas[e] + eta * overload * 0.2)

    delivered = sum(1 for p in packets if p.delivered)
    total = len(packets)
    return (delivered / total) if total > 0 else 0.0

def sweep_R(
    topo: str,
    traffic: str,
    Rs: List[int],
    runs: int,
    horizon: int,
    scheduler: Scheduler,
    broadcast_period: int = 1,
    seed0: int = 42,
) -> List[Tuple[int, float, float]]:
    """
    Returns list of (R, mean_delivery, std_delivery)
    """
    out = []
    for R in Rs:
        vals = []
        for i in range(runs):
            vals.append(simulate_once(
                topo=topo, traffic=traffic, R=R,
                horizon=horizon, seed=seed0 + 1000*R + i,
                scheduler=scheduler,
                broadcast_period=broadcast_period
            ))
        out.append((R, statistics.mean(vals), statistics.pstdev(vals)))
    return out

def plot_results(results_by_policy: Dict[str, List[Tuple[int,float,float]]], out_path: str, title: str):
    """
    Uses matplotlib only when available. If not, writes a CSV-like text file.
    """
    try:
        import matplotlib.pyplot as plt
    except Exception:
        # Fallback: write text
        with open(out_path + ".txt", "w", encoding="utf-8") as f:
            f.write(title + "\n")
            for pol, rows in results_by_policy.items():
                f.write(f"\n[{pol}]\nR,mean,std\n")
                for R,m,s in rows:
                    f.write(f"{R},{m:.6f},{s:.6f}\n")
        return

    plt.figure()
    for pol, rows in results_by_policy.items():
        xs = [r[0] for r in rows]
        ys = [r[1] for r in rows]
        yerr = [r[2] for r in rows]
        plt.errorbar(xs, ys, yerr=yerr, marker='o', capsize=3, label=pol)
    plt.ylim(0, 1.02)
    plt.xlabel("Redundancy factor R")
    plt.ylabel("Delivery ratio")
    plt.title(title)
    plt.legend()
    plt.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    plt.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topo", choices=["small","grid"], default="small")
    ap.add_argument("--traffic", choices=["light","heavy"], default="light")
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--horizon", type=int, default=150)
    ap.add_argument("--Rmin", type=int, default=1)
    ap.add_argument("--Rmax", type=int, default=6)
    ap.add_argument("--out", type=str, default="delivery_vs_R.png")
    ap.add_argument("--pdd", action="store_true", help="Also run PDD-like (stale prices) using broadcast period Tb.")
    ap.add_argument("--Tb", type=int, default=10, help="Broadcast period for PDD-like run.")
    args = ap.parse_args()

    Rs = list(range(args.Rmin, args.Rmax+1))

    policies: List[Tuple[str, Scheduler, int]] = [
        ("EDF", EDFScheduler(), 1),
        ("PRICED_EDF", PricedEDFScheduler(), 1),
        ("RANDOM", RandomScheduler(), 1),
    ]
    if args.pdd:
        # PDD-like: same heuristic but with stale lambdas
        policies.append((f"PRICED_EDF_PDD_Tb={args.Tb}", PricedEDFScheduler(), args.Tb))

    results_by_policy = {}
    for name, sched, Tb in policies:
        rows = sweep_R(
            topo=args.topo, traffic=args.traffic, Rs=Rs,
            runs=args.runs, horizon=args.horizon,
            scheduler=sched, broadcast_period=Tb
        )
        results_by_policy[name] = rows

    title = f"Delivery ratio vs R | topo={args.topo} | traffic={args.traffic} | runs={args.runs}"
    plot_results(results_by_policy, args.out, title)
    print("Saved:", args.out)
    for pol, rows in results_by_policy.items():
        print(pol, ":", ", ".join([f"R={R}-> {m:.3f}" for R,m,_ in rows]))

if __name__ == "__main__":
    main()
