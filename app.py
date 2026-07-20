아이고, 잘 진행되다가 갑자기 에러 창이 떡하니 떠서 많이 놀라셨죠! 😭 사진을 올려주신 덕분에 원인을 1초 만에 찾았습니다.

에러 메시지를 보니, 파이썬이 데이터를 한 줄씩 읽어오는 명령어(itertuples)를 사용했는데, 이 명령어가 '계정'이나 '항목구분명' 같은 한글로 된 제목을 읽다가 충돌을 일으킨 것입니다. (서버 환경에 따라 한글 이름을 제대로 소화하지 못하는 고질적인 버그입니다.)

이런 깐깐한 에러를 완벽하게 피해갈 수 있는 가장 안전하고 튼튼한 명령어(iterrows)로 해당 부분을 싹 고쳤습니다. 다른 부분은 전혀 건드리지 않았으니 안심하시고 다시 한번만 덮어써 주세요!

🛠️ [한글 충돌 에러 해결] Top 3 랭킹 최종 코드 (app.py)
깃허브의 app.py 연필 아이콘을 누르시고, Ctrl + A로 기존 내용을 완전히 싹 지우신 뒤 아래 코드를 그대로 덮어써 주세요.

Python
import streamlit as st
import pandas as pd
import plotly.express as px
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 대시보드 페이지 설정
st.set_page_config(page_title="송도캠퍼스 파이낸셜 네비게이터", layout="wide")

try:
    # --- [CI 구역: 구버전 완벽 호환 정중앙 정렬] ---
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

    # 대시보드 메인 제목
    st.title("📊 송도캠퍼스 팀별 파이낸셜 네비게이터")

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

            # 4. 사이드바 데이터 매칭
            st.sidebar.markdown("### ⚙️ 데이터 매칭")
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
                        except KeyError:
                            st.sidebar.error("⚠️ Secrets에 이메일 정보가 없습니다!")
                        except Exception as e:
                            st.sidebar.error("메일 발송 실패: 정보를 확인해 주세요.")
                    else:
                        st.sidebar.warning("⚠️ 받는 사람 메일 주소를 입력해주세요.")
            elif admin_password != "":
                st.sidebar.error("❌ 암호가 올바르지 않습니다.")

            # --- [대시보드 메인 화면] ---
            st.markdown("---")
            selected_team = st.selectbox("📌 조회할 팀을 선택하세요", ["전체보기"] + list(cc_mapping.values()))

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

            # 막대 그래프 배치
            st.markdown("### 📈 예산 대비 집행 현황 (통합)")
            fig = px.bar(
                df_plot, x='팀명', y=['예산금액', '집행금액'], barmode='group',
                color_discrete_sequence=['#1f77b4', '#ff7f0e']
            )
            for i, t in enumerate(fig.data):
                t.text = df_plot['예산금액_라벨'] if t.name == '예산금액' else df_plot['집행금액_라벨']
                t.textposition = 'outside'

            current_bargap = 0.7 if len(df_plot) == 1 else 0.2

            fig.update_layout(
                xaxis_title="팀명", 
                yaxis_title="금액 (원)", 
                legend_title="구분", 
                yaxis=dict(tickformat=",.0f"),
                bargap=current_bargap, 
                height=450
            )
            st.plotly_chart(fig, use_container_width=True)

            # --- [세부 항목 분석 구역 (TOP 3 랭킹 - 안전한 코드로 수정)] ---
            st.markdown("---")
            title_text = "전체 팀" if selected_team == "전체보기" else selected_team
            st.markdown(f"### 🔍 {title_text} - 항목별(제조경비 세부) 상세 분석")
            
            col_b, col_a = st.columns(2)
            
            # [좌측] 예산 비율 및 TOP 3
            with col_b:
                st.markdown("#### 💰 수립 예산 구성비율")
                if '계정' in df_b_detail.columns:
                    df_b_cat = df_b_detail[df_b_detail[budget_col] > 0]
                    if not df_b_cat.empty:
                        # 1. 원형 차트 그리기
                        df_b_grouped_cat = df_b_cat.groupby('계정')[budget_col].sum().reset_index()
                        df_b_grouped_cat = df_b_grouped_cat.sort_values(by=budget_col, ascending=False).head(10)
                        
                        fig_b = px.pie(df_b_grouped_cat, values=budget_col, names='계정', hole=0.4, 
                                       color_discrete_sequence=px.colors.sequential.Blues_r)
                        fig_b.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_b, use_container_width=True)

                        # 2. 예산 TOP 3 랭킹 박스 추가 (안전한 iterrows 방식 적용)
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

            # [우측] 집행 비율 및 TOP 3
            with col_a:
                st.markdown("#### 💸 실제 집행 구성비율")
                if '항목구분명' in df_a_detail.columns:
                    df_a_cat = df_a_detail[df_a_detail[actual_col] > 0]
                    if not df_a_cat.empty:
                        # 1. 원형 차트 그리기
                        df_a_grouped_cat = df_a_cat.groupby('항목구분명')[actual_col].sum().reset_index()
                        df_a_grouped_cat = df_a_grouped_cat.sort_values(by=actual_col, ascending=False).head(10)
                        
                        fig_a = px.pie(df_a_grouped_cat, values=actual_col, names='항목구분명', hole=0.4,
                                       color_discrete_sequence=px.colors.sequential.Oranges_r)
                        fig_a.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig_a, use_container_width=True)

                        # 2. 집행 TOP 3 랭킹 박스 추가 (안전한 iterrows 방식 적용)
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
            st.markdown("### 📋 상세 데이터")
            st.dataframe(df_display.style.format({'예산금액': '{:,.0f}', '집행금액': '{:,.0f}', '집행률(%)': '{:.1f}%'}))
        else:
            st.error("데이터 조립 과정에서 오류가 발생했거나 데이터가 비어있습니다.")
    else:
        st.error("❌ 깃허브 폴더에서 '예산' 또는 '경비집행' 파일을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"⚠️ 데이터 처리 중 오류가 발생했습니다: {e}")
