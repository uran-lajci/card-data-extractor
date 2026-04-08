"""
Card Text Extractor — Streamlit + Ollama (qwen3:8b-vl)
Extracts structured fields from insurance cards and personal ID cards.
"""

import streamlit as st
import ollama
import base64
import json
import re
from io import BytesIO

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Card Text Extractor",
    page_icon="🪪",
    layout="centered",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .block-container { max-width: 740px; }
    div[data-testid="stFileUploader"] {
        border: 2px dashed #4a90d9;
        border-radius: 12px;
        padding: 8px;
    }
    .result-box {
        background: #f0f4fa;
        border-left: 4px solid #4a90d9;
        border-radius: 8px;
        padding: 18px 22px;
        margin-top: 12px;
        font-family: 'Segoe UI', sans-serif;
        line-height: 1.8;
    }
    .result-box b { color: #1a3a5c; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Constants ────────────────────────────────────────────────────────────────
MODEL = "qwen3-vl:8b"

INSURANCE_FIELDS = [
    "Insurance no.",
    "Country",
    "Name",
    "Given names",
    "Date of birth",
    "Personal identification number",
    "Identification number of the institution",
    "Identification number of the card",
    "Expiry date",
]

PERSONAL_ID_FIELDS = [
    "Country",
    "Document type",
    "Document number",
    "Surname",
    "Given name(s)",
    "Date of birth",
    "Name",
    "Sex",
    "Height",
    "Nationality",
    "Document Number",
    "Date of Issue",
    "Date of Expiry",
    "document-number line",
    "personal-data line",
]


# ── Helpers ──────────────────────────────────────────────────────────────────
def image_to_base64(uploaded_file) -> str:
    """Convert a Streamlit UploadedFile to a base64 string."""
    return base64.b64encode(uploaded_file.getvalue()).decode("utf-8")


def build_prompt(fields: list[str], card_label: str, multi_image: bool = False) -> str:
    """Build the extraction prompt sent to the vision model."""
    fields_list = "\n".join(f"- {f}" for f in fields)

    extra = ""
    if multi_image:
        extra = (
            "You are given TWO images: the front and the back of the card. "
            "Use information from BOTH sides to fill in every field.\n\n"
        )

    return (
        f"You are an expert OCR assistant. {extra}"
        f"Extract the following fields from the {card_label}.\n\n"
        f"Fields:\n{fields_list}\n\n"
        "Rules:\n"
        '1. Return ONLY a valid JSON object — no markdown, no explanation, no ```json fences.\n'
        '2. Use the exact field names listed above as JSON keys.\n'
        '3. If a field cannot be found, set its value to null.\n'
        '4. Do NOT invent or guess information that is not visible in the image.\n'
        "/no_think"
    )


def extract_json(text: str) -> dict | None:
    """Try to parse JSON from the model output, tolerating markdown fences."""
    # Strip common wrappers
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Last-ditch: find first { ... } block
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def call_ollama(images_b64: list[str], prompt: str) -> dict | None:
    """Send images + prompt to the Ollama vision model and return parsed JSON."""
    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
                "images": images_b64,
            }
        ],
    )
    raw = response["message"]["content"]
    return raw, extract_json(raw)


def render_results(data: dict, fields: list[str]):
    """Display extracted fields in a styled HTML block."""
    rows = ""
    for field in fields:
        value = data.get(field)
        display = value if value is not None else "—"
        rows += f"<b>{field}:</b> {display}<br/>"
    st.markdown(f'<div class="result-box">{rows}</div>', unsafe_allow_html=True)


# ── UI ───────────────────────────────────────────────────────────────────────
st.title("🪪 Card Text Extractor")
st.caption(f"Powered by **{MODEL}** via Ollama")

card_type = st.selectbox(
    "Select card type",
    options=["Insurance Card", "Personal ID Card"],
    index=0,
)

st.divider()

if card_type == "Insurance Card":
    st.subheader("📋 Insurance Card")
    st.info(
        "Upload **one** image of the insurance card. "
        "The following fields will be extracted:\n\n"
        + ", ".join(f"*{f}*" for f in INSURANCE_FIELDS)
    )
    uploaded = st.file_uploader(
        "Upload insurance card image",
        type=["png", "jpg", "jpeg", "webp"],
        key="insurance_upload",
    )

    if uploaded:
        st.image(uploaded, caption="Insurance Card", use_container_width=True)

        if st.button("🔍 Extract Information", key="ins_btn", type="primary"):
            with st.spinner("Analysing card with vision model …"):
                b64 = image_to_base64(uploaded)
                prompt = build_prompt(INSURANCE_FIELDS, "insurance card")
                raw, parsed = call_ollama([b64], prompt)

            if parsed:
                st.success("Extraction complete!")
                render_results(parsed, INSURANCE_FIELDS)
                with st.expander("Raw model output"):
                    st.code(raw, language="json")
            else:
                st.error("Could not parse structured data from the model response.")
                st.code(raw)

else:  # Personal ID Card
    st.subheader("🆔 Personal ID Card")
    st.info(
        "Upload **two** images — front and back of the ID card. "
        "The following fields will be extracted:\n\n"
        + ", ".join(f"*{f}*" for f in PERSONAL_ID_FIELDS)
    )

    col1, col2 = st.columns(2)
    with col1:
        front = st.file_uploader(
            "Front side",
            type=["png", "jpg", "jpeg", "webp"],
            key="id_front",
        )
        if front:
            st.image(front, caption="Front", use_container_width=True)

    with col2:
        back = st.file_uploader(
            "Back side",
            type=["png", "jpg", "jpeg", "webp"],
            key="id_back",
        )
        if back:
            st.image(back, caption="Back", use_container_width=True)

    if front and back:
        if st.button("🔍 Extract Information", key="id_btn", type="primary"):
            with st.spinner("Analysing both sides with vision model …"):
                images = [image_to_base64(front), image_to_base64(back)]
                prompt = build_prompt(
                    PERSONAL_ID_FIELDS, "personal ID card", multi_image=True
                )
                raw, parsed = call_ollama(images, prompt)

            if parsed:
                st.success("Extraction complete!")
                render_results(parsed, PERSONAL_ID_FIELDS)
                with st.expander("Raw model output"):
                    st.code(raw, language="json")
            else:
                st.error("Could not parse structured data from the model response.")
                st.code(raw)
    elif front or back:
        st.warning("Please upload both the front and back of the ID card.")