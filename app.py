import streamlit as st
import pandas as pd

st.set_page_config(page_title="2026 송도캠퍼스 예산 대시보드", layout="wide")
st.title("📊 2026년 팀별 예산 및 예실분석 대시보드")

try:
    # 1. 예산 데이터 원본 파일 로드
    budget_file = "「반출」확정) 송도캠퍼스 예산(QC,QA 포함)_251016.xlsx - 전체.csv"
    df_budget = pd.read_csv(budget_file)
    
    # 2. 5월 집행 내역 원본 파일 로드 (노경비집계표)
    try:
        df_actual = pd.read_csv("노경비집계표.csv")
    except:
        df_actual = pd.read_excel("노경비집계표.xlsx")

    st.success("🎉 파일을 성공적으로 불러왔습니다! 열 이름을 확인합니다.")

    # 3. 화면에 각 파일의 실제 열(Column) 이름들을 보여줍니다.
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 💰 예산 파일의 실제 열 이름 목록")
        st.write(list(df_budget.columns))
        st.markdown("#### 예산 데이터 상단 미리보기")
        st.dataframe(df_budget.head(3))
        
    with col2:
        st.markdown("### 💸 노경비집계표의 실제 열 이름 목록")
        st.write(list(df_actual.columns))
        st.markdown("#### 노경비집계표 상단 미리보기")
        st.dataframe(df_actual.head(3))

except Exception as e:
    st.error(f"⚠️ 파일 연동 오류 발생: {e}")
