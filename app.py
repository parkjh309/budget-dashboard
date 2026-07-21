import streamlit as st
import pandas as pd
import plotly.express as px
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit.components.v1 as components

# 대시보드 페이지 설정
st.set_page_config(page_title="송도캠퍼스 팀별 경비예산 분석", layout="wide")

# ★★★ [인쇄 전용 CSS 주입] ★★★
print_css = """
<style>
@media print {
    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0px !important; padding-left: 0px !important; padding-right: 0px !important; max-width: 100% !important; }
    .stButton, iframe { display: none !important; }
    .stApp, .block-container { background-color: white !important; }
    h1, h2, h3, h4, p, div { color: black !important; }
}
</style>
"""
st.markdown(print_css, unsafe_allow_html=True)

# 0️⃣ [페이지 라우팅 기억장치 초기화]
if 'page' not in st.session_state:
    st.session_state.page = 'main'
if 'chosen_team' not in st.session_state:
    st.session_state.chosen_team = '전체보기'

try:
    # --- [CI 구역] ---
    logo_path = '「반출」logo.png'  
    
    with st.sidebar:
        if os.path.exists(logo_path):
            log_col1, log_col2, log_col3 = st.columns([1, 4, 1])
            with log_col2:
                st.image(logo_path)
        
        st.markdown("<h1 style='text-align: center; font-size: 32px; margin-top: 5px; font-weight: bold;'>동아ST</h1>", unsafe_allow_html=True)
        st.markdown("---")

    all_files = os.listdir('.')
    
    # 7개 팀 매칭 정보
    cc_mapping = {
        'SM_SMF': '송도공장장', 'SM_SAO': '제조팀', 'SM_SHO': '설비관리팀',
        'SM_SDO': '생산지원팀', 'SM_SVO': '밸리데이션팀', 'SM_QSF': '품질관리6팀', 'SM_SQA': '품질보증3팀'
    }

    # 1. 파일 자동 탐색
    budget_file = next((f for f in all_files if "예산" in f and (f.endswith('.xlsx') or f.endswith('.csv'))), None)
    actual_file = next((f for f in all_files if ("경비집행" in f or "집행" in f) and (f.endswith('.xlsx') or f.endswith('.csv'))), None)

    if budget_file and actual_file:
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
            
            if 'CC코드' in df_actual.columns:
                df_actual['최종팀명'] = df_actual['CC코드'].astype(str).str.strip().map(cc_mapping)
            elif 'CC명' in df_actual.columns:
                df_actual['최종팀명'] = df_actual['CC명'].apply(
                    lambda x: next((v for k, v in cc_mapping.items() if k in str(x) or v in str(x)), None)
                )

            actual_month_cols = [f"{i:02d}월" for i in range(1, 13) if f"{i:02d}월" in df_actual.columns]
            if '합계' not in df_actual.columns and actual_month_cols:
                for mc in actual_month_cols:
                    df_actual[mc] = pd.to_numeric(df_actual[mc].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df_actual['합계'] = df_actual[actual_month_cols].sum(axis=1)

        if not df_budget.empty and not df_actual.empty:
            df_budget.columns = [str(c).strip() for c in df_budget.columns]
            df_actual.columns = [str(c).strip() for c in df_actual.columns]

            # 4. 사이드바 - 분석 주기 선택
            st.sidebar.markdown("### ⚙️ 데이터 매칭 및 예실분석")
            analysis_type = st.sidebar.selectbox(
                "📅 분석 주기 선택", 
                ['월별/통합 분석', '1분기 (1~3월)', '2분기 (4~6월)', '3분기 (7~9월)', '4분기 (10~12월)']
            )
            
            display_names = ['TOTAL', '01월', '02월', '03월', '04월', '05월', '06월', '07월', '08월', '09월', '10월', '11월', '12월']
            budget_real_cols = {
                'TOTAL': '2026', '01월': '2026.01', '02월': '2026.02', '03월': '2026.03', 
                '04월': '2026.04', '05월': '2026.05', '06월': '2026.06', '07월': '2026.07',
                '08월': '2026.08', '09월': '2026.09', '10월': '2026.1', '11월': '2026.11', '12월': '2026.12'
            }
            for col in df_budget.columns:
                if col in ['2026.10', "2026.'10"]:
                    budget_real_cols['10월'] = col
            
            actual_real_cols = {'TOTAL': '합계'}
            for i in range(1, 13):
                actual_real_cols[f"{i:02d}월"] = f"{i:02d}월"

            # 1. 일반 월별 분석
            if analysis_type == '월별/통합 분석':
                b_keys = [k for k in display_names if budget_real_cols.get(k) in df_budget.columns]
                a_keys = [k for k in display_names if actual_real_cols.get(k) in df_actual.columns]
                
                if not b_keys: b_keys = df_budget.columns.tolist()
                if not a_keys: a_keys = df_actual.columns.tolist()

                selected_b_key = st.sidebar.selectbox("💰 [예산] 금액 열 선택", b_keys, index=0)
                selected_a_key = st.sidebar.selectbox("💸 [집행] 금액 열 선택", a_keys, index=0)

                budget_col = budget_real_cols.get(selected_b_key, selected_b_key)
                actual_col = actual_real_cols.get(selected_a_key, selected_a_key)

                df_budget[budget_col] = pd.to_numeric(df_budget[budget_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                df_actual[actual_col] = pd.to_numeric(df_actual[actual_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # 2. 분기별 분석
            else:
                if '1분기' in analysis_type: months = [1, 2, 3]
                elif '2분기' in analysis_type: months = [4, 5, 6]
                elif '3분기' in analysis_type: months = [7, 8, 9]
                else: months = [10, 11, 12]

                b_cols_to_sum = []
                for m in months:
                    possible_cols = [f"2026.{m:02d}", f"2026.{m}"]
                    if m == 10: possible_cols.extend(['2026.1', "2026.'10"])
                    found_col = next((c for c in possible_cols if c in df_budget.columns), None)
                    if found_col: b_cols_to_sum.append(found_col)

                a_cols_to_sum = [f"{m:02d}월" for m in months if f"{m:02d}월" in df_actual.columns]

                for col in b_cols_to_sum: df_budget[col] = pd.to_numeric(df_budget[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                for col in a_cols_to_sum: df_actual[col] = pd.to_numeric(df_actual[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)

                df_budget['🎯분기예산'] = df_budget[b_cols_to_sum].sum(axis=1) if b_cols_to_sum else 0
                df_actual['🎯분기집행'] = df_actual[a_cols_to_sum].sum(axis=1) if a_cols_to_sum else 0

                budget_col = '🎯분기예산'
                actual_col = '🎯분기집행'

            # 그룹화 및 병합
            df_b_grouped = df_budget.groupby('최종팀명')[budget_col].sum().reset_index()
            df_a_grouped = df_actual.groupby('최종팀명')[actual_col].sum().reset_index()

            df_b_grouped.rename(columns={'최종팀명': '팀명', budget_col: '예산금액'}, inplace=True)
            df_a_grouped.rename(columns={'최종팀명': '팀명', actual_col: '집행금액'}, inplace=True)

            df_final_teams = pd.DataFrame({'팀명': list(cc_mapping.values())})
            df_merged = pd.merge(df_final_teams, df_b_grouped, on='팀명', how='left').fillna(0)
            df_merged = pd.merge(df_merged, df_a_grouped, on='팀명', how='left').fillna(0)
            df_merged['집행률(%)'] = df_merged.apply(lambda row: (row['집행금액'] / row['예산금액'] * 100) if row['예산금액'] > 0 else 0, axis=1).round(1)

            # --- [이메일 발송 기능] ---
            st.sidebar.markdown("---")
            st.sidebar.markdown("### 🔐 관리자 인증")
            admin_password = st.sidebar.text_input("개발자 암호를 입력하세요", type="password")

            if admin_password == "admin1234":
                st.sidebar.markdown("### 📧 수동 알림 발송 (인증됨)")
                alert_threshold = st.sidebar.slider("알림 기준 집행률(%)", 50, 100, 80)
                receiver_email = st.sidebar.text_input("받는 사람 메일")

                if st.sidebar.button("📩 초과 알림 메일 발송하기"):
                    if receiver_email:
                        try:
                            sender_email = st.secrets["sender_email"]
                            sender_pw = st.secrets["sender_pw"]
                            over_budget_teams = df_merged[df_merged['집행률(%)'] >= alert_threshold]['팀명'].tolist()
                            
                            if over_budget_teams:
                                msg = MIMEMultipart()
                                msg['From'] = sender_email
                                msg['To'] = receiver_email
                                msg['Subject'] = f"⚠️ [예산 경고] {len(over_budget_teams)}개 팀 집행률 {alert_threshold}% 초과"
                                body = f"다음 팀들의 예산 집행률이 {alert_threshold}%를 초과했습니다.\n\n"
                                for team in over_budget_teams:
                                    rate = df_merged[df_merged['팀명'] == team]['집행률(%)'].values[0]
                                    body += f"- {team}: {rate}%\n"
                                body += "\n자세한 사항은 송도캠퍼스 예산 대시보드를 확인해 주세요."
                                msg.attach(MIMEText(body, 'plain'))
                                server = smtplib.SMTP('smtp.gmail.com', 587)
                                server.starttls()
                                server.login(sender_email, sender_pw)
                                server.send_message(msg)
                                server.quit()
                                st.sidebar.success(f"✅ {len(over_budget_teams)}개 팀에 경고 메일 발송 완료!")
                            else:
                                st.sidebar.info("현재 기준치를 초과한 팀이 없습니다.")
                        except Exception:
                            st.sidebar.error("메일 발송 실패: 정보를 확인해 주세요.")
                    else:
                        st.sidebar.warning("⚠️ 받는 사람 메일 주소를 입력해주세요.")

            # ==========================================
            # 🏁 [1번 화면: 메인 대시보드 페이지]
            # ==========================================
            if st.session_state.page == 'main':
                st.title("📊 송도캠퍼스 팀별 경비예산 분석")
                st.markdown("---")
                
                selected_team = st.selectbox("📌 조회할 팀을 선택하세요", ["전체보기"] + list(cc_mapping.values()))

                if selected_team != "전체보기":
                    page_col1, page_col2 = st.columns([5, 1])
                    with page_col2:
                        if st.button("📂 상세내역 분석 페이지 ➡️"):
                            st.session_state.page = 'detail'
                            st.session_state.chosen_team = selected_team
                            st.rerun()

                if selected_team != "전체보기":
                    df_display = df_merged[df_merged['팀명'] == selected_team].copy()
                    df_b_detail = df_budget[df_budget['최종팀명'] == selected_team].copy()
                    df_a_detail = df_actual[df_actual['최종팀명'] == selected_team].copy()
                else:
                    df_display = df_merged.copy()
                    df_b_detail = df_budget.copy()
                    df_a_detail = df_actual.copy()

                # KPI 요약 지표
                st.markdown("### 💡 팀 통합 요약 지표")
                total_budget = df_display['예산금액'].sum()
                total_actual = df_display['집행금액'].sum()
                avg_rate = (total_actual / total_budget * 100) if total_budget > 0 else 0

                col1, col2, col3 = st.columns(3)
                col1.metric("총 수립 예산", f"{total_budget:,.0f} 원")
                col2.metric("누적 집행 금액", f"{total_actual:,.0f} 원")
                col3.metric("평균 집행률", f"{avg_rate:.1f} %")

                def convert_to_korean_amount(val):
                    if val >= 100000000: return f"{val / 100000000:.1f}억 원"
                    elif val >= 10000: return f"{val / 10000:,.0f}만 원"
                    elif val > 0: return f"{val:,.0f} 원"
                    return "0 원"

                df_plot = df_display.copy()
                df_plot['예산금액_라벨'] = df_plot['예산금액'].apply(convert_to_korean_amount)
                df_plot['집행금액_라벨'] = df_plot['집행금액'].apply(convert_to_korean_amount)

                # 막대 그래프
                st.markdown("### 📈 예산 대비 집행 현황 (통합)")
                fig = px.bar(
                    df_plot, x='팀명', y=['예산금액', '집행금액'], barmode='group',
                    color_discrete_sequence=['#1f77b4', '#ff7f0e']
                )
                for i, t in enumerate(fig.data):
                    t.text = df_plot['예산금액_라벨'] if t.name == '예산금액' else df_plot['집행금액_라벨']
                    t.textposition = 'outside'

                current_bargap = 0.7 if len(df_plot) == 1 else 0.2
                fig.update_layout(xaxis_title="팀명", yaxis_title="금액 (원)", legend_title="구분", yaxis=dict(tickformat=",.0f"), bargap=current_bargap, height=450)
                st.plotly_chart(fig, use_container_width=True)

                # [세부 항목 분석 구역]
                st.markdown("---")
                title_text = "전체 팀" if selected_team == "전체보기" else selected_team
                st.markdown(f"### 🔍 {title_text} - 항목별(제조경비 세부) 상세 분석")

                if analysis_type != '월별/통합 분석':
                    if '1분기' in analysis_type:
                        st.info("💡 1분기 데이터입니다. (올해 이전 분기 데이터가 존재하지 않아 전 분기 비교가 생략됩니다.)")
                    else:
                        if '2분기' in analysis_type: prev_months = [1, 2, 3]
                        elif '3분기' in analysis_type: prev_months = [4, 5, 6]
                        else: prev_months = [7, 8, 9]
                        
                        prev_a_cols = [f"{m:02d}월" for m in prev_months if f"{m:02d}월" in df_a_detail.columns]
                        
                        if prev_a_cols:
                            prev_total = df_a_detail[prev_a_cols].sum().sum()
                            curr_total = df_a_detail[actual_col].sum()
                            diff_total = curr_total - prev_total
                            
                            df_prev_cat = df_a_detail.groupby('항목구분명')[prev_a_cols].sum().sum(axis=1).reset_index(name='prev_amt')
                            df_curr_cat = df_a_detail.groupby('항목구분명')[actual_col].sum().reset_index(name='curr_amt')
                            
                            df_trend = pd.merge(df_curr_cat, df_prev_cat, on='항목구분명', how='outer').fillna(0)
                            df_trend['diff'] = df_trend['curr_amt'] - df_trend['prev_amt']
                            
                            diff_str = f"{abs(diff_total):,.0f}원 " + ("<span style='color:red;'>증가 🔺</span>" if diff_total > 0 else "<span style='color:blue;'>감소 🔽</span>")
                            
                            max_inc_cat = df_trend.sort_values(by='diff', ascending=False).iloc[0] if not df_trend.empty and df_trend['diff'].max() > 0 else None
                            max_dec_cat = df_trend.sort_values(by='diff', ascending=True).iloc[0] if not df_trend.empty and df_trend['diff'].min() < 0 else None
                            
                            report_html = f"""
                            <div style='background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 6px solid #4a4a4a; margin-bottom: 20px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);'>
                                <h4 style='margin-top:0px; margin-bottom:15px; color:#343a40;'>📝 {analysis_type[:3]} 집행 요약 리포트</h4>
                                <ul style='font-size: 16px; line-height: 1.8; margin-bottom: 0px;'>
                                    <li>전 분기 대비 총 집행 금액이 <b>{diff_str}</b>했습니다.</li>
                            """
                            if max_inc_cat is not None:
                                report_html += f"<li>비용이 가장 많이 증가한 항목은 <b>{max_inc_cat['항목구분명']}</b> (+{max_inc_cat['diff']:,.0f}원) 입니다.</li>"
                            if max_dec_cat is not None:
                                report_html += f"<li>비용이 가장 많이 절감된 항목은 <b>{max_dec_cat['항목구분명']}</b> ({max_dec_cat['diff']:,.0f}원) 입니다.</li>"
                                
                            report_html += "</ul></div>"
                            st.markdown(report_html, unsafe_allow_html=True)
                        else:
                            st.info("⚠️ 엑셀 파일 내 전 분기 월별 데이터가 부족하여 비교할 수 없습니다.")
                
                col_b, col_a = st.columns(2)
                
                with col_b:
                    st.markdown("#### 💰 수립 예산 구성비율")
                    if '계정' in df_b_detail.columns:
                        df_b_cat = df_b_detail[df_b_detail[budget_col] > 0]
                        if not df_b_cat.empty:
                            df_b_grouped_cat = df_b_cat.groupby('계정')[budget_col].sum().reset_index()
                            df_b_grouped_cat = df_b_grouped_cat.sort_values(by=budget_col, ascending=False).head(10)
                            
                            fig_b = px.pie(df_b_grouped_cat, values=budget_col, names='계정', hole=0.4, 
                                           color_discrete_sequence=px.colors.sequential.Blues_r)
                            fig_b.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_b, use_container_width=True)

                            top3_b = df_b_grouped_cat.head(3)
                            total_b_amt = df_b_cat[budget_col].sum()
                            medals = ['🥇', '🥈', '🥉']
                            
                            html_b = "<div style='background-color: #f0f8ff; padding: 15px; border-radius: 10px; border-left: 5px solid #1f77b4; margin-top: -20px;'>"
                            html_b += "<h4 style='margin-top:0px; margin-bottom:15px; color:#1f77b4;'>🏆 예산 비중 TOP 3</h4>"
                            for i, (idx, row) in enumerate(top3_b.iterrows()):
                                acc_name = row['계정']
                                amt = row[budget_col]
                                pct = (amt / total_b_amt) * 100 if total_b_amt > 0 else 0
                                html_b += f"<div style='font-size: 20px; font-weight: bold; margin-bottom: 10px;'>{medals[i]} {acc_name} <span style='font-size: 16px; color: #555;'>({pct:.1f}%)</span></div>"
                            html_b += "</div>"
                            st.markdown(html_b, unsafe_allow_html=True)
                        else:
                            st.info("선택된 기간의 예산 세부 데이터가 없습니다.")
                    else:
                        st.warning("예산 파일에 '계정' 열을 찾을 수 없어 분석할 수 없습니다.")

                with col_a:
                    st.markdown("#### 💸 실제 집행 구성비율")
                    if '항목구분명' in df_a_detail.columns:
                        df_a_cat = df_a_detail[df_a_detail[actual_col] > 0]
                        if not df_a_cat.empty:
                            df_a_grouped_cat = df_a_cat.groupby('항목구분명')[actual_col].sum().reset_index()
                            df_a_grouped_cat = df_a_grouped_cat.sort_values(by=actual_col, ascending=False).head(10)
                            
                            fig_a = px.pie(df_a_grouped_cat, values=actual_col, names='항목구분명', hole=0.4,
                                           color_discrete_sequence=px.colors.sequential.Oranges_r)
                            fig_a.update_traces(textposition='inside', textinfo='percent+label')
                            st.plotly_chart(fig_a, use_container_width=True)

                            top3_a = df_a_grouped_cat.head(3)
                            total_a_amt = df_a_cat[actual_col].sum()
                            medals = ['🥇', '🥈', '🥉']
                            
                            html_a = "<div style='background-color: #fffaf0; padding: 15px; border-radius: 10px; border-left: 5px solid #ff7f0e; margin-top: -20px;'>"
                            html_a += "<h4 style='margin-top:0px; margin-bottom:15px; color:#ff7f0e;'>🏆 집행 비중 TOP 3</h4>"
                            for i, (idx, row) in enumerate(top3_a.iterrows()):
                                acc_name = row['항목구분명']
                                amt = row[actual_col]
                                pct = (amt / total_a_amt) * 100 if total_a_amt > 0 else 0
                                html_a += f"<div style='font-size: 20px; font-weight: bold; margin-bottom: 10px;'>{medals[i]} {acc_name} <span style='font-size: 16px; color: #555;'>({pct:.1f}%)</span></div>"
                            html_a += "</div>"
                            st.markdown(html_a, unsafe_allow_html=True)
                        else:
                            st.info("선택된 기간의 집행 세부 데이터가 없습니다.")
                    else:
                        st.warning("집행 파일에 '항목구분명' 열을 찾을 수 없어 분석할 수 없습니다.")

                st.markdown("---")
                st.markdown("### 📋 요약 데이터 표")
                st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))

            # ==========================================
            # 📂 [2번 화면: 상세 예산 분석 페이지]
            # ==========================================
            elif st.session_state.page == 'detail':
                
                col_btn1, col_btn2 = st.columns([1, 4])
                
                with col_btn1:
                    if st.button("⬅️ 메인 대시보드로 돌아가기"):
                        st.session_state.page = 'main'
                        st.rerun()
                
                with col_btn2:
                    components.html(
                        """
                        <button onclick="window.parent.print()" style="
                            background-color: #2e7d32;
                            color: white;
                            border: none;
                            padding: 8px 16px;
                            border-radius: 5px;
                            cursor: pointer;
                            font-size: 14px;
                            font-weight: bold;
                            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
                            box-shadow: 1px 1px 3px rgba(0,0,0,0.2);
                        ">🖨️ 현재 페이지 PDF로 저장/인쇄</button>
                        """,
                        height=50
                    )

                st.title(f"📂 {st.session_state.chosen_team} - 상세 경비 집행 분석")
                
                # 선택된 팀의 세부 데이터 필터링 (사이드바에서 고른 월/분기에 맞춰)
                df_b_detail = df_budget[df_budget['최종팀명'] == st.session_state.chosen_team].copy()
                df_a_detail = df_actual[df_actual['최종팀명'] == st.session_state.chosen_team].copy()

                # ★★★ [신규 핵심 기능: 항목별(계정별) 예산 대비 집행 현황] ★★★
                st.markdown("---")
                st.markdown(f"### 🎯 항목별 예산 대비 집행률 분석 ({analysis_type})")
                st.write("항목별로 예산이 얼마나 할당되었고, 얼마나 남았는지 직관적으로 확인하세요. (집행률이 높을수록 붉게 표시됩니다.)")

                if '계정' in df_b_detail.columns and '항목구분명' in df_a_detail.columns:
                    # 예산 데이터 합산
                    df_b_item = df_b_detail.groupby('계정')[budget_col].sum().reset_index()
                    df_b_item.rename(columns={'계정': '항목명', budget_col: '예산금액'}, inplace=True)
                    
                    # 집행 데이터 합산
                    df_a_item = df_a_detail.groupby('항목구분명')[actual_col].sum().reset_index()
                    df_a_item.rename(columns={'항목구분명': '항목명', actual_col: '집행금액'}, inplace=True)
                    
                    # 계정명(항목명) 기준으로 병합 (Full Outer Join)
                    df_item_merged = pd.merge(df_b_item, df_a_item, on='항목명', how='outer').fillna(0)
                    
                    # 잔여 예산 및 집행률 계산
                    df_item_merged['잔여예산'] = df_item_merged['예산금액'] - df_item_merged['집행금액']
                    df_item_merged['집행률(%)'] = df_item_merged.apply(
                        lambda x: (x['집행금액'] / x['예산금액'] * 100) if x['예산금액'] > 0 else (100 if x['집행금액'] > 0 else 0), axis=1
                    )
                    
                    # 0원 데이터 청소 및 정렬
                    df_item_merged = df_item_merged[(df_item_merged['예산금액'] > 0) | (df_item_merged['집행금액'] > 0)]
                    df_item_merged = df_item_merged.sort_values(by='집행률(%)', ascending=False)
                    
                    # 데이터프레임 스타일링 출력 (그라데이션 색상 적용)
                    st.dataframe(
                        df_item_merged.style.format({
                            '예산금액': '{:,.0f} 원',
                            '집행금액': '{:,.0f} 원',
                            '잔여예산': '{:,.0f} 원',
                            '집행률(%)': '{:.1f} %'
                        }).background_gradient(subset=['집행률(%)'], cmap='Reds', vmin=0, vmax=100),
                        use_container_width=True
                    )
                else:
                    st.warning("데이터에 '계정' 또는 '항목구분명' 열이 없어 비교할 수 없습니다.")

                # 기존 상세 그리드 및 차트
                st.markdown("---")
                st.markdown(f"### 📊 월별 전체 집행 내역 그리드")
                st.write("나중에 연동할 수만 줄짜리 '세부 전표 내역'이 들어갈 핵심 자리입니다. 현재는 엑셀에 내장된 월별 세부 지출이 정밀하게 표시됩니다.")

                cols_to_format = ['합계'] + [c for c in df_a_detail.columns if '월' in c]
                format_dict = {col: '{:,.0f} 원' for col in cols_to_format if col in df_a_detail.columns}

                display_cols = [c for c in df_a_detail.columns if c not in ['최종팀명', '🎯분기집행']]
                st.dataframe(df_a_detail[display_cols].style.format(format_dict))

        else:
            st.error("데이터 조립 과정에서 오류가 발생했거나 데이터가 비어있습니다.")
    else:
        st.error("❌ 깃허브 폴더에서 '예산' 또는 '경비집행' 파일을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
