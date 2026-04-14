# Card Data Extractor

A pilot application that automatically extracts structured fields from card images using Amazon Bedrock (Claude Sonnet
4.5). Supports insurance cards, personal IDs, and credit cards with a predefined set of fields per card type.

## Architecture

The system is a **Streamlit UI** that lets the user select a card type, upload the required image(s), and receive the
extracted fields as a structured table (and downloadable JSON). Uploaded images are resized client-side to stay within
Bedrock's vision limits, then sent to Claude Sonnet 4.5 via the Bedrock Converse API. The model returns a JSON object
keyed by the predefined fields for the selected card type.

Supported card types:

- **Insurance card** — 1 image (one side)
- **Personal ID** — 2 images (front + back)
- **Credit card** — 1 image (front)

## Setup

### 1. Create conda environment

```bash
conda create -n card_extractor python=3.10
conda activate card_extractor
```

### 2. Install dependencies

```bash
pip install -e .
```

### 3. Configure environment

Copy `.env_template` to `.env` in the project root and fill in the values:

```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=eu-central-1
```

The IAM principal needs `bedrock:InvokeModel` permission for `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` in
`eu-central-1`, and the model must be enabled under **Model access** in the Bedrock console.

## Usage

### Run the UI

```bash
streamlit run streamlit_app.py
```

### Deploy to Streamlit Cloud

Set the main file path to `streamlit_app.py` and add the AWS credentials under **Settings → Secrets** in TOML format:

```toml
AWS_ACCESS_KEY_ID = "your_access_key"
AWS_SECRET_ACCESS_KEY = "your_secret_key"
AWS_REGION = "eu-central-1"
```

## Extracted Fields

**Insurance card:** Insurance no., Country, Name, Given names, Date of birth, Personal identification number,
Identification number of the institution, Identification number of the card, Expiry date

**Personal ID:** Country, Document type, Document number, Surname, Given name(s), Date of birth, Name, Sex, Height,
Nationality, Date of Issue, Date of Expiry

**Credit card:** Card number, Cardholder name, Expiry date, Issuing bank

Fields that cannot be read from the image are returned as `null`.

## Output Schema

```json
{
  "Insurance no.": "1234567890",
  "Country": "DE",
  "Name": "Doe",
  "Given names": "Jane",
  "Date of birth": "01/01/1990",
  "Personal identification number": null,
  "Identification number of the institution": "109500969",
  "Identification number of the card": "80276883110000012501",
  "Expiry date": "12/2030"
}
```
