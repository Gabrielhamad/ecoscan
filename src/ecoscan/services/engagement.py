"""Educational awards are non-financial, once per mission and account."""
from __future__ import annotations

import hashlib
import json

from ecoscan.config import PROJECT_ROOT
from ecoscan.services.accounts import (
    append_point_transaction, build_point_transaction, read_point_transactions,
)


CATALOG = json.loads((PROJECT_ROOT / "config" / "education.json").read_text(encoding="utf-8"))
LESSONS = CATALOG["materials"]


def award_once(path, *, user_id, mission_id, points, note, detected_class=None, probability=None):
    if not user_id or user_id.startswith("visitor_"):
        raise ValueError("Entre em sua conta para salvar pontos.")
    if any(row.mission_id == mission_id and row.status == "awarded"
           for row in read_point_transactions(path, user_id=user_id)):
        raise ValueError("Esta missão já foi pontuada na sua conta.")
    # UNIQUE(owner, mission, evidence) prevents simultaneous awards in the database.
    # The stable completion key is not the hash of an uploaded photograph.
    key = hashlib.sha256(f"ecoscan:once:{mission_id}".encode()).hexdigest()
    transaction = build_point_transaction(
        user_id=user_id, mission_id=mission_id, points=points, evidence_sha256=key,
        detected_class=detected_class, probability=probability, note=note,
    )
    append_point_transaction(path, transaction)
    return transaction


def award_quiz(path, *, user_id, material, answer):
    lesson = LESSONS.get(material)
    if lesson is None or type(answer) is not int or answer != lesson["answer"]:
        raise ValueError("Revise a orientação e tente novamente.")
    return award_once(path, user_id=user_id, mission_id=f"aprender:{material}:v1", points=10,
                      note="Verificação educativa respondida corretamente; não comprova descarte.")
