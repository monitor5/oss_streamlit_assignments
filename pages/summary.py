import streamlit as st

st.title('사용자 정보 요약')

# 모든 데이터에 접근
st.write(f"이름: {st.session_state.user_data['name']}")
st.write(f"나이: {st.session_state.user_data['age']}")
st.write("선호도:")
for pref in st.session_state.user_data['preferences']:
    st.write(f"- {pref}")


