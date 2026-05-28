import streamlit as st
import streamlit.components.v1 as components
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
        "塑料敞口": "#333333",
        "实心木塞": "#8B7355",
        "真空中空塞": "#C0C0C0"
    },
    "内外壁": {
        "单层塑料": "#6B8DD6",
        "单层玻璃": "#B8D4E3",
        "单层不锈钢": "#A8A8A8",
        "双层塑料": "#4A6FA5",
        "双层玻璃": "#9EC5D8",
        "双层不锈钢": "#888888"
    },
    "夹层": {
        "无夹层": "transparent",
        "填充空气": "#F0F0F0",
        "抽真空": "#1a1a2e"
    },
    "涂层": {
        "无涂层": "transparent",
        "镀银涂层": "#E8E8E8"
    }
}

# ===================== 2. 数据库功能 =====================
@st.cache_resource
def get_connection():
    return sqlite3.connect('thermos_scores.db', check_same_thread=False)

def init_db():
    conn = get_connection()
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
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO submissions (name, stopper, wall, gap, coating, score)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, stopper, wall, gap, coating, score))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = get_connection()
    df = pd.read_sql_query('SELECT name, score, stopper, wall, gap, coating FROM submissions ORDER BY score DESC', conn)
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
    
    # 优化后的加成算法
    if selections["内外壁"] in ["单层不锈钢", "双层不锈钢"]:
        if selections["夹层"] == "抽真空":
            total_thermal += 35
        elif selections["夹层"] == "填充空气":
            total_thermal += 15
    
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
    is_single_wall = not is_double_wall
    
    svg = f'''
    <svg width="600" height="520" viewBox="0 0 600 520">
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
        
        <!-- 外层瓶壁 -->
        <path d="M180 100 L170 120 L170 360 Q170 400 200 400 L240 400 Q270 400 270 360 L270 120 L260 100 Z" fill="url(#wallGradient)" stroke="#333" stroke-width="3"/>
        
        <!-- 双层：内层瓶壁 -->
        {'<path d="M250 120 L255 130 L255 350 Q255 390 245 390 L235 390 Q225 390 225 350 L225 130 L230 120 Z" fill="{wall_color}" opacity="0.5" stroke="#555" stroke-width="2"/>' if is_double_wall else ''}
        
        <!-- 双层：夹层（两层瓶壁之间） -->
        {f'<path d="M225 120 L225 350 Q225 390 235 390 L245 390 Q255 390 255 350 L255 130 Z" fill="{gap_color}" opacity="0.6"/>' if is_double_wall and gap != "无夹层" else ''}
        
        <!-- 涂层（内壁内侧） -->
        {f'<path d="M228 130 L228 345 Q228 385 237 385 L243 385 Q252 385 252 345 L252 130 Z" fill="{coating_color}" opacity="0.4" filter="url(#glow)"/>' if show_coating else ''}
        
        <!-- 瓶口 -->
        <path d="M180 80 L175 100 L265 100 L260 80 Z" fill="url(#wallGradient)" stroke="#333" stroke-width="3"/>
        
        <!-- 瓶塞 -->
        <rect x="190" y="50" width="60" height="30" rx="6" fill="url(#stopperGradient)" stroke="#333" stroke-width="2"/>
        <path d="M175 80 L165 100 L190 95 L250 95 L275 100 L265 80 Z" fill="url(#stopperGradient)" stroke="#333" stroke-width="2"/>
        
        <!-- 瓶底 -->
        <ellipse cx="220" cy="403" rx="52" ry="12" fill="{wall_color}" opacity="0.8" stroke="#333" stroke-width="3"/>
        
        <!-- ===== 标注线 - 纵向分布避免重叠 ===== -->
        
        <!-- 瓶塞标注 - 右侧上方 Y=65 -->
        <line x1="275" y1="65" x2="250" y2="65" stroke="#ff6b6b" stroke-width="2"/>
        <text x="280" y="69" font-size="15" fill="#ff6b6b" font-weight="bold">瓶塞: {stopper}</text>
        
        <!-- 涂层标注 - 左侧上方 Y=150 -->
        {f'<line x1="160" y1="150" x2="225" y2="150" stroke="#a855f7" stroke-width="2"/>' if show_coating else '<line x1="140" y1="150" x2="165" y2="150" stroke="#666" stroke-width="1" stroke-dasharray="3,3"/>'}
        {f'<text x="155" y="146" font-size="15" fill="#a855f7" font-weight="bold" text-anchor="end">涂层: {coating}</text>' if show_coating else '<text x="135" y="146" font-size="12" fill="#666" text-anchor="end">涂层</text>'}
        
        <!-- 夹层标注 - 右侧中间 Y=260 -->
        {f'<line x1="275" y1="260" x2="255" y2="260" stroke="#ffe66d" stroke-width="2"/>' if is_double_wall else ''}
        {f'<text x="280" y="264" font-size="15" fill="#ffe66d" font-weight="bold">夹层: {gap}</text>' if is_double_wall else '<text x="280" y="264" font-size="13" fill="#666">单层无夹层</text>'}
        
        <!-- 内外壁标注 - 右侧下方 Y=340 -->
        <line x1="275" y1="340" x2="270" y2="340" stroke="#4ecdc4" stroke-width="2"/>
        <text x="280" y="344" font-size="15" fill="#4ecdc4" font-weight="bold">内外壁: {wall}</text>
        
        <!-- 底部标题 -->
        <text x="220" y="430" text-anchor="middle" font-size="16" fill="#888" font-weight="bold">保温瓶模型</text>
    </svg>
    '''
    return svg

# ===================== 6. 主应用代码 =====================
st.set_page_config(page_title="保温杯终极设计师", layout="wide")
st.title("🥤 保温杯终极设计师")

# 初始化数据库
init_db()

# ===================== 初始化session_state =====================
if 'submitted_score' not in st.session_state:
    st.session_state.submitted_score = None
if 'show_leaderboard' not in st.session_state:
    st.session_state.show_leaderboard = False

RANDOM_NAMES = ["无名大侠", "神秘工匠", "设计新星", "创意达人", "探索先锋", "材料达人"]

# ===================== 英雄榜弹窗 =====================
@st.dialog("🏆 全班排行榜", width="large")
def show_leaderboard_dialog():
    leaderboard = get_leaderboard()
    if not leaderboard.empty:
        st.dataframe(leaderboard, use_container_width=True)
    else:
        st.info("暂无提交记录，成为第一个提交者吧！")
    if st.button("关闭", key="close_board"):
        st.session_state.show_leaderboard = False
        st.rerun()

# 点击英雄榜按钮触发弹窗
if st.session_state.show_leaderboard:
    show_leaderboard_dialog()

# ===================== 侧边栏 - 工程控制台 =====================
st.sidebar.header("️ 工程控制台")

stopper_label = st.sidebar.selectbox("瓶塞选择", get_material_options("瓶塞"), index=0)
wall_label = st.sidebar.selectbox("内外壁选择", get_material_options("内外壁"), index=0)

stopper = parse_material_label(stopper_label)
wall = parse_material_label(wall_label)
is_double_wall = "双层" in wall

# 单层材料不能选夹层，自动锁定为"无夹层"
if is_double_wall:
    gap_label = st.sidebar.selectbox("夹层选择", get_material_options("夹层"), index=0)
else:
    st.sidebar.selectbox("夹层选择", ["无夹层 ➡️(效能0) ¥0 (单层不可选)"], index=0, disabled=True)
    gap_label = "无夹层 ➡️(效能0) ¥0 (单层不可选)"

coating_label = st.sidebar.selectbox("涂层选择", get_material_options("涂层"), index=0)

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

# ===================== 智能评语 =====================
def get_evaluation(score):
    if score >= 50:
        return "🌟", "保温杯大师！您的设计太出色了！", "#FFD700"
    elif score >= 40:
        return "👍", "优秀设计师！保温效果很好！", "#4CAF50"
    elif score >= 30:
        return "💪", "不错的设计！可以再优化一下～", "#2196F3"
    elif score >= 20:
        return "🔧", "继续尝试！多试几种组合吧～", "#FF9800"
    else:
        return "", "初次探索！慢慢发现其中的奥秘！", "#9E9E9E"

# ===================== 主区域 =====================
col_left, col_right = st.columns([2.5, 1.5])

# 左列：大保温瓶模型 + 配置信息
with col_left:
    st.subheader("🧪 保温杯模型")
    svg_content = generate_thermos_svg(stopper, wall, gap, coating)
    components.html(
        f'''
        <div style="display: flex; justify-content: center; align-items: center; padding: 5px;">
            {svg_content}
        </div>
        ''',
        height=560
    )
    st.markdown(f"**当前配置:** {stopper} | {wall} | {gap} | {coating}")

# 右列：雷达图 + 性能指标 + 降温曲线
with col_right:
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
        title='',
        height=300
    )
    fig_radar.update_traces(fill='toself')
    fig_radar.update_layout(margin=dict(l=30, r=30, t=30, b=30))
    st.plotly_chart(fig_radar, use_container_width=True)

    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("保温效能", f"{total_thermal}")
    with metric_col2:
        st.metric("总成本", f"¥{total_cost}")
    with metric_col3:
        st.metric("坚固度", f"{total_strength}")

    t = np.linspace(0, 60, 100)
    k = 0.1 - (total_thermal / 500)
    k = max(0.01, k)
    T = 20 + 80 * np.exp(-k * t)
    temp_data = pd.DataFrame({'时间(分钟)': t, '温度(℃)': T})
    fig_temp = px.line(
        temp_data,
        x='时间(分钟)',
        y='温度(℃)',
        title='降温模拟',
        range_y=[20, 100],
        height=200
    )
    fig_temp.update_layout(margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(fig_temp, use_container_width=True)

# ===================== 提交区 =====================
st.divider()

# 姓名输入框
designer_name = st.text_input("设计师姓名/代号", label_visibility="collapsed", placeholder="请输入姓名（留空将使用随机称号）")

# 按钮区域
btn_col1, btn_col2 = st.columns([1, 1])

with btn_col1:
    if st.button("✅ 提交我的设计", type="primary", use_container_width=True):
        final_name = designer_name if designer_name else np.random.choice(RANDOM_NAMES)
        save_submission(final_name, stopper, wall, gap, coating, score)
        st.session_state.submitted_score = score
        st.rerun()

with btn_col2:
    if st.button("🏆 英雄榜", use_container_width=True):
        st.session_state.show_leaderboard = True
        st.rerun()

if st.session_state.submitted_score is not None:
    emoji, comment, color = get_evaluation(st.session_state.submitted_score)
    st.balloons()
    st.markdown(f"""
    <div style="text-align: center; padding: 20px; border-radius: 15px; background: linear-gradient(135deg, {color}22, {color}44); margin: 10px 0;">
        <h1 style="font-size: 50px; margin: 0;">{emoji}</h1>
        <h2 style="color: {color}; margin: 5px 0;">{comment}</h2>
        <h1 style="font-size: 40px; color: {color}; margin: 5px 0;">{st.session_state.submitted_score:.2f} 分</h1>
    </div>
    """, unsafe_allow_html=True)
    if st.button(" 继续探索"):
        st.session_state.submitted_score = None
        st.rerun()
