import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# =================================================
# Streamlit 기본 설정
# =================================================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =================================================
# 한글 폰트 (Cloud 포함)
# =================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# =================================================
# 경로 설정 (가장 중요)
# =================================================
BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / "data"

# =================================================
# 상수
# =================================================
SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

# =================================================
# 파일 탐색 유틸 (NFC/NFD 완벽 대응)
# =================================================
def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def find_file(directory: Path, target_name: str):
    target = normalize(target_name)
    for f in directory.iterdir():
        if normalize(f.name) == target:
            return f
    return None

# =================================================
# 데이터 로딩
# =================================================
@st.cache_data
def load_environment_data():
    env = {}

    with st.spinner("📂 환경 데이터 불러오는 중..."):
        for school in SCHOOL_EC.keys():
            file_path = find_file(DATA_DIR, f"{school}_환경데이터.csv")

            if file_path is None:
                st.error(f"❌ 환경 데이터 파일 탐색 실패: {school}")
                continue

            df = pd.read_csv(file_path)
            df["time"] = pd.to_datetime(df["time"])
            df["학교"] = school
            env[school] = df

    return env

@st.cache_data
def load_growth_data():
    with st.spinner("📂 생육 결과 데이터 불러오는 중..."):
        file_path = find_file(DATA_DIR, "4개교_생육결과데이터.xlsx")

        if file_path is None:
            st.error("❌ 생육 결과 XLSX 파일 탐색 실패")
            return pd.DataFrame()

        xls = pd.ExcelFile(file_path, engine="openpyxl")
        all_df = []

        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            df["학교"] = sheet
            df["EC"] = SCHOOL_EC.get(sheet)
            all_df.append(df)

        return pd.concat(all_df, ignore_index=True)

# =================================================
# 데이터 로드
# =================================================
env_data = load_environment_data()
growth_df = load_growth_data()

if not env_data or growth_df.empty:
    st.stop()

# =================================================
# 사이드바
# =================================================
st.sidebar.title("🏫 학교 선택")
school_choice = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_EC.keys())
)

# =================================================
# 제목
# =================================================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =================================================
# TAB 1
# =================================================
with tab1:
    st.subheader("🔬 연구 목적")
    st.markdown("""
    EC 농도 차이에 따른 극지식물의 생육 반응을 분석하여  
    **최적 EC 조건을 과학적으로 도출**하는 것을 목표로 한다.
    """)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("총 개체수", len(growth_df))
    col2.metric("평균 온도", f"{pd.concat(env_data.values())['temperature'].mean():.1f} ℃")
    col3.metric("평균 습도", f"{pd.concat(env_data.values())['humidity'].mean():.1f} %")

    best_ec = growth_df.groupby("EC")["생중량(g)"].mean().idxmax()
    col4.metric("최적 EC", f"{best_ec} ⭐")

# =================================================
# TAB 2 환경 데이터
# =================================================
with tab2:
    env_avg = pd.concat(env_data.values()).groupby("학교").mean(numeric_only=True).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["temperature"]), 1, 1)
    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["humidity"]), 1, 2)
    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["ph"]), 2, 1)

    fig.add_trace(go.Bar(
        x=list(SCHOOL_EC.keys()),
        y=list(SCHOOL_EC.values()),
        name="목표 EC"
    ), 2, 2)

    fig.add_trace(go.Bar(
        x=env_avg["학교"],
        y=env_avg["ec"],
        name="실측 EC"
    ), 2, 2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

# =================================================
# TAB 3 생육 결과
# =================================================
with tab3:
    ec_mean = growth_df.groupby("EC")["생중량(g)"].mean().reset_index()

    fig = px.bar(ec_mean, x="EC", y="생중량(g)", title="EC별 평균 생중량")
    fig.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"### ⭐ 최적 EC = **{best_ec} (하늘고)**")

    with st.expander("📂 생육 데이터 원본"):
        st.dataframe(growth_df, use_container_width=True)

        buffer = io.BytesIO()
        growth_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과_통합.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
