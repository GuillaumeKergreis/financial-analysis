import datetime
import math

import pandas as pd
import streamlit as st
from bravado.client import SwaggerClient
from pandas import DataFrame

from utils.bitmex_utils import get_bitmex_client

st.set_page_config(page_title='BitMex Arbitrage', layout='wide', page_icon='📈')

st.title('BitMex Arbitrage 📈')

# Sidebar
st.sidebar.title('Configuration')

contract_currency = st.sidebar.selectbox(label='Currency contract', options=['USD', 'USDT'])
time_interval = st.sidebar.selectbox(label='Time interval', options=['1m','5m','1h','1d'])
risk_free_rate = st.sidebar.number_input(label='Risk free rate (%)', value=5.3, min_value=0.0, max_value=100.0, step=0.1)
initial_investment = st.sidebar.number_input(label='Initial investment ($)', value=1000, min_value=0)
leverage = st.sidebar.number_input(label='Leverage', value=2, min_value=0)

nominal_investment = initial_investment * leverage
st.sidebar.write('Nominal investment : ', nominal_investment, '$')

client = get_bitmex_client()

def get_active_instruments(client: SwaggerClient) -> DataFrame:
    active_instruments, _ = client.Instrument.Instrument_getActive().result()
    return pd.DataFrame(active_instruments)


# instruments = client.Instrument.Instrument_get(filter=json.dumps({'symbol': 'BTC'})).result()
active_instruments = get_active_instruments(client)

current_btc_price = active_instruments[active_instruments['symbol'] == f'XBT{contract_currency}'].iloc[0]['midPrice']

st.write('Current BTC value (perpetual contract) : ', current_btc_price, '$')

current_date_time = datetime.datetime.now()

active_instruments = active_instruments[active_instruments['typ'].isin(['FFWCSX', 'FFWCSF', 'FFCCSX'])]
active_instruments = active_instruments[active_instruments['rootSymbol'] == 'XBT']
active_instruments = active_instruments[active_instruments['state'] == 'Open']
active_instruments = active_instruments[active_instruments['quoteCurrency'] == contract_currency]
active_instruments = active_instruments[['symbol', 'typ', 'expiry', 'midPrice', 'bidPrice', 'askPrice']]
active_instruments['spread'] = active_instruments['askPrice'] - active_instruments['bidPrice']
active_instruments['spread (%)'] = ((active_instruments['askPrice'] / active_instruments['bidPrice']) - 1) * 100

active_instruments['current_premium'] = active_instruments['midPrice'] - current_btc_price
active_instruments['current_premium (%)'] = ((active_instruments['midPrice'] - current_btc_price) / current_btc_price) * 100
active_instruments.loc[active_instruments['expiry'].isna(), 'expiry'] = pd.to_datetime(current_date_time, utc=True)
active_instruments['expiry'] = pd.to_datetime(active_instruments['expiry'], utc=True)

active_instruments['expected_value'] = active_instruments['expiry'].apply(lambda x: current_btc_price * math.exp((risk_free_rate/100) * ((x - pd.to_datetime(current_date_time, utc=True)).days / 365)))
active_instruments['expected_premium'] = active_instruments['expected_value'] - current_btc_price
active_instruments['expected_premium (%)'] = ((active_instruments['expected_value'] - current_btc_price) / current_btc_price) * 100

def get_discount_factor(yearly_rate: float, start_date, end_date):
    number_of_days = (end_date - start_date).days
    number_of_years = number_of_days / 365
    discount_factor = math.exp(yearly_rate / 100 * number_of_years)
    return discount_factor
def discount(amount: float, yearly_rate: float, start_date, end_date) -> float:
    discount_factor = get_discount_factor(yearly_rate, start_date, end_date)
    return amount / discount_factor


def profit_per_day(amount: float, start_date, end_date) -> float:
    number_of_days = (end_date - start_date).days
    if number_of_days == 0:
        return 0
    else:
        return amount / number_of_days


active_instruments['excess return (%)'] = active_instruments['current_premium (%)'] - active_instruments['expected_premium (%)']
active_instruments['excess return - spread (%)'] = active_instruments['current_premium (%)'] - active_instruments['expected_premium (%)'] - active_instruments['spread (%)']
active_instruments['potential profit'] = (initial_investment * (active_instruments['current_premium (%)'] / 100)) + ((nominal_investment - initial_investment) * (active_instruments['excess return - spread (%)'] / 100))
active_instruments['profit/day'] = active_instruments.apply(lambda x : profit_per_day(x['potential profit'], pd.to_datetime(current_date_time, utc=True), x['expiry']), axis=1)
active_instruments['discounted profit'] = active_instruments.apply(lambda x: discount(x['potential profit'], risk_free_rate, pd.to_datetime(current_date_time, utc=True), x['expiry']), axis=1)



# active_instruments['potential profit/BTC'] / (1 + active_instruments['expected_premium (%)']/ 100)

st.write('# BTC Contract summary')
st.dataframe(active_instruments, hide_index=True)

st.write('# Price per maturity')
st.line_chart(active_instruments, x='expiry', y=['midPrice', 'expected_value'])

st.write('# Premium (%) per maturity')
st.line_chart(active_instruments, x='expiry', y=['current_premium (%)', 'expected_premium (%)'], )

xbtquotes = pd.DataFrame(client.Quote.Quote_getBucketed(symbol=f'XBT{contract_currency}', binSize=time_interval, partial=True, reverse=True, endTime=datetime.datetime.now(), count=1000).result()[0]).sort_values(by='timestamp', ascending=True)
st.dataframe(xbtquotes, hide_index=True)

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


for i, instrument in active_instruments[active_instruments['typ'] == 'FFCCSX'].iterrows():
    instrument_symbol = instrument['symbol']
    st.write('# ', instrument_symbol)
    quotes: DataFrame = pd.DataFrame(client.Quote.Quote_getBucketed(symbol=instrument['symbol'], binSize=time_interval, partial=True, reverse=True,
                                                  endTime=datetime.datetime.now(),
                                                  count=1000).result()[0]).sort_values(by='timestamp', ascending=True)

    joigned_quotes = pd.merge(quotes, xbtquotes, left_on='timestamp', right_on='timestamp', how='left', suffixes=('', '_XBT'))
    joigned_quotes['premium'] = ((joigned_quotes['askPrice'] + joigned_quotes['bidPrice']) / 2) - ((joigned_quotes['askPrice_XBT'] + joigned_quotes['bidPrice_XBT']) / 2)
    joigned_quotes['premium (%)'] = joigned_quotes['premium'] / ((joigned_quotes['askPrice_XBT'] + joigned_quotes['bidPrice_XBT']) / 2) * 100
    joigned_quotes['annualized premium (%)'] = joigned_quotes.apply(lambda x: get_annualized_premium(x['timestamp'], instrument['expiry'], x['premium (%)']) , axis=1)
    joigned_quotes['expected_premium (%)'] = joigned_quotes.apply(lambda x: (get_discount_factor(risk_free_rate, x['timestamp'], instrument['expiry']) - 1) * 100, axis=1)
    # joigned_quotes['excess return (%)'] = joigned_quotes['premium (%)'] - joigned_quotes['expected_premium (%)']

    days_till_expiration = (instrument['expiry'] - pd.to_datetime(current_date_time, utc=True)).days

    current_quote = joigned_quotes.iloc[-1]
    current_spread = current_quote['askPrice'] - current_quote['bidPrice']
    current_spread_percent = (current_spread / current_quote['bidPrice']) * 100
    current_premium_percent = current_quote['premium (%)']
    current_annualized_potential_return = round(get_annualized_premium_from_period(days_till_expiration, current_quote['premium (%)']), 2)
    expected_premium_percent = current_quote['expected_premium (%)']

    st.write('Maturity : ', datetime.datetime.fromisoformat(str(instrument['expiry'])).strftime("%B %d, %Y"))
    st.write('Current premiun (Compared to BTC) : ', round(current_premium_percent, 2), '% (', current_annualized_potential_return, '% annualized)')
    st.write('Current premiun (Compared to risk free rate) : ', round(current_premium_percent - expected_premium_percent, 2), '%')
    st.write('Current spread : ', round(current_spread_percent, 2), '%')
    st.line_chart(joigned_quotes, x='timestamp', y=['premium (%)', 'expected_premium (%)', 'annualized premium (%)'])


    if current_spread_percent > 1:
        st.write('=> Spread is high currently, it\'s time to provide liquidity !')
        st.line_chart(joigned_quotes, x='timestamp', y=['bidPrice', 'askPrice', 'bidPrice_XBT'])
        st.write('Potential market making arbitrage possible : ')
        st.write('- Place an bid (buy) limit order on ', instrument_symbol, ' at ', current_quote['bidPrice'], '. If someone take it, sell the XBTUSD at market (', current_btc_price,') and benefit of a', round(((current_btc_price / current_quote['bidPrice']) - 1) * 100, 2), '% return in', days_till_expiration, 'days. Equivalent to a ', round(get_annualized_premium_from_period(days_till_expiration, (((current_btc_price / current_quote['bidPrice']) - 1) * 100)), 2), '% annualised return.')
        st.write('- Place an ask (sell) limit order on ', instrument_symbol, ' at ', current_quote['askPrice'], '. If someone take it, buy the XBTUSD at market (', current_btc_price,') and benefit of a', round(((current_quote['askPrice'] / current_btc_price) - 1) * 100, 2), '% return in', days_till_expiration, 'days. Equivalent to a ', round(get_annualized_premium_from_period(days_till_expiration, (((current_quote['askPrice'] / current_btc_price) - 1) * 100)), 2), '% annualised return.')

    if current_annualized_potential_return > risk_free_rate:
        st.write('=> Annualized premium compared to risk free rate is currently high and spread is low !')
        st.write('- Borrow money at the risk free rate (', risk_free_rate, '% annual), use the borrowed money to buy XBTUSD at market (', current_btc_price,
                 ') and sell ', instrument_symbol, ' with a market order at bid price (', current_quote['bidPrice'], ').'
                 'After ', days_till_expiration, ' days, close both positions, return the borrowed money and the due interest rates (', round(expected_premium_percent, 2), '%) and benefit from a net ', round(current_premium_percent - expected_premium_percent, 2), '% excess profit on your operation. ',
                 'Equivalent to a ', round(get_annualized_premium_from_period(days_till_expiration, (current_premium_percent - expected_premium_percent)), 2), '% net excess annualised return, or '
                 'to a ', round(get_annualized_premium_from_period(days_till_expiration, current_premium_percent), 2), '% gross annualised return.')


