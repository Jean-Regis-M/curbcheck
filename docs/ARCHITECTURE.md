# Architecture (draft)

`mermaid
flowchart LR
  A[Photo] --> B[Image encoder, CPU, pretrained]
  B --> C[Item classifier head]
  C --> D[Calibration + abstention]
  D --> E[Rules lookup by city]
  E --> F[accept / reject / not sure + cited rule]
`
- Backend: Python, FastAPI. Frontend: static web page served by the backend.
- Model: small pretrained image encoder with a trained head, exported to ONNX for CPU inference (dev machine has no discrete GPU).
- Abstention: temperature scaling plus a confidence threshold chosen on a validation set.
- Rules: JSON per city, every row with source URL and retrieval date.
- Evaluation: train on one dataset, test on another; report false-accept rate vs coverage with confidence intervals and a material-only baseline.
