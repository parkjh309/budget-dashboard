import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="송도캠퍼스 파이낸셜 네비게이터", layout="wide")
st.title("📊 송도캠퍼스 팀별 파이낸셜 네비게이터")

try:
    # 1. 깃허브에 올라온 모든 파일 중 '예산'과 '경비집행' 글자가 들어간 CSV 파일들을 알아서 찾습니다.
    all_files = os.listdir('.')
    budget_csv_files = [f for f in all_files if "예산" in f and f.endswith('.csv')]
    actual_csv_file = next((f for f in all_files if "경비집행" in f and f.endswith('.csv')), None)

    if budget_csv_files and actual_csv_file:
        # 2. 팀 코드 매칭 (이름표 달아주기)
        cc_mapping = {
            'SM_SMF': '송도공장장', 'SM_SAO': '제조팀', 'SM_SHO': '설비관리팀',
            'SM_SDO': '생산지원팀', 'SM_SVO': '밸리데이션팀', 'SM_QSF': '품질관리6팀', 'SM_SQA': '품질보증3팀'
        }

        st.success(f"✅ 깃허브에서 데이터 조립 완료! (예산 팀별 파일 {len(budget_csv_files)}개, 경비집행 1개)")

        # 3. 예산 데이터 7개 파일 하나로 조립 (위의 불필요한 2줄 알아서 건너뛰기: header=2)
        df_budget_list = []
        for f in budget_csv_files:
            team_code = next((code for code in cc_mapping.keys() if code in f), None)
            if team_code:
                df = pd.read_csv(f, header=2)
                # 빈칸 데이터 없애고 팀 이름표 붙여서 모으기
                if not df.empty and '계정코드' in df.columns:
                    df = df[df['계정코드'].notna()]
                    df['최종팀명'] = cc_mapping[team_code]
                    df_budget_list.append(df)
        
        df_budget = pd.concat(df_budget_list, ignore_index=True) if df_budget_list else pd.DataFrame()

        # 4. 경비집행 데이터 로드 (첫 줄부터 바로 읽기)
        df_actual = pd.read_csv(actual_csv_file)
        if 'CC코드' in df_actual.columns:
            df_actual['최종팀명'] = df_actual['CC코드'].astype(str).str.strip().map(cc_mapping)

        # 5. 사이드바 - 열 매칭 자동화
        st.sidebar.markdown("### ⚙️ 데이터 매칭")
        b_cols = [c for c in df_budget.columns.tolist() if 'Unnamed' not in str(c)]
        a_cols = [c for c in df_actual.columns.tolist() if 'Unnamed' not in str(c)]

        # 기본값: 예산은 '2026', 집행은 '05월'을 찾아서 세팅
        default_idx_b = next((i for i, c in enumerate(b_cols) if '2026' in str(c)), 0)
        default_idx_a = next((i for i, c in enumerate(a_cols) if '05월' in str(c)), 0)

        budget_col = st.sidebar.selectbox("💰 [예산] 금액 열 선택", b_cols, index=default_idx_b)
        actual_col = st.sidebar.selectbox("💸 [집행] 금액 열 선택", a_cols, index=default_idx_a)

        # 6. 금액 글자를 순수 숫자로 정제
        df_budget[budget_col] = pd.to_numeric(df_budget[budget_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df_actual[actual_col] = pd.to_numeric(df_actual[actual_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

        # 7. 그룹화 및 병합 (표 계산)
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

        # 8. 대시보드 화면 구성
        st.markdown("---")
        selected_team = st.selectbox("📌 조회할 팀을 선택하세요", ["전체보기"] + list(cc_mapping.values()))

        if selected_team != "전체보기":
            df_display = df_merged[df_merged['팀명'] == selected_team].copy()
        else:
            df_display = df_merged.copy()

        # KPI 지표 3개 (총 수립 예산, 집행 금액, 집행률)
        st.markdown("### 💡 요약 지표")
        total_budget = df_display['예산금액'].sum()
        total_actual = df_display['집행금액'].sum()
        avg_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("총 수립 예산", f"{total_budget:,.0f} 원")
        col2.metric("누적 집행 금액", f"{total_actual:,.0f} 원")
        col3.metric("평균 집행률", f"{avg_rate:.1f} %")

        # 숫자 포맷 변경 함수
        def convert_to_korean_amount(val):
            if val >= 100000000: return f"{val / 100000000:.1f}억 원"
            elif val >= 10000: return f"{val / 10000:,.0f}만 원"
            elif val > 0: return f"{val:,.0f} 원"
            return "0 원"

        df_plot = df_display.copy()
        df_plot['예산금액_라벨'] = df_plot['예산금액'].apply(convert_to_korean_amount)
        df_plot['집행금액_라벨'] = df_plot['집행금액'].apply(convert_to_korean_amount)

        # 9. 화려한 바 차트 시각화
        st.markdown("### 📈 예산 대비 집행 현황")
        fig = px.bar(
            df_plot, x='팀명', y=['예산금액', '집행금액'], barmode='group',
            color_discrete_sequence=['#1f77b4', '#ff7f0e']
        )
        for i, t in enumerate(fig.data):
            t.text = df_plot['예산금액_라벨'] if t.name == '예산금액' else df_plot['집행금액_라벨']
            t.textposition = 'outside'

        fig.update_layout(xaxis_title="팀명", yaxis_title="금액 (원)", legend_title="구분", yaxis=dict(tickformat=",.0f"))
        st.plotly_chart(fig, use_container_width=True)

        # 10. 상세 표
        st.markdown("### 📋 상세 데이터")
        st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))

    else:
        st.error("❌ 깃허브에서 CSV 파일들을 찾을 수 없습니다.")
        st.write("현재 폴더 파일목록:", all_files)

except Exception as e:
    st.error(f"⚠️ 오류가 발생했습니다: {e}")
