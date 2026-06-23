import streamlit as st
import pandas as pd

st.set_page_config(page_title="2026 송도캠퍼스 예산 대시보드", layout="wide")
st.title("📊 2026년 팀별 예산 및 예실분석 대시보드")

try:
    # 깃허브에 올린 짧은 이름의 파일들을 불러옵니다
    df_budget = pd.read_csv("budget.csv")
    df_actual = pd.read_csv("actual.csv")
    
    st.success("🎉 성공적으로 예산과 집행 데이터를 불러왔습니다!")
    
    st.markdown("### 💰 예산 수립 내역 원본")
    st.dataframe(df_budget)
    
    st.markdown("### 💸 5월 집행 내역 원본")
    st.dataframe(df_actual)
    
except Exception as e:
    st.error(f"데이터를 불러오는 중 문제가 발생했습니다: {e}")
