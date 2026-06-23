import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="2026 송도캠퍼스 예실분석 대시보드", layout="wide")
st.title("📊 2026년 팀별 예실분석 대시보드")

try:
    # 1. 파일 찾기 (.xlsx 확장자만 찾습니다)
    all_files = os.listdir('.')
    budget_file = next((f for f in all_files if "예산" in f and f.endswith('.xlsx')), None)
    actual_file = next((f for f in all_files if "집행내역" in f and f.endswith('.xlsx')), None)

    if budget_file and actual_file:
        # 2. 예산 엑셀 파일 읽기 (모든 시트를 한 번에 읽고, 상단 2줄 쓰레기값은 건너뜁니다)
        budget_sheets = pd.read_excel(budget_file, sheet_name=None, skiprows=2)
        
        df_budget_list = []
        for sheet_name, df in budget_sheets.items():
            if not df.empty:
                df['시트명(팀명)'] = sheet_name  # 엑셀 하단 탭(시트) 이름을 팀명으로 씁니다
                df_budget_list.append(df)
        
        # 쪼개진 시트를 하나의 거대한 표로 합치기
        df_budget = pd.concat(df_budget_list, ignore_index=True)
        
        # 3. 집행내역 엑셀 파일 읽기
        df_actual = pd.read_excel(actual_file)

        st.success("🎉 여러 시트로 나뉜 예산 엑셀 파일과 집행내역을 완벽하게 불러왔습니다!")

        # 4. 사이드바 - 데이터 컬럼 설정
        st.sidebar.markdown("### ⚙️ 데이터 매칭 (관리자용)")
        st.sidebar.info("오류가 난다면 이곳에서 올바른 열(Column)을 선택해주세요.")
        
        b_cols = df_budget.columns.tolist()
        a_cols = df_actual.columns.tolist()

        # 예산 파일에서는 새로 만든 '시트명(팀명)'을 기본 팀명으로 씁니다
        team_col_b = st.sidebar.selectbox("💰 [예산] 파일의 '팀명' 열", ['시트명(팀명)'] + b_cols, index=0)
        budget_col = st.sidebar.selectbox("💰 [예산] 파일의 '금액' 열", b_cols, index=len(b_cols)-1)

        team_col_a = st.sidebar.selectbox("💸 [집행] 파일의 '팀명' 열", a_cols, index=0)
        actual_col = st.sidebar.selectbox("💸 [집행] 파일의 '금액' 열", a_cols, index=len(a_cols)-1)

        # 5. 데이터 병합 로직
        df_b_grouped = df_budget.groupby(team_col_b)[budget_col].sum().reset_index()
        df_a_grouped = df_actual.groupby(team_col_a)[actual_col].sum().reset_index()

        df_b_grouped.rename(columns={team_col_b: '팀명', budget_col: '예산금액'}, inplace=True)
        df_a_grouped.rename(columns={team_col_a: '팀명', actual_col: '집행금액'}, inplace=True)

        df_merged = pd.merge(df_b_grouped, df_a_grouped, on='팀명', how='outer').fillna(0)
        df_merged['집행률(%)'] = (df_merged['집행금액'] / df_merged['예산금액'] * 100).round(1)

        st.markdown("---")

        # 6. 대시보드 화면 구성
        team_list = ["전체보기"] + sorted(df_merged['팀명'].astype(str).unique().tolist())
        selected_team = st.selectbox("📌 조회할 팀(시트)을 선택하세요", team_list)

        if selected_team != "전체보기":
            df_display = df_merged[df_merged['팀명'].astype(str) == selected_team]
        else:
            df_display = df_merged

        # KPI 요약 지표
        st.markdown("### 💡 요약 지표")
        col1, col2, col3 = st.columns(3)
        col1.metric("총 수립 예산", f"{df_display['예산금액'].sum():,.0f} 원")
        col2.metric("누적 집행 금액", f"{df_display['집행금액'].sum():,.0f} 원")
        
        avg_rate = (df_display['집행금액'].sum() / df_display['예산금액'].sum() * 100) if df_display['예산금액'].sum() > 0 else 0
        col3.metric("평균 집행률", f"{avg_rate:.1f} %")

        # 시각화 차트
        st.markdown("### 📈 팀별 예산 대비 집행 현황")
        fig = px.bar(
            df_display, x='팀명', y=['예산금액', '집행금액'], barmode='group', text_auto='.2s',
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        st.plotly_chart(fig, use_container_width=True)

        # 상세 표
        st.markdown("### 📋 상세 데이터")
        st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))

    else:
        st.error("❌ 깃허브에서 .xlsx 확장자를 가진 '예산' 또는 '집행내역' 파일을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
