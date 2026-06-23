import streamlit as st
import pandas as pd

st.title("📊 2026년 팀별 예산 대시보드 테스트")
st.write("대시보드 웹 링크가 성공적으로 연결되었습니다!")

# 데이터가 잘 올라갔는지 확인하는 표
try:
    df_budget = pd.read_csv("budget.csv")
    st.write("✔️ 예산 데이터 미리보기")
    st.dataframe(df_budget.head())
except:
    st.info("데이터를 불러오는 중이거나 파일 이름이 다릅니다.")
