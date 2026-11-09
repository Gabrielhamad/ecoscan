"""Read-only adversarial probes of the frozen main; fixtures never measure field accuracy."""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import replace
from datetime import datetime
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import zipfile
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from PIL import Image

from ecoscan.app.pipeline import default_processing_options, run_processing_pipeline
from ecoscan.classification.prediction import ClassificationPrediction
from ecoscan.classification.runtime import ModelLoadError, load_recognition_model
from ecoscan.classification.semantic_onnx import file_digest
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract
from ecoscan.image_processing.image_io import load_rgb_image
from ecoscan.image_processing.validation import ImageValidationError
from ecoscan.segmentation.methods import SegmentationResult
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.contribution_store import SupabaseContributions
from ecoscan.services.delivery_pack import build_delivery_pack
from ecoscan.services.identity import resolve_identity
from ecoscan.services.processing_evidence import array_digest, processing_evidence_zip
from ecoscan.services.recognition_safety import build_recognition_safety_decision
from ecoscan.ui.common_views import _render_user_error

SOURCE_SHA = "89622ec714b815c216a9215ab9ba69999b39c6b8"


def _assert_source() -> None:
    run = subprocess.run(
        [
            "git",
            "diff",
            "--quiet",
            SOURCE_SHA,
            "--",
            "src/ecoscan",
            "config",
            "models/semantic-v1",
            "streamlit_app.py",
        ],
        cwd=ROOT,
    )
    if run.returncode:
        raise ValueError("Refuse to attribute changed application code to the frozen SHA")


def run_probes(output: Path, *, onnx: bool) -> dict:
    _assert_source()
    output.mkdir(parents=True, exist_ok=True)
    config = load_config()
    config = replace(config, model={**config.model, "remote_models_enabled": False})
    metadata_path = ROOT / "models/semantic-v1/semantic.json"
    metadata = json.loads(metadata_path.read_text())
    results = []

    def record(
        identifier: str, title: str, passed: bool | None, scope: str, **observations
    ) -> None:
        results.append(
            {
                "id": identifier,
                "title": title,
                "status": "BLOCKED" if passed is None else "PASS" if passed else "FAIL",
                "scope": scope,
                "observations": observations,
            }
        )

    # One artificial scene for contracts/operations; no material ground truth exists.
    y, x = np.indices((96, 128))
    rgb = np.stack((180 + x // 4, 180 + y // 3, 190 + x // 8), axis=-1).astype(np.uint8)
    rgb[20:80, 35:95] = (45, 105, 70)
    rgb[40:46, 60:66] = 240
    with tempfile.TemporaryDirectory(prefix="ecoscan-final-audit-") as temp:
        temporary = Path(temp)
        photo = temporary / "technical-fixture.png"
        Image.fromarray(rgb).save(photo)
        options = default_processing_options(config)
        baseline = run_processing_pipeline(photo, config, options)
        altered = run_processing_pipeline(
            photo,
            config,
            replace(
                options, filter_name="gaussian", filter_parameters={"kernel_size": 7, "sigma": 2.0}
            ),
        )
        changed = int(
            np.count_nonzero(
                np.any(baseline.recognition_image != altered.recognition_image, axis=2)
            )
        )
        equal_contract = (
            baseline.metadata["recognition_preparation"]["contract"]
            == altered.metadata["recognition_preparation"]["contract"]
        )
        record(
            "ADV-01",
            "Filtro didático não deve alterar o encoder oficial",
            changed == 0 and equal_contract,
            "synthetic_contract_probe",
            changed_encoder_pixels=changed,
            input_before=array_digest(baseline.recognition_image),
            input_after=array_digest(altered.recognition_image),
            default_contract_matches_model=baseline.metadata["recognition_preparation"]["contract"]
            == metadata["processing"],
            changed_contract_matches_model=altered.metadata["recognition_preparation"]["contract"]
            == metadata["processing"],
            accuracy_effect="not_measured",
        )

        control = run_processing_pipeline(
            photo, config, replace(options, segmentation_name="none", morphology_name="none")
        )
        for value in (0, 255):
            mask = np.full(rgb.shape[:2], value, dtype=np.uint8)
            segmentation = SegmentationResult(
                "otsu", mask, rgb.copy(), {}, float(value > 0), "technical stub", "fixture"
            )
            with patch("ecoscan.app.pipeline.segment_image", return_value=segmentation):
                probe = run_processing_pipeline(
                    photo,
                    config,
                    replace(options, segmentation_name="otsu", morphology_name="none"),
                )
            record(
                f"ADV-02-{value}",
                "Máscara degenerada permanece diagnóstica",
                np.array_equal(control.recognition_image, probe.recognition_image),
                "synthetic_mask_probe",
                mask_value=value,
                mask_applied_to_classifier=probe.metadata["recognition_preparation"][
                    "mask_applied"
                ],
            )

        for name, content in [("corrupt", b"not-an-image"), ("empty", b"")]:
            invalid = temporary / (name + ".png")
            invalid.write_bytes(content)
            rejected = False
            try:
                load_rgb_image(
                    invalid,
                    allowed_extensions=config.allowed_extensions,
                    min_size=config.min_image_size,
                )
            except ImageValidationError:
                rejected = True
            record(
                "ADV-03-" + name, "Arquivo inválido recusado", rejected, "technical_file_validation"
            )

        oriented = temporary / "orientation.png"
        exif = Image.Exif()
        exif[274] = 6
        Image.fromarray(rgb).save(oriented, exif=exif)
        loaded = load_rgb_image(
            oriented, allowed_extensions=config.allowed_extensions, min_size=config.min_image_size
        )
        record(
            "ADV-04",
            "EXIF aplicado antes do preparo RGB",
            np.array_equal(loaded.array, np.rot90(rgb, -1)),
            "technical_orientation_fixture",
            shape=list(loaded.array.shape),
            dtype=str(loaded.array.dtype),
        )

        for label in (*config.classes, "unknown"):
            probabilities = {class_id: 0.0 for class_id in (*config.classes, "unknown")}
            probabilities[label] = 0.99
            probabilities["unknown" if label != "unknown" else "metal"] = 0.01
            prediction = ClassificationPrediction(
                label,
                label if label != "unknown" else None,
                0.99,
                probabilities,
                label != "unknown",
                0.8,
            )
            bundle = SimpleNamespace(
                model_type="semantic_onnx_assisted",
                classifier=SimpleNamespace(
                    metadata={"processing": processing_contract(config)},
                    predict_image=lambda image, prediction=prediction: prediction,
                ),
            )
            result = analyze_waste_image(
                photo, config, model_path=metadata_path, model_bundle=bundle
            )
            decision = build_recognition_safety_decision(result)
            record(
                "ADV-05-" + label,
                "Score alto não autoriza mensagem categórica sem gate",
                not result.accepted
                and decision.status != "identified"
                and not decision.allow_disposal_guidance,
                "stub_policy_not_classifier_accuracy",
                class_id=label,
                decision=decision.status,
                accepted=result.accepted,
            )

        wrong_bundle = SimpleNamespace(
            model_type="semantic_onnx_assisted",
            classifier=SimpleNamespace(
                metadata={"processing": {"sha256": "technical-incompatible-contract"}},
                predict_image=lambda image: ClassificationPrediction(
                    "metal", "metal", 0.99, {"metal": 0.99}, True, 0.8
                ),
            ),
        )
        result = analyze_waste_image(
            photo, config, model_path=metadata_path, model_bundle=wrong_bundle
        )
        decision = build_recognition_safety_decision(result)
        record(
            "ADV-06",
            "Contrato incompatível não libera decisão",
            not result.processing_compatible and not result.accepted,
            "stub_contract_probe",
            decision=decision.status,
        )

        for label, value in [("dark", 0), ("empty_white", 255)]:
            frame = temporary / (label + ".png")
            Image.fromarray(np.full_like(rgb, value)).save(frame)
            probe = run_processing_pipeline(
                frame, config, replace(options, segmentation_name="none")
            )
            status = probe.capture_quality.status
            record(
                "ADV-07-" + label,
                "Captura uniforme pede nova foto",
                status == "retake",
                "uniform_technical_frame_not_a_field_photo",
                capture_status=status,
                score=probe.capture_quality.score,
            )

        isolated = temporary / "models/semantic-v1"
        isolated.mkdir(parents=True)
        for name in ("semantic.json", "head.npz"):
            shutil.copyfile(ROOT / "models/semantic-v1" / name, isolated / name)
        isolated_config = replace(
            config, directories={**config.directories, "models": isolated.parent}
        )
        refused = False
        try:
            load_recognition_model(isolated_config, isolated / "semantic.json")
        except ModelLoadError:
            refused = True
        record(
            "ADV-08",
            "Falta de encoder falha de modo controlado",
            refused,
            "isolated_real_model_loader",
        )

        # Exercise the real Streamlit controller, actual pipeline and real loader with no parts.
        from streamlit.testing.v1 import AppTest

        app = AppTest.from_string(
            """
import io
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import streamlit as st
from ecoscan.config import load_config
from ecoscan.app.pipeline import default_processing_options
from ecoscan.services.accounts import UserProfile
from ecoscan.ui.app_resources import load_app_resources
from ecoscan.ui.analysis_controller import render_analysis_page
from ecoscan.ui.session_state import AnalysisSession
config=load_config()
resources=load_app_resources(config)
folder=Path(st.session_state.folder)
config=replace(config, directories={**config.directories, 'models':folder.parent}, model={**config.model,'remote_models_enabled':False})
upload=io.BytesIO(st.session_state.fixture)
upload.name='technical.png'
with patch('streamlit.file_uploader',return_value=upload), patch('ecoscan.services.analysis_service._model_path',return_value=folder/'semantic.json'):
 render_analysis_page(st,nullcontext(),config,UserProfile('visitor_audit','Visitante','user'),resources.guidance_by_class,resources.targets_by_class,resources.impacts_by_class,resources.collection_points,default_processing_options(config),False,AnalysisSession(st.session_state))
""",
            default_timeout=30,
        )
        app.session_state["folder"] = str(isolated)
        app.session_state["fixture"] = photo.read_bytes()
        # The deliberately unsafe main handler must not send even synthetic raw detail to terminal logs.
        with patch("ecoscan.ui.common_views.LOGGER"):
            app.run()
        selectors = [item.label for item in app.selectbox]
        record(
            "ADV-09",
            "Modelo ausente preserva correção manual na página",
            any("material" in label.casefold() for label in selectors),
            "real_controller_and_missing_encoder_apptest",
            visible_errors=len(app.error),
            uncaught_exceptions=len(app.exception),
            material_selector_available=bool(selectors),
        )

        marker = "AUDIT_SYNTHETIC_DETAIL"
        ui = []
        fake_st = SimpleNamespace(
            error=ui.append, info=ui.append, code=ui.append, expander=lambda *a, **k: nullcontext()
        )
        logger = logging.getLogger("ecoscan.ui.common_views")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        old_level, old_propagate = logger.level, logger.propagate
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        try:
            _render_user_error(fake_st, RuntimeError(marker), context="audit_fixture")
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
            logger.propagate = old_propagate
        ui_leak, log_leak = any(marker in str(item) for item in ui), marker in stream.getvalue()
        record(
            "ADV-10",
            "Boundary público não deve expor exceção bruta",
            not ui_leak and not log_leak,
            "synthetic_marker_no_personal_data",
            raw_detail_reached_ui=ui_leak,
            raw_detail_reached_log=log_leak,
        )

        visitor = resolve_identity(
            {}, {"admin_emails": ["audit@example.invalid"]}, "technical-session"
        )
        forged = resolve_identity(
            {"is_logged_in": True, "email": "audit@example.invalid"},
            {"admin_emails": ["audit@example.invalid"]},
            "technical-session",
        )
        record(
            "ADV-11",
            "Visitante/claims incompletos não elevam privilégio",
            not visitor.is_admin and not forged.is_admin,
            "identity_stubs_no_real_accounts",
        )

        client = MagicMock()
        client.table.side_effect = OSError(marker)
        sanitized = False
        try:
            SupabaseContributions(client).list()
        except OSError as exc:
            sanitized = marker not in str(exc)
        record(
            "ADV-12",
            "Indisponibilidade de banco sanitizada no serviço",
            sanitized,
            "database_stub_no_network_or_production",
        )

        from ecoscan.services.published_model import _CACHE, published_model

        cache_store = MagicMock()
        cache_store.list.return_value = []
        cache_store.client.storage.from_.return_value.download.return_value = (
            b'{"id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","reviews":{}}'
        )
        _CACHE.clear()
        with (
            patch.dict("os.environ", {"ECOSCAN_REMOTE_MODELS": "true"}),
            patch("ecoscan.services.published_model.remote_store", return_value=cache_store),
            patch(
                "ecoscan.services.semantic_release.materialize",
                return_value=Path("technical-remote/semantic.json"),
            ),
            patch("ecoscan.services.published_model.time.monotonic", return_value=5),
        ):
            cache_result = published_model(config)
        record(
            "ADV-16",
            "Cache frio deve consultar release antes do TTL",
            cache_result is not None,
            "stub_clock_no_remote_access",
            monotonic_seconds=5,
            source_store_consulted=cache_store.list.called,
        )
        _CACHE.clear()

        inventory = build_delivery_pack(config)
        ac10 = next(item for item in inventory.acceptance if item.code == "AC-10")
        record(
            "ADV-17",
            "Inventário não deve aprovar gate independente pela presença do artefato",
            ac10.status != "ok",
            "legacy_inventory_with_no_field_evidence_not_release",
            legacy_ac10_status=ac10.status,
            independent_test=False,
            raw_images=inventory.raw_total,
            curated_images=inventory.curated_total,
            limitation="Existência local do modelo não comprova validação independente",
        )

        evidence_bytes = processing_evidence_zip(baseline)
        (output / "technical_processing.zip").write_bytes(evidence_bytes)
        with zipfile.ZipFile(io.BytesIO(evidence_bytes)) as archive:
            evidence = json.loads(archive.read("manifest.json"))
            expected = array_digest(baseline.recognition_image)
            same = evidence["classifier_input_sha256"] == expected
            no_path = str(photo) not in json.dumps(evidence)
        record(
            "ADV-13",
            "ZIP representa a execução e não inclui caminho privado no manifesto",
            same and no_path,
            "synthetic_lossless_evidence",
            stages=len(evidence["stages"]),
            input_sha256=expected,
            artifact_sha256=hashlib.sha256(evidence_bytes).hexdigest(),
        )

        joined = hashlib.sha256()
        parts_valid = True
        for part in metadata["parts"]:
            file = ROOT / "models/semantic-v1" / part["name"]
            parts_valid &= file_digest(file) == part["sha256"]
            with file.open("rb") as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    joined.update(block)
        record(
            "ADV-14",
            "Integridade cabeça/shards/encoder/contrato",
            parts_valid
            and joined.hexdigest() == metadata["encoder_sha256"]
            and file_digest(ROOT / "models/semantic-v1/head.npz") == metadata["head_sha256"]
            and metadata["processing"] == processing_contract(config),
            "real_bundled_artifact_hashes",
            metadata_sha256=file_digest(metadata_path),
            head_sha256=metadata["head_sha256"],
            encoder_sha256=joined.hexdigest(),
            processing_sha256=metadata["processing"]["sha256"],
        )
        if onnx:
            import socket

            def blocked(*args, **kwargs):
                raise OSError("Technical probe disables outgoing connections")

            encoder_already_assembled = (metadata_path.parent / "encoder.onnx").is_file()
            started = time.perf_counter()
            with patch.object(socket.socket, "connect", blocked):
                result = analyze_waste_image(photo, config, model_path=metadata_path)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            decision = build_recognition_safety_decision(result)
            record(
                "ADV-15",
                "ONNX CPU local com conexões Python bloqueadas",
                result.model_type == "semantic_onnx_assisted"
                and result.processing_compatible
                and not result.accepted,
                "real_local_onnx_synthetic_image_no_accuracy",
                decision=decision.status,
                processing_compatible=result.processing_compatible,
                automatic_accepted=result.accepted,
                python_socket_connect_blocked=True,
                native_library_network="not_monitored",
                analysis_wall_ms=elapsed_ms,
                latency_samples=1,
                assembled_encoder_present_before_call=encoder_already_assembled,
            )
        else:
            record("ADV-15", "Inferência ONNX CPU real", None, "not_executed_add_onnx_flag")

    for identifier, title in [
        ("FIELD-01", "Plástico versus vidro transparente"),
        ("FIELD-02", "Metal refletivo"),
        ("FIELD-03", "Fundo confuso/sem objeto real"),
        ("FIELD-04", "CLI em conjunto real novo"),
        ("DEVICE-01", "PC/Android/iPhone reais"),
        ("APS-REHEARSAL", "Três ensaios de apresentação"),
    ]:
        record(identifier, title, None, "manual_pending_no_authorized_data_or_device")
    verdict = "GO" if all(row["status"] == "PASS" for row in results) else "NO-GO"
    report = {
        "schema_version": 1,
        "source_sha": SOURCE_SHA,
        "verdict": verdict,
        "generated_at_local": datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat(
            timespec="seconds"
        ),
        "technical_fixtures_only": True,
        "independent_test": False,
        "production_or_real_accounts_accessed": False,
        "results": results,
    }
    (output / "probes.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--onnx", action="store_true")
    args = parser.parse_args()
    # Read no ambient application secrets and disable optional shared stores.
    # Mocks below are the only remote-store clients used by these probes.
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("ECOSCAN_")
    }
    environment.update(
        ECOSCAN_REMOTE_MODELS="false",
        ECOSCAN_COMMUNITY_ENABLED="false",
        ECOSCAN_OPERATIONS_ENABLED="false",
    )
    with patch.dict(os.environ, environment, clear=True), patch("streamlit.secrets", {}):
        report = run_probes(args.output, onnx=args.onnx)
    print(
        json.dumps(
            {
                "source_sha": SOURCE_SHA,
                "verdict": report["verdict"],
                "counts": {
                    state: sum(row["status"] == state for row in report["results"])
                    for state in ("PASS", "FAIL", "BLOCKED")
                },
            }
        )
    )
    return 0 if report["verdict"] == "GO" else 2


if __name__ == "__main__":
    raise SystemExit(main())
