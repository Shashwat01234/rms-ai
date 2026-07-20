# ai/certificate_verifier.py — AI Certificate Authenticity Checker using Gemini Vision
import os
import base64
import json

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf", "webp"}

MIME_MAP = {
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "png":  "image/png",
    "webp": "image/webp",
    "pdf":  "application/pdf",
}


def get_file_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def pdf_to_image_bytes(pdf_bytes: bytes) -> bytes:
    """Convert first page of PDF to PNG bytes using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)          # 2x zoom for better clarity
        pix = page.get_pixmap(matrix=mat)
        return pix.tobytes("png")
    except ImportError:
        return pdf_bytes                      # Return as-is if fitz not available
    except Exception:
        return pdf_bytes


def verify_certificate(image_bytes: bytes, filename: str, student_id: str = "") -> dict:
    """Main entry point — analyze certificate and return structured result."""
    ext = get_file_extension(filename)

    if ext not in ALLOWED_EXTENSIONS:
        return _error_result("Unsupported file type. Upload JPG, PNG, or PDF.")

    # Convert PDF to image for vision analysis
    mime_type = MIME_MAP.get(ext, "image/jpeg")
    if ext == "pdf":
        image_bytes = pdf_to_image_bytes(image_bytes)
        mime_type   = "image/png"

    if not GEMINI_API_KEY:
        return _error_result("GEMINI_API_KEY not configured. Please add it to your .env file.")

    try:
        return _gemini_verify(image_bytes, mime_type)
    except json.JSONDecodeError:
        return _error_result("AI returned an unparseable response. Please retry.")
    except Exception as e:
        return _error_result(f"Verification failed: {str(e)}")


def _gemini_verify(image_bytes: bytes, mime_type: str) -> dict:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)

    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = """Carefully analyze this certificate/document image for authenticity.

Return ONLY a valid JSON object (no markdown, no extra text) with this exact structure:

{
  "extracted": {
    "name": "full name on certificate or null",
    "institution": "issuing institution name or null",
    "degree_or_title": "degree/award/certificate title or null",
    "date": "date of issue or null",
    "certificate_number": "certificate/roll/registration number if visible or null",
    "authorized_by": "signatory name or designation if visible or null"
  },
  "checks": {
    "official_seal_or_stamp": true_or_false,
    "authorized_signature": true_or_false,
    "watermark_or_security_feature": true_or_false,
    "official_letterhead": true_or_false,
    "unique_identifier_number": true_or_false,
    "consistent_typography": true_or_false,
    "no_visible_tampering": true_or_false,
    "professional_print_quality": true_or_false
  },
  "flags": ["list any suspicious elements here, or empty array if none"],
  "verdict": "GENUINE or LIKELY GENUINE or SUSPICIOUS or REQUIRES MANUAL REVIEW",
  "confidence": 85,
  "summary": "2-3 sentences summarizing the analysis findings."
}

Be fair and thorough. A scanned/photocopied document may miss some visual markers but still be genuine. Judge based on overall impression and available indicators."""

    image_part = {
        "mime_type": mime_type,
        "data":      base64.b64encode(image_bytes).decode("utf-8"),
    }

    response = model.generate_content([prompt, image_part])
    raw      = response.text.strip()

    # Strip markdown code fences if present
    if "```" in raw:
        parts = raw.split("```")
        # parts[1] is the code block content
        raw = parts[1].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    data = json.loads(raw)

    # Normalize and compute pass rate
    checks   = data.get("checks", {})
    passed   = sum(1 for v in checks.values() if v is True)
    total    = len(checks) or 1
    pass_pct = round((passed / total) * 100)

    verdict    = data.get("verdict", "REQUIRES MANUAL REVIEW")
    confidence = data.get("confidence", pass_pct)

    return {
        "extracted":   data.get("extracted", {}),
        "checks":      checks,
        "pass_rate":   pass_pct,
        "flags":       data.get("flags", []),
        "verdict":     verdict,
        "confidence":  confidence,
        "summary":     data.get("summary", ""),
        "ai_powered":  True,
    }


def _error_result(msg: str) -> dict:
    return {
        "extracted":  {},
        "checks":     {},
        "pass_rate":  0,
        "flags":      [msg],
        "verdict":    "REQUIRES MANUAL REVIEW",
        "confidence": 0,
        "summary":    msg,
        "ai_powered": False,
        "error":      msg,
    }
