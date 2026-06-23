import streamlit as st
import pandas as pd

st.set_page_config(page_title="2026 송도캠퍼스 예산 대시보드", layout="wide")
st.title("📊 2026년 팀별 예산 대시보드 (데이터 연결)")

# 1. 예산 파일 로드 (.xlsx 읽기)
budget_file = "「반출」확정) 송도캠퍼스 예산(QC,QA 포함)_251016.xlsx"
try:
    df_budget = pd.read_excel(budget_file)
    st.success(f"✔️ 예산 데이터 로드 성공: {budget_file}")
    st.dataframe(df_budget.head(3))
except Exception as e:
    st.error(f"❌ 예산 데이터 오류: {e}")

# 2. 노경비 파일 로드 (구형 .xls 읽기)
actual_file = "「반출」 노경비집계표 (26.06).xls"
try:
    df_actual = pd.read_excel(actual_file)
    st.success(f"✔️ 노경비 데이터 로드 성공: {actual_file}")
    st.dataframe(df_actual.head(3))
except Exception as e:
    st.error(f"❌ 노경비 데이터 오류: {e}")
