# ADR 0001: Python application with a C++ kernel

Status: accepted (platform v0.1, 2026-10-10); carried into the Data Core in DC1.

**Context.** A two-engineer team needs a maintainable evidence workflow; Python and C++ were requested.

**Decision.** Keep the API, I/O, transactions and orchestration in Python; use Python `Decimal` for unit arithmetic;
compile only the candidate name distance as a C++17 pybind11 extension (`cpp/`). Serve a same-origin HTML/CSS/JavaScript
interface from FastAPI.

**Alternatives considered.** All Python (simpler packaging, no native component); a separate C++ service and a separate
frontend service (more deployment and protocol overhead).

**Reasoning.** Name ranking is the one hot loop; everything else is I/O-bound and easier to test in Python.

**Consequences.** One deployment; native integration tests; a C++ compiler for source builds. Measured on 2026-10-10:
1,000 pairs of 64-character Unicode names gave equal distances, Python 0.294 s, native 0.005 s (58.75×). No other
performance claims without measurement.
