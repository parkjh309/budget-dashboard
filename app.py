import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="송도캠퍼스 파이낸셜 네비게이터", layout="wide")
st.title("📊 송도캠퍼스 팀별 파이낸셜 네비게이터")

try:
    all_files = os.listdir('.')
    
    # 7개 팀 매칭 정보 (시트 이름 및 CC코드 기준)
    cc_mapping = {
        'SM_SMF': '송도공장장', 'SM_SAO': '제조팀', 'SM_SHO': '설비관리팀',
        'SM_SDO': '생산지원팀', 'SM_SVO': '밸리데이션팀', 'SM_QSF': '품질관리6팀', 'SM_SQA': '품질보증3팀'
    }

    # 1. 파일 자동 탐색
    budget_file = next((f for f in all_files if "예산" in f and (f.endswith('.xlsx') or f.endswith('.csv'))), None)
    actual_file = next((f for f in all_files if ("경비집행" in f or "집행" in f) and (f.endswith('.xlsx') or f.endswith('.csv'))), None)

    if budget_file and actual_file:
        st.success(f"✅ 데이터를 성공적으로 찾았습니다!\n* 예산 파일: `{budget_file}`\n* 집행 파일: `{actual_file}`")

        # 2. 예산 데이터 로드
        df_budget_list = []
        if budget_file.endswith('.xlsx'):
            xl = pd.ExcelFile(budget_file)
            for sheet in cc_mapping.keys():
                if sheet in xl.sheet_names:
                    df = pd.read_excel(budget_file, sheet_name=sheet, header=2)
                    if not df.empty and '계정코드' in df.columns:
                        df = df[df['계정코드'].notna()]
                        df['최종팀명'] = cc_mapping[sheet]
                        df_budget_list.append(df)
        else:
            budget_csv_files = [f for f in all_files if "예산" in f and f.endswith('.csv')]
            for f in budget_csv_files:
                team_code = next((code for code in cc_mapping.keys() if code in f), None)
                if team_code:
                    df = pd.read_csv(f, header=2)
                    if not df.empty and '계정코드' in df.columns:
                        df = df[df['계정코드'].notna()]
                        df['최종팀명'] = cc_mapping[team_code]
                        df_budget_list.append(df)

        df_budget = pd.concat(df_budget_list, ignore_index=True) if df_budget_list else pd.DataFrame()

        # 3. 집행 데이터 로드
        if actual_file.endswith('.xlsx'):
            df_actual = pd.read_excel(actual_file)
        else:
            df_actual = pd.read_csv(actual_file)

        if not df_actual.empty:
            if '항목코드' in df_actual.columns:
                df_actual = df_actual[df_actual['항목코드'].notna()]
            
            # CC코드를 최종팀명으로 매칭
            if 'CC코드' in df_actual.columns:
                df_actual['최종팀명'] = df_actual['CC코드'].astype(str).str.strip().map(cc_mapping)
            elif 'CC명' in df_actual.columns:
                df_actual['최종팀명'] = df_actual['CC명'].apply(
                    lambda x: next((v for k, v in cc_mapping.items() if k in str(x) or v in str(x)), None)
                )

        if not df_budget.empty and not df_actual.empty:
            # 4. 사이드바 - 열 매칭 및 필터링
            st.sidebar.markdown("### ⚙️ 데이터 매칭")
            b_cols = [c for c in df_budget.columns.tolist() if 'Unnamed' not in str(c)]
            a_cols = [c for c in df_actual.columns.tolist() if 'Unnamed' not in str(c)]

            # ★ [안전 수정] 드롭다운에서 불필요한 메뉴 제외하고 딱 원하는 항목만 남기기 ★
            allowed_budget = ['2026', '2026.01', '2026.02', '2026.03', '2026.04', '2026.05']
            b_cols_filtered = [c for c in b_cols if str(c).strip() in allowed_budget]
            
            # 안전장치 (예외 상황 대비)
            if not b_cols_filtered:
                b_cols_filtered = b_cols

            # 기본 매칭 인덱스 설정
            default_idx_b = next((i for i, c in enumerate(b_cols_filtered) if '2026.05' in str(c)), 
                                 next((i for i, c in enumerate(b_cols_filtered) if '2026' in str(c)), 0))
            default_idx_a = next((i for i, c in enumerate(a_cols) if '05월' in str(c)), 0)

            budget_col = st.sidebar.selectbox("💰 [예산] 금액 열 선택", b_cols_filtered, index=default_idx_b)
            actual_col = st.sidebar.selectbox("💸 [집행] 금액 열 선택", a_cols, index=default_idx_a)

            # 5. 금액 데이터 정제
            df_budget[budget_col] = pd.to_numeric(df_budget[budget_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            df_actual[actual_col] = pd.to_numeric(df_actual[actual_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

            # 6. 그룹화 및 병합
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

            # 7. 대시보드 화면 구성
            st.markdown("---")
            selected_team = st.selectbox("📌 조회할 팀을 선택하세요", ["전체보기"] + list(cc_mapping.values()))

            if selected_team != "전체보기":
                df_display = df_merged[df_merged['팀명'] == selected_team].copy()
            else:
                df_display = df_merged.copy()

            # KPI 요약 지표
            st.markdown("### 💡 요약 지표")
            total_budget = df_display['예산금액'].sum()
            total_actual = df_display['집행금액'].sum()
            avg_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("총 수립 예산", f"{total_budget:,.0f} 원")
            col2.metric("누적 집행 금액", f"{total_actual:,.0f} 원")
            col3.metric("평균 집행률", f"{avg_rate:.1f} %")

            # 한글 금액 단위 변환기
            def convert_to_korean_amount(val):
                if val >= 100000000: return f"{val / 100000000:.1f}억 원"
                elif val >= 10000: return f"{val / 10000:,.0f}만 원"
                elif val > 0: return f"{val:,.0f} 원"
                return "0 원"

            df_plot = df_display.copy()
            df_plot['예산금액_라벨'] = df_plot['예산금액'].apply(convert_to_korean_amount)
            df_plot['집행금액_라벨'] = df_plot['집행금액'].apply(convert_to_korean_amount)

            # 8. 바 차트 시각화
            st.markdown("### 📈 예산 대비 집행 현황")
            fig = px.bar(
                df_plot, x='팀명', y=['예산금액', '집행금액'], barmode='group',
                color_discrete_sequence=['#1f77b4', '#ff7f0e']
            )
            for i, t in enumerate(fig.data):
                t.text = df_plot['예산금액_라벨'] if t.name == '예산금액' else df_plot['집행금액_라벨']
                t.textposition = 'outside'

            fig.update_layout(
                xaxis_title="팀명", 
                yaxis_title="금액 (원)", 
                legend_title="구분", 
                yaxis=dict(tickformat=",.0f")
            )
            st.plotly_chart(fig, use_container_width=True)

            # 9. 상세 표
            st.markdown("### 📋 상세 데이터")
            st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))
        else:
            st.error("데이터 조립 과정에서 오류가 발생했거나 데이터가 비어있습니다.")
    else:
        st.error("❌ 깃허브 폴더에서 '예산' 또는 '경비집행' 파일을 찾을 수 없습니다.")
        st.write("현재 폴더 파일 목록:", all_files)

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
