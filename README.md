# Final-project-Network-Safety-Course-
# Network Safety Final Project - Part B: Multihop Routing & Scheduling Simulation

## Overview
This repository contains Part B of the final project for the **Network Safety** course at Ben-Gurion University of the Negev (BGU). It features a custom Python-based discrete-time simulator designed to evaluate online routing and scheduling algorithms in multihop networks under strict latency constraints (deadlines).

The project implements, simulates, and analyzes the theoretical Primal-Dual framework proposed in the paper:
> **"Online Routing and Scheduling With Capacity Redundancy for Timely Delivery Guarantees in Multihop Networks"**
> (Han Deng, Tao Zhao, I-Hong Hou)

## Theoretical Background & Problem Statement
In modern multihop networks, ensuring packets arrive before a strict deadline is critical. Standard scheduling policies like Earliest-Deadline-First (EDF) often fail during high congestion because they prioritize deadlines while ignoring spatial bottlenecks and link loads.

To solve this, the paper proposes a **Primal-Dual (PD)** algorithmic framework that leverages **Capacity Redundancy ($R$)**—scaling the physical or logical bandwidth of links. The core mechanism implemented here is the **Priced-EDF** policy. It assigns a "shadow price" (dual variable) to each link based on its real-time congestion level. Packets are then scheduled using a combined priority metric that accounts for both their deadline urgency and the congestion price of their route, effectively mitigating bottlenecks.

## Simulator Architecture & Features
The simulator (`Safety_in_graph_networks_PART_B.py`) models a slotted-time network environment:
* **Time & Transmission:** 1 hop takes 1 time slot. Each link has a capacity of $C_l \times R$ packets per slot.
* **Routing:** Packets follow a shortest-path trajectory (hop count) towards their destinations to keep routing deterministic.
* **Performance Metric:** The primary evaluation metric is the **Delivery Ratio** (the percentage of packets that successfully reach their destination before their deadline expires).

### Supported Topologies
1. **Small Network:** A basic multi-path topology used to verify algorithmic behavior and baseline metrics.
2. **5x5 Grid Network:** A complex, highly connected topology ideal for simulating heavy traffic loads, forcing severe bottlenecks, and demonstrating the superiority of price-based scheduling.

### Implemented Scheduling Policies
* `RANDOM`: A baseline policy that selects packets randomly for transmission.
* `EDF (Earliest-Deadline-First)`: Prioritizes packets with the most urgent deadlines, blind to network congestion.
* `PRICED_EDF`: The heuristic derived from the Primal-Dual framework. It penalizes congested links, providing high stability and delivery guarantees under heavy loads.
* `PRICED_EDF_PDD`: A distributed variant of Priced-EDF (Primal-Dual Distributed) where link prices are broadcasted and updated only every $T_b$ slots. This simulates real-world environments with communication overhead and stale information.

## Usage & CLI Arguments
The simulation is executed via the command line, allowing full control over the network parameters to reproduce the paper's experiments.

**Arguments:**
* `--topo`: Network topology (`small` or `grid`).
* `--traffic`: Traffic generation rate (`light` or `heavy`).
* `--runs`: Number of iterations to average the results.
* `--horizon`: Total number of time slots per simulation run.
* `--Rmin` / `--Rmax`: The range of the Capacity Redundancy factor ($R$) to sweep.
* `--pdd` & `--Tb`: Flags to enable the distributed PDD policy with a specific broadcast period $T_b$.

