import pandas as pd
import streamlit as st

from utils.bitmex_utils import get_bitmex_client

st.set_page_config(page_title='BitMex Positions', layout='wide', page_icon='📈')

st.title('BitMex Positions 📈')

# Sidebar
st.sidebar.title('Configuration')

client = get_bitmex_client()

positions = pd.DataFrame(client.Position.Position_get().result()[0])
positions = positions[positions['isOpen'] == True]
st.dataframe(positions, hide_index=True)
st.write('Total of all positions:', positions['foreignNotional'].abs().sum(), '$')


st.write('## Wallet assets')
wallet_assets = pd.DataFrame(client.Wallet.Wallet_getAssetsConfig().result()[0])
wallet_assets = wallet_assets[wallet_assets['isMarginCurrency'] == True]
st.dataframe(wallet_assets, hide_index=True)
# st.write('Total of all wallet assets:', wallet_assets['total'].abs().sum(), '$')

for quote_currency in positions['quoteCurrency'].unique():
    st.write('## ', quote_currency, ' Positions')
    currency_positions = positions[positions['quoteCurrency'] == quote_currency]
    reference_position = currency_positions[currency_positions['symbol'] == f'XBT{quote_currency}']
    st.write('Reference position')
    st.dataframe(reference_position, hide_index=True)
    futures_position = currency_positions[currency_positions['symbol'] != f'XBT{quote_currency}']
    st.write('Futures positions')
    st.dataframe(futures_position, hide_index=True)
