# Release de reconhecimento semantic-v1

CLIP ViT-B/32 QuickGELU visual encoder (OpenAI weights), exported to ONNX FP16.
Source: https://github.com/openai/CLIP. Upstream MIT license included.
The supervised head was fitted on the reviewed public-image reference. Private
contribution photos and user regression photos were not fitted into this head.

The three encoder parts reconstruct `encoder.onnx` locally. SHA-256 checks
cover each part, the assembled encoder and `head.npz`. The assembled file is
not versioned. Inference requires ONNX Runtime, not PyTorch or OpenCLIP.

This is assisted recognition, not a globally approved automatic release.
All hypotheses require material confirmation. Do not use this release to
validate disposal, award mission points or claim certified material identity.
Class names are materials, not localized object detections. See
`docs/modelo_reconhecimento.md` for data and evaluation limitations.

FP16 evaluation on the same historical 145 feature rows: 101 first-choice matches,
47 correct out of 51 accepted at the model threshold; 94 rejected. All three
known user cases have the correct top material; two exceed the threshold.
The application intentionally treats even those two as unconfirmed hypotheses.

The reviewed-learning seed contains 397 training examples and a 145-example
validation set. Candidate heads must improve the fixed gate without reducing
per-class recall before remote publication. See `docs/modelo_reconhecimento.md`.

Reproduce the exact bundled evidence with `python scripts/evaluate_bundled_model.py`.
The original images and object/session groups are not bundled, so this is not an
independent test and cannot re-audit scene leakage.
