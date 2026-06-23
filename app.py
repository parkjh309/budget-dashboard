import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="2026 송도캠퍼스 예산 대시보드", layout="wide")
st.title("📊 2026년 팀별 예산 및 예실분석 대시보드")

try:
    # 1. 예산 데이터 원본 파일 로드
    budget_file = "「반출」확정) 송도캠퍼스 예산(QC,QA 포함)_251016.xlsx - 전체.csv"
    df_budget = pd.read_csv(budget_file)
    
    # 팀명 통일 (QC -> 품질관리6팀, QA -> 품질보증3팀)
    if '팀명' in df_budget.columns:
        df_budget['팀명'] = df_budget['팀명'].replace({'QC': '품질관리6팀', 'QA': '품질보증3팀'})

    # 2. 5월 집행 내역 원본 파일 로드 (노경비집계표)
    # 확장자가 csv인지 xlsx인지에 따라 아래 코드 중 하나만 작동합니다.
    try:
        df_actual = pd.read_csv("노경비집계표.csv")
    except:
        df_actual = pd.read_excel("노경비집계표.xlsx")

    if '팀명' in df_actual.columns:
        df_actual['팀명'] = df_actual['팀명'].replace({'QC': '품질관리6팀', 'QA': '품질보증3팀'})

    st.success("🎉 예산 데이터와 노경비집계표를 성공적으로 연결했습니다!")

    # 3. 사이드바 검색 필터
    st.sidebar.header("검색 조건")
    team_list = ["전체"] + list(df_budget['팀명'].unique())
    selected_team = st.sidebar.selectbox("팀 선택", team_list)

    # 4. 데이터 필터링 적용
    if selected_team != "전체":
        df_budget = df_budget[df_budget['팀명'] == selected_team]
        if '팀명' in df_actual.columns:
            df_actual = df_actual[df_actual['팀명'] == selected_team]

    # 5. 화면에 데이터 표 보여주기
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"### 💰 {selected_team} 예산 수립 내역")
        st.dataframe(df_budget, use_container_width=True)
    with col2:
        st.markdown(f"### 💸 {selected_team} 5월 집행 내역 (노경비집계표)")
        st.dataframe(df_actual, use_container_width=True)

except Exception as e:
    st.error(f"⚠️ 파일 연동 오류 발생: {e}")
    st.info("GitHub 저장소에 '「반출」확정) 송도캠퍼스 예산(QC,QA 포함)_251016.xlsx - 전체.csv' 파일과 '노경비집계표' 파일이 올바른 확장명으로 업로드되어 있는지 확인해 주세요.")
