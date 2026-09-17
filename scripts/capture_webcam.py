from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.disposal.impact import get_environmental_impact, load_environmental_impacts
from ecoscan.errors import build_error_payload, format_console_error, format_error_payload_for_console
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.visual_report import save_pipeline_artifacts
from ecoscan.utils.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture one webcam frame and run EcoScan detection.")
    parser.add_argument("--camera-index", type=int, default=0)
    parser.add_argument("--capture-dir", type=Path, default=PROJECT_ROOT / "reports" / "camera_detection" / "captures")
    parser.add_argument("--report-dir", type=Path, default=PROJECT_ROOT / "reports" / "camera_detection")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--filter", default="auto")
    parser.add_argument("--segmentation", default="auto")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        import cv2  # type: ignore
    except ImportError:
        print(
            format_error_payload_for_console(
                build_error_payload(
                    code="CAM-005",
                    title="OpenCV ausente",
                    message="A captura direta por webcam precisa da biblioteca opencv-python.",
                    action="Instale opencv-python ou use a câmera do navegador pela interface Streamlit.",
                    category="camera",
                )
            )
        )
        return 1

    capture = cv2.VideoCapture(args.camera_index)
    if not capture.isOpened():
        print(
            format_error_payload_for_console(
                build_error_payload(
                    code="CAM-006",
                    title="Webcam indisponível",
                    message=f"A câmera de índice {args.camera_index} não foi encontrada ou está sem permissão.",
                    action="Confira a permissão da câmera, feche aplicativos que possam estar usando a webcam ou teste outro índice.",
                    category="camera",
                )
            )
        )
        return 1

    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        print(
            format_error_payload_for_console(
                build_error_payload(
                    code="CAM-007",
                    title="Captura falhou",
                    message="A webcam abriu, mas não retornou um frame válido.",
                    action="Tente novamente com boa iluminação ou reinicie a câmera.",
                    category="camera",
                )
            )
        )
        return 1

    try:
        args.capture_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = args.capture_dir / f"webcam_{timestamp}.jpg"
        cv2.imwrite(str(output_path), frame)
        print(f"Frame capturado: {output_path}")

        config = load_config()
        configure_logging(config.directories["logs"], include_stream=False)
        report_dir = args.report_dir / timestamp
        result = analyze_waste_image(
            output_path,
            config,
            options=ProcessingPipelineOptions(
                filter_name=args.filter,
                segmentation_name=args.segmentation,
            ),
            model_path=args.model,
        )
        save_pipeline_artifacts(result.pipeline, report_dir)
        print("Detecção concluída.")
        print(f"Modelo: {result.model_type}")
        print(f"Classe mais provável: {result.top_class}")
        print(f"Classe aceita: {result.predicted_class or '__uncertain__'}")
        if result.probability is not None:
            print(f"Probabilidade/score: {result.probability:.3f}")
        print(result.message)
        if result.guidance:
            print(f"Categoria ambiental: {result.guidance.environmental_category}")
            print(f"Orientação: {result.guidance.guidance}")
            impacts = load_environmental_impacts(config.project_root / "config" / "environmental_impacts.json")
            impact = get_environmental_impact(result.guidance.class_id, impacts)
            print(f"Risco do mau descarte: {impact.risk_label}")
            print(f"Impacto: {impact.bad_disposal_risks[0]}")
            print(f"Ação positiva: {impact.positive_action}")
        else:
            print("Sugestão: capturar novamente com resíduo centralizado e boa iluminação.")
        print(f"Evidências: {report_dir}")
    except Exception as exc:
        print(format_console_error(exc))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
