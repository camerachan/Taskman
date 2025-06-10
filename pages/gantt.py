import streamlit as st

st.set_page_config(page_title="Gantt Chart", layout="wide")

st.title("📈 ガントチャートビュー")
st.write("このページではタスクをガントチャートで可視化します（仮表示）。")

# デモ用に仮データを表示
import pandas as pd

df = pd.DataFrame({
    "Task": ["仕様作成", "コーディング", "レビュー"],
    "Start": ["2024-06-01", "2024-06-10", "2024-06-20"],
    "End":   ["2024-06-09", "2024-06-19", "2024-06-25"]
})

st.dataframe(df)