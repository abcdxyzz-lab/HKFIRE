import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px
import plotly.graph_objects as go

# ================= 配置與介面設定 =================
st.set_page_config(page_title="HK FIRE Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stMetric { background-color: #1E2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

DATA_FILE = "fire_record.json"

# ================= 數據儲存與讀取邏輯 =================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "stocks": [["", 0] for _ in range(20)],
        "real_estate": [["", 0.0, 0.0] for _ in range(10)],
        "cash": {"USD": 0.0, "HKD": 0.0, "EUR": 0.0, "GBP": 0.0, "JPY": 0.0, "TWD": 0.0},
        "bonds": [["", 0.0] for _ in range(10)],
        "active_income": [["", 0.0] for _ in range(10)],
        "passive_income": [["", 0.0] for _ in range(10)],
        "monthly_expenses": [["", 0.0] for _ in range(25)],
        "annual_expenses": [["", 0.0] for _ in range(10)],
        "settings": {"fire_rate": 0.04}
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    st.toast('✅ 數據已成功儲存！', icon='💾')

if 'data' not in st.session_state:
    st.session_state.data = load_data()

data = st.session_state.data

# ================= 即時金融數據抓取 =================
@st.cache_data(ttl=3600)
def get_fx_rates():
    rates = {"HKD": 1.0}
    symbols = {"USD": "HKD=X", "EUR": "EURHKD=X", "GBP": "GBPHKD=X", "JPY": "JPYHKD=X", "TWD": "TWDHKD=X"}
    for curr, sym in symbols.items():
        try:
            rates[curr] = yf.Ticker(sym).fast_info['lastPrice']
        except:
            rates[curr] = 0.0
    return rates

@st.cache_data(ttl=900)
def get_stock_price_hkd(ticker, usd_hkd_rate):
    if not ticker: return 0.0
    try:
        price = yf.Ticker(ticker).fast_info['lastPrice']
        if not str(ticker).upper().endswith(".HK"):
            price *= usd_hkd_rate
        return price
    except:
        return 0.0

fx_rates = get_fx_rates()
usd_hkd = fx_rates.get("USD", 7.8)

# ================= 介面佈局 =================
st.title("🔥 香港財務自由 (FIRE) Dashboard")

tab_dash, tab_assets, tab_inc_act, tab_inc_pass, tab_exp_m, tab_exp_y = st.tabs([
    "📊 核心指標與圖表", "💰 當前總資產", "💼 每月主動收入", "💸 每月被動收入", "💳 每月支出", "📅 每年支出"
])

# --- 🎯 這裡修正了錯誤：加上了 key=data_key ---
def create_editor(tab, title, columns, data_key, height=400):
    with tab:
        st.subheader(title)
        df = pd.DataFrame(data[data_key], columns=columns)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=height, key=data_key)
        data[data_key] = edited_df.values.tolist()
        return edited_df

with tab_assets:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 股票 (自動抓取股價)")
        st.caption("港股請加 .HK (例: 0700.HK)，美股直接輸入代號 (例: AAPL)")
        df_stocks = pd.DataFrame(data["stocks"], columns=["股票代號", "股數"])
        # --- 🎯 這裡修正了錯誤：加上了 key="stocks_editor" ---
        edited_stocks = st.data_editor(df_stocks, height=400, use_container_width=True, key="stocks_editor")
        data["stocks"] = edited_stocks.values.tolist()
        
        st.subheader("💵 現金 (自動匯率換算 HKD)")
        c1, c2, c3 = st.columns(3)
        data["cash"]["HKD"] = c1.number_input("HKD 港元", value=float(data["cash"]["HKD"]))
        data["cash"]["USD"] = c2.number_input("USD 美元", value=float(data["cash"]["USD"]))
        data["cash"]["EUR"] = c3.number_input("EUR 歐元", value=float(data["cash"]["EUR"]))
        data["cash"]["GBP"] = c1.number_input("GBP 英鎊", value=float(data["cash"]["GBP"]))
        data["cash"]["JPY"] = c2.number_input("JPY 日元", value=float(data["cash"]["JPY"]))
        data["cash"]["TWD"] = c3.number_input("TWD 台幣", value=float(data["cash"]["TWD"]))

    with col2:
        df_real_estate = create_editor(tab_assets, "🏠 地產", ["物業名稱", "現值 (HKD)", "按揭餘額 (HKD)"], "real_estate")
        df_bonds = create_editor(tab_assets, "📜 債券", ["債券名稱", "現值 (HKD)"], "bonds", height=300)

df_active_inc = create_editor(tab_inc_act, "💼 每月主動收入", ["項目名稱", "金額 (HKD)"], "active_income")
df_passive_inc = create_editor(tab_inc_pass, "💸 每月被動收入", ["項目名稱", "金額 (HKD)"], "passive_income")
df_exp_m = create_editor(tab_exp_m, "💳 每月支出", ["項目名稱", "金額 (HKD)"], "monthly_expenses", height=600)
df_exp_y = create_editor(tab_exp_y, "📅 每年支出 (非月費)", ["項目名稱", "金額 (HKD)"], "annual_expenses")

# ================= 核心邏輯計算 =================
stock_value_hkd = sum([row[1] * get_stock_price_hkd(row[0], usd_hkd) for row in data["stocks"] if row[0]])
property_net_value = sum([float(row[1]) - float(row[2]) for row in data["real_estate"] if row[0]])
cash_value_hkd = sum([float(val) * fx_rates.get(curr, 1.0) for curr, val in data["cash"].items()])
bond_value_hkd = sum([float(row[1]) for row in data["bonds"] if row[0]])
total_net_assets = stock_value_hkd + property_net_value + cash_value_hkd + bond_value_hkd

m_active = sum([float(row[1]) for row in data["active_income"] if row[0]])
m_passive = sum([float(row[1]) for row in data["passive_income"] if row[0]])
m_exp = sum([float(row[1]) for row in data["monthly_expenses"] if row[0]])
y_exp = sum([float(row[1]) for row in data["annual_expenses"] if row[0]])

annual_total_exp = (m_exp * 12) + y_exp
annual_surplus = ((m_active + m_passive) * 12) - annual_total_exp

with tab_dash:
    col_rate, col_save = st.columns([3, 1])
    with col_rate:
        fire_rate_str = st.radio("選擇安全提領率 (SWR):", ["4%", "3.5%", "3%"], horizontal=True, 
                                 index=["4%", "3.5%", "3%"].index(f"{int(data['settings']['fire_rate']*100)}%") if data['settings'].get('fire_rate') else 0)
        data["settings"]["fire_rate"] = float(fire_rate_str.strip('%')) / 100
        fire_rate = data["settings"]["fire_rate"]
    with col_save:
        st.write("") 
        if st.button("💾 儲存所有記錄", use_container_width=True, type="primary"):
            save_data(data)

    target_fire = annual_total_exp / fire_rate if fire_rate > 0 else 0
    fire_progress = (total_net_assets / target_fire * 100) if target_fire > 0 else 0

    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🎯 目標 FIRE 金額", f"HK$ {target_fire:,.0f}")
    m2.metric("💰 現行資產淨值", f"HK$ {total_net_assets:,.0f}")
    m3.metric("📈 每年盈餘", f"HK$ {annual_surplus:,.0f}")
    m4.metric("🔥 財務自由進度", f"{fire_progress:,.2f} %")

    st.progress(min(fire_progress / 100, 1.0))
    st.markdown("<br>", unsafe_allow_html=True)
    
    chart_col1, chart_col2 = st.columns([1, 2])
    
    with chart_col1:
        st.subheader("資產分佈")
        pie_data = pd.DataFrame({
            "類別": ["股票", "地產(淨值)", "現金", "債券"],
            "金額": [stock_value_hkd, property_net_value, cash_value_hkd, bond_value_hkd]
        })
        pie_data = pie_data[pie_data["金額"] > 0]
        if not pie_data.empty:
            fig_pie = px.pie(pie_data, values="金額", names="類別", hole=0.4, 
                             color_discrete_sequence=px.colors.sequential.Teal)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("尚無資產數據")

    with chart_col2:
        st.subheader("未來 20 年複利成長預測")
        growth_rate = st.selectbox("選擇預期年化報酬率:", [0.04, 0.05, 0.06, 0.07, 0.08], 
                                   format_func=lambda x: f"{int(x*100)}%", index=1)
        
        years = list(range(21))
        projected_assets = []
        current_val = total_net_assets
        
        for y in years:
            projected_assets.append(current_val)
            current_val = (current_val * (1 + growth_rate)) + annual_surplus
            
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(x=years, y=projected_assets, mode='lines+markers', 
                                      name="預期資產", line=dict(color='#00FF7F', width=3)))
        fig_line.add_hline(y=target_fire, line_dash="dash", line_color="red", annotation_text="FIRE 目標")
        
        fig_line.update_layout(
            xaxis_title="未來年數", yaxis_title="資產淨值 (HKD)",
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10)
        )
        st.plotly_chart(fig_line, use_container_width=True)
