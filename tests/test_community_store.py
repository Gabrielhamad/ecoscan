import copy
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from PIL import Image

from ecoscan.services.civic_reports import build_civic_report_record
from ecoscan.services.community_store import (
    CommunityStore, REPORTS, CAMPAIGNS, community_store, private_jpeg,
)


class MemoryClient:
    """Query double enforcing filters/CAS, not a substitute for PostgreSQL tests."""
    def __init__(self):
        self.rows = {REPORTS: {}, CAMPAIGNS: {}}
        self.blobs = {}
        self.storage = SimpleNamespace(from_=lambda name: self)
        self.failure = False
        self.timeout_after_insert = False
        self.before_update = None

    def upload(self, key, data, **kwargs):
        if key in self.blobs:
            raise OSError("duplicate")
        self.blobs[key] = data

    def download(self, key):
        return self.blobs[key]

    def table(self, name):
        return Query(self, name)


class Query:
    def __init__(self, db, name):
        self.db, self.name, self.filters = db, name, {}
        self.action, self.payload, self.maximum = "select", None, 1000

    def select(self, columns):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, *args, **kwargs):
        return self

    def limit(self, value):
        self.maximum = value
        return self

    def insert(self, payload):
        self.action, self.payload = "insert", copy.deepcopy(payload)
        return self

    def update(self, payload):
        self.action, self.payload = "update", copy.deepcopy(payload)
        return self

    def execute(self):
        if self.db.failure:
            raise OSError("private connection detail")
        rows = self.db.rows[self.name]
        if self.action == "insert":
            if self.payload["id"] in rows:
                raise OSError("duplicate")
            rows[self.payload["id"]] = {"created_at": "2026-10-05T12:00:00Z", **self.payload}
            result = [rows[self.payload["id"]]]
            if self.db.timeout_after_insert:
                raise TimeoutError()
        else:
            if self.action == "update" and self.db.before_update:
                self.db.before_update(rows)
            result = [r for r in rows.values() if all(r[k] == v for k, v in self.filters.items())]
            if self.action == "update":
                for row in result:
                    row.update(self.payload)
        return SimpleNamespace(data=copy.deepcopy(result[:self.maximum]))


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.db = MemoryClient()
        self.store = CommunityStore(self.db)
        self.user = SimpleNamespace(id="supabase_" + str(uuid4()), is_admin=False)
        self.other = SimpleNamespace(id="supabase_" + str(uuid4()), is_admin=False)
        self.admin = SimpleNamespace(id="supabase_" + str(uuid4()), is_admin=True)
        self.auth = {"token": "verified", "access": {}}
        self.verify = patch("ecoscan.services.community_store.verified_profile", return_value=self.user).start()
        self.addCleanup(patch.stopall)
        image = Image.new("RGB", (60, 80), "green")
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        self.image = stream.getvalue()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "photo.png"
        path.write_bytes(self.image)
        self.record = build_civic_report_record(SimpleNamespace(
            accepted=False, predicted_class=None, top_class="metal", probability=.4,
            pipeline=SimpleNamespace(metadata={}, element_analysis=None)),
            evidence_path=path, location_note="Bairro de teste", description="Material descartado",
            submitted_by="forged_identity")
        self.submission = str(uuid4())

    def submit(self, **kwargs):
        return self.store.submit(self.record, self.image, submission_id=self.submission,
                                 consent=True, **self.auth, **kwargs)

    def test_rollout_closed_without_connecting(self):
        with patch.dict(os.environ, {"ECOSCAN_COMMUNITY_ENABLED": "false"}), patch(
                "ecoscan.services.community_store.remote_store") as remote:
            with self.assertRaises(OSError):
                community_store()
            remote.assert_not_called()

    def test_rollout_requires_credentials(self):
        with patch.dict(os.environ, {"ECOSCAN_COMMUNITY_ENABLED": "true"}), patch(
                "ecoscan.services.community_store.remote_store", return_value=None):
            with self.assertRaises(OSError):
                community_store()

    def test_missing_or_invalid_session_does_not_write(self):
        for token in (None, "expired"):
            self.verify.side_effect = ValueError("expired")
            with self.assertRaises((ValueError, PermissionError)):
                self.store.submit(self.record, self.image, submission_id=self.submission,
                                  consent=True, token=token, access={})
        self.assertFalse(self.db.rows[REPORTS])
        self.assertFalse(self.db.blobs)

    def test_submit_overrides_owner_and_removes_local_path(self):
        row = self.submit()
        self.assertEqual(row["reporter_id"], self.user.id)
        self.assertEqual(row["record"]["submitted_by"], self.user.id)
        self.assertEqual(row["record"]["evidence_path"], "")
        self.assertEqual(row["reviews"], [])
        self.assertEqual(len(self.db.blobs), 1)

    def test_retry_is_idempotent_even_after_committed_timeout(self):
        self.db.timeout_after_insert = True
        first = self.submit()
        second = self.submit()
        self.assertEqual(first, second)
        self.assertEqual(len(self.db.rows[REPORTS]), 1)

    def test_upload_timeout_retry_validates_existing_photo(self):
        original = self.db.upload
        def timedout(*args, **kwargs):
            original(*args, **kwargs)
            raise TimeoutError()
        self.db.upload = timedout
        self.assertTrue(self.submit()["id"])

    def test_changed_form_cannot_reuse_protocol(self):
        from dataclasses import replace
        self.submit()
        self.record = replace(self.record, description="Outra descrição")
        with self.assertRaises(ValueError):
            self.submit()

    def test_consent_and_required_fields_before_storage(self):
        from dataclasses import replace
        with self.assertRaises(ValueError):
            self.store.submit(self.record, self.image, submission_id=self.submission,
                              consent=False, **self.auth)
        self.record = replace(self.record, location_note="")
        with self.assertRaises(ValueError):
            self.submit()
        self.assertFalse(self.db.blobs)

    def test_private_queries_filter_before_limiting(self):
        row = self.submit()
        self.verify.return_value = self.other
        self.assertEqual(self.store.reports(**self.auth), [])
        with self.assertRaises(PermissionError):
            self.store.evidence(row["id"], **self.auth)
        self.verify.return_value = self.admin
        self.assertEqual(len(self.store.reports(**self.auth)), 1)
        self.assertEqual(self.store.reports(**self.auth, own_only=True), [])

    def test_user_cannot_review_or_publish(self):
        with self.assertRaises(PermissionError):
            self.store.review(str(uuid4()), expected_revision=0, decision="arquivar", note="Resposta", **self.auth)
        with self.assertRaises(PermissionError):
            self.store.publish_campaign({}, expected_revision=None, **self.auth)

    def test_review_visible_to_author_and_original_immutable(self):
        row = self.submit()
        self.verify.return_value = self.admin
        updated = self.store.review(row["id"], expected_revision=0, decision="solicitar_nova_foto",
                                    note="Inclua o entorno na nova foto.", **self.auth)
        self.assertEqual(updated["record"], row["record"])
        self.assertEqual(updated["revision"], 1)
        self.verify.return_value = self.user
        self.assertIn("entorno", self.store.reports(**self.auth)[0]["reviews"][0]["note"])

    def test_concurrent_review_cannot_overwrite(self):
        row = self.submit()
        self.verify.return_value = self.admin
        self.db.before_update = lambda rows: rows[row["id"]].update(revision=1)
        with self.assertRaisesRegex(ValueError, "Outro analista"):
            self.store.review(row["id"], expected_revision=0, decision="arquivar", note="Resposta", **self.auth)
        self.assertEqual(self.db.rows[REPORTS][row["id"]]["reviews"], [])

    def test_stale_revision_rejected_before_update(self):
        row = self.submit()
        self.verify.return_value = self.admin
        with self.assertRaises(ValueError):
            self.store.review(row["id"], expected_revision=9, decision="arquivar", note="Resposta", **self.auth)

    def test_outage_never_looks_like_empty_history_or_success(self):
        self.db.failure = True
        with self.assertRaises(OSError) as error:
            self.store.reports(**self.auth)
        self.assertNotIn("private", str(error.exception))
        with self.assertRaises(OSError):
            self.submit()
        self.assertFalse(self.db.blobs)

    def test_image_integrity_and_metadata_removal(self):
        row = self.submit()
        jpeg = self.store.evidence(row["id"], **self.auth)
        with Image.open(io.BytesIO(jpeg)) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertFalse(image.getexif())
        self.db.blobs[row["id"] + ".jpg"] = b"corrupted"
        with self.assertRaises(OSError):
            self.store.evidence(row["id"], **self.auth)
        with self.assertRaises(ValueError):
            private_jpeg(b"not an image")

    def test_campaign_public_read_and_optimistic_update(self):
        self.verify.return_value = self.admin
        payload = json.loads((Path(__file__).parents[1] / "config/campaigns.json").read_text(encoding="utf-8"))
        first = self.store.publish_campaign(payload, expected_revision=None, **self.auth)
        self.assertEqual(first["revision"], 0)
        payload["title"] = "Campanha revisada"
        self.store.publish_campaign(payload, expected_revision=0, **self.auth)
        self.assertEqual(self.store.campaign()["record"]["title"], "Campanha revisada")
        with self.assertRaises(ValueError):
            self.store.publish_campaign(payload, expected_revision=0, **self.auth)

    def test_campaign_outage_does_not_fall_back(self):
        self.db.failure = True
        with self.assertRaises(OSError):
            self.store.campaign()

    def test_full_queue_does_not_upload_new_photo(self):
        for number in range(200):
            identifier = str(uuid4())
            self.db.rows[REPORTS][identifier] = {"id": identifier, "reporter_id": self.user.id}
        with self.assertRaisesRegex(ValueError, "fila"):
            self.submit()
        self.assertFalse(self.db.blobs)
