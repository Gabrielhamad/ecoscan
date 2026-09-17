"""Supported objects for the pilot; material labels are not object detectors."""
from dataclasses import replace

from ecoscan.classification.baseline import BaselinePrediction


ITEMS = {
    "drink_can": ("Lata de bebida", "metal"),
    "food_can": ("Lata de conserva vazia", "metal"),
    "pet_bottle": ("Garrafa plástica PET", "plastic"),
    "plastic_container": ("Frasco ou pote plástico rígido vazio", "plastic"),
    "cardboard_box": ("Caixa de papelão", "paper_cardboard"),
    "paper_sheet": ("Folha de papel ou jornal", "paper_cardboard"),
    "glass_bottle": ("Garrafa de vidro", "glass"),
    "glass_jar": ("Pote de vidro", "glass"),
    "battery": ("Pilha ou bateria portátil", "battery"),
    "small_electronic": ("Celular, mouse, carregador ou pequeno eletrônico", "electronic"),
    "out_of_scope": ("Alimento, orgânico ou outro item fora da lista", "out_of_scope"),
    "unknown": ("Não sei identificar o material", "unknown"),
}


def restrict_prediction(prediction: BaselinePrediction, classes: tuple[str, ...]) -> BaselinePrediction:
    if prediction.top_class_id in classes and (
        prediction.class_id is None or prediction.class_id in classes
    ):
        return prediction
    # Keep the original scores; never promote a runner-up after rejecting a class.
    return replace(prediction, class_id=None, top_class_id="", accepted=False)
