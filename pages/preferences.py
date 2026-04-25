import streamlit as st

st.title('선호도 설정')

# 같은 세션 상태에 접근
preferences = st.multiselect(
    '관심 분야를 선택하세요', 
    ['데이터 과학', '웹 개발', '모바일 앱', '게임 개발'],
    st.session_state.user_data.get('preferences', [])
)

st.session_state.user_data['preferences'] = preferences