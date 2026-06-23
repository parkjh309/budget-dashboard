import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="2026 송도캠퍼스 예산 대시보드", layout="wide")
st.title("📊 2026년 팀별 예산 대시보드 (파일 스캔 모드)")

# 1. 깃허브 저장소에 있는 실제 파일 목록을 화면에 그대로 출력합니다.
st.markdown("### 🔍 현재 GitHub 저장소에 존재하는 실제 파일 이름 목록")
all_files = os.listdir('.')
st.write(all_files)

st.divider()

st.markdown("### ⚙️ 데이터 로드 상태 파악")

# 2. 예산 데이터 로드 시도
budget_file = "「반출」확정) 송도캠퍼스 예산(QC,QA 포함)_251016.xlsx - 전체.csv"
if budget_file in all_files:
    try:
        df_budget = pd.read_csv(budget_file)
        st.success(f"✔️ 예산 파일을 성공적으로 불러왔습니다: {budget_file}")
        st.dataframe(df_budget.head(3))
    except Exception as e:
        st.error(f"❌ 예산 파일을 읽는 중 오류 발생: {e}")
else:
    st.error(f"❌ 코드에 적힌 예산 파일명이 저장소의 파일명과 일치하지 않습니다. (적힌 이름: {budget_file})")

st.markdown("---")

# 3. 집행 내역 파일 자동 매칭 로드 시도
# 파일 목록 중 '노경비' 또는 '집계표'라는 단어가 포함된 파일을 자동으로 찾습니다.
actual_file = None
for f in all_files:
    if "노경비" in f or "집계표" in f:
        actual_file = f
        break

if actual_file:
    st.success(f"✔️ 집행 내역(노경비) 파일 발견: [{actual_file}]")
    try:
        # 확장자에 맞게 자동으로 읽어옵니다.
        if actual_file.endswith('.xlsx'):
            df_actual = pd.read_excel(actual_file)
        else:
            df_actual = pd.read_csv(actual_file)
        st.success("🎉 집행 내역 데이터를 성공적으로 불러왔습니다!")
        st.dataframe(df_actual.head(3))
    except Exception as e:
        st.error(f"❌ 파일을 찾았으나 읽어오는 중 오류가 발생했습니다: {e}")
else:
    st.error("❌ 저장소 파일 목록에서 '노경비' 또는 '집계표'가 포함된 파일을 찾을 수 없습니다.")
    
