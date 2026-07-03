from __future__ import annotations

import pytest

from grading.adapters.canvas import canvas_adapter, canvas_client
from grading.ports.canvas_port import AttachmentRef
from grading.ports.credentials_port import CanvasCredentials, CredentialsPort


def test_fetch_submission_attachment_maps_and_passes_creds(monkeypatch):
    captured: dict = {}

    def fake_fetch(*, base_url, token, course_id, assignment_id, user_id):
        captured.update(base_url=base_url, token=token, user_id=user_id)
        return {"attachments": [{"id": 999, "display_name": "tarea.docx", "url": "https://dl/1"}]}

    monkeypatch.setattr(canvas_client, "fetch_assignment_submission", fake_fetch)
    adapter = canvas_adapter.CanvasAdapter(base_url="https://eig.x/", token="tok")

    ref = adapter.fetch_submission_attachment(course_id="c", assignment_id="a", user_id="self")

    assert ref == AttachmentRef(file_id="999", filename="tarea.docx", download_url="https://dl/1")
    assert captured["base_url"] == "https://eig.x"  # rstrip de la barra final
    assert captured["token"] == "tok"


def test_fetch_submission_attachment_without_attachments(monkeypatch):
    monkeypatch.setattr(
        canvas_client, "fetch_assignment_submission", lambda **_: {"attachments": []}
    )
    adapter = canvas_adapter.CanvasAdapter(base_url="https://x", token="t")

    with pytest.raises(canvas_client.CanvasApiError):
        adapter.fetch_submission_attachment(course_id="c", assignment_id="a", user_id="1")


def test_fetch_submission_attachment_index_out_of_range(monkeypatch):
    monkeypatch.setattr(
        canvas_client,
        "fetch_assignment_submission",
        lambda **_: {"attachments": [{"id": 1}]},
    )
    adapter = canvas_adapter.CanvasAdapter(base_url="https://x", token="t")

    with pytest.raises(canvas_client.CanvasApiError):
        adapter.fetch_submission_attachment(
            course_id="c", assignment_id="a", user_id="1", attachment_index=3
        )


def test_download_file_prefers_attachment_filename(monkeypatch):
    monkeypatch.setattr(
        canvas_client, "fetch_file_metadata", lambda **_: {"display_name": "meta.pdf"}
    )
    monkeypatch.setattr(canvas_client, "download_file_bytes", lambda **_: b"PDFDATA")
    adapter = canvas_adapter.CanvasAdapter(base_url="https://x", token="t")

    data, name = adapter.download_file(
        attachment=AttachmentRef(file_id="5", filename="orig.pdf", download_url=None)
    )

    assert data == b"PDFDATA"
    assert name == "orig.pdf"


def test_publish_grade_delegates(monkeypatch):
    calls: dict = {}
    monkeypatch.setattr(canvas_client, "update_submission_grade", lambda **k: calls.update(k))
    adapter = canvas_adapter.CanvasAdapter(base_url="https://x/", token="t")

    adapter.publish_grade(course_id="c", assignment_id="a", user_id="u", score=8, comment="bien")

    assert calls["base_url"] == "https://x"
    assert calls["score"] == 8
    assert calls["comment"] == "bien"


def test_factory_resolves_credentials_per_university():
    class FakeCreds(CredentialsPort):
        def get_canvas_credentials(self, *, universidad_id, env):
            assert universidad_id == "eig"
            assert env == "prod"
            return CanvasCredentials(base_url="https://eig.x", token="T")

    factory = canvas_adapter.CanvasAdapterFactory(FakeCreds())

    adapter = factory.for_university(universidad_id="eig", env="prod")

    assert isinstance(adapter, canvas_adapter.CanvasAdapter)
    assert adapter.base_url == "https://eig.x"
    assert adapter.token == "T"
