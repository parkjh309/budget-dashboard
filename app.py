import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="송도캠퍼스 파이낸셜 네비게이터", layout="wide")
st.title("📊 송도캠퍼스 파이낸셜 네비게이터 (안전 모드)")

try:
    st.write("🔍 깃허브에 있는 파일들을 확인하는 중입니다...")
    all_files = os.listdir('.')
    
    budget_file = next((f for f in all_files if "예산" in f and (f.endswith('.xlsx') or f.endswith('.csv'))), None)
    actual_file = next((f for f in all_files if "집행" in f and (f.endswith('.xlsx') or f.endswith('.csv'))), None)

    if not budget_file or not actual_file:
        st.error("❌ '예산' 또는 '집행' 파일이 깃허브에 없습니다. 위 파일 목록을 확인해주세요.")
        st.write("현재 폴더의 파일 목록:", all_files)
    else:
        st.success(f"✅ 파일 찾기 성공! (예산: {budget_file} / 집행: {actual_file})")

        # 데이터 읽기 시도
        st.write("⏳ 엑셀 데이터를 여는 중입니다...")
        if budget_file.endswith('.csv'):
            df_budget = pd.read_csv(budget_file)
        else:
            df_budget = pd.read_excel(budget_file)

        if actual_file.endswith('.csv'):
            df_actual = pd.read_csv(actual_file)
        else:
            df_actual = pd.read_excel(actual_file)

        st.success("✅ 데이터 열기 성공! 아래에 원본 데이터를 보여줍니다.")

        st.subheader("📋 예산 파일 원본 (첫 5줄)")
        st.dataframe(df_budget.head())

        st.subheader("📋 집행 내역 파일 원본 (첫 5줄)")
        st.dataframe(df_actual.head())

except Exception as e:
    st.error(f"⚠️ 치명적인 오류가 발생했습니다: {e}")
