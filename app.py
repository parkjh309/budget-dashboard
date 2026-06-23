import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="2026 송도캠퍼스 예실분석 대시보드", layout="wide")
st.title("📊 2026년 팀별 예실분석 대시보드")

# 1. 파일 자동 탐색
all_files = os.listdir('.')
budget_file = next((f for f in all_files if "예산" in f), None)
actual_file = next((f for f in all_files if "집행내역" in f), None)

if budget_file and actual_file:
    try:
        # 2. 데이터 로드
        df_budget = pd.read_excel(budget_file)
        df_actual = pd.read_excel(actual_file)

        # 3. 사이드바 - 데이터 컬럼 매핑 (에러 방지용)
        st.sidebar.markdown("### ⚙️ 데이터 설정 (관리자용)")
        st.sidebar.info("엑셀 파일의 실제 제목줄 이름에 맞춰 아래 항목을 선택해주세요.")

        b_cols = df_budget.columns.tolist()
        a_cols = df_actual.columns.tolist()

        team_col_b = st.sidebar.selectbox("💰 [예산] 파일의 '팀명' 열", b_cols, index=0)
        budget_col = st.sidebar.selectbox("💰 [예산] 파일의 '금액' 열", b_cols, index=len(b_cols)-1)

        team_col_a = st.sidebar.selectbox("💸 [집행] 파일의 '팀명' 열", a_cols, index=0)
        actual_col = st.sidebar.selectbox("💸 [집행] 파일의 '금액' 열", a_cols, index=len(a_cols)-1)

        # 4. 데이터 전처리 및 병합
        # 팀별로 그룹화하여 합계 계산
        df_b_grouped = df_budget.groupby(team_col_b)[budget_col].sum().reset_index()
        df_a_grouped = df_actual.groupby(team_col_a)[actual_col].sum().reset_index()

        # 열 이름을 알아보기 쉽게 통일
        df_b_grouped.rename(columns={team_col_b: '팀명', budget_col: '예산금액'}, inplace=True)
        df_a_grouped.rename(columns={team_col_a: '팀명', actual_col: '집행금액'}, inplace=True)

        # 두 데이터 합치기
        df_merged = pd.merge(df_b_grouped, df_a_grouped, on='팀명', how='outer').fillna(0)
        df_merged['집행률(%)'] = (df_merged['집행금액'] / df_merged['예산금액'] * 100).round(1)

        st.markdown("---")

        # 5. 화면 UI (팀 검색 필터)
        team_list = ["전체보기"] + sorted(df_merged['팀명'].unique().tolist())
        selected_team = st.selectbox("📌 조회할 팀을 선택하세요", team_list)

        # 선택된 팀 데이터만 필터링
        if selected_team != "전체보기":
            df_display = df_merged[df_merged['팀명'] == selected_team]
        else:
            df_display = df_merged

        # 6. 핵심 지표 (KPI)
        st.markdown("### 💡 요약 지표")
        total_budget = df_display['예산금액'].sum()
        total_actual = df_display['집행금액'].sum()
        avg_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("총 수립 예산", f"{total_budget:,.0f} 원")
        col2.metric("누적 집행 금액", f"{total_actual:,.0f} 원")
        col3.metric("평균 집행률", f"{avg_rate:.1f} %")

        # 7. 예실분석 차트 (Plotly)
        st.markdown("### 📈 팀별 예산 대비 집행 현황")
        fig = px.bar(
            df_display,
            x='팀명',
            y=['예산금액', '집행금액'],
            barmode='group',
            text_auto='.2s',
            color_discrete_sequence=['#1f77b4', '#ff7f0e'] # 파란색(예산), 주황색(집행)
        )
        fig.update_layout(xaxis_title="팀명", yaxis_title="금액 (원)", legend_title="구분")
        st.plotly_chart(fig, use_container_width=True)

        # 8. 상세 데이터 표
        st.markdown("### 📋 상세 데이터")
        st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))

    except Exception as e:
        st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
        st.info("왼쪽 사이드바(숨겨져 있다면 〉화살표 클릭)에서 올바른 열(Column) 이름이 선택되었는지 확인해주세요.")
else:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. 파일명이 깃허브에 잘 올라갔는지 확인해주세요.")
