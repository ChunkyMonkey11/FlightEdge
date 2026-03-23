# FlightEdge

FlightEdge is an edge-ML sandbox for telemetry anomaly detection workflows.

The repository currently focuses on model experimentation, inference benchmarking, and dashboard work.

---

# Project Structure

```text
flightedge/
│
├── README.md
├── requirements.txt
│
├── model/
│   ├── train.py
│   ├── infer.py
│   ├── export_onnx.py
│   ├── quantize.py
│   └── artifacts/
│
├── benchmarks/
│   ├── benchmark_fp32.py
│   ├── benchmark_quantized.py
│   └── results/
│
├── dashboard/
│   ├── app.py
│   └── components/
│
├── data/
│   ├── synthetic_runs/
│   └── telemetry_schema.json
│
└── docs/
    ├── architecture.md
    ├── telemetry_schema.md
    ├── roadmap.md
    └── plans/
```
