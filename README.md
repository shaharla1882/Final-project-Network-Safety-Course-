# Final-project-Network-Safety-Course-

## Overview
This repository contains a Python-based simulation developed as part of the final project for the Network Safety course at Ben-Gurion University of the Negev (BGU). 

The simulation evaluates online routing and scheduling mechanisms for packet delivery in multihop networks under strict deadlines. We compare different scheduling policies and analyze how capacity redundancy affects the successful delivery ratio.

## Credits & Acknowledgments
The algorithms and theoretical framework implemented in this project are based on the following paper:
> **"Online Routing and Scheduling With Capacity Redundancy for Timely Delivery Guarantees in Multihop Networks"**
> Authors: Han Deng, Tao Zhao, and I-Hong Hou.

**Student Team:** Daniel Kachura, Ron Ashkenazi, Shahar Lavi, Asaf Schreiber, Ron Zimmerman  
**Course Instructor:** Prof. Kobi Cohen  

*Note: This code is intended for academic and educational purposes. All rights to the original Primal-Dual framework and Priced-EDF theory belong to the authors of the paper.*

## Features
The simulator (`Safety_in_graph_networks_PART_B.py`) allows you to test:
1. **Topologies:** A basic small network and a more complex 5x5 grid.
2. **Scheduling Policies:**
   * `EDF (Earliest-Deadline-First)`: Standard scheduling prioritizing packets with the closest deadline.
   * `PRICED_EDF`: A Primal-Dual based heuristic (proposed by the paper) that adds a congestion penalty (dual-price) to the EDF priority to prevent network bottlenecks.
   * `RANDOM`: Random packet selection, used as a baseline for comparison.
3. **Redundancy Sweep:** Run the models under varying redundancy factors ($R$) to measure the delivery ratio as link capacities increase.

## Usage
The simulation is executed via the command line. You can configure the topology, traffic load, and the number of iterations. The script outputs a PNG graph comparing the performance of the policies.

**Run examples:**

Small network with light traffic:
```bash
