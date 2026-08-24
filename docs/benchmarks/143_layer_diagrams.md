# 143 — layer graphs of the pinned public repos

Generated from `scripts/layer_diagram_report.py` against `scripts/cross_repo_samples.json`. HEURISTIC-only arrows are dashed.

## `laravel/laravel` @ `ff031db`

- layers: 5 shown of 5
- DYNAMIC-only crossings omitted: 1

```mermaid
flowchart LR
N0["Config / Migration"]
N1["HTTP / Entry"]
N2["Tests"]
N3["Uncategorised"]
N4["Domain / Data"]
```

## `symfony/demo` @ `03fe256`

- layers: 7 shown of 7
- DYNAMIC-only crossings omitted: 13

```mermaid
flowchart LR
N0["Uncategorised"]
N1["HTTP / Entry"]
N2["Tests"]
N3["Views"]
N4["Config / Migration"]
N5["Shared Library"]
N6["Domain / Data"]
N0 -->|"24"| N6
N1 -->|"12"| N6
N3 -->|"3"| N6
N2 -->|"2"| N0
N0 -.->|"2"| N5
N6 -->|"1"| N0
N6 -.->|"1"| N3
N1 -->|"1"| N0
N5 -.->|"1"| N3
N2 -.->|"1"| N6
```

## `brick/math` @ `b61d8e6`

- layers: 2 shown of 2
- DYNAMIC-only crossings omitted: 26

```mermaid
flowchart LR
N0["Tests"]
N1["Uncategorised"]
N0 -->|"33"| N1
```
