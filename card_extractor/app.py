import json

import streamlit as st

from card_extractor.config import APP_PASSWORD
from card_extractor.extractor import CARD_FIELDS, EXPECTED_IMAGE_COUNT, extract_fields

IMAGE_LABELS = {
    'insurance': ['Insurance card'],
    'personal_id': ['ID front', 'ID back'],
    'credit_card': ['Credit card front'],
}

CARD_TYPE_LABELS = {
    'insurance': 'Insurance card',
    'personal_id': 'Personal ID',
    'credit_card': 'Credit card',
}

ACCEPTED_TYPES = ['jpg', 'jpeg', 'png', 'gif', 'webp']


def check_password() -> bool:
    if st.session_state.get('authenticated'):
        return True

    st.title('🔒 Card Field Extractor')
    pwd = st.text_input('Password', type='password')
    if st.button('Sign in'):
        if APP_PASSWORD and pwd == APP_PASSWORD:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error('Incorrect password.')
    return False


def main() -> None:
    st.set_page_config(page_title='Card Field Extractor', page_icon='🪪', layout='centered')

    if not check_password():
        return

    st.title('🪪 Card Field Extractor')

    card_type = st.selectbox('Card type', options=list(CARD_FIELDS), format_func=lambda k: CARD_TYPE_LABELS[k])

    expected = EXPECTED_IMAGE_COUNT[card_type]
    labels = IMAGE_LABELS[card_type]

    st.subheader(f'Upload image{"s" if expected > 1 else ""}')
    uploaded = []
    cols = st.columns(expected)
    for i in range(expected):
        with cols[i]:
            f = st.file_uploader(labels[i], type=ACCEPTED_TYPES, key=f'file_{card_type}_{i}')
            if f is not None:
                st.image(f, caption=labels[i], width='stretch')
                uploaded.append(f.getvalue())

    with st.expander('Fields that will be extracted'):
        st.write(CARD_FIELDS[card_type])

    ready = len(uploaded) == expected
    if st.button('Extract fields', type='primary', disabled=not ready):
        with st.spinner('Extracting...'):
            try:
                result = extract_fields(card_type, uploaded)
            except Exception as e:
                st.error(f'Extraction failed: {e}')
                return

        st.success('Done')
        st.subheader('Extracted fields')
        st.table([{'Field': k, 'Value': v if v is not None else '—'} for k, v in result.items()])

        st.download_button(
            'Download JSON',
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name=f'{card_type}_extracted.json',
            mime='application/json',
        )


if __name__ == '__main__':
    main()
