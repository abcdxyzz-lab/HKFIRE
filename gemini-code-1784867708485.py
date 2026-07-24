import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import plotly.express as px
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials

# ================= 配置與介面設定 =================
st.set_page_config(page_title="HK FIRE Dashboard", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    [data-testid="stMetric"] { background-color: #1E2127; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: #CBD5E1 !important; }
    </style>
""", unsafe_allow_html=True)

# ================= 連線 Google Sheets =================
@st.cache_resource
def get_gspread_client():
    creds_dict = json.loads(st.secrets["GOOGLE_JSON"])
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_sheet():
    client = get_gspread_client()
    return client.open_by_url(st.secrets["SHEET_URL"]).sheet1

# ================= 數據儲存與讀取邏輯 =================
def load_data():
    try:
        sheet = get_sheet()
        val = sheet.acell('A1').value
        if val:
            return json.loads(val)
    except Exception as e:
        st.warning(f"讀取雲端資料失敗，將使用預設空白表格。錯誤：{e}")
        
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
    try:
        sheet = get_sheet()
        sheet.update_acell('A1', json.dumps(data, ensure_ascii=False))
        st.toast('✅ 數據已成功同步至 Google Sheets！', icon='☁️')
    except Exception as e:
        st.error(f"❌ 儲存失敗：{e}")

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
def get_stock_price_hkd(ticker, fx_rates_dict):
    if not ticker: return 0.0
    try:
        info = yf.Ticker(ticker).fast_info
        price = info['lastPrice']
        currency = info.get('currency', 'USD').upper()
        
        if currency == "HKD":
            return price
        elif currency in fx_rates_dict:
            return price * fx_rates_dict[currency]
        else:
            return price
    except:
        return 0.0

fx_rates = get_fx_rates()

# ================= 介面佈局 =================
st.title("🔥 香港財務自由 (FIRE) Dashboard")

# 🌟 這裡加入了全新的「📈 個股明細」分頁
tab_dash, tab_assets, tab_stock_detail, tab_inc_act, tab_inc_pass, tab_exp_m, tab_exp_y = st.tabs([
    "📊 核心指標與圖表", "💰 當前總資產", "📈 個股明細", "💼 每月主動收入", "💸 每月被動收入", "💳 每月支出", "📅 每年支出"
])

def create_editor(tab, title, columns, data_key, height=400):
    with tab:
        st.subheader(title)
        df = pd.DataFrame(data[data_key], columns=columns)
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=height, key=data_key)
        return edited_df

with tab_assets:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 股票 (自動抓取股價)")
        st.caption("港股加 .HK，美股直打，日股加 .T (如 7203.T)")
        df_stocks = pd.DataFrame(data["stocks"], columns=["股票代號", "股數"])
        edited_stocks = st.data_editor(df_stocks, height=600, use_container_width=True, key="stocks_editor", num_rows="dynamic")
        
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
def safe_num(val):
    try: return float(val) if pd.notna(val) and val != "" else 0.0
    except: return 0.0

def safe_str(val):
    return str(val).strip() if pd.notna(val) and val != "" else ""

hk_stock_val = 0.0
us_stock_val = 0.0
jp_stock_val = 0.0
stock_details_list = [] # 🌟 用來儲存每隻股票嘅詳細資料

for _, row in edited_stocks.iterrows():
    ticker = safe_str(row["股票代號"]).upper()
    shares = safe_num(row["股數"])
    if ticker and shares > 0:
        price_hkd = get_stock_price_hkd(ticker, fx_rates)
        val = shares * price_hkd
        
        region = "美股"
        if ticker.endswith(".HK"):
            hk_stock_val += val
            region = "港股"
        elif ticker.endswith(".T"):
            jp_stock_val += val
            region = "日股"
        else:
            us_stock_val += val
            
        # 記錄每隻股票嘅換算結果
        stock_details_list.append({
            "股票代號": ticker,
            "市場": region,
            "持有股數": shares,
            "現價 (HKD)": price_hkd,
            "總市值 (HKD)": val
        })

stock_value_hkd = hk_stock_val + us_stock_val + jp_stock_val
property_net_value = sum([safe_num(row["現值 (HKD)"]) - safe_num(row["按揭餘額 (HKD)"]) for _, row in df_real_estate.iterrows() if safe_str(row["物業名稱"])])
cash_value_hkd = sum([float(val) * fx_rates.get(curr, 1.0) for curr, val in data["cash"].items()])
bond_value_hkd = sum([safe_num(row["現值 (HKD)"]) for _, row in df_bonds.iterrows() if safe_str(row["債券名稱"])])

total_net_assets = stock_value_hkd + property_net_value + cash_value_hkd + bond_value_hkd
liquid_assets = total_net_assets - property_net_value

m_active = sum([safe_num(row["金額 (HKD)"]) for _, row in df_active_inc.iterrows() if safe_str(row["項目名稱"])])
m_passive = sum([safe_num(row["金額 (HKD)"]) for _, row in df_passive_inc.iterrows() if safe_str(row["項目名稱"])])
m_exp = sum([safe_num(row["金額 (HKD)"]) for _, row in df_exp_m.iterrows() if safe_str(row["項目名稱"])])
y_exp = sum([safe_num(row["金額 (HKD)"]) for _, row in df_exp_y.iterrows() if safe_str(row["項目名稱"])])

annual_total_exp = (m_exp * 12) + y_exp
annual_surplus = ((m_active + m_passive) * 12) - annual_total_exp

# ================= 新增：個股明細分頁內容 =================
with tab_stock_detail:
    if stock_details_list:
        col_list, col_tree = st.columns([1, 1.2])
        
        df_stocks_display = pd.DataFrame(stock_details_list)
        # 自動由大至小排序
        df_stocks_display = df_stocks_display.sort_values(by="總市值 (HKD)", ascending=False).reset_index(drop=True)
        # 計算佔比
        df_stocks_display["佔股票總值"] = (df_stocks_display["總市值 (HKD)"] / stock_value_hkd)
        
        with col_list:
            st.subheader("📋 個股即時市值清單")
            st.dataframe(
                df_stocks_display.style.format({
                    "持有股數": "{:,.0f}",
                    "現價 (HKD)": "${:,.2f}",
                    "總市值 (HKD)": "${:,.2f}",
                    "佔股票總值": "{:.1%}"
                }),
                use_container_width=True,
                height=550
            )
            
        with col_tree:
            st.subheader("📊 股票矩陣分佈 (Treemap)")
            # 畫出極具專業感嘅矩陣圖
            fig_tree = px.treemap(
                df_stocks_display, 
                path=["市場", "股票代號"], 
                values="總市值 (HKD)",
                color="市場", 
                color_discrete_map={"港股":"#FF595E", "美股":"#1982C4", "日股":"#FFCA3A"}
            )
            fig_tree.update_traces(textinfo="label+value+percent parent")
            fig_tree.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_tree, use_container_width=True)
    else:
        st.info("尚無股票數據，請先於「💰 當前總資產」分頁中輸入股票代號及股數。")


# ================= Dashboard 儀表板 =================
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
            def df_to_list(df):
                return df.fillna("").values.tolist()
            
            data["stocks"] = df_to_list(edited_stocks)
            data["real_estate"] = df_to_list(df_real_estate)
            data["bonds"] = df_to_list(df_bonds)
            data["active_income"] = df_to_list(df_active_inc)
            data["passive_income"] = df_to_list(df_passive_inc)
            data["monthly_expenses"] = df_to_list(df_exp_m)
            data["annual_expenses"] = df_to_list(df_exp_y)
            
            save_data(data)

    target_fire = annual_total_exp / fire_rate if fire_rate > 0 else 0
    fire_progress = (total_net_assets / target_fire * 100) if target_fire > 0 else 0

    st.divider()

    m1, m2, m3 = st.columns(3)
    m1.metric("🎯 目標 FIRE 金額", f"HK$ {target_fire:,.0f}")
    m2.metric("💰 現行資產淨值", f"HK$ {total_net_assets:,.0f}")
    m3.metric("💧 總流動資產", f"HK$ {liquid_assets:,.0f}")
    
    m4, m5, m6 = st.columns(3)
    m4.metric("💳 每年總支出", f"HK$ {annual_total_exp:,.0f}")
    m5.metric("📈 每年盈餘", f"HK$ {annual_surplus:,.0f}")
    m6.metric("🔥 財務自由進度", f"{fire_progress:,.2f} %")

    st.progress(min(fire_progress / 100, 1.0))
    st.markdown("<br>", unsafe_allow_html=True)
    
    chart_col1, chart_col2 = st.columns([1, 2])
    
    with chart_col1:
        st.subheader("資產分佈")
        pie_data = pd.DataFrame({
            "類別": ["港股", "美股", "日股", "地產(淨值)", "現金", "債券"],
            "金額": [hk_stock_val, us_stock_val, jp_stock_val, property_net_value, cash_value_hkd, bond_value_hkd]
        })
        pie_data = pie_data[pie_data["金額"] > 0]
        if not pie_data.empty:
            custom_colors = ["#FF595E", "#1982C4", "#FFCA3A", "#8AC926", "#F4A261", "#6A4C93"]
            fig_pie = px.pie(pie_data, values="金額", names="類別", hole=0.4, 
                             color_discrete_sequence=custom_colors)
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
        current_liquid = liquid_assets
        
        for y in years:
            projected_assets.append(current_liquid + property_net_value)
            current_liquid = (current_liquid * (1 + growth_rate)) + annual_surplus
            
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
        
    st.divider()
    if target_fire > 0:
        if total_net_assets >= target_fire:
            st.success("🎉 恭喜你！根據目前的資產狀況，你已經成功達到財務自由！")
        else:
            fire_year = 0
            temp_liquid = liquid_assets
            temp_total = total_net_assets
            
            while temp_total < target_fire and fire_year < 100:
                fire_year += 1
                temp_liquid = (temp_liquid * (1 + growth_rate)) + annual_surplus
                temp_total = temp_liquid + property_net_value
                
            if fire_year >= 100:
                st.warning("⚠️ 根據目前盈餘與投資回報率，距離財務自由仍需超過 100 年。建議減少支出或嘗試提高收入！")
            else:
                st.info(f"🚀 堅持下去！根據目前預測，你將會於 **第 {fire_year} 年** 達到財務自由！")
    else:
        st.info("💡 請先輸入相關支出數據，以計算你的財務自由進度。")
