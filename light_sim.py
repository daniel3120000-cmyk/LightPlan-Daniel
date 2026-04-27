import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import json
import pymongo
import io
from datetime import datetime
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. ניהול מצב (State) ועיצוב דף
# ==========================================
st.set_page_config(page_title="LightPlan 3D - Daniel Halfon", layout="wide")

# אתחול זיכרון פנימי
if 'room_w' not in st.session_state: st.session_state['room_w'] = 6.0
if 'room_d' not in st.session_state: st.session_state['room_d'] = 8.0
if 'room_h' not in st.session_state: st.session_state['room_h'] = 2.8
if 'wall_mat' not in st.session_state: st.session_state['wall_mat'] = "טיח לבן"

st.title("🏙️ הסטודיו המקצועי של דניאל חלפון (Daniel Halfon)")
st.subheader("מערכת LightPlan 3D Ultimate: תאורה, AI וסנכרון ענן")
st.caption("פיתוח מקורי - חיבור לענן MongoDB ומנוע הנדסי משולב")

# ==========================================
# 2. חיבור למסד הנתונים (Cloud Database)
# ==========================================
@st.cache_resource
def init_connection():
    try:
        # שימוש ב-Secret המאובטח שהגדרנו
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception as e:
        return None

client = init_connection()
if client:
    db = client["LightPlanDB"]
    projects_col = db["Projects"]

# ==========================================
# 3. מנוע AI Vision (תיקון שגיאת 404)
# ==========================================
with st.sidebar.expander("🤖 סריקת חדר אוטומטית (AI Vision)", expanded=True):
    st.write("העלה תמונה וה-AI ינתח את החלל.")
    uploaded_img = st.file_uploader("בחר תמונה (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    
    if st.button("🔍 נתח תמונה ועדכן סליידרים"):
        if not uploaded_img:
            st.error("אנא העלה תמונה תחילה.")
        else:
            with st.spinner("ה-AI מנסה להתחבר למודל הגרפי..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    # ניסיון התחברות למודל העדכני ביותר
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                    except:
                        model = genai.GenerativeModel('gemini-pro-vision')
                    
                    img = Image.open(uploaded_img)
                    prompt = """Analyze this architectural space. Return ONLY a JSON object. 
                    Keys: "room_w" (float, width), "room_d" (float, depth), "room_h" (float, height), 
                    "wall_mat" (string, choose: "טיח לבן", "בטון", "עץ", "זכוכית")."""
                    
                    response = model.generate_content([prompt, img])
                    # ניקוי הטקסט מה-AI לפורמט JSON נקי
                    clean_text = response.text.replace("```json", "").replace("```", "").strip()
                    data = json.loads(clean_text)
                    
                    st.session_state['room_w'] = float(data.get('room_w', 6.0))
                    st.session_state['room_d'] = float(data.get('room_d', 8.0))
                    st.session_state['room_h'] = float(data.get('room_h', 2.8))
                    st.session_state['wall_mat'] = data.get('wall_mat', "טיח לבן")
                    
                    st.success("✅ ה-AI סיים את הניתוח! המידות עודכנו.")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאת AI: {e}. וודא שמפתח ה-API תקין ב-Secrets.")

# ==========================================
# 4. סרגל צד: אדריכלות ואור יום
# ==========================================
st.sidebar.header("📐 גיאומטריה ומרקמים")
sensor_h = st.sidebar.slider("גובה מישור המדידה (Z)", 0.0, 3.0, 0.75)

room_shape = st.sidebar.selectbox("צורת חלל", ["מלבן", "צורת L (L-Shape)"])
room_w = st.sidebar.slider("רוחב מקסימלי (X)", 2.0, 15.0, key='room_w')
room_d = st.sidebar.slider("עומק מקסימלי (Y)", 2.0, 15.0, key='room_d')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, key='room_h')

albedo_map = {"טיח לבן": 0.85, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
wall_mat = st.sidebar.selectbox("חומר קירות", list(albedo_map.keys()), 
                                 index=list(albedo_map.keys()).index(st.session_state['wall_mat']))
rho_w = albedo_map[wall_mat]

st.sidebar.header("☀️ אור יום (Solar Engine)")
daylight_on = st.sidebar.toggle("הפעל סימולציית חלון", value=False)
sun_lux = 0
if daylight_on:
    hour = st.sidebar.slider("שעה (06:00-18:00)", 6, 18, 12)
    sun_lux = 1500 * max(0, np.sin(np.radians((hour - 6) * 15)))

# ==========================================
# 5. רהיטים ושמירה לענן
# ==========================================
st.sidebar.header("🪑 ריהוט (נפח וצללים)")
with st.sidebar.expander("𛛏 הגדרות מיטה"):
    bx = st.slider("X מיטה", 0.0, float(room_w-1.6), 0.5)
    by = st.slider("Y מיטה", 0.0, float(room_d-2.0), 0.5)
    bh = 0.5
with st.sidebar.expander("🖥️ הגדרות שולחן"):
    dx = st.slider("X שולחן", 0.0, float(room_w-1.2), float(room_w-1.5))
    dy = st.slider("Y שולחן", 0.0, float(room_d-0.7), float(room_d-1.0))
    dh = 0.75

st.sidebar.header("☁️ ניהול פרויקטים (Cloud)")
p_id = st.sidebar.text_input("שם הפרויקט:", value=f"Daniel_Project_{datetime.now().strftime('%d%m')}")
if st.sidebar.button("💾 שמור פרויקט ל-MongoDB"):
    if client:
        try:
            p_doc = {
                "user": "Daniel Halfon",
                "project_id": p_id,
                "dimensions": {"w": room_w, "d": room_d, "h": room_h},
                "lux_avg": "חישוב בזמן אמת",
                "timestamp": datetime.now()
            }
            projects_col.update_one({"project_id": p_id}, {"$set": p_doc}, upsert=True)
            st.sidebar.success(f"הפרויקט '{p_id}' נשמר בענן!")
        except Exception as e: st.sidebar.error(e)
    else: st.sidebar.error("אין חיבור לשרת")

# ==========================================
# 6. מנוע חישוב פוטומטרי (The Core)
# ==========================================
st.sidebar.header("💡 גופי תאורה")
num_l = st.sidebar.number_input("מספר גופים", 1, 12, 2)
lamps = []
for i in range(int(num_l)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X_{i+1}", 0.0, float(room_w), float(room_w/2))
        ly = st.slider(f"Y_{i+1}", 0.0, float(room_d), float(room_d/2))
        lz = st.slider(f"Z_{i+1}", 1.0, float(room_h), float(room_h)-0.2)
        lp = st.slider(f"Watts_{i+1}", 10, 500, 150)
        lb = st.slider(f"Beam_{i+1}", 10, 160, 60)
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': lb})

def solve_lux(x_in, y_in, z_in, lamps_list, rho, rw, rd):
    val = np.zeros_like(x_in)
    for l in lamps_list:
        dz = abs(l['z'] - z_in)
        dist_sq = (x_in - l['x'])**2 + (y_in - l['y'])**2 + dz**2
        dist = np.sqrt(dist_sq)
        cos_t = dz / (dist + 0.001)
        beam_r = np.radians(l['beam'])
        ang = np.arccos(np.clip(cos_t, -1, 1))
        b_f = np.exp(-(ang**2) / (2 * (beam_r/2.355)**2))
        val += (l['p'] * 50 * cos_t * b_f) / (dist_sq + 0.1)
    # החזרים מהקירות (Radiosity approximation)
    return val + (sum(l['p'] for l in lamps_list) * rho * 6 / (rw * rd))

# יצירת רשת
res = 65
x_axis = np.linspace(0, room_w, res)
y_axis = np.linspace(0, room_d, res)
X, Y = np.meshgrid(x_axis, y_axis)

# מסיכה לצורת L
mask = np.ones_like(X)
if room_shape == "צורת L (L-Shape)":
    mask[(X > room_w/2) & (Y > room_d/2)] = 0

lux_main = solve_lux(X, Y, sensor_h, lamps, rho_w, room_w, room_d) * mask

# אור יום
if daylight_on:
    lux_main[(X < 0.5) & (mask > 0)] += sun_lux

# צללים
if sensor_h < bh: lux_main[(X >= bx) & (X <= bx+1.6) & (Y >= by) & (Y <= by+2.0)] *= 0.15
if sensor_h < dh: lux_main[(X >= dx) & (X <= dx+1.2) & (Y >= dy) & (Y <= dy+0.7)] *= 0.15

# חישוב אור על משטחי הרהיטים
res_f = 15
Xb, Yb = np.meshgrid(np.linspace(bx, bx+1.6, res_f), np.linspace(by, by+2.0, res_f))
lux_bed = solve_lux(Xb, Yb, bh, lamps, rho_w, room_w, room_d)
Xt, Yt = np.meshgrid(np.linspace(dx, dx+1.2, res_f), np.linspace(dy, dy+0.7, res_f))
lux_table = solve_lux(Xt, Yt, dh, lamps, rho_w, room_w, room_d)

# ==========================================
# 7. ויזואליזציה (3D Studio & 2D)
# ==========================================
valid_data = lux_main[mask > 0]
avg_l = np.mean(valid_data) if len(valid_data) > 0 else 0
ugr = 8 * np.log10(max(1, np.mean(valid_data**2) / 1000))

t3, t2 = st.tabs(["🎮 3D Engineering Studio", "📊 מפת חום ותקינה"])

with t3:
    fig = go.Figure()
    # מישור מדידה עם Hover מפורט
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), 
                             surfacecolor=np.where(mask==1, lux_main, np.nan), 
                             colorscale='Turbo', name="Floor/Sensor",
                             customdata=lux_main,
                             hovertemplate='<b>עוצמת אור: %{customdata:.0f} Lux</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>'))
    
    # מיטה
    fig.add_trace(go.Surface(x=Xb, y=Yb, z=np.full_like(Xb, bh), surfacecolor=lux_bed, 
                             colorscale='Turbo', showscale=False, customdata=lux_bed,
                             hovertemplate='<b>Lux על המיטה: %{customdata:.0f}</b><extra></extra>'))
    
    # שולחן
    fig.add_trace(go.Surface(x=Xt, y=Yt, z=np.full_like(Xt, dh), surfacecolor=lux_table, 
                             colorscale='Turbo', showscale=False, customdata=lux_table,
                             hovertemplate='<b>Lux על השולחן: %{customdata:.0f}</b><extra></extra>'))

    # גופי תאורה
    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers',
                                   marker=dict(size=10, color='gold', symbol='diamond'), name="מנורה"))

    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h])), height=750, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    st.subheader("ניתוח פוטומטרי ותקינה")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("LUX ממוצע", f"{int(avg_l)}", delta=f"{int(avg_l - 300)}")
    col_b.metric("מדד סנוור (UGR)", f"{ugr:.1f}")
    col_c.metric("סטטוס", "עומד בתקן ✅" if avg_l > 250 else "תאורה חלשה ❌")
    
    fig_2d = go.Figure(data=go.Contour(z=np.where(mask==1, lux_main, np.nan), x=x_axis, y=y_axis, 
                                      colorscale='Turbo', contours=dict(showlabels=True)))
    fig_2d.update_layout(title="מפת חום דו-מימדית (Lux Heatmap)")
    st.plotly_chart(fig_2d, use_container_width=True)

# ==========================================
# 8. הפקת דוחות
# ==========================================
st.divider()
rep_html = f"""
<html dir="rtl">
<body style="font-family:Arial; padding:40px;">
    <h1 style="color:#2c3e50;">דוח הנדסי: LightPlan 3D Ultimate</h1>
    <hr>
    <p><strong>מתכנן:</strong> דניאל חלפון (Daniel Halfon)</p>
    <p><strong>פרויקט:</strong> {p_id}</p>
    <p><strong>מידות חלל:</strong> {room_w}x{room_d} מ'. גובה {room_h} מ'.</p>
    <p><strong>חומר קירות:</strong> {wall_mat}</p>
    <h2 style="color:#2980b9;">תוצאות סימולציה:</h2>
    <ul>
        <li>עוצמת אור ממוצעת: {int(avg_l)} Lux</li>
        <li>מדד סנוור UGR: {ugr:.1f}</li>
        <li>גובה מישור הבדיקה: {sensor_h} מ'</li>
    </ul>
    <p><em>הופק באמצעות המנוע הפוטומטרי של דניאל חלפון</em></p>
</body>
</html>
"""
st.download_button("🖨️ הורד דוח PDF/HTML לאדריכל", data=rep_html.encode('utf-8'), file_name=f"Daniel_Report_{p_id}.html")
