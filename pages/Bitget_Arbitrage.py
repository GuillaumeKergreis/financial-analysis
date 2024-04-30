from datetime import datetime

import pandas
import pandas as pd
import streamlit as st
from pybitget import Client

from utils.bitmex_utils import get_annualized_premium

st.set_page_config(page_title='Bitget Arbitrage', layout='wide', page_icon='📈')

api_key = st.secrets.bitget.bitget_client_id
api_secret = st.secrets.bitget.bitget_client_secret
api_passphrase = st.secrets.bitget.bitget_passphrase

client = Client(api_key, api_secret, passphrase=api_passphrase)
symbol_tickers = pd.DataFrame(client.mix_get_all_symbol_ticker('dmcbl')['data'])

for column in symbol_tickers.columns:
    symbol_tickers[column] = pandas.to_numeric(symbol_tickers[column], errors='ignore')

currency_pairs = ['BTCUSD', 'ETHUSD']
selected_currency_pair = st.selectbox('Currency Pair', currency_pairs)

symbol_tickers = symbol_tickers[symbol_tickers['symbol'].str.startswith(selected_currency_pair)]

symbol_tickers['Spread (%)'] = ((symbol_tickers['bestAsk'] / symbol_tickers['bestBid']) - 1) * 100
symbol_tickers['expiration'] = symbol_tickers['deliveryTime'].apply(lambda x: pd.to_datetime(x, unit='ms', utc=True))
symbol_tickers.loc[symbol_tickers['expiration'].isna(), 'expiration'] = pd.to_datetime(datetime.now(), utc=True)

product_type = 'DMCBL'

perpetual_contract_reference = symbol_tickers[symbol_tickers['symbol'] == f'{selected_currency_pair}_{product_type}']

perpetual_contract_reference_ask = perpetual_contract_reference.iloc[0]['bestAsk']
symbol_tickers['Premium (%)'] = symbol_tickers.apply(lambda x: ((x['bestBid'] / perpetual_contract_reference_ask) - 1) * 100, axis=1)
symbol_tickers['Annualised premium (%)'] = symbol_tickers.apply(lambda x: get_annualized_premium(pd.to_datetime(datetime.now(), utc=True), x['expiration'], x['Premium (%)']), axis=1)

st.write('Perpetual contract : ', perpetual_contract_reference_ask, '$')
st.dataframe(perpetual_contract_reference, hide_index=True)

future_contracts = symbol_tickers[symbol_tickers['symbol'] != f'{selected_currency_pair}_{product_type}']

st.write('Perpetual contract :')
st.dataframe(future_contracts, hide_index=True)

st.write('Premium (%) per maturity')
st.line_chart(symbol_tickers, x='expiration', y='Premium (%)')

st.write('Annualised premium (%) per maturity')
st.line_chart(symbol_tickers, x='expiration', y='Annualised premium (%)')
