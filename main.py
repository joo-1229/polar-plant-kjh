import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ===============================
# 한글 폰트 (깨짐 방지)
# ===============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# ===============================
# 상수 정의
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

SCHOOL_EC = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR = {
    "송도고": "#1f77b4",
    "하늘고": "#2ca02c",
    "아라고": "#ff7f0e",
    "동산고": "#d62728"
}

# ===============================
# 파일 찾기 (NFC/NFD 완벽 대응)
# ===============================
def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def find_file_by_name(directory: Path, target_name: str):
    target_norm = normalize_text(target_name)
    for file in directory.iterdir():
        if normalize_text(file.name) == target_norm:
            return file
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data = {}
    with st.spinner("📂 환경 데이터 불러오는 중..."):
        for school in SCHOOL_EC.keys():
            filename = f"{school}_환경데이터.csv"
            file_path = find_file_by_name(DATA_DIR, filename)

            if file_path is None:
                st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {filename}")
                continue

            df = pd.read_csv(file_path)
            df["time"] = pd.to_datetime(df["time"])
            df["학교"] = school
            data[school] = df

    return data

@st.cache_data
def load_growth_data():
    with st.spinner("📂 생육 결과 데이터 불러오는 중..."):
        xlsx_file = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")

        if xlsx_file is None:
            st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
            return pd.DataFrame()

        excel = pd.ExcelFile(xlsx_file, engine="openpyxl")
        all_data = []

        for sheet in excel.sheet_names:
            df = excel.parse(sheet)
            df["학교"] = sheet
            df["EC"] = SCHOOL_EC.get(sheet)
            all_data.append(df)

        return pd.concat(all_data, ignore_index=True)

env_data = load_environment_data()
growth_df = load_growth_data()

if not env_data or growth_df.empty:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_EC.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =========================================================
# TAB 1 : 실험 개요
# =========================================================
with tab1:
    st.subheader("🔬 연구 배경 및 목적")
    st.markdown("""
    본 연구는 **극지식물**의 생육에 영향을 미치는 **양액 EC 농도**에 따라  
    생장 지표가 어떻게 달라지는지 비교 분석하여 **최적 EC 농도**를 도출하는 것을 목표로 한다.
    """)

    overview_df = pd.DataFrame({
        "학교명": SCHOOL_EC.keys(),
        "EC 목표": SCHOOL_EC.values(),
        "개체수": growth_df.groupby("학교").size().values,
        "색상": [SCHOOL_COLOR[s] for s in SCHOOL_EC.keys()]
    })

    st.subheader("🏫 학교별 EC 조건")
    st.dataframe(overview_df, use_container_width=True)

    col1, col2, col3, col4 = st.columns(4)

    total_count = len(growth_df)
    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_humi = pd.concat(env_data.values())["humidity"].mean()
    optimal_ec = growth_df.groupby("EC")["생중량(g)"].mean().idxmax()

    col1.metric("총 개체수", f"{total_count} 개")
    col2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    col3.metric("평균 습도", f"{avg_humi:.1f} %")
    col4.metric("최적 EC", f"{optimal_ec} ⭐")

# =========================================================
# TAB 2 : 환경 데이터
# =========================================================
with tab2:
    st.subheader("📊 학교별 환경 평균 비교")

    env_avg = pd.concat(env_data.values()).groupby("학교").mean(numeric_only=True).reset_index()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["temperature"]), row=1, col=1)
    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["humidity"]), row=1, col=2)
    fig.add_trace(go.Bar(x=env_avg["학교"], y=env_avg["ph"]), row=2, col=1)

    fig.add_trace(go.Bar(
        x=list(SCHOOL_EC.keys()),
        y=list(SCHOOL_EC.values()),
        name="목표 EC"
    ), row=2, col=2)

    fig.add_trace(go.Bar(
        x=env_avg["학교"],
        y=env_avg["ec"],
        name="실측 EC"
    ), row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=df["time"], y=df["temperature"], name="온도"))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["humidity"], name="습도"))
        fig2.add_trace(go.Scatter(x=df["time"], y=df["ec"], name="EC"))

        fig2.add_hline(
            y=SCHOOL_EC[school_option],
            line_dash="dash",
            annotation_text="목표 EC"
        )

        fig2.update_layout(
            title=f"{school_option} 환경 변화 시계열",
            font=PLOTLY_FONT
        )
        st.plotly_chart(fig2, use_container_width=True)

        with st.expander("📂 환경 데이터 원본"):
            st.dataframe(df, use_container_width=True)

            buffer = io.BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8-sig")
            buffer.seek(0)

            st.download_button(
                "CSV 다운로드",
                data=buffer,
                file_name=f"{school_option}_환경데이터.csv",
                mime="text/csv"
            )

# =========================================================
# TAB 3 : 생육 결과
# =========================================================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    ec_weight = growth_df.groupby("EC")["생중량(g)"].mean().reset_index()
    best_ec = ec_weight.loc[ec_weight["생중량(g)"].idxmax(), "EC"]

    fig = px.bar(
        ec_weight,
        x="EC",
        y="생중량(g)",
        color="EC",
        title="EC별 평균 생중량 비교"
    )
    fig.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(f"### ⭐ 최적 EC 농도: **{best_ec} (하늘고)**")

    fig2 = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig2.add_trace(go.Bar(x=ec_weight["EC"], y=ec_weight["생중량(g)"]), row=1, col=1)

    fig2.add_trace(go.Bar(
        x=growth_df.groupby("EC")["잎 수(장)"].mean().index,
        y=growth_df.groupby("EC")["잎 수(장)"].mean()
    ), row=1, col=2)

    fig2.add_trace(go.Bar(
        x=growth_df.groupby("EC")["지상부 길이(mm)"].mean().index,
        y=growth_df.groupby("EC")["지상부 길이(mm)"].mean()
    ), row=2, col=1)

    fig2.add_trace(go.Bar(
        x=growth_df.groupby("EC").size().index,
        y=growth_df.groupby("EC").size()
    ), row=2, col=2)

    fig2.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📦 학교별 생중량 분포")
    fig3 = px.box(
        growth_df,
        x="학교",
        y="생중량(g)",
        color="학교"
    )
    fig3.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("📈 상관관계 분석")
    col1, col2 = st.columns(2)

    with col1:
        fig4 = px.scatter(
            growth_df,
            x="잎 수(장)",
            y="생중량(g)",
            color="학교"
        )
        fig4.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig4, use_container_width=True)

    with col2:
        fig5 = px.scatter(
            growth_df,
            x="지상부 길이(mm)",
            y="생중량(g)",
            color="학교"
        )
        fig5.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig5, use_container_width=True)

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
