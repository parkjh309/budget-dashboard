import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="송도캠퍼스 파이낸셜 네비게이터", layout="wide")
st.title("📊 송도캠퍼스 파이낸셜 네비게이터")

# 아까 확인된 파일들을 안전하게 읽기
try:
    df_b = pd.read_csv("「반출」예산(2026).xlsx - SM_SQA.csv", header=2)
    df_a = pd.read_csv("「반출」경비집행 (5월마감).xlsx - Sheet1.csv")

    st.success("데이터를 성공적으로 불러왔습니다.")

    # 간단한 그래프 예시 (데이터 구조에 맞춤)
    st.subheader("📈 예산 vs 집행 요약")
    
    # 예산 데이터의 2026 열과 집행 데이터의 05월 열을 비교하는 그래프
    # (표의 컬럼명에 따라 수정 가능합니다)
    fig = px.bar(df_b.head(10), x='계정', y='2026', title="팀별 예산 현황")
    st.plotly_chart(fig)

except Exception as e:
    st.error(f"데이터 처리 중 오류: {e}")
