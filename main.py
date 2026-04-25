
import streamlit as st
import pandas as pd
import numpy as np
import time

# import 생략

st.header('3. 캐싱 매개변수 활용')


# TTL(Time To Live) 설정
@st.cache_data(ttl=60*60)  # 1시간 후 캐시 만료
def load_updated_data():
    # 주기적으로 업데이트되는 데이터 로드
    return pd.read_csv("data.csv")

# 최대 100개의 서로 다른 user_id 값에 대한 결과를 캐시할 수 있다는 의미
@st.cache_data(max_entries=100)
def process_user_data(user_id):
    # 사용자별 데이터 처리
    return data[data['user_id'] == user_id]

@st.cache_data(show_spinner="데이터 필터링 중...")
def filter_data(start_date, end_date, category):
    # 필터링 코드
    time.sleep(1.5)  # 처리 시간 시뮬레이션
    filtered = data[(data['date'] >= start_date) & 
                   (data['date'] <= end_date) & 
                   (data['category'] == category)]
    return filtered

@st.cache_data(persist=True)
def load_large_dataset():
    # 큰 데이터셋 로딩 코드
    st.write("대용량 데이터셋 로딩 중...")
    time.sleep(3)
    return pd.read_csv("large_dataset.csv")

