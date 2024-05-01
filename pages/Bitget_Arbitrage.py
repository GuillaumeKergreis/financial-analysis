from datetime import datetime

import pandas
import pandas as pd
import streamlit as st
from pandas import DataFrame
from pybitget import Client

from utils.bitmex_utils import get_annualized_premium, get_annualized_premium_from_period

st.set_page_config(page_title='Bitget Arbitrage', layout='wide', page_icon='📈')

api_key = st.secrets.bitget.bitget_client_id
api_secret = st.secrets.bitget.bitget_client_secret
api_passphrase = st.secrets.bitget.bitget_passphrase


@st.cache_resource
def get_bitget_client():
    return Client(api_key, api_secret, passphrase=api_passphrase)


client = get_bitget_client()

symbol_tickers = pd.DataFrame(client.mix_get_all_symbol_ticker('dmcbl')['data'])

for column in symbol_tickers.columns:
    symbol_tickers[column] = pandas.to_numeric(symbol_tickers[column], errors='ignore')

currency_pairs = ['BTCUSD', 'ETHUSD']
selected_currency_pair = st.selectbox('Currency Pair', currency_pairs)

symbol_tickers = symbol_tickers[symbol_tickers['symbol'].str.startswith(selected_currency_pair)]

symbol_tickers['Spread (%)'] = ((symbol_tickers['bestAsk'] / symbol_tickers['bestBid']) - 1) * 100
symbol_tickers['Expiration'] = symbol_tickers['deliveryTime'].apply(lambda x: pd.to_datetime(x, unit='ms', utc=True))
symbol_tickers.loc[symbol_tickers['Expiration'].isna(), 'Expiration'] = pd.to_datetime(datetime.now(), utc=True)

product_type = 'DMCBL'

perpetual_contract_symbol = f'{selected_currency_pair}_{product_type}'
perpetual_contract_reference = symbol_tickers[symbol_tickers['symbol'] == perpetual_contract_symbol]

perpetual_contract_reference_ask = perpetual_contract_reference.iloc[0]['bestAsk']
symbol_tickers['Premium (%)'] = symbol_tickers.apply(
    lambda x: ((x['bestBid'] / perpetual_contract_reference_ask) - 1) * 100, axis=1)
symbol_tickers['Annualised premium (%)'] = symbol_tickers.apply(
    lambda x: get_annualized_premium(pd.to_datetime(datetime.now(), utc=True), x['Expiration'], x['Premium (%)']),
    axis=1)

st.write('Perpetual contract : ', perpetual_contract_reference_ask, '$')
st.dataframe(perpetual_contract_reference, hide_index=True)

future_contracts = symbol_tickers[symbol_tickers['symbol'] != f'{selected_currency_pair}_{product_type}']

st.write('Perpetual contract :')
st.dataframe(future_contracts, hide_index=True)

st.write('Premium (%) per maturity')
st.line_chart(symbol_tickers, x='Expiration', y='Premium (%)')

st.write('Annualised premium (%) per maturity')
st.line_chart(symbol_tickers, x='Expiration', y='Annualised premium (%)')

granularities = [
    '1m',
    '5m',
    '15m',
    '30m',
    '1H',
    '4H',
    '6H',
    '12H',
    '1D',
]

granularity = st.sidebar.selectbox('Granularity', granularities)


def get_quotes(symbol: str, _granularity: str) -> DataFrame:
    quotes = client.mix_get_candles(symbol=symbol,
                                    granularity=_granularity,
                                    limit=1000,
                                    startTime=int(datetime(2020, 1, 1).timestamp() * 1000),
                                    endTime=int(datetime.now().timestamp() * 1000))
    quotes = pd.DataFrame(quotes,
                          columns=['Timestamp', 'Open', 'High', 'Low', 'Close',
                                   'Base currency volume', 'Quote currency volume'])
    for column in quotes.columns:
        quotes[column] = pandas.to_numeric(quotes[column], errors='ignore')

    quotes['Date'] = pd.to_datetime(quotes['Timestamp'], unit='ms')

    return quotes


perpetual_contract_quotes = get_quotes(perpetual_contract_symbol, granularity)

# st.dataframe(perpetual_contract_quotes, hide_index=True)

for i, future_contract in future_contracts.iterrows():
    contract_symbol = future_contract['symbol']

    st.write('# ', contract_symbol)

    quotes = get_quotes(contract_symbol, granularity)

    days_till_expiration = (future_contract['Expiration'] - pd.to_datetime(datetime.now(), utc=True)).days

    joigned_quotes = pd.merge(quotes, perpetual_contract_quotes, left_on='Date', right_on='Date', how='left',
                              suffixes=('', '_PERPETUAL'))
    joigned_quotes['Premium'] = (joigned_quotes['Close'] - joigned_quotes['Close_PERPETUAL'])
    joigned_quotes['Premium (%)'] = joigned_quotes['Premium'] / joigned_quotes['Close_PERPETUAL'] * 100
    joigned_quotes['Annualized premium (%)'] = joigned_quotes.apply(
        lambda x: get_annualized_premium(pd.to_datetime(datetime.now(), utc=True), future_contract['Expiration'],
                                         x['Premium (%)']), axis=1)

    current_quote = joigned_quotes.iloc[-1]
    current_spread_percent = future_contract['Spread (%)']
    current_premium_percent = future_contract['Premium (%)']
    current_annualized_potential_return = round(
        get_annualized_premium_from_period(days_till_expiration, current_quote['Premium (%)']), 2)

    st.write('Maturity : ', datetime.fromisoformat(str(future_contract['Expiration'])).strftime("%B %d, %Y"))
    st.write('Current premiun (Compared to BTC) : ', round(current_premium_percent, 2), '% (',
             current_annualized_potential_return, '% annualized)')
    st.write('Current spread : ', round(current_spread_percent, 2), '%')
    st.line_chart(joigned_quotes, x='Date', y=['Premium (%)', 'Annualized premium (%)'])
