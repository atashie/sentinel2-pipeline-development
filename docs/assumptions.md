# Planning assumptions

Each row drives design, scope, or a target. Each carries a provenance status:

- `sourced`: traceable to the owner's written answers on 2026-09-09, a cited page, or a recorded decision.
- `unsourced`: stated in this repository on 2026-09-09 without a written source. Confirm it, correct it, or record the decision that set it.

[Decision 0001](decisions/0001-scope-and-sequence.md) records the owner's answers that source most rows.

| # | Assumption | Status | Used in | Note |
|---|---|---|---|---|
| A1 | Scope is data ingestion for a modeling project. The store serves raw band values, not derived water-quality indices. | sourced | everywhere | Owner answer 2026-09-09. |
| A2 | The one derived product is a set of quality flags: cloud, sensor malfunction, glint and other sensor interference, snow and ice. | sourced | [data-contract.md](data-contract.md), [s2-best-practices.md](s2-best-practices.md) | Owner answer 2026-09-09. Flag definitions are discovery work. |
| A3 | "All potentially relevant bands" means every Level-2A reflectance band (B1 to B12 except B10) plus SCL, AOT, WVP, and the cloud and snow probability layers. | unsourced | [data-contract.md](data-contract.md) | The owner asked for all potentially relevant bands. This exact list is the implementer's reading. Confirm or correct. |
| A4 | Service area is the United States now. Infrastructure must scale globally. | sourced | [assessment-protocol.md](assessment-protocol.md), [discovery-plan.md](discovery-plan.md) | Owner answer 2026-09-09. |
| A5 | Thousands of water bodies are served today, including small ponds on golf courses. | sourced | [../benchmarks/workloads.json](../benchmarks/workloads.json) | Owner answer 2026-09-09. |
| A6 | The benchmark matrix runs 1 to 10,000 water bodies. 10,000 is the ceiling for cost curves. | unsourced | [../benchmarks/workloads.json](../benchmarks/workloads.json), [assessment-protocol.md](assessment-protocol.md) | Chosen from "thousands" plus global scaling. Confirm or correct. |
| A7 | The smallest water body of interest is 10 m across. | sourced | [s2-best-practices.md](s2-best-practices.md), [data-contract.md](data-contract.md) | Owner answer 2026-09-09. Such a body is one pixel at 10 m and less than one pixel at 20 m. |
| A8 | Customer water-body polygons live in an in-house database and are serviced today with a commercial imagery provider. They never enter this repository. Prototypes use public polygons. | sourced | [../examples/README.md](../examples/README.md), [discovery-plan.md](discovery-plan.md) | Owner answer 2026-09-09. |
| A9 | The reference design rasterizes each polygon once to tile row and column masks at initialization. Extraction is then a mask lookup per scene. | sourced | [discovery-plan.md](discovery-plan.md), [data-contract.md](data-contract.md) | Owner suggestion 2026-09-09. Other workflows are compared against it. It is not selected. |
| A10 | History scenarios are 2017 onward and 2021 onward. Five years suffices for current needs. | sourced | [../benchmarks/workloads.json](../benchmarks/workloads.json), [assessment-protocol.md](assessment-protocol.md) | Owner answer 2026-09-09. The 2021 boundary also matches the geometric refinement change, claim G7 in [s2-best-practices.md](s2-best-practices.md). |
| A11 | The store supports both near-real-time ingestion of new scenes and historical backfill. | sourced | [data-contract.md](data-contract.md), [assessment-protocol.md](assessment-protocol.md) | Owner answer 2026-09-09. No latency target is set. |
| A12 | No orchestrator is mandated. Specifications stay orchestrator-agnostic. | sourced | [assessment-protocol.md](assessment-protocol.md), [discovery-plan.md](discovery-plan.md) | Owner answer 2026-09-09. |
| A13 | Sentinel-2 via AWS is the strongly preferred route. Managed and non-AWS alternatives are assessed for comparison on the same criteria. | sourced | [discovery-plan.md](discovery-plan.md) | Owner answer 2026-09-09. Preference is not selection. |
| A14 | Estimating compute and storage cost is a goal. No budget or spending ceiling exists. | sourced | [assessment-protocol.md](assessment-protocol.md) | Owner answer 2026-09-09. |
| A15 | Validation of extracted values against field observations is out of scope. | sourced | [assessment-protocol.md](assessment-protocol.md) | Owner answer 2026-09-09. |
| A16 | Joining with the weather feature pipeline is out of scope now and expected later. | sourced | [data-contract.md](data-contract.md) | Owner answer 2026-09-09. A stable water-body id keeps the join possible. |
| A17 | Cost and time scale with distinct tile-dates read, not with water-body count. | unsourced | [../benchmarks/workloads.json](../benchmarks/workloads.json), [../benchmarks/README.md](../benchmarks/README.md) | Working hypothesis from tile geometry. Measure it in prototyping before quoting it. |
| A18 | This repository can become public. | unsourced | [../CLAUDE.md](../CLAUDE.md) | Not confirmed by the owner. Roles-only naming applies regardless. |
| A19 | No dated milestones exist. Steps are ordered, not scheduled. | sourced | [work-plan.md](work-plan.md) | Owner answer 2026-09-09. |

To change an assumption, record a decision in [decisions/](decisions/README.md) and update this table.
