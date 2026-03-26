import streamlit as st
st.header("__FEEDBACK__")
st.write("MRECW STUDENT FEEDBACK")
st.text_input("student name:")
st.text_input("roll number:")
st.text_input("year of study:")
st.text_input("Branch:")

st.radio("section", ["A", "B", "C","D","E"])
st.text_input("faculty name:")
st.sidebar.selectbox("select the subject", ["DM", "DBMA", "DAA", "BEFA","SFDS"])
st.text_area("feedback")
num=st.selectbox("select the rating", [1, 2, 3, 4, 5]) 
