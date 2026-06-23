import streamlit as st
import pandas as pd
import plotly.express as px
import glob

st.set_page_config(page_title="2026 송도캠퍼스 예실분석 대시보드", layout="wide")
st.title("📊 2026년 팀별 예실분석 대시보드")

try:
    # 1. 쪼개진 예산 CSV 파일들을 찾아서 하나로 합치기
    budget_files = glob.glob("*예산*.csv")
    df_budget_list = []

    for f in budget_files:
        # 상단 2줄(■ 제조원가 등)을 무시하고 3번째 줄을 표의 진짜 제목(Header)으로 사용합니다.
        try:
            temp_df = pd.read_csv(f, header=2)
            # 파일 이름에서 시트명(예: SM_SMF)을 추출해서 '시트명(팀명)' 이라는 새로운 열을 만들어 줍니다.
            sheet_name = f.split('-')[-1].replace('.csv', '').strip()
            temp_df['시트명(팀명)'] = sheet_name
            df_budget_list.append(temp_df)
        except:
            pass # 문제 있는 파일은 부드럽게 넘어갑니다.

    # 2. 집행내역 파일 찾기
    actual_files = glob.glob("*집행내역*.csv")

    if budget_files and actual_files:
        # 합친 예산 데이터와 집행내역 데이터 완성
        df_budget = pd.concat(df_budget_list, ignore_index=True)
        df_actual = pd.read_csv(actual_files[0])

        st.success("🎉 쪼개진 예산 시트 7개와 집행내역을 완벽하게 하나로 합쳐서 불러왔습니다!")

        # 3. 사이드바 - 데이터 컬럼 설정 (에러 방지용)
        st.sidebar.markdown("### ⚙️ 데이터 매칭 (관리자용)")
        b_cols = df_budget.columns.tolist()
        a_cols = df_actual.columns.tolist()

        team_col_b = st.sidebar.selectbox("💰 [예산] 파일의 '팀명' 열", ['시트명(팀명)'] + b_cols, index=0)
        budget_col = st.sidebar.selectbox("💰 [예산] 파일의 '예산 금액' 열", b_cols)

        team_col_a = st.sidebar.selectbox("💸 [집행] 파일의 '팀명' 열", a_cols)
        actual_col = st.sidebar.selectbox("💸 [집행] 파일의 '집행 금액' 열", a_cols)

        # 4. 데이터 전처리 및 분석 로직
        df_b_grouped = df_budget.groupby(team_col_b)[budget_col].sum().reset_index()
        df_a_grouped = df_actual.groupby(team_col_a)[actual_col].sum().reset_index()

        df_b_grouped.rename(columns={team_col_b: '팀명', budget_col: '예산금액'}, inplace=True)
        df_a_grouped.rename(columns={team_col_a: '팀명', actual_col: '집행금액'}, inplace=True)

        df_merged = pd.merge(df_b_grouped, df_a_grouped, on='팀명', how='outer').fillna(0)
        df_merged['집행률(%)'] = (df_merged['집행금액'] / df_merged['예산금액'] * 100).round(1)

        st.markdown("---")

        # 5. 대시보드 화면 구성
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
        st.error("❌ 깃허브에 예산.csv 또는 집행내역.csv 파일이 부족합니다.")

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
