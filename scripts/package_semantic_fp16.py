"""Convert the already exported float encoder and package bounded Git files."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import onnx
from onnxconverter_common import float16


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Use a new output")
    args.output.mkdir(parents=True)
    model = onnx.load(str(args.source / "encoder_float.onnx"))
    converted = float16.convert_float_to_float16(model, keep_io_types=True)
    # Preserve dtype consistency for explicit casts already present in CLIP's graph.
    tensor_types = {value.name: value.type.tensor_type.elem_type
                    for value in list(converted.graph.value_info) + list(converted.graph.output)}
    for node in converted.graph.node:
        if node.op_type == "Cast" and tensor_types.get(node.output[0]) == onnx.TensorProto.FLOAT16:
            for attribute in node.attribute:
                if attribute.name == "to" and attribute.i == onnx.TensorProto.FLOAT:
                    attribute.i = onnx.TensorProto.FLOAT16
    encoder = args.output / "encoder.onnx"
    onnx.save(converted, str(encoder))
    metadata = json.loads((args.source / "semantic.json").read_text())
    metadata["format"] = "clip-probe-fp16-v1"
    metadata["encoder_file"] = "encoder.onnx"
    metadata["encoder_sha256"] = hashlib.sha256(encoder.read_bytes()).hexdigest()
    parts = []
    with encoder.open("rb") as file:
        index = 0
        while data := file.read(80 * 1024 * 1024):
            name = f"encoder_{index:02d}.part"
            (args.output / name).write_bytes(data)
            parts.append({"name": name, "sha256": hashlib.sha256(data).hexdigest()})
            index += 1
    metadata["parts"] = parts
    shutil.copy2(args.source / "head.npz", args.output / "head.npz")
    (args.output / "semantic.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps({"bytes": encoder.stat().st_size, "parts": len(parts)}))


if __name__ == "__main__":
    main()
