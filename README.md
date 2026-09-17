# NIST Post-Quantum Cryptography & Machine Learning (PQC-ML) Toolchain

[![Build Status](https://img.shields.io/badge/tests-55%20passed-00ff87?style=flat-square)](https://github.com/KayraYavuz/Post-Quantum-Cryptography-ML-)
[![CBOM](https://img.shields.io/badge/CycloneDX-1.6%20Compliant-00f2fe?style=flat-square)](artifacts/cbom.json)
[![Compliance](https://img.shields.io/badge/NIST-SP%20800--208%20%7C%20CNSA%202.0-a855f7?style=flat-square)](artifacts/cbom_policy_report.json)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.14.0%2Bcpu-ee4c2c?style=flat-square)](artifacts/checkpoints/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1%20Live-05998b?style=flat-square)](http://claw.lan:8090)

A comprehensive open-source measurement toolchain for NIST Post-Quantum Cryptography (PQC) algorithm security, constant-time verification, quantum resource estimation, correlation power analysis (CPA), and deep learning-based side-channel leakage detection.

---

## 🏛️ System Architecture

```text
+-----------------------------------------------------------------------------------------+
|                                    USER INTERFACE                                       |
|  Live Web Dashboard (http://claw.lan:8090)  •  RESTful API Endpoints  •  CLI Matrix     |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                                   FASTAPI CORE ENGINE                                   |
|   • /api/v1/cbom             • /api/v1/security-estimate    • /api/v1/quantum-cost      |
|   • /api/v1/model/predict    • /api/v1/model/metrics        • /health                   |
|   • /api/v1/model/cpa-benchmark • /api/v1/constant-time/analysis • /api/v1/report/export |
+---------------------+----------------------+---------------------+----------------------+
                      |                      |                     |
                      v                      v                     v
+-----------------------------+ +---------------------------+ +---------------------------+
|    PQC ANALYSIS & CBOM      | |   SECURITY & QUANTUM      | |    DEEP LEARNING & CPA    |
| • CycloneDX 1.6 Generator   | | • Lattice Estimator (±2b) | | • PyTorch 1D-CNN (DLSCA)  |
| • NIST SP 800-208 Policy    | | • ML-KEM-768: 192 bits    | | • Pearson CPA Attack Lab  |
| • KyberSlash Disassembly    | | • Azure QRE & Qualtran    | | • 1st-Order Masking Check |
|   & TVLA Welch's t-test     | | • Logical Qubits & T-Gates| | • LWE MLP Distinguisher   |
| • CNSA 2.0 Audit Exporter   | | • Algorithm Migration API | | • Guessing Entropy (1.0)  |
+-----------------------------+ +---------------------------+ +---------------------------+
                      |                      |                     |
                      +----------------------+---------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                              INFRASTRUCTURE & ENVIRONMENT                               |
|   Debian Linux Server (192.168.1.23)  •  OpenClaw Autonomous Agent (Ruhi)  •  Docker    |
+-----------------------------------------------------------------------------------------+
```

---

## 🚀 Live Dashboard & Web Service

The live web service and glassmorphic dashboard run continuously on port `8090`:

- **Host LAN URL:** [http://claw.lan:8090](http://claw.lan:8090) or [http://192.168.1.23:8090](http://192.168.1.23:8090)
- **Interactive Swagger Docs:** [http://claw.lan:8090/docs](http://claw.lan:8090/docs)
- **Health Check:** `curl http://claw.lan:8090/health`

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Single-page interactive dark-mode glassmorphic dashboard (with CPA & KyberSlash Labs) |
| `GET` | `/health` | System uptime, PyTorch device status, checkpoint validation |
| `GET` | `/api/v1/cbom` | Full CycloneDX 1.6 CBOM inventory and NIST policy evaluation |
| `POST` | `/api/v1/security-estimate` | Classical bit security estimation for ML-KEM and ML-DSA |
| `POST` | `/api/v1/quantum-cost` | Logical qubit and T-gate estimation (AQRE vs Qualtran) |
| `POST` | `/api/v1/model/predict` | Real-time PyTorch CNN side-channel trace inference & vulnerability score |
| `GET` | `/api/v1/model/metrics` | Model training history, loss curves, and Guessing Entropy |
| `POST` | `/api/v1/model/cpa-benchmark` | Run automated Pearson CPA vs Deep Learning benchmark with Boolean masking |
| `GET` | `/api/v1/constant-time/analysis` | KyberSlash / Clangover disassembly inspection and Welch's t-test TVLA data |
| `GET` | `/api/v1/report/export` | Export structured JSON and Markdown NIST SP 800-208 / CNSA 2.0 audit report |
| `GET` | `/api/v1/status` | Comprehensive status of all 14 project work streams |

---

## Phase 5: Synthetic Telemetry and SIMD Timing Statistics

- `/ws/traces` supports bounded synthetic snapshots, playback, and Live Play/Pause.
  Requests accept 8–1024 samples and 1–60 requested frames per second; actual
  throughput is not guaranteed. Frames explicitly identify `source: synthetic`.
  This endpoint does not read HDF5 files or acquire hardware traces.
- `pqc_bench.simd_timing` compares **synthetic, uncalibrated modeled cycle units**
  under AVX2, AVX-512, and ARM NEON labels. It does not execute SIMD NTT kernels,
  measure processor cycles, reproduce a CVE, or prove constant-time behavior.
  Lower modeled variance is not evidence that an architecture is more secure.
- Existing NumPy statistics and the existing module are reused; no new dependency
  or hardware benchmark framework is introduced.

Run the scoped regression tests and the synthetic report:

```bash
python3 -m pytest tests/test_phase5.py tests/test_simd_timing.py -q
python3 -m pqc_bench.simd_timing
```

The authoritative next work item and outstanding hardware limitations are tracked
in [PROJECT_STATE.md](PROJECT_STATE.md).

---

## 🔬 Advanced Modules (Phase 3: WS-ADV)

### 1. Correlation Power Analysis (CPA) vs Deep Learning Lab (`WS-ADV.1`)
- **Pearson CPA Engine:** Computes Pearson correlation coefficients $\rho(k)$ between predicted intermediate Hamming weights and simulated EM/power traces across candidate key hypotheses.
- **Countermeasure Evaluation:** Benchmarks classic CPA vs Deep Learning 1D-CNN under Boolean masking countermeasures. While 1st-order Boolean masking drives classic Pearson CPA Guessing Entropy up to $\approx 25.0$ (defense effective), the non-linear multi-layer CNN bypasses 1st-order masking and achieves $\text{GE} = 1.0$.

### 2. KyberSlash / Clangover Constant-Time Inspector (`WS-ADV.2`)
- **Assembly Inspection:** Directly inspects disassembly outputs comparing vulnerable variable-time operations (`idivl`, `divl`) against constant-time Montgomery and Barrett reduction implementations (mitigating CVE-2024-37880).
- **TVLA Timing Leakage Simulation:** Implements Welch's two-sample t-test ($t = \frac{\mu_1 - \mu_2}{\sqrt{s_1^2/n_1 + s_2^2/n_2}}$). A $|t| > 4.5$ score marks statistically significant side-channel timing leakage.

### 3. Compliance Audit Report Exporter (`WS-ADV.3`)
- **Automated Audit:** Evaluates the cryptographic inventory against NIST SP 800-208 (stateful hash-based signatures) and NSA CNSA 2.0 (commercial national security algorithm suite).
- **Markdown & JSON Export:** Ready-to-file executive compliance summary with immediate remediation flags for legacy algorithms (e.g., RSA-2048, ECC P-256).

---

## 🧠 Deep Learning Side-Channel Leakage Detection

The project features a tailored 1D Convolutional Neural Network (`SideChannel1DCNN`) designed according to Deep Learning Side-Channel Analysis (DLSCA) benchmarks:

- **Input:** Power / EM consumption traces (length: 256 samples) simulating intermediate polynomial multiplication (NTT butterfly operations) and unpacking routines in ML-KEM.
- **Architecture:** 3 Multi-channel 1D Convolution blocks with Batch Normalization, ReLU, MaxPool1d, Adaptive Average Pooling, and Dropout classification head.
- **Target:** Intermediate Hamming Weight classes ($HW \in [0, 8]$) and key hypothesis ranking.
- **Guessing Entropy (GE):** Measures the average rank of the true secret candidate as attack traces aggregate. The trained model successfully drops GE to **1.0**, indicating complete secret recovery within 10 traces.

### Training Performance Summary

| Metric | Side-Channel 1D-CNN | LWE Distinguisher MLP |
|---|---|---|
| **Architecture** | Conv1d(32-64-128) + AdaptivePool | Dense(8 → 64 → 128 → 64 → 2) |
| **Epochs** | 15 epochs | 15 epochs |
| **Duration** | 19.92 seconds | 4.05 seconds |
| **Training Loss** | $1.8908 \rightarrow 1.0404$ | $0.6931 \rightarrow 0.6120$ |
| **Best Val Accuracy**| **35.83%** (vs 11.1% random baseline) | **54.50%** |
| **Guessing Entropy** | **1.0** (Target: 1.0) | - |
| **Checkpoint** | `artifacts/checkpoints/side_channel_cnn.pt` | `artifacts/checkpoints/lwe_mlp.pt` |

---

## WS-P6.1: Residual 1D waveform backbone (generic synthetic)

`SideChannelResNet1D` (in `src/pqc_bench/models/resnet1d.py`) is a residual 1D
ResNet-style classifier for **project-owned synthetic waveforms**, in the spirit
of standard residual architectures using the existing PyTorch dependency. It accepts
`(batch, length)` or `(batch, channels, length)` inputs and produces `(batch,
num_classes)` logits; the head is independent of `input_length` thanks to
adaptive average pooling.

Scope: general waveform classification only — no secret-key material, no
key-recovery targets, and no third-party attack-tool integration. No accuracy,
training, or attack-success claims are made. Unit tests cover shape handling,
residual connectivity, gradient flow, serialization round-trips, and bounded
configuration/input validation on CPU (`tests/test_resnet1d.py`). Known
BatchNorm constraint: in training mode with a single-sample batch, inputs whose
stem+stages collapse to one temporal position (with an explicitly selected 3-stage
configuration at `input_length = 32`) raise PyTorch's standard "more than
1 value per channel" error; evaluation mode handles all supported lengths
(32-4096). The default has **two** stages. See [API and limits](docs/resnet1d.md).

## 📊 Workstream Status Table

All 14 workstreams across Phase 1, Phase 2, and Phase 3 are completed and verified:

| # | Workstream | Status | Details |
|---|---|---|---|
| **WS-0** | Infrastructure & Kueue K8s | `DONE` | Multi-stage Dockerfile, pyproject.toml, Kueue k8s queues |
| **WS-G** | Constant-Time Matrix | `DONE` | KyberSlash / Clangover compiler matrix ({gcc, clang} x {-O0..-Os}) |
| **WS-F** | CycloneDX 1.6 CBOM | `DONE` | 8 PQC algorithms inventoried, NIST SP 800-208 policy evaluation |
| **WS-A** | Security Estimation | `DONE` | ML-KEM-768 verified at 192 bits (literature ±2 bit tolerance) |
| **WS-D** | Quantum Cost Calculation | `DONE` | AQRE (4,215 logical qubits) vs Qualtran comparison |
| **WS-E** | PQC Service Migration | `DONE` | Clean cryptographic migration abstraction |
| **WS-C** | Side-Channel Analyzer | `DONE` | Guessing Entropy compatible 1st and 2nd order leakage separation |
| **WS-B** | LWE Toy Distinguisher | `DONE` | Threshold analysis and secret recovery |
| **WS-EXP.1** | Deep Learning Training | `DONE` | PyTorch CNN/MLP training, saved checkpoints and JSON metrics |
| **WS-EXP.2** | Live FastAPI Web Service | `DONE` | Real-time REST endpoints and dashboard on `0.0.0.0:8090` |
| **WS-EXP.3** | E2E Tests & Documentation | `DONE` | 46/46 unit & integration tests passing |
| **WS-ADV.1** | CPA vs DL Attack Lab | `DONE` | Pearson CPA engine & 1st-order Boolean masking benchmark |
| **WS-ADV.2** | KyberSlash TVLA Suite | `DONE` | CVE-2024-37880 idiv vs Montgomery ASM & Welch t-test simulation |
| **WS-ADV.3** | Compliance Exporter | `DONE` | NIST SP 800-208 and CNSA 2.0 audit matrix & Markdown exporter |

---

## 🛠️ Quickstart Guide

### 1. Run Complete Unit & Integration Test Suite (55 Tests)
```bash
PYTHONPATH=src python3 -m unittest discover tests/ -v
```

### 2. Run CPA vs Deep Learning Benchmark
```bash
curl -X POST http://localhost:8090/api/v1/model/cpa-benchmark \
     -H "Content-Type: application/json" \
     -d '{"num_traces": 100, "masked": true}'
```

### 3. Inspect Constant-Time & KyberSlash Disassembly
```bash
curl http://localhost:8090/api/v1/constant-time/analysis
```

### 4. Export NIST & CNSA Compliance Report
```bash
curl http://localhost:8090/api/v1/report/export
```

### 5. Launch the Live Web Service
```bash
PYTHONPATH=src python3 -m uvicorn pqc_bench.api.main:app --host 0.0.0.0 --port 8090
```
Open [http://localhost:8090](http://localhost:8090) or [http://claw.lan:8090](http://claw.lan:8090) in your browser.

---

## WS-P5.3: Local ELF instruction review

A bounded, read-only ELF32/ELF64 x86 instruction reviewer is available as
`python3 -m pqc_bench.constant_time.binary_auditor PATH --project-root ROOT`
(use `PYTHONPATH=src` from a checkout). It uses pyelftools and Capstone; input
files are never executed. Integer division instructions are review findings,
**not leakage evidence**, and zero findings do **not** certify constant-time code.

See [scope, JSON/exit semantics, limits and tests](docs/binary_timing_review.md).
For current workstream and validation status, use [PROJECT_STATE.md](PROJECT_STATE.md).
Historical test counts above are not the current suite total.

## WS-P5.4: Bounded telemetry review notifications

The optional `alerts` policy on `/ws/traces` adds a `telemetry_alert` JSON result
inside each frame. Example request (sent over the existing WebSocket):

```json
{"trace_type":"playback","n_chunks":2,"alerts":{"visual_score_threshold":0.8,"cooldown_seconds":60.0}}
```

No alert field is added by default. Threshold exceedance means **review only**,
not leakage, exploitation, or a constant-time violation. The historical
`leakage_score` field is evaluated as a synthetic `visual_score`, not a statistical
leakage test. Alerts do not consume P5.3 static findings. P5.2 modeled cycles are
not converted to real latency.

Cooldown history is connection-local, survives pause with the same policy, and
resets when the policy changes or a new connection opens. It is not a durable,
distributed rate limiter. WebSocket clients cannot configure webhook URLs.
For project-owned local scalar measurements, use `TelemetrySample` and
`AlertEngine` directly; network sending is disabled unless an operator explicitly
supplies a transport. See [schema, transport limits and tests](docs/telemetry_alerts.md).

## WS-P6.2: Generic synthetic waveform Transformer

`WaveformTransformer1D` adds bounded patchwise multi-head self-attention with
ResNet-compatible input shapes, boolean sample padding masks, masked pooling,
and a probability helper. It uses PyTorch's existing attention implementation.
This isolated model is for general synthetic waveform classes only: no secret
labels, key recovery, imported hardware traces, or attack/service integration.
CPU unit tests check shapes, masks, gradients and serialization; no accuracy,
phase-shift robustness, training benchmark or GPU performance is claimed.
See [API, mask semantics and bounds](docs/waveform_transformer.md).

## 📜 License
Apache-2.0 License. Maintained autonomously by Ruhi (OpenClaw) and Antigravity.
