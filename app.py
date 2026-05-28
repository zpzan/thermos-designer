import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import numpy as np

# ===================== 1. 材料字典定义 =====================
MATERIALS = {
    "瓶塞": {
        "塑料敞口": (-20, 1, 10),
        "实心木塞": (10, 3, 20),
        "真空中空塞": (30, 8, 15)
    },
    "内外壁": {
        "单层塑料": (5, 2, 30),
        "单层玻璃": (10, 4, 5),
        "单层不锈钢": (-30, 5, 50)
    },
    "夹层": {
        "无夹层": (0, 0, 0),
        "填充空气": (10, 2, 5),
        "抽真空": (40, 15, -5)
    },
    "涂层": {
        "无涂层": (0, 0, 0),
        "镀银涂层": (20, 10, 5)
    }
}

# ===================== 2. 数据库功能 =====================
def init_db():
    conn = sqlite3.connect('thermos_scores.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS submissions
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         name TEXT,
         stopper TEXT,
         wall TEXT,
         gap TEXT,
         coating TEXT,
         score REAL)
    ''')
    conn.commit()
    conn.close()

def save_submission(name, stopper, wall, gap, coating, score):
    conn = sqlite3.connect('thermos_scores.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO submissions (name, stopper, wall, gap, coating, score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, stopper, wall, gap, coating, score))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect('thermos_scores.db')
    df = pd.read_sql_query('SELECT * FROM submissions ORDER BY score DESC', conn)
    conn.close()
    return df

# ===================== 3. 物理算法与计算 =====================
def calculate_total(selections):
    total_thermal = 0
    total_cost = 0
    total_strength = 0
    
    for category, material in selections.items():
        thermal, cost, strength = MATERIALS[category][material]
        total_thermal += thermal
        total_cost += cost
        total_strength += strength
    
    # 隐藏加成算法
    if selections["内外壁"] == "单层不锈钢" and selections["夹层"] == "抽真空":
        total_thermal += 20
    
    # 计算总分
    if total_cost > 30:
        return total_thermal, total_cost, total_strength, 0
    else:
        score = (total_thermal * 0.5) + ((30 - total_cost) * 0.3) + (total_strength * 0.2)
        return total_thermal, total_cost, total_strength, score

# ===================== 4. 主应用代码 =====================
st.set_page_config(page_title="保温杯终极设计师", layout="wide")
st.title("🥤 保温杯终极设计师")

# 初始化数据库
init_db()

# ===================== 侧边栏 - 工程控制台 =====================
st.sidebar.header("🛠️ 工程控制台")

# 材料选择
stopper = st.sidebar.selectbox("瓶塞选择", list(MATERIALS["瓶塞"].keys()), index=0)
wall = st.sidebar.selectbox("内外壁选择", list(MATERIALS["内外壁"].keys()), index=0)
gap = st.sidebar.selectbox("夹层选择", list(MATERIALS["夹层"].keys()), index=0)
coating = st.sidebar.selectbox("涂层选择", list(MATERIALS["涂层"].keys()), index=0)

selections = {
    "瓶塞": stopper,
    "内外壁": wall,
    "夹层": gap,
    "涂层": coating
}

# 计算各项指标
total_thermal, total_cost, total_strength, score = calculate_total(selections)
remaining_budget = 30 - total_cost

# 显示预算余额
st.sidebar.metric(
    label="剩余预算",
    value=f"{remaining_budget}",
    delta_color="inverse" if remaining_budget < 0 else "normal"
)

if total_cost > 30:
    st.error("⚠️ 预算超支，工程破产！")

# ===================== 主区域 =====================
col1, col2 = st.columns(2)

# 左列：雷达图
with col1:
    st.subheader("📊 性能雷达图")
    cost_control = 30 - total_cost
    radar_data = pd.DataFrame({
        '维度': ['保温效能', '成本控制', '坚固度'],
        '数值': [total_thermal, cost_control, total_strength]
    })
    fig_radar = px.line_polar(
        radar_data,
        r='数值',
        theta='维度',
        line_close=True,
        range_r=[-30, 70],
        title='保温杯性能分析'
    )
    fig_radar.update_traces(fill='toself')
    st.plotly_chart(fig_radar, use_container_width=True)

# 右列：降温曲线
with col2:
    st.subheader("📈 降温模拟曲线")
    t = np.linspace(0, 60, 100)
    # 根据总保温效能计算衰减系数 k
    # 假设 k 与保温效能负相关：保温效能越高，k 越小
    k = 0.1 - (total_thermal / 500)
    k = max(0.01, k)  # 确保 k 不为负
    T = 20 + 80 * np.exp(-k * t)
    temp_data = pd.DataFrame({'时间(分钟)': t, '温度(℃)': T})
    fig_temp = px.line(
        temp_data,
        x='时间(分钟)',
        y='温度(℃)',
        title='保温杯降温模拟',
        range_y=[20, 100]
    )
    st.plotly_chart(fig_temp, use_container_width=True)

# ===================== 提交区 =====================
st.subheader("✅ 提交我的设计")
designer_name = st.text_input("设计师姓名/代号")
if st.button("提交我的设计"):
    if designer_name:
        save_submission(designer_name, stopper, wall, gap, coating, score)
        st.success(f"🎉 设计已提交！你的总分是: {score:.2f}")
    else:
        st.warning("请输入设计师姓名/代号")

# ===================== 排行榜 =====================
with st.expander("🏆 全班排行榜"):
    leaderboard = get_leaderboard()
    if not leaderboard.empty:
        st.dataframe(leaderboard, use_container_width=True)
    else:
        st.info("暂无提交记录，成为第一个提交者吧！")
