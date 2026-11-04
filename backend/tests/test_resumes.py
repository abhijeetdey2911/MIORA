"""Tests for Project JobHunter Phase 3A Resume Manager Endpoints."""

import io
import docx
import pymupdf  # PyMuPDF
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_sample_pdf_bytes(text: str = "Abhijeet Sharma\nSenior Data & Full-Stack Engineer\nSkills: Python, SQL, FastAPI, React") -> bytes:
    """Create an in-memory PDF with a real text layer using PyMuPDF."""
    doc = pymupdf.open()
    page = doc.new_page()
    if text:
        page.insert_text((72, 72), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _create_scanned_pdf_bytes() -> bytes:
    """Create an in-memory image-only (scanned) PDF with no text layer."""
    doc = pymupdf.open()
    page = doc.new_page()
    # Create a tiny 10x10 PNG pixmap and insert it as an image on the page
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), False)
    pix.set_rect(pix.irect, (200, 200, 200))
    img_bytes = pix.tobytes("png")
    page.insert_image(pymupdf.Rect(72, 72, 200, 200), stream=img_bytes)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def _create_sample_docx_bytes(text: str = "Abhijeet Sharma — Data Analytics Resume\nExperience: 3 Years in SQL, Python, Power BI") -> bytes:
    """Create an in-memory DOCX document using python-docx."""
    doc = docx.Document()
    if text:
        for line in text.split("\n"):
            doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_pdf_and_docx_resume_lifecycle_with_preferences() -> None:
    """Test PDF upload, DOCX upload, text extraction, preference mapping, download, rename, and delete."""
    # Create two sample job preferences to test association mapping
    pref1_res = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "Data Analytics Profile",
            "job_roles": ["Data Analyst", "BI Analyst"],
            "locations": ["Bangalore", "Remote (India)"],
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "experience_level": "Entry-level",
            "min_salary": 900000,
            "max_salary": 1600000,
            "currency": "INR",
            "skills": ["SQL", "Python", "Power BI"],
            "minimum_match_score": 75,
            "is_active": True,
        },
    )
    pref2_res = client.post(
        "/api/v1/preferences",
        json={
            "preference_name": "Software Engineering Profile",
            "job_roles": ["Software Engineer", "Full-Stack Developer"],
            "locations": ["Hyderabad", "Bangalore"],
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "experience_level": "Experienced",
            "min_salary": 1500000,
            "max_salary": 2800000,
            "currency": "INR",
            "skills": ["Python", "FastAPI", "React", "TypeScript"],
            "minimum_match_score": 80,
            "is_active": True,
        },
    )
    assert pref1_res.status_code == 201
    assert pref2_res.status_code == 201
    pref1_id = pref1_res.json()["id"]
    pref2_id = pref2_res.json()["id"]

    pdf_resume_id = None
    docx_resume_id = None

    try:
        # 1. Upload PDF Resume associated only with pref1 (not auto-associated with pref2)
        pdf_bytes = _create_sample_pdf_bytes()
        pdf_res = client.post(
            "/api/v1/resumes",
            files={"file": ("Abhijeet_FullStack_Resume.pdf", pdf_bytes, "application/pdf")},
            data={
                "resume_name": "Full-Stack Master Resume",
                "preference_ids": f'["{pref1_id}"]',
            },
        )
        assert pdf_res.status_code == 201, pdf_res.text
        pdf_data = pdf_res.json()
        pdf_resume_id = pdf_data["id"]
        assert pdf_data["name"] == "Full-Stack Master Resume"
        assert pdf_data["resume_name"] == "Full-Stack Master Resume"
        assert pdf_data["original_filename"] == "Abhijeet_FullStack_Resume.pdf"
        assert pdf_data["file_type"] == "PDF"
        assert pdf_data["file_format"] == "PDF"
        assert "upload_date" in pdf_data
        assert "stored_filename" not in pdf_data
        assert "storage_path" not in pdf_data
        assert pdf_data["processing_status"] == "Processed"
        assert pdf_data["requires_ocr"] is False
        assert "Abhijeet Sharma" in (pdf_data["extracted_text"] or "")
        assert "FastAPI" in (pdf_data["extracted_text"] or "")
        assert len(pdf_data["associated_preferences"]) == 1
        assert pdf_data["associated_preferences"][0]["id"] == pref1_id

        # 2. Upload DOCX Resume with no initial preferences
        docx_bytes = _create_sample_docx_bytes()
        docx_res = client.post(
            "/api/v1/resumes",
            files={
                "file": (
                    "Data_Analytics_Resume.docx",
                    docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert docx_res.status_code == 201, docx_res.text
        docx_data = docx_res.json()
        docx_resume_id = docx_data["id"]
        assert docx_data["file_format"] == "DOCX"
        assert docx_data["processing_status"] == "Processed"
        assert "Power BI" in (docx_data["extracted_text"] or "")
        assert docx_data["associated_preferences"] == []

        # 3. List resumes (GET /api/v1/resumes)
        list_res = client.get("/api/v1/resumes")
        assert list_res.status_code == 200
        listed_ids = {item["id"] for item in list_res.json()}
        assert pdf_resume_id in listed_ids
        assert docx_resume_id in listed_ids

        # 4. Get single resume (GET /api/v1/resumes/{id})
        get_res = client.get(f"/api/v1/resumes/{pdf_resume_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == pdf_resume_id

        # 5. Download resume (GET /api/v1/resumes/{id}/download)
        dl_res = client.get(f"/api/v1/resumes/{pdf_resume_id}/download")
        assert dl_res.status_code == 200
        assert dl_res.headers["x-content-type-options"] == "nosniff"
        assert dl_res.content == pdf_bytes

        # 6. Rename and update preference associations (PATCH /api/v1/resumes/{id})
        patch_res = client.patch(
            f"/api/v1/resumes/{pdf_resume_id}",
            json={
                "resume_name": "Updated Engineering & Analytics Resume",
                "preference_ids": [pref1_id, pref2_id],
            },
        )
        assert patch_res.status_code == 200
        patched = patch_res.json()
        assert patched["resume_name"] == "Updated Engineering & Analytics Resume"
        assert {p["id"] for p in patched["associated_preferences"]} == {pref1_id, pref2_id}

    finally:
        if pdf_resume_id:
            del_pdf = client.delete(f"/api/v1/resumes/{pdf_resume_id}")
            assert del_pdf.status_code == 200
        if docx_resume_id:
            del_docx = client.delete(f"/api/v1/resumes/{docx_resume_id}")
            assert del_docx.status_code == 200
        client.delete(f"/api/v1/preferences/{pref1_id}")
        client.delete(f"/api/v1/preferences/{pref2_id}")


def test_scanned_pdf_and_empty_document_handling() -> None:
    """Test that scanned PDFs are marked as requiring OCR and empty docs fail cleanly."""
    # Scanned PDF (image only, no text layer)
    scanned_bytes = _create_scanned_pdf_bytes()
    res_scanned = client.post(
        "/api/v1/resumes",
        files={"file": ("Scanned_Resume.pdf", scanned_bytes, "application/pdf")},
    )
    assert res_scanned.status_code == 201
    scanned_data = res_scanned.json()
    try:
        assert scanned_data["processing_status"] == "Failed"
        assert scanned_data["requires_ocr"] is True
        assert scanned_data["extracted_text"] is None
        assert "requires OCR" in (scanned_data["processing_message"] or "")
    finally:
        client.delete(f"/api/v1/resumes/{scanned_data['id']}")

    # Empty DOCX (no text paragraphs)
    empty_docx_bytes = _create_sample_docx_bytes(text="")
    res_empty = client.post(
        "/api/v1/resumes",
        files={"file": ("Empty_Resume.docx", empty_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )
    assert res_empty.status_code == 201
    empty_data = res_empty.json()
    try:
        assert empty_data["processing_status"] == "Failed"
        assert empty_data["extracted_text"] is None
        assert "Empty DOCX" in (empty_data["processing_message"] or "")
    finally:
        client.delete(f"/api/v1/resumes/{empty_data['id']}")


def test_invalid_resume_rejection() -> None:
    """Test rejection of unsupported formats, corrupted headers, and empty 0-byte files."""
    # Unsupported format (.txt)
    res_txt = client.post(
        "/api/v1/resumes",
        files={"file": ("resume.txt", b"Plain text resume", "text/plain")},
    )
    assert res_txt.status_code == 400
    assert "Unsupported file format" in res_txt.json()["message"]

    # Fake PDF with invalid magic bytes
    res_fake_pdf = client.post(
        "/api/v1/resumes",
        files={"file": ("fake.pdf", b"not a real pdf file", "application/pdf")},
    )
    assert res_fake_pdf.status_code == 400
    assert "PDF header" in res_fake_pdf.json()["message"]

    # 0-byte file
    res_zero = client.post(
        "/api/v1/resumes",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res_zero.status_code == 400

    # Oversized file (> 10 MB)
    oversized_bytes = b"%PDF-1.7\n" + (b"0" * (10 * 1024 * 1024 + 64))
    res_oversized = client.post(
        "/api/v1/resumes",
        files={"file": ("oversized.pdf", oversized_bytes, "application/pdf")},
    )
    assert res_oversized.status_code == 400
    assert "10 MB" in res_oversized.json()["message"]
