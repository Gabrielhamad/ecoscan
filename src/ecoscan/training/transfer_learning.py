from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecoscan.config import AppConfig


SUPPORTED_ARCHITECTURES = {
    "MobileNetV2",
    "EfficientNetB0",
    "ResNet50",
}


class TrainingEnvironmentError(RuntimeError):
    """Raised when the training environment is not ready for the final model."""


@dataclass(frozen=True)
class TrainingPlan:
    framework: str
    architecture: str
    weights: str | None
    image_size: tuple[int, int]
    classes: tuple[str, ...]
    train_dir: str
    validation_dir: str
    output_path: str
    batch_size: int
    epochs: int
    fine_tune: bool
    fine_tune_epochs: int
    learning_rate: float
    early_stopping_patience: int
    notes: list[str]


def build_training_plan(config: AppConfig) -> TrainingPlan:
    model_config = config.model
    architecture = str(model_config.get("architecture", "MobileNetV2"))
    if architecture not in SUPPORTED_ARCHITECTURES:
        raise ValueError(f"Unsupported architecture: {architecture}")

    output_path = config.project_root / str(model_config.get("output_path", "models/ecoscan_transfer.keras"))
    return TrainingPlan(
        framework=str(model_config.get("framework", "tensorflow")),
        architecture=architecture,
        weights=model_config.get("weights", "imagenet"),
        image_size=config.image_size,
        classes=config.classes,
        train_dir=str(config.directories["train_data"]),
        validation_dir=str(config.directories["validation_data"]),
        output_path=str(output_path),
        batch_size=int(model_config.get("batch_size", 16)),
        epochs=int(model_config.get("epochs", 12)),
        fine_tune=bool(model_config.get("fine_tune", False)),
        fine_tune_epochs=int(model_config.get("fine_tune_epochs", 8)),
        learning_rate=float(model_config.get("learning_rate", 0.0001)),
        early_stopping_patience=int(model_config.get("early_stopping_patience", 4)),
        notes=[
            "Use Python 3.12 para maior compatibilidade com TensorFlow.",
            "Revise e limpe o dataset antes de usar este treinamento como resultado final.",
            "Pesos ImageNet podem exigir download na primeira execução.",
        ],
    )


def save_training_plan(plan: TrainingPlan, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.__dict__, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _tensorflow_applications(tf: Any, architecture: str) -> tuple[Any, Any]:
    if architecture == "MobileNetV2":
        return tf.keras.applications.MobileNetV2, tf.keras.applications.mobilenet_v2.preprocess_input
    if architecture == "EfficientNetB0":
        return tf.keras.applications.EfficientNetB0, tf.keras.applications.efficientnet.preprocess_input
    if architecture == "ResNet50":
        return tf.keras.applications.ResNet50, tf.keras.applications.resnet50.preprocess_input
    raise ValueError(f"Unsupported architecture: {architecture}")


def train_tensorflow_model(config: AppConfig, *, plan: TrainingPlan | None = None) -> dict[str, Any]:
    try:
        import tensorflow as tf  # type: ignore
    except ImportError as exc:
        raise TrainingEnvironmentError("TensorFlow não está instalado neste ambiente.") from exc

    selected_plan = plan or build_training_plan(config)
    if selected_plan.framework != "tensorflow":
        raise ValueError("Only TensorFlow training is implemented in this script.")

    train_ds = tf.keras.utils.image_dataset_from_directory(
        selected_plan.train_dir,
        labels="inferred",
        label_mode="categorical",
        class_names=list(selected_plan.classes),
        image_size=selected_plan.image_size,
        batch_size=selected_plan.batch_size,
        shuffle=True,
        seed=config.random_seed,
    )
    validation_ds = tf.keras.utils.image_dataset_from_directory(
        selected_plan.validation_dir,
        labels="inferred",
        label_mode="categorical",
        class_names=list(selected_plan.classes),
        image_size=selected_plan.image_size,
        batch_size=selected_plan.batch_size,
        shuffle=False,
    )

    application, preprocess_input = _tensorflow_applications(tf, selected_plan.architecture)
    data_augmentation = tf.keras.Sequential(
        [
            tf.keras.layers.RandomFlip("horizontal"),
            tf.keras.layers.RandomRotation(0.06),
            tf.keras.layers.RandomZoom(0.08),
            tf.keras.layers.RandomContrast(0.08),
        ],
        name="moderate_data_augmentation",
    )

    inputs = tf.keras.Input(shape=(*selected_plan.image_size, 3))
    x = data_augmentation(inputs)
    x = tf.keras.layers.Lambda(preprocess_input, name="model_preprocess")(x)
    base_model = application(
        include_top=False,
        weights=selected_plan.weights,
        input_tensor=x,
        pooling="avg",
    )
    base_model.trainable = False
    x = tf.keras.layers.Dropout(float(config.model.get("dropout", 0.2)))(base_model.output)
    outputs = tf.keras.layers.Dense(len(selected_plan.classes), activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs, name=f"ecoscan_{selected_plan.architecture.lower()}")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=selected_plan.learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )

    output_path = Path(selected_plan.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor="val_loss",
            patience=selected_plan.early_stopping_patience,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(output_path),
            monitor="val_loss",
            save_best_only=True,
        ),
    ]

    history = model.fit(
        train_ds,
        validation_data=validation_ds,
        epochs=selected_plan.epochs,
        callbacks=callbacks,
    )

    class_names_path = config.project_root / str(config.model.get("class_names_path", "models/class_names.json"))
    class_names_path.parent.mkdir(parents=True, exist_ok=True)
    class_names_path.write_text(json.dumps(list(selected_plan.classes), indent=2, ensure_ascii=False), encoding="utf-8")

    history_data = {
        metric: [float(value) for value in values]
        for metric, values in history.history.items()
    }
    history_path = config.directories["reports"] / "training" / "history.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "model_path": str(output_path),
        "class_names_path": str(class_names_path),
        "history_path": str(history_path),
        "history": history_data,
    }
