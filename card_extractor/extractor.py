import json
import re
from io import BytesIO

import boto3
from PIL import Image

from card_extractor.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, MODEL_ID

MAX_LONG_EDGE_PX = 1568
MAX_IMAGE_BYTES = 5 * 1024 * 1024

CARD_FIELDS = {
    'insurance': [
        'Insurance no.', 'Country', 'Name', 'Given names', 'Date of birth',
        'Personal identification number', 'Identification number of the institution',
        'Identification number of the card', 'Expiry date',
    ],
    'personal_id': [
        'Country', 'Document type', 'Document number', 'Surname', 'Given name(s)',
        'Date of birth', 'Name', 'Sex', 'Height', 'Nationality', 'Date of Issue', 'Date of Expiry',
    ],
    'credit_card': [
        'Card number', 'Cardholder name', 'Expiry date', 'Issuing bank',
    ],
}

EXPECTED_IMAGE_COUNT = {'insurance': 1, 'personal_id': 2, 'credit_card': 1}

IMAGE_NOTES = {
    'insurance': 'The image shows one side of a health/insurance card.',
    'personal_id': (
        'Image 1 is the FRONT of a personal ID document; Image 2 is the BACK. '
        'Combine information from both sides. Ignore the machine-readable MRZ lines '
        "at the bottom (the '<<<'-delimited document-number and personal-data lines); "
        'extract only from the visually printed fields.'
    ),
    'credit_card': 'The image shows the front of a credit/debit card.',
}


def prepare_image(raw: bytes) -> tuple[bytes, str]:
    img = Image.open(BytesIO(raw))
    img.load()

    fmt = (img.format or 'JPEG').lower()
    fmt = 'jpeg' if fmt == 'jpg' else fmt
    fits = max(img.size) <= MAX_LONG_EDGE_PX and len(raw) <= MAX_IMAGE_BYTES
    if fits and fmt in {'jpeg', 'png', 'gif', 'webp'}:
        return raw, fmt

    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
    img.thumbnail((MAX_LONG_EDGE_PX, MAX_LONG_EDGE_PX), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format='JPEG', quality=85, optimize=True)
    return buf.getvalue(), 'jpeg'


def build_prompt(card_type: str, fields: list[str], n_images: int) -> str:
    skeleton = ',\n'.join(f'    "{f}": null' for f in fields)
    merge_hint = '- Merge fields across the provided images.\n' if n_images > 1 else ''
    return (
        f'You are an expert document information-extraction system.\n\n'
        f'{IMAGE_NOTES[card_type]}\n\n'
        f'Extract ONLY the following fields. Use the exact keys shown below.\n\n'
        f'Rules:\n'
        f'- Return a single JSON object and nothing else (no prose, no markdown fences).\n'
        f'- If a field is not present or not legible, set its value to null.\n'
        f'- Preserve values verbatim as printed on the card.\n'
        f'{merge_hint}\n'
        f'Expected JSON schema (fill in the values):\n'
        f'{{\n{skeleton}\n}}\n'
    )


def build_message(prompt: str, images: list[tuple[bytes, str]]) -> dict:
    content = []
    for idx, (data, fmt) in enumerate(images, start=1):
        if len(images) > 1:
            content.append({'text': f'Image {idx}:'})
        content.append({'image': {'format': fmt, 'source': {'bytes': data}}})
    content.append({'text': prompt})
    return {'role': 'user', 'content': content}


def parse_json(text: str) -> dict:
    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        raise ValueError(f'No JSON object found in model response:\n{text}')
    return json.loads(match.group(0))


def get_bedrock_client():
    return boto3.client(
        'bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )


def extract_fields(card_type: str, image_bytes_list: list[bytes]) -> dict:
    if card_type not in CARD_FIELDS:
        raise ValueError(f"Unknown card_type '{card_type}'. Expected one of: {list(CARD_FIELDS)}")

    expected = EXPECTED_IMAGE_COUNT[card_type]
    if len(image_bytes_list) != expected:
        raise ValueError(f"card_type '{card_type}' requires {expected} image(s), got {len(image_bytes_list)}.")

    fields = CARD_FIELDS[card_type]
    images = [prepare_image(b) for b in image_bytes_list]
    prompt = build_prompt(card_type, fields, len(images))
    message = build_message(prompt, images)

    response = get_bedrock_client().converse(
        modelId=MODEL_ID,
        messages=[message],
        inferenceConfig={'maxTokens': 1024, 'temperature': 0.0},
    )

    text = '\n'.join(b['text'] for b in response['output']['message']['content'] if 'text' in b).strip()
    data = parse_json(text)
    return {f: data.get(f) for f in fields}
