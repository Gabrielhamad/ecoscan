"""Export the trusted experimental CLIP probe for CPU-only inference."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from ecoscan.classification.contrastive import ContrastiveProbeClassifier
from ecoscan.config import load_config


class Encoder(torch.nn.Module):
    def __init__(self, model):
        super().__init__()
        self.visual = model.visual

    def forward(self, image):
        features = self.visual(image)
        return features / features.norm(dim=-1, keepdim=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output")
    torch.set_num_threads(2)
    classifier = ContrastiveProbeClassifier.load(args.candidate, load_config(), args.cache)
    args.output.mkdir(parents=True)
    original = args.output / "encoder_float.onnx"
    compact = args.output / "encoder_int8.onnx"
    torch.onnx.export(Encoder(classifier.encoder.model).eval(), torch.zeros(1, 3, 224, 224),
                      str(original), input_names=["image"], output_names=["features"],
                      opset_version=17, dynamo=False)
    quantize_dynamic(str(original), str(compact), weight_type=QuantType.QInt8,
                     per_channel=True, op_types_to_quantize=["MatMul", "Gemm"])
    head = classifier.payload["head"]
    scaler = head.named_steps["standardscaler"]
    linear = head.named_steps["logisticregression"]
    arrays = args.output / "head.npz"
    np.savez_compressed(arrays, mean=scaler.mean_, scale=scaler.scale_,
                        coef=linear.coef_, intercept=linear.intercept_,
                        prototypes=classifier.encoder.prototypes.detach().cpu().numpy(),
                        logit_scale=classifier.encoder.model.logit_scale.detach().exp().cpu().numpy())
    metadata = {"format": "clip-probe-int8-v1", "experimental": True,
        "classes": classifier.payload["classes"], "head_classes": list(linear.classes_),
        "threshold": classifier.payload["threshold"], "prior_weight": classifier.payload["prior_weight"],
        "processing": classifier.payload["processing"],
        "encoder_sha256": hashlib.sha256(compact.read_bytes()).hexdigest(),
        "head_sha256": hashlib.sha256(arrays.read_bytes()).hexdigest(),
        "source_sha256": hashlib.sha256((args.candidate / "contrastive_probe.joblib").read_bytes()).hexdigest()}
    (args.output / "semantic.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"encoder_bytes": compact.stat().st_size, "head_bytes": arrays.stat().st_size}))


if __name__ == "__main__":
    main()
