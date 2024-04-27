import json
from builtins import str
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup
from pandas import DataFrame

from utils.bitmex_utils import get_annualized_premium

st.set_page_config(page_title="Coin Market Cap Analysis", layout="wide", page_icon='📈')


@st.cache_data(ttl='60m')
def get_derivative_exchanges() -> DataFrame:
    page = BeautifulSoup(requests.get('https://coinmarketcap.com/rankings/exchanges/derivatives/').text)
    meta_data_json = json.loads(page.find('script', {'id': '__NEXT_DATA__'}).contents[0])
    derivative_exchanges_data = meta_data_json['props']['pageProps']['initialData']['exchanges']
    return pd.DataFrame(derivative_exchanges_data)


@st.cache_data(ttl='1m')
def get_derivative_exchange_perpetuals(exchange_slug: str) -> DataFrame:
    res = requests.get(
        f'https://api.coinmarketcap.com/data-api/v3/exchange/market-pairs/latest?slug={exchange_slug}&category=perpetual&start=1&limit=100').json()
    exchange_perpetuals = pd.DataFrame(res['data']['marketPairs'])
    return exchange_perpetuals


@st.cache_data(ttl='100m')
def get_all_exchanges_perpetuals(exchanges_df: DataFrame) -> DataFrame:
    df_to_concat = []
    for exchange_slug in exchanges_df['slug'].unique():
        df_to_concat.append(get_derivative_exchange_perpetuals(exchange_slug))
    return pd.concat(df_to_concat)


@st.cache_data(ttl='1m')
def get_derivative_exchange_futures(exchange_slug: str) -> DataFrame:
    try:
        res = requests.get(
            f'https://api.coinmarketcap.com/data-api/v3/exchange/market-pairs/latest?slug={exchange_slug}&category=futures&start=1&limit=100').json()
        exchange_futures = pd.DataFrame(res['data']['marketPairs'])
        exchange_futures['expiration'] = exchange_futures['expiration'].apply(lambda x: pd.to_datetime(x))
        return exchange_futures
    except:
        return pd.DataFrame()


@st.cache_data(ttl='100m')
def get_all_exchanges_futures(exchanges_df: DataFrame) -> DataFrame:
    df_to_concat = []
    for exchange_slug in exchanges_df['slug'].unique():
        df_to_concat.append(get_derivative_exchange_futures(exchange_slug))
    return pd.concat(df_to_concat)


derivatives_exchanges = get_derivative_exchanges()
st.title('Derivatives exchanges')
st.dataframe(derivatives_exchanges, hide_index=True)

selected_market_pair = st.selectbox('Market pair', ['BTC/USD', 'BTC/USDT'])
if selected_market_pair == 'BTC/USD':
    selected_market_pairs = ['BTC/USD', 'XBT/USD']
elif selected_market_pair == 'BTC/USDT':
    selected_market_pairs = ['BTC/USDT', 'XBT/USDT']

all_exchanges_perpetuals = get_all_exchanges_perpetuals(derivatives_exchanges)
all_exchanges_perpetuals = all_exchanges_perpetuals[~((all_exchanges_perpetuals['exchangeName'] == 'Kraken') & (all_exchanges_perpetuals['derivativeTickerId'].str.startswith('PI')))]

all_exchanges_futures = get_all_exchanges_futures(derivatives_exchanges)
all_exchanges_futures = all_exchanges_futures[all_exchanges_futures['marketPair'].isin(selected_market_pairs)]
all_exchanges_futures = all_exchanges_futures[all_exchanges_futures['price'] > 0]
all_exchanges_futures = all_exchanges_futures[all_exchanges_futures['expiration'] < pd.to_datetime(datetime(2026, 1, 1), utc=True)]
all_exchanges_futures = all_exchanges_futures[all_exchanges_futures['expiration'] >= pd.to_datetime(datetime.now(), utc=True)]

all_exchanges_futures = pd.merge(all_exchanges_futures, all_exchanges_perpetuals, left_on=['exchangeName', 'marketPair'], right_on=['exchangeName', 'marketPair'], how='left', suffixes=('', '_perpetual'))
all_exchanges_futures['Premium (%)'] = (all_exchanges_futures['price'] / all_exchanges_futures['price_perpetual'] - 1) * 100
all_exchanges_futures['Annualised premium (%)'] = all_exchanges_futures.apply(lambda x: get_annualized_premium(pd.to_datetime(datetime.now(), utc=True), x['expiration'], x['Premium (%)']), axis=1)

st.dataframe(all_exchanges_futures)

st.write('## Premium per maturity')
st.line_chart(all_exchanges_futures, x='expiration', y='Premium (%)', color='exchangeName')

st.write('## Annualised premium per maturity')
st.line_chart(all_exchanges_futures, x='expiration', y='Annualised premium (%)', color='exchangeName')





def get_exchange_name_from_slug(exchange_slug: str):
    return derivatives_exchanges[derivatives_exchanges['slug'] == exchange_slug].iloc[0]['name']


selected_exchange_slug = st.selectbox('Exchange', derivatives_exchanges['slug'].unique(),
                                      format_func=lambda x: get_exchange_name_from_slug(x))
exchange_futures = get_derivative_exchange_futures(selected_exchange_slug)
exchange_futures = exchange_futures[
        exchange_futures['marketPair'].isin(selected_market_pairs) & exchange_futures['price'] != 0]

exchange_perpetuals = get_derivative_exchange_perpetuals(selected_exchange_slug)

if len(exchange_futures):

    st.dataframe(exchange_futures, hide_index=True)

    selected_perpetual = exchange_perpetuals[exchange_perpetuals['marketPair'].isin(selected_market_pairs)].iloc[0]

    st.write('Perpetual price : ', selected_perpetual['price'], '$')

    st.line_chart(exchange_futures, x='expiration', y='quote')
else:
    st.warning('No data for this exchange')
