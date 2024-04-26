from datetime import datetime

import pandas as pd
import streamlit as st

from utils.bitmex_utils import get_bitmex_client, round_2, get_annualized_premium

st.set_page_config(page_title='BitMex Positions', layout='wide', page_icon='📈')

st.title('BitMex Positions 📈')

# Sidebar
st.sidebar.title('Configuration')

client = get_bitmex_client()

xbtquotes = pd.DataFrame(client.Quote.Quote_get(symbol=f'XBTUSD', reverse=True).result()[0])
xbt_last_quote = xbtquotes.iloc[0]
current_btc_price = (xbt_last_quote['bidPrice'] + xbt_last_quote['bidPrice']) / 2
st.write('### Current BTC price : ', round_2(current_btc_price), '$')

active_instruments = pd.DataFrame(client.Instrument.Instrument_getActive().result()[0])

positions = pd.DataFrame(client.Position.Position_get().result()[0])
positions = positions[positions['isOpen'] == True]
positions.loc[positions['currency'] == 'USDt', 'unrealised_pnl ($)'] = positions['unrealisedPnl'] / 1000000
positions.loc[positions['currency'] == 'XBt', 'unrealised_pnl ($)'] = positions['unrealisedPnl'] / 100000000 * current_btc_price

positions = pd.merge(positions, active_instruments, left_on='symbol', right_on='symbol', how='left', suffixes=('', '_instrument'))
positions_selected_columns = ['symbol', 'currency', 'underlying', 'quoteCurrency', 'currentQty', 'markPrice', 'homeNotional', 'foreignNotional', 'unrealisedPnl', 'avgEntryPrice', 'liquidationPrice', 'unrealised_pnl ($)', 'expiry', 'midPrice']
positions = positions[positions_selected_columns]

st.dataframe(positions, hide_index=True)
st.write('Total of all positions:', round_2(positions['foreignNotional'].abs().sum()), '$')
st.write('Current P/L:', round_2(positions['unrealised_pnl ($)'].sum()), '$')


st.write('## Wallet assets')
assets = pd.DataFrame(client.Wallet.Wallet_getAssetsConfig().result()[0])
assets = assets[assets['isMarginCurrency'] == True]

user_wallets = []
for currency in assets['currency'].unique():
    user_wallets.append(client.User.User_getWallet(currency=currency).result()[0])

user_assets = pd.merge(assets, pd.DataFrame(user_wallets), left_on='currency', right_on='currency')
user_assets = user_assets[['asset', 'currency', 'name', 'currencyType', 'amount']]


user_assets.loc[user_assets['asset'] == 'USDT', 'amount ($)'] = user_assets['amount'] / 1000000
user_assets.loc[user_assets['asset'] == 'XBT', 'amount ($)'] = user_assets['amount'] / 100000000 * current_btc_price

user_assets.loc[user_assets['asset'] == 'USDT', 'unrealised_pnl ($)'] = positions.loc[positions['currency'] == 'USDt', 'unrealised_pnl ($)'].sum()
user_assets.loc[user_assets['asset'] == 'XBT', 'unrealised_pnl ($)'] = positions.loc[positions['currency'] == 'XBt', 'unrealised_pnl ($)'].sum()

user_assets['total_balance ($)'] = user_assets['amount ($)'] + user_assets['unrealised_pnl ($)']

user_assets.loc[user_assets['asset'] == 'USDT', 'opened_positions ($)'] = positions.loc[positions['currency'] == 'USDt', 'foreignNotional'].abs().sum()
user_assets.loc[user_assets['asset'] == 'XBT', 'opened_positions ($)'] = positions.loc[positions['currency'] == 'XBt', 'foreignNotional'].abs().sum()

user_assets['leverage'] = user_assets['opened_positions ($)'] / user_assets['total_balance ($)']

total_account_balance = round_2(user_assets['amount ($)'].sum() + positions['unrealised_pnl ($)'].sum())
total_leverage = round_2(positions['foreignNotional'].abs().sum() / total_account_balance)
st.write('Total account Balance (', total_account_balance, '\$) = User assets (', round_2(user_assets['amount ($)'].sum()), '\$) + Unrealized PnL (', round_2(positions['unrealised_pnl ($)'].sum()), '\$)')
st.write('Current account leverage : ', total_leverage)
st.dataframe(user_assets, hide_index=True)

st.divider()

pandas_now_datetime = pd.to_datetime(datetime.now(), utc=True)

for quote_currency in positions['quoteCurrency'].unique():
    st.write('## ', quote_currency, ' Positions')
    currency_positions = positions[positions['quoteCurrency'] == quote_currency]
    reference_position = currency_positions[currency_positions['symbol'] == f'XBT{quote_currency}']
    st.write('Reference position')
    st.dataframe(reference_position, hide_index=True)
    reference_position_mid_price = reference_position.iloc[0]['midPrice']
    reference_position_currency = reference_position.iloc[0]['currency']
    futures_position = currency_positions[currency_positions['symbol'] != f'XBT{quote_currency}']
    futures_position['position_premium (%)'] = futures_position.apply(lambda x: ((x['midPrice'] / reference_position_mid_price) - 1) * 100, axis=1)
    futures_position['position_annualised_return (%)'] = futures_position.apply(lambda x: get_annualized_premium(pandas_now_datetime, x['expiry'], x['position_premium (%)']), axis=1)
    futures_position['future_return ($)'] = futures_position['position_premium (%)']/100 * futures_position['foreignNotional']
    futures_position['future_return_annualised ($)'] = futures_position['position_annualised_return (%)']/100 * futures_position['foreignNotional']


    st.write('Futures positions')
    st.dataframe(futures_position, hide_index=True)
    st.write('##### Current PnL : ', round_2(currency_positions['unrealised_pnl ($)'].sum()), '$')
    st.write('##### Upcoming PnL : ', round_2(futures_position['future_return ($)'].sum()), '\$ (', round_2(futures_position['future_return_annualised ($)'].sum()), '\$ annualised)')
    st.write('##### Annualised potential ROIC : ', round_2(futures_position['future_return_annualised ($)'].sum() / user_assets.loc[user_assets['currency'] == reference_position_currency, 'total_balance ($)'].sum() * 100), '%')


