import streamlit as st
import bitmex
from bravado.client import SwaggerClient

client_id = st.secrets.bitmex.bitmex_client_id
client_secret = st.secrets.bitmex.bitmex_client_secret

@st.cache_resource
def get_bitmex_client(api_key: str = client_id, api_secret: str = client_secret) -> SwaggerClient:
    return bitmex.bitmex(test=False, api_key=api_key, api_secret=api_secret)