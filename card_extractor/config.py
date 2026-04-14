import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, '.env'))


def get_secret(key: str) -> str | None:
    value = os.getenv(key)
    if value:
        return value

    try:
        import streamlit as st
        return st.secrets.get(key)
    except Exception as e:
        print(e)
        return None


AWS_ACCESS_KEY_ID = get_secret('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = get_secret('AWS_SECRET_ACCESS_KEY')
AWS_REGION = get_secret('AWS_REGION')

APP_PASSWORD = get_secret('APP_PASSWORD')

MODEL_ID = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'
