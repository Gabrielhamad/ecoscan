from __future__ import annotations

from collections import Counter
import csv
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def confusion_matrix(labels: list[str], predictions: list[str | None], classes: list[str]) -> list[list[int]]:
    index = {class_id: position for position, class_id in enumerate(classes)}
    matrix = [[0 for _ in classes] for _ in classes]
    for label, prediction in zip(labels, predictions, strict=True):
        if label not in index or prediction not in index:
            continue
        matrix[index[label]][index[prediction]] += 1
    return matrix


def classification_report(labels: list[str], predictions: list[str | None], classes: list[str]) -> dict:
    accepted_predictions = [prediction if prediction is not None else "__uncertain__" for prediction in predictions]
    total = len(labels)
    correct = sum(label == prediction for label, prediction in zip(labels, accepted_predictions, strict=True))

    by_class: dict[str, dict[str, float | int]] = {}
    label_counts = Counter(labels)
    prediction_counts = Counter(accepted_predictions)
    for class_id in classes:
        true_positive = sum(
            label == class_id and prediction == class_id
            for label, prediction in zip(labels, accepted_predictions, strict=True)
        )
        precision = true_positive / prediction_counts[class_id] if prediction_counts[class_id] else 0.0
        recall = true_positive / label_counts[class_id] if label_counts[class_id] else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        by_class[class_id] = {
            "support": label_counts[class_id],
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    macro_precision = sum(float(item["precision"]) for item in by_class.values()) / max(1, len(classes))
    macro_recall = sum(float(item["recall"]) for item in by_class.values()) / max(1, len(classes))
    macro_f1 = sum(float(item["f1"]) for item in by_class.values()) / max(1, len(classes))
    uncertain_count = accepted_predictions.count("__uncertain__")

    return {
        "accuracy": correct / total if total else 0.0,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "uncertain_count": uncertain_count,
        "total": total,
        "by_class": by_class,
        "confusion_matrix": confusion_matrix(labels, predictions, classes),
        "classes": classes,
    }


def write_confusion_matrix_csv(matrix: list[list[int]], classes: list[str], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["true\\predicted", *classes])
        for class_id, row in zip(classes, matrix, strict=True):
            writer.writerow([class_id, *row])
    return output_path


def _load_font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def write_confusion_matrix_image(matrix: list[list[int]], classes: list[str], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cell = 74
    label_w = 160
    top_h = 120
    width = label_w + len(classes) * cell + 24
    height = top_h + len(classes) * cell + 24
    max_value = max((value for row in matrix for value in row), default=1) or 1

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = _load_font(12)
    title_font = _load_font(16)
    draw.text((16, 16), "Matriz de confusao", fill="black", font=title_font)
    draw.text((label_w, 52), "Predito", fill="black", font=font)
    draw.text((16, top_h), "Real", fill="black", font=font)

    for col, class_id in enumerate(classes):
        x = label_w + col * cell
        draw.text((x + 4, 78), class_id[:10], fill="black", font=font)

    for row_index, class_id in enumerate(classes):
        y = top_h + row_index * cell
        draw.text((16, y + 26), class_id[:18], fill="black", font=font)
        for col_index, value in enumerate(matrix[row_index]):
            x = label_w + col_index * cell
            intensity = int(255 - (value / max_value) * 180)
            fill = (intensity, intensity + 20 if intensity < 235 else 255, 255)
            draw.rectangle((x, y, x + cell - 4, y + cell - 4), fill=fill, outline=(210, 210, 210))
            draw.text((x + 26, y + 26), str(value), fill="black", font=font)

    image.save(output_path)
    return output_path

