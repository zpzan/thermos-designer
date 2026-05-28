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
        "单层不锈钢": (-30, 5, 50),
        "双层塑料": (10, 4, 50),
        "双层玻璃": (20, 8, 10),
        "双层不锈钢": (-20, 10, 80)
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

# 材料颜色映射
COLORS = {
    "瓶塞": {
        "塑料敞口": "#8B4513",
        "实心木塞": "#D2691E",
        "真空中空塞": "#C0C0C0"
    },
    "内外壁": {
        "单层塑料": "#4A90D9",
        "单层玻璃": "#87CEEB",
        "单层不锈钢": "#708090",
        "双层塑料": "#357ABD",
        "双层玻璃": "#5BA3C0",
        "双层不锈钢": "#4A5568"
    },
    "夹层": {
        "无夹层": "transparent",
        "填充空气": "#E0E0E0",
        "抽真空": "#1a1a2e"
    },
    "涂层": {
        "无涂层": "transparent",
        "镀银涂层": "#C0C0C0"
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
    
    if selections["内外壁"] in ["单层不锈钢", "双层不锈钢"] and selections["夹层"] == "抽真空":
        total_thermal += 20
    
    if total_cost > 30:
        return total_thermal, total_cost, total_strength, 0
    else:
        score = (total_thermal * 0.5) + ((30 - total_cost) * 0.3) + (total_strength * 0.2)
        return total_thermal, total_cost, total_strength, score

# ===================== 4. 生成带属性的选项标签 =====================
def get_material_options(category):
    options = []
    for name, (thermal, cost, strength) in MATERIALS[category].items():
        thermal_icon = "🔥" if thermal > 0 else "❄️" if thermal < 0 else "➡️"
        options.append(f"{name} {thermal_icon}(效能{thermal}) ¥{cost}")
    return options

def parse_material_label(label):
    return label.split(" ")[0]

# ===================== 5. 生成保温杯SVG =====================
def generate_thermos_svg(stopper, wall, gap, coating):
    stopper_color = COLORS["瓶塞"].get(stopper, "#8B4513")
    wall_color = COLORS["内外壁"].get(wall, "#708090")
    gap_color = COLORS["夹层"].get(gap, "transparent")
    coating_color = COLORS["涂层"].get(coating, "transparent")
    
    is_double_wall = "双层" in wall
    show_coating = coating != "无涂层"
    
    svg = f'''
    <svg width="200" height="300" viewBox="0 0 200 300">
        <defs>
            <linearGradient id="wallGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:{wall_color};stop-opacity:1" />
                <stop offset="50%" style="stop-color:{wall_color};stop-opacity:0.8" />
                <stop offset="100%" style="stop-color:{wall_color};stop-opacity:1" />
            </linearGradient>
            <linearGradient id="stopperGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:{stopper_color};stop-opacity:1" />
                <stop offset="100%" style="stop-color:{stopper_color};stop-opacity:0.7" />
            </linearGradient>
            <filter id="glow">
                <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        
        <rect x="60" y="10" width="80" height="30" rx="5" fill="url(#stopperGradient)" stroke="#333" stroke-width="2"/>
        <path d="M55 40 L50 60 L70 55 L130 55 L150 60 L145 40 Z" fill="url(#stopperGradient)" stroke="#333" stroke-width="2"/>
        
        {f'<path d="M60 60 L55 70 L65 68 L65 260 Q65 280 85 280 L115 280 Q135 280 135 260 L135 68 L145 70 L140 60 Z" fill="{gap_color}" opacity="0.6"/>' if gap != "无夹层" else ''}
        
        <path d="M65 68 L60 75 L60 260 Q60 285 80 285 L120 285 Q140 285 140 260 L140 75 L135 68 Z" fill="url(#wallGradient)" stroke="#333" stroke-width="2"/>
        
        {f'<path d="M70 75 L68 80 L68 255 Q68 278 82 278 L118 278 Q132 278 132 255 L132 80 L130 75 Z" fill="{wall_color}" opacity="0.5" stroke="#333" stroke-width="1"/>' if is_double_wall else ''}
        
        {f'<path d="M72 80 L70 85 L70 250 Q70 275 85 275 L115 275 Q130 275 130 250 L130 85 L128 80 Z" fill="{coating_color}" opacity="0.4" filter="url(#glow)"/>' if show_coating else ''}
        
        <ellipse cx="100" cy="285" rx="45" ry="10" fill="{wall_color}" opacity="0.8" stroke="#333" stroke-width="2"/>
        
        <text x="100" y="298" text-anchor="middle" font-size="12" fill="#666">保温瓶</text>
    </svg>
    '''
    return svg

# ===================== 6. 主应用代码 =====================
st.set_page_config(page_title="保温杯终极设计师", layout="wide")
st.title("🥤 保温杯终极设计师")

init_db()

# ===================== 侧边栏 - 工程控制台 =====================
st.sidebar.header("🛠️ 工程控制台")

stopper_label = st.sidebar.selectbox("瓶塞选择", get_material_options("瓶塞"), index=0)
wall_label = st.sidebar.selectbox("内外壁选择", get_material_options("内外壁"), index=0)
gap_label = st.sidebar.selectbox("夹层选择", get_material_options("夹层"), index=0)
coating_label = st.sidebar.selectbox("涂层选择", get_material_options("涂层"), index=0)

stopper = parse_material_label(stopper_label)
wall = parse_material_label(wall_label)
gap = parse_material_label(gap_label)
coating = parse_material_label(coating_label)

selections = {
    "瓶塞": stopper,
    "内外壁": wall,
    "夹层": gap,
    "涂层": coating
}

total_thermal, total_cost, total_strength, score = calculate_total(selections)
remaining_budget = 30 - total_cost

st.sidebar.metric(
    label="剩余预算",
    value=f"{remaining_budget}",
    delta_color="inverse" if remaining_budget < 0 else "normal"
)

if total_cost > 30:
    st.error("⚠️ 预算超支，工程破产！")

# ===================== 主区域 =====================
col1, col2, col3 = st.columns([2, 1.5, 1.5])

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

# 中列：保温瓶可视化
with col2:
    st.subheader("🧪 保温杯模型")
    st.markdown(generate_thermos_svg(stopper, wall, gap, coating), unsafe_allow_html=True)
    st.markdown(f"""
    **当前配置:**
    - 瓶塞: {stopper}
    - 内外壁: {wall}
    - 夹层: {gap}
    - 涂层: {coating}
    """)

# 右列：降温曲线
with col3:
    st.subheader("📈 降温模拟")
    t = np.linspace(0, 60, 100)
    k = 0.1 - (total_thermal / 500)
    k = max(0.01, k)
    T = 20 + 80 * np.exp(-k * t)
    temp_data = pd.DataFrame({'时间(分钟)': t, '温度(℃)': T})
    fig_temp = px.line(
        temp_data,
        x='时间(分钟)',
        y='温度(℃)',
        title='降温曲线',
        range_y=[20, 100],
        height=250
    )
    fig_temp.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_temp, use_container_width=True)

    st.subheader("📋 性能指标")
    st.metric("保温效能", f"{total_thermal}")
    st.metric("总成本", f"¥{total_cost}")
    st.metric("坚固度", f"{total_strength}")
    st.metric("综合得分", f"{score:.2f}")

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
