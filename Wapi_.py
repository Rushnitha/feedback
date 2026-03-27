import requests
import streamlit as st

city = st.text_input("Enter the city name:")
api_key="b967520bdba1ac5f398c0821adf08f19"
if city:
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}"
    response = requests.get(url)
    data = response.json()
    st.write(data)
    