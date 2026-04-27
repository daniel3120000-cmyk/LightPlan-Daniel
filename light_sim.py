import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import json
import pymongo
from datetime import datetime
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. הגדרות דף וניהול מצב (State)
# ==========================================
st.set_page_config(page_title="LightPlan 3D - Daniel Halfon", layout="wide")

if 'room_w' not in st.session_state: st.session_state['room_w'] = 6.0
if 'room_d' not in st.session_state: st.session_state['room_d'] = 8.0
if 'room_h' not in st.session_state: st.session_state['room_h'] = 2.8
if 'wall_mat' not in st.session_state: st.session_state['wall_mat'] = "טיח לבן"

st.title("🏙️ LightPlan 3D: הסטודיו המקצועי של דניאל חלפון (Daniel Halfon)")
st.caption("מערכת הנדסית משולבת AI וחיבור לענן MongoDB - פיתוח מקורי")

# ==========================================
# 2. חיבור למסד הנתונים (MongoDB Cloud)
# ==========================================
@st.cache_resource
def init_connection():
    try:
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception as e:
        return None

client = init_connection()
if client:
    db = client["LightPlanDB"]
    projects_col = db["Projects"]

# ==========================================
# 3. מנוע AI (Gemini Vision) 
# ==========================================
with st.sidebar.expander("🤖 סריקת חדר אוטומטית (AI Vision)", expanded=False):
    st.write("העלה תמונה וה-AI יזהה את המידות והחומרים אוטומטית.")
    uploaded_img = st.file_uploader("בחר תמונה (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    
    if st.button("🔍 נתח תמונה ועדכן נתונים"):
        if not uploaded_img:
            st.error("חובה להעלות תמונה קודם.")
        else:
            with st.spinner("ה-AI מנתח את החלל..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    img = Image.open(uploaded_img)
                    prompt = """Analyze this room. Return ONLY a valid JSON. Keys: 
                    "room_w": float (width in meters), "room_d": float (depth in meters), "wall_mat": string (choose: "טיח לבן", "בטון", "עץ", "זכוכית")"""
                    
                    response = model.generate_content([prompt, img])
                    data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                    
                    st.session_state['room_w'] = float(data.get('room_w', 5.0))
                    st.session_state['room_d'] = float(data.get('room_d', 5.0))
                    st.session_state['wall_mat'] = data.get('wall_mat', "טיח לבן")
                    st.success("✅ הנתונים עודכנו בהצלחה מהתמונה!")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בניתוח ה-AI: {e}")

# ==========================================
# 4. סרגל צד: אדריכלות, גיאומטריה ואור יום
# ==========================================
st.sidebar.header("📐 גיאומטריה ומרקמים")
sensor_h = st.sidebar.slider("גובה חיישן (Z-Plane)", 0.0, 3.0, 0.75, help="0 = רצפה, 0.75 = שולחן עבודה")

room_shape = st.sidebar.selectbox("צורת חדר", ["מלבן", "צורת L (L-Shape)"])
room_w = st.sidebar.slider("רוחב מקסימלי (X)", 2.0, 15.0, key='room_w')
room_d = st.sidebar.slider("עומק מקסימלי (Y)", 2.0, 15.0, key='room_d')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, key='room_h')

albedo_map = {"טיח לבן": 0.85, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
wall_mat = st.sidebar.selectbox("חומר קירות", list(albedo_map.keys()), 
                                 index=list(albedo_map.keys()).index(st.session_state['wall_mat']))
rho_w = albedo_map[wall_mat]

st.sidebar.header("☀️ אור יום (Solar Engine)")
daylight_toggle = st.sidebar.toggle("הפעל סימולציית חלון", value=False)
sun_lux = 0
if daylight_toggle:
    hour = st.sidebar.slider("שעה ביום (06:00-18:00)", 6, 18, 12)
    sun_alt = np.sin(np.radians((hour - 6) * 15))
    sun_lux = 1500 * max(0, sun_alt)

# ==========================================
# 5. רהיטים ושמירה בענן
# ==========================================
st.sidebar.header("🪑 רהיטים (יוצרים צללים)")
with st.sidebar.expander("𛛏 מיטה"):
    bx = st.slider("X מיטה", 0.0, float(room_w-1.6), 0.5)
    by = st.slider("Y מיטה", 0.0, float(room_d-2.0), 0.5)
    bh = 0.5
with st.sidebar.expander("🖥️ שולחן"):
    dx = st.slider("X שולחן", 0.0, float(room_w-1.2), float(room_w-1.5))
    dy = st.slider("Y שולחן", 0.0, float(room_d-0.7), float(room_d-1.0))
    dh = 0.75

st.sidebar.header("☁️ שמירה בענן")
proj_name = st.sidebar.text_input("שם הפרויקט:", value=f"Project_Daniel_{st.session_state['room_w']}x{st.session_state['room_d']}")
if st.sidebar.button("💾 שמור פרויקט ל-MongoDB"):
    if client:
        try:
            p_data = {"id": proj_name, "w": room_w, "d": room_d, "mat": wall_mat, "time": datetime.now()}
            projects_col.update_one({"id": proj_name}, {"$set": p_data}, upsert=True)
            st.sidebar.success("✅ נשמר בהצלחה בענן!")
        except Exception as e: st.sidebar.error(e)
    else:
        st.sidebar.error("אין חיבור למסד הנתונים")

# ==========================================
# 6. מנוע פיזיקלי משולב (הכל בבת אחת)
# ==========================================
st.sidebar.header("💡 תאורה הנדסית")
num_lamps = st.sidebar.number_input("מספר גופים", 1, 10, 2)
lamps = []
for i in range(int(num_lamps)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X_{i+1}", 0.0, float(room_w), float(room_w)/2 + (i*0.5))
        ly = st.slider(f"Y_{i+1}", 0.0, float(room_d), float(room_d)/2)
        lz = st.slider(f"Z_{i+1}", 1.0, float(room_h), float(room_h)-0.2)
        lp = st.slider(f"Watts_{i+1}", 10, 500, 150)
        l_beam = st.slider(f"Beam Angle_{i+1}", 10, 160, 60)
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': l_beam})

res = 65
x = np.linspace(0, room_w, res)
y = np.linspace(0, room_d, res)
X, Y = np.meshgrid(x, y)
lux_grid = np.zeros_like(X)
ugr_comp = np.zeros_like(X)

# יצירת מסיכה לצורת L
mask = np.ones_like(X)
if room_shape == "צורת L (L-Shape)":
    mask[(X > room_w/2) & (Y > room_d/2)] = 0

for l in lamps:
    dz = abs(l['z'] - sensor_h)
    dist_sq = (X - l['x'])**2 + (Y - l['y'])**2 + dz**2
    dist = np.sqrt(dist_sq)
    cos_theta = dz / (dist + 0.001)
    
    beam_rad = np.radians(l['beam'])
    angle_from_axis = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    beam_factor = np.exp(-(angle_from_axis**2) / (2 * (beam_rad/2.355)**2))
    
    lamp_lux = (l['p'] * 50 * cos_theta * beam_factor) / (dist_sq + 0.1)
    lux_grid += lamp_lux * mask
    ugr_comp += (lamp_lux**2) / (dz**2 + 0.1)

# הוספת אור יום והחזרים מהקירות
if daylight_toggle:
    lux_grid[(X < 0.5) & mask.astype(bool)] += sun_lux
reflection = (sum(l['p'] for l in lamps) * rho_w * 6) / (room_w * room_d)
lux_grid += reflection * mask

# צללים של רהיטים
if sensor_h < bh: lux_grid[(X >= bx) & (X <= bx+1.6) & (Y >= by) & (Y <= by+2.0)] *= 0.15
if sensor_h < dh: lux_grid[(X >= dx) & (X <= dx+1.2) & (Y >= dy) & (Y <= dy+0.7)] *= 0.15

# פונקציה מקוצרת לחישוב אור עילי על הרהיטים (כדי לחסוך קוד כפול)
def get_surface_lux(x_arr, y_arr, z_val):
    g = np.zeros_like(x_arr)
    for l in lamps:
        d_sq = (x_arr - l['x'])**2 + (y_arr - l['y'])**2 + (l['z'] - z_val)**2
        cos_t = (l['z'] - z_val) / np.sqrt(d_sq + 0.001)
        b_fac = np.exp(-(np.arccos(np.clip(cos_t, -1, 1))**2) / (2 * (np.radians(l['beam'])/2.355)**2))
        g += (l['p'] * 50 * cos_t * b_fac) / (d_sq + 0.1)
    return g + reflection

res_f = 15
X_b, Y_b = np.meshgrid(np.linspace(bx, bx+1.6, res_f), np.linspace(by, by+2.0, res_f))
lux_b = get_surface_lux(X_b, Y_b, bh)
X_t, Y_t = np.meshgrid(np.linspace(dx, dx+1.2, res_f), np.linspace(dy, dy+0.7, res_f))
lux_t = get_surface_lux(X_t, Y_t, dh)

# ==========================================
# 7. לשוניות: 3D, 2D ודוחות
# ==========================================
valid_lux = lux_grid[mask > 0]
avg_lux = np.mean(valid_lux) if len(valid_lux) > 0 else 0
ugr_val = 8 * np.log10(max(1, np.mean(ugr_comp[mask > 0]) / 50))
uniformity = np.min(valid_lux) / avg_lux if avg_lux > 0 else 0

tab_3d, tab_2d = st.tabs(["🎮 3D Engineering Studio", "📊 מפת חום ותקינה 2D"])

with tab_3d:
    fig = go.Figure()
    # רצפה / מישור המדידה
    lux_display = np.where(mask == 1, lux_grid, np.nan) # מסתיר את החלק החתוך ב-L
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), surfacecolor=lux_display, colorscale='Turbo',
                             hovertemplate='X: %{x:.1f}m<br>Y: %{y:.1f}m<br><b>Lux: %{surfacecolor:.0f}</b><extra></extra>'))
    
    # משטחי רהיטים
    fig.add_trace(go.Surface(x=X_b, y=Y_b, z=np.full_like(X_b, bh), surfacecolor=lux_b, colorscale='Turbo', showscale=False))
    fig.add_trace(go.Surface(x=X_t, y=Y_t, z=np.full_like(X_t, dh), surfacecolor=lux_t, colorscale='Turbo', showscale=False))

    # מנורות
    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers',
                                   marker=dict(size=12, color='gold', symbol='diamond'), name="מנורה"))

    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h])), height=700, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with tab_2d:
    st.subheader("מדדי תקינה הנדסיים")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LUX ממוצע", f"{int(avg_lux)}", delta=f"{int(avg_lux - 300)}")
    c2.metric("אחידות (Uo)", f"{uniformity:.2f}", delta="תקין" if uniformity > 0.4 else "לקוי")
    c3.metric("מדד סנוור (UGR)", f"{ugr_val:.1f}", delta="מסנוור" if ugr_val > 19 else "תקין", delta_color="inverse")
    c4.metric("סטטוס כללי", "עובר ✅" if avg_lux >= 270 else "נכשל ❌")
    
    fig_heat = go.Figure(data=go.Contour(z=lux_display, x=x, y=y, colorscale='Turbo'))
    fig_heat.update_layout(title="חתך דו-מימדי (Heatmap)")
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# 8. דוח HTML מקצועי (להדפסת PDF)
# ==========================================
st.divider()
html_rep = f"""<html dir="rtl"><body style="font-family:Arial; padding:30px;">
<h1>דוח תאורה הנדסי - LightPlan 3D Ultimate</h1>
<h3>מתכנן ראשי: דניאל חלפון (Daniel Halfon)</h3>
<hr>
<p><strong>מזהה פרויקט:</strong> {proj_name}</p>
<p><strong>מידות חלל:</strong> רוחב {room_w} מ', עומק {room_d} מ'. צורה: {room_shape}.</p>
<p><strong>חומר קירות:</strong> {wall_mat}.</p>
<br>
<h3>תוצאות מדידה (בגובה {sensor_h} מטר)</h3>
<ul>
    <li><strong>LUX ממוצע:</strong> {int(avg_lux)}</li>
    <li><strong>אחידות אור (Uniformity):</strong> {uniformity:.2f}</li>
    <li><strong>מדד סנוור עולמי (UGR):</strong> {ugr_val:.1f}</li>
</ul>
<br>
<p><em>הופק אוטומטית על ידי מנוע LightPlan 3D Engine.</em></p>
</body></html>"""

st.download_button("🖨️ הורד דוח לאדריכל (HTML)", data=html_rep.encode('utf-8'), file_name="Daniel_Halfon_Report.html")
