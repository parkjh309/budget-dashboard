import streamlit as st
import pandas as pd
import os

st.title("📊 예산 대시보드 (최소 실행 모드)")

# 1. 파일 목록 확인
files = os.listdir('.')
st.write("현재 폴더 파일:", files)

# 2. 파일 읽기 (에러 방지용)
try:
    # 파일 중 '예산'과 '집행' 키워드가 들어간 첫 번째 파일만 읽기
    budget_file = next((f for f in files if "예산" in f and f.endswith('.csv')), None)
    actual_file = next((f for f in files if "집행" in f and f.endswith('.csv')), None)

    if budget_file:
        df_b = pd.read_csv(budget_file)
        st.write("### 예산 데이터 미리보기", df_b.head())
    
    if actual_file:
        df_a = pd.read_csv(actual_file)
        st.write("### 집행 데이터 미리보기", df_a.head())
        
    if not budget_file or not actual_file:
        st.warning("예산 또는 집행 CSV 파일을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")
