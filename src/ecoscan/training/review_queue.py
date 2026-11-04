from __future__ import annotations


BUCKET = "ecoscan-training"


def eligible(rows, classes):
    return [
        row
        for row in rows
        if row.get("status") == "approved"
        and row.get("consent") is True
        and row.get("expected_class") in classes
    ]


def update_rows(store, rows, state, run_id):
    for row in rows:
        previous = row.get("revision", 0)
        updated = dict(
            row,
            revision=previous + 1,
            training_status=state,
            candidate_id=run_id,
        )
        saved = store.save(updated, previous_revision=previous)
        row.update(saved)
