import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="2026 송도캠퍼스 예실분석 대시보드", layout="wide")
st.title("📊 2026년 팀별 예실분석 대시보드")

try:
    # 1. 파일 찾기
    all_files = os.listdir('.')
    budget_file = next((f for f in all_files if "예산" in f and f.endswith('.xlsx')), None)
    actual_file = next((f for f in all_files if "집행내역" in f and f.endswith('.xlsx')), None)

    if budget_file and actual_file:
        # 2. 지정된 7개 팀 및 CC코드 매칭 정보
        cc_mapping = {
            'SM_SMF': '송도공장장',
            'SM_SAO': '제조팀',
            'SM_SHO': '설비관리팀',
            'SM_SDO': '생산지원팀',
            'SM_SVO': '밸리데이션팀',
            'SM_QSF': '품질관리6팀',
            'SM_SQA': '품질보증3팀'
        }

        # 3. 예산 엑셀 파일 로드
        budget_sheets = pd.read_excel(budget_file, sheet_name=None, skiprows=2)
        df_budget_list = []

        for sheet_name, df in budget_sheets.items():
            sheet_key = sheet_name.strip()
            if sheet_key in cc_mapping:
                if not df.empty:
                    df['최종팀명'] = cc_mapping[sheet_key]
                    df_budget_list.append(df)
        
        df_budget = pd.concat(df_budget_list, ignore_index=True)
        
        # 4. 집행내역 엑셀 파일 로드
        df_actual = pd.read_excel(actual_file)
        
        # ★★★ 문제의 에러가 발생했던 부분 완벽 수정 (.str 추가) ★★★
        if 'CC코드' in df_actual.columns:
            df_actual['최종팀명'] = df_actual['CC코드'].astype(str).str.strip().map(cc_mapping)
        elif 'CC명' in df_actual.columns:
            df_actual['최종팀명'] = df_actual['CC명'].apply(
                lambda x: next((v for k, v in cc_mapping.items() if k in str(x) or v in str(x)), None)
            )

        # 5. 사이드바 - 열 매칭 자동 세팅
        st.sidebar.markdown("### ⚙️ 데이터 매칭 정보 (자동 완료)")
        
        b_cols = df_budget.columns.tolist()
        a_cols = df_actual.columns.tolist()

        default_idx_b = b_cols.index('2026') if '2026' in b_cols else (b_cols.index('합계') if '합계' in b_cols else len(b_cols)-1)
        default_idx_a = a_cols.index('합계') if '합계' in a_cols else len(a_cols)-1

        budget_col = st.sidebar.selectbox("💰 [예산] 금액 열", b_cols, index=default_idx_b)
        actual_col = st.sidebar.selectbox("💸 [집행] 금액 열", a_cols, index=default_idx_a)

        # 6. 금액 데이터 정제
        df_budget[budget_col] = pd.to_numeric(df_budget[budget_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df_actual[actual_col] = pd.to_numeric(df_actual[actual_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        # 7. 7개 팀 기준으로 그룹화 및 병합
        df_b_grouped = df_budget.groupby('최종팀명')[budget_col].sum().reset_index()
        df_a_grouped = df_actual.groupby('최종팀명')[actual_col].sum().reset_index()

        df_b_grouped.rename(columns={'최종팀명': '팀명', budget_col: '예산금액'}, inplace=True)
        df_a_grouped.rename(columns={'최종팀명': '팀명', actual_col: '집행금액'}, inplace=True)

        df_final_teams = pd.DataFrame({'팀명': list(cc_mapping.values())})
        
        df_merged = pd.merge(df_final_teams, df_b_grouped, on='팀명', how='left').fillna(0)
        df_merged = pd.merge(df_merged, df_a_grouped, on='팀명', how='left').fillna(0)
        
        df_merged['집행률(%)'] = df_merged.apply(
            lambda row: (row['집행금액'] / row['예산금액'] * 100) if row['예산금액'] > 0 else 0, axis=1
        ).round(1)

        st.markdown("---")

        # 8. 대시보드 화면 구성
        selected_team = st.selectbox("📌 조회할 팀을 선택하세요", ["전체보기"] + list(cc_mapping.values()))

        if selected_team != "전체보기":
            df_display = df_merged[df_merged['팀명'] == selected_team]
        else:
            df_display = df_merged

        # KPI 요약 지표
        st.markdown("### 💡 요약 지표")
        total_budget = df_display['예산금액'].sum()
        total_actual = df_display['집행금액'].sum()
        avg_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("총 수립 예산", f"{total_budget:,.0f} 원")
        col2.metric("누적 집행 금액", f"{total_actual:,.0f} 원")
        col3.metric("평균 집행률", f"{avg_rate:.1f} %")

        # 시각화 바 차트
        st.markdown("### 📈 예산 대비 집행 현황")
        fig = px.bar(
            df_display, x='팀명', y=['예산금액', '집행금액'], barmode='group', text_auto='.2s',
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        fig.update_layout(xaxis_title="팀명", yaxis_title="금액 (원)", legend_title="구분")
        st.plotly_chart(fig, use_container_width=True)

        # 상세 표
        st.markdown("### 📋 상세 데이터")
        st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))

    else:
        st.error("❌ 깃허브에서 .xlsx 확장자를 가진 '예산' 또는 '집행내역' 파일을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
