# Project File Tree (Module 1)

```
smart-attendance/
│
├── .env.example                        # Environment config template
├── .gitignore                          # Git ignore rules
├── README.md                           # Project overview
├── QUICKSTART.md                       # Quick start guide
├── VALIDATION_CHECKLIST.md             # Testing checklist
├── MODULE_1_SUMMARY.md                 # Implementation summary
├── setup.ps1                           # Windows setup script
├── pyproject.toml                      # Project metadata
├── requirements.txt                    # Python dependencies
├── pytest.ini                          # Pytest configuration
├── MLproject                           # MLflow project config
├── conda.yaml                          # Conda environment
│
├── .github/
│   └── workflows/
│       └── ci.yml                      # CI/CD pipeline
│
├── docker/
│   ├── Dockerfile.edge                 # Edge device container
│   └── Dockerfile.server               # Server container
│
├── infra/
│   ├── k8s_deploy.yaml                 # Kubernetes deployment
│   └── canary_rollout.yaml             # Canary rollout config
│
├── scripts/
│   ├── export_onnx.sh                  # ONNX export (stub)
│   ├── quantize_onnx.sh                # ONNX quantization (stub)
│   ├── sign_model.sh                   # Model signing (stub)
│   └── deploy_canary.sh                # Canary deployment (stub)
│
├── sample_data/
│   └── sample_frame.jpg                # Sample image (placeholder)
│
├── src/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                     # ✅ FastAPI app
│   │   ├── deps.py                     # ✅ Dependency injection
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── routes_health.py    # ✅ Health endpoint
│   │   │       ├── routes_device.py    # ✅ Device registration
│   │   │       ├── routes_models.py    # ✅ Model management
│   │   │       ├── routes_stream.py    # ✅ Stream management
│   │   │       └── routes_attendance.py # ✅ Attendance & enrollment
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── config.py               # ✅ Pydantic config
│   │   │   ├── stream_models.py        # ✅ Stream models
│   │   │   ├── detection_models.py     # ✅ Detection models
│   │   │   └── attendance_models.py    # ✅ Attendance models
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── stream_service.py       # ✅ Stream service (stub)
│   │       ├── detector_service.py     # 🔲 Detector (NotImplementedError)
│   │       ├── pose_service.py         # 🔲 Pose (NotImplementedError)
│   │       ├── embedding_service.py    # 🔲 Embedding (NotImplementedError)
│   │       ├── pafu_service.py         # 🔲 PAFU (NotImplementedError)
│   │       ├── tracker_service.py      # 🔲 Tracker (NotImplementedError)
│   │       ├── matcher_service.py      # 🔲 Matcher (NotImplementedError)
│   │       └── attendance_service.py   # ✅ Attendance service (stub)
│   │
│   ├── pipeline/                       # 🔲 All stubs (Module 2+)
│   │   ├── io/
│   │   │   ├── rtsp_reader.py          # TODO: Module 2
│   │   │   └── frame_queue.py          # TODO: Module 2
│   │   ├── bafs/
│   │   │   └── bafs_scheduler.py       # TODO: Module 2
│   │   ├── detection/
│   │   │   ├── yolov10_tiny.py         # TODO: Module 3
│   │   │   └── yolo_onnx_wrapper.py    # TODO: Module 3
│   │   ├── pose/
│   │   │   ├── movenet_thunder.py      # TODO: Module 4
│   │   │   └── pose_utils.py           # TODO: Module 4
│   │   ├── embeddings/
│   │   │   ├── lightcnn_backbone.py    # TODO: Module 5
│   │   │   ├── adaface_wrapper.py      # TODO: Module 7
│   │   │   ├── peri_tiny.py            # TODO: Module 8
│   │   │   └── embedding_utils.py      # TODO: Modules 5-8
│   │   ├── pafu/
│   │   │   ├── hybrid_pafu.py          # TODO: Module 6
│   │   │   └── pafu_utils.py           # TODO: Module 6
│   │   ├── reid/
│   │   │   └── osnet_x025.py           # TODO: Module 8
│   │   ├── fusion/
│   │   │   └── pamie.py                # TODO: Module 9
│   │   ├── tracking/
│   │   │   └── mr2_bytetrack.py        # TODO: Module 10
│   │   ├── matching/
│   │   │   └── lqfb.py                 # TODO: Module 11
│   │   └── persistence/
│   │       └── sqlite_store.py         # TODO: Module 12
│   │
│   ├── mlflow/                         # 🔲 All stubs (Module 14)
│   │   ├── train/
│   │   │   ├── pafu_finetune.py        # TODO: Module 14
│   │   │   └── train_utils.py          # TODO: Module 14
│   │   ├── ci/
│   │   │   └── mlflow_ci.sh            # TODO: Module 14
│   │   └── registry_utils.py           # TODO: Module 14
│   │
│   └── utils/
│       ├── __init__.py
│       ├── downloads.py                # ✅ Model downloader (stub)
│       ├── security.py                 # ✅ Security utils (stub)
│       ├── timers.py                   # ✅ Performance timing
│       └── logging.py                  # ✅ Structured logging
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_routes.py              # ✅ Complete route tests
│   │   ├── test_rtsp_reader.py         # TODO: Module 2
│   │   ├── test_bafs_scheduler.py      # TODO: Module 2
│   │   └── test_pafu_adapter.py        # TODO: Module 6
│   └── integration/
│       └── test_end2end_cpu_onnx.sh    # TODO: Module 15
│
└── notebooks/
    └── viz_finetune.ipynb              # TODO: Module 14

Legend:
✅ = Implemented and tested (Module 1)
🔲 = Stub/placeholder (future modules)
TODO = Not yet created (future modules)
```

## File Count Summary

### Module 1 (Implemented)
- **Application Code**: 25 files
- **Tests**: 2 files (+ framework)
- **Configuration**: 6 files
- **Documentation**: 5 files
- **Infrastructure**: 6 files (stubs)
- **Total Created**: ~50 files

### Future Modules (Placeholders)
- **Pipeline**: 0 files created (directories exist in structure only)
- **MLflow**: 0 files created
- **Integration Tests**: 0 files created

### Lines of Code (Module 1)
- **Application**: ~1,500 lines
- **Tests**: ~200 lines
- **Config**: ~300 lines
- **Docs**: ~1,000 lines
- **Total**: ~3,000 lines

## Directory Status

| Directory | Status | Module |
|-----------|--------|--------|
| `src/app/` | ✅ Complete | 1 |
| `src/utils/` | ✅ Stubs | 1 |
| `src/pipeline/` | 🔲 Empty | 2-12 |
| `src/mlflow/` | 🔲 Empty | 14 |
| `tests/unit/` | ✅ Partial | 1 |
| `tests/integration/` | 🔲 Empty | 15 |
| `docker/` | ✅ Stubs | 16 |
| `infra/` | ✅ Stubs | 16 |
| `scripts/` | ✅ Stubs | 14-16 |

## Next Module Additions

**Module 2** will add:
- `src/pipeline/io/rtsp_reader.py`
- `src/pipeline/io/frame_queue.py`
- `src/pipeline/bafs/bafs_scheduler.py`
- `tests/unit/test_rtsp_reader.py`
- `tests/unit/test_frame_queue.py`
- `tests/unit/test_bafs_scheduler.py`

Estimated: +6 files, ~800 lines of code
