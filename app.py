import streamlit as st

st.set_page_config(page_title="Financial analysis application", page_icon='📈')

st.title('Financial analysis application')

st.write('Hello, welcome on this application which is the result of my different quantitative researches.')

with st.container(border=True):
    st.title('Bitmex arbitrage application 📈')
    st.write('The purpose of this application is to provide an analysis over the different premium / discount in the futures contract avaliable on BitMex')
    st.write('The application propose then, when it is appropriate, an arbitrage stategy to profit from market inneficiencies 💲💲💲.')
    st.write('I am already using this application to open positions on the platform, either as a market maker or as a market maker.')
    st.write('I plan to expand this application to other exchanges as well to have a broader view of the market and identify cross-exchanges market inneficiencies.')
    st.write('⬇ Click on the button below to access the app ⬇')

    if st.button('Access Bitmex Arbitrage application 📈', type='primary', use_container_width=True):
        st.switch_page('pages/BitMex_Arbitrage.py')


with st.container(border=True):
    st.title('Bitget arbitrage application 📈')
    st.write('The purpose of this application is to provide an analysis over the different premium / discount in the futures contract avaliable on Bitget')
    st.write('The application propose then, when it is appropriate, an arbitrage stategy to profit from market inneficiencies 💲💲💲.')
    st.write('I am already using this application to open positions on the platform, either as a market maker or as a market maker.')
    st.write('I plan to expand this application to other exchanges as well to have a broader view of the market and identify cross-exchanges market inneficiencies.')
    st.write('⬇ Click on the button below to access the app ⬇')

    if st.button('Access Bitget Arbitrage application 📈', type='primary', use_container_width=True):
        st.switch_page('pages/Bitget_Arbitrage.py')
