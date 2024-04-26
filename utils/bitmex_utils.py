import streamlit as st
import bitmex
from bravado.client import SwaggerClient

client_id = st.secrets.bitmex.bitmex_client_id
client_secret = st.secrets.bitmex.bitmex_client_secret

@st.cache_resource
def get_bitmex_client(api_key: str = client_id, api_secret: str = client_secret) -> SwaggerClient:
    return bitmex.bitmex(test=False, api_key=api_key, api_secret=api_secret)

def round_2(number: float):
    return round(number, 2)

def get_annualized_premium(start_date, end_date, period_premium):
    nb_days = (end_date - start_date).days
    if nb_days == 0:
        return 0
    else:
        return 365 / nb_days * period_premium

def get_annualized_premium_from_period(period_days, period_premium):
    if period_days == 0:
        return 0
    else:
        return 365 / period_days * period_premium