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
# 1. הגדרות דף וניהול מצב (Daniel Halfon Edition)
# ==========================================
st.set_page_config(page_title="LightPlan 3D - Daniel Halfon", layout="wide")

# זיכרון פנימי לסנכרון בין ה-AI לסליידרים
if 'room_w' not in st.session_state: st.session_state['room_w'] = 6.0
if 'room_d' not in st.session_state: st.session_state['room_d'] = 8.0
if 'room_h' not in st.session_state: st.session_state['room_h'] = 2.8
if 'wall_mat' not in st.session_state: st.session_state['wall_mat'] = "טיח לבן"

st.title("🏙️ הסטודיו המקצועי של דניאל חלפון (Daniel Halfon)")
st.subheader("מערכת LightPlan 3D Ultimate: הנדסה, AI וסנכרון ענן")
st.caption("פיתוח מקורי - חיבור למסד נתונים MongoDB ומנוע ויזואלי מתקדם")

# ==========================================
# 2. חיבור למסד הנתונים (MongoDB Atlas)
# ==========================================
@st.cache_resource
def init_connection():
    try:
        # שליכת ה-URI מה-Secrets המאובטחים
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception:
        return None

client = init_connection()
if client:
    db = client["LightPlanDB"]
    projects_col = db["Projects"]

# ==========================================
# 3. מנוע AI Vision - תיקון שגיאת 404 הסופי
# ==========================================
with st.sidebar.expander("🤖 סריקת חדר אוטומטית (AI Vision)", expanded=True):
    st.write("העלה תמונה וה-AI יבנה את המודל עבורך.")
    uploaded_img = st.file_uploader("בחר תמונה (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    
    if st.button("🔍 נתח חלל ועדכן מערכת"):
        if not uploaded_img:
            st.error("אנא בחר תמונה תחילה.")
        else:
            with st.spinner("מנסה להתחבר למודל AI זמין..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # מנגנון חכם למציאת המודל המתאים (למניעת 404)
                    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    selected_model = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in available_models else available_models[0]
                    
                    model = genai.GenerativeModel(selected_model)
                    img = Image.open(uploaded_img)
                    
                    prompt = """Analyze this space. Return ONLY a JSON string. 
                    Keys: "room_w" (float), "room_d" (float), "room_h" (float), 
                    "wall_mat" (string, one of: "טיח לבן", "בטון", "עץ", "זכוכית")."""
                    
                    response = model.generate_content([prompt, img])
                    clean_data = response.text.replace("```json", "").replace("```", "").strip()
                    res_json = json.loads(clean_data)
                    
                    # עדכון ה-Session State
                    st.session_state['room_w'] = float(res_json.get('room_w', 6.0))
                    st.session_state['room_d'] = float(res_json.get('room_d', 8.0))
                    st.session_state['room_h'] = float(res_json.get('room_h', 2.8))
                    st.session_state['wall_mat'] = res_json.get('wall_mat', "טיח לבן")
                    
                    st.success(f"ה-AI השלים את המשימה באמצעות {selected_model}")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאת התחברות ל-AI: {e}")

# ==========================================
# 4. סרגל צד: ארכיטקטורה וסימולציה
# ==========================================
st.sidebar.header("📐 גיאומטריה ומרקמים")
sensor_h = st.sidebar.slider("גובה חיישן (Z-Plane)", 0.0, 3.0, 0.75)

r_shape = st.sidebar.selectbox("צורת החדר", ["מלבן", "צורת L (L-Shape)"])
room_w = st.sidebar.slider("רוחב (X)", 2.0, 15.0, key='room_w')
room_d = st.sidebar.slider("עומק (Y)", 2.0, 15.0, key='room_d')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, key='room_h')

albedo_map = {"טיח לבן": 0.85, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
wall_mat = st.sidebar.selectbox("חומר קירות", list(albedo_map.keys()), 
                                 index=list(albedo_map.keys()).index(st.session_state['wall_mat']))
rho_w = albedo_map[wall_mat]

st.sidebar.header("☀️ סימולציית שמש")
sun_on = st.sidebar.toggle("הפעל אור יום", value=False)
sun_lux = 0
if sun_on:
    hour = st.sidebar.slider("שעה", 6, 18, 12)
    sun_lux = 1200 * max(0, np.sin(np.radians((hour - 6) * 15)))

# ==========================================
# 5. רהיטים וניהול ענן
# ==========================================
st.sidebar.header("🪑 ריהוט (נפח וצל)")
with st.sidebar.expander("𛛏 מיטה זוגית"):
    bx = st.slider("X מיטה", 0.0, float(room_w-1.6), 0.5)
    by = st.slider("Y מיטה", 0.0, float(room_d-2.0), 0.5)
    bh = 0.5
with st.sidebar.expander("🖥️ שולחן משרדי"):
    dx = st.slider("X שולחן", 0.0, float(room_w-1.2), float(room_w-1.5))
    dy = st.slider("Y שולחן", 0.0, float(room_d-0.7), float(room_d-1.0))
    dh = 0.75

st.sidebar.header("☁️ שמירה לענן (Daniel's Server)")
p_name = st.sidebar.text_input("שם הפרויקט:", value=f"Daniel_{datetime.now().strftime('%H%M')}")
if st.sidebar.button("💾 שלח נתונים ל-MongoDB"):
    if client:
        try:
            p_doc = {
                "author": "Daniel Halfon",
                "id": p_name,
                "config": {"w": room_w, "d": room_d, "h": room_h, "mat": wall_mat},
                "last_update": datetime.now()
            }
            projects_col.update_one({"id": p_name}, {"$set": p_doc}, upsert=True)
            st.sidebar.success("הפרויקט סונכרן עם הענן!")
        except Exception as e: st.sidebar.error(e)
    else: st.sidebar.error("מסד הנתונים לא מחובר")

# ==========================================
# 6. מנוע חישוב (The Photometric Engine)
# ==========================================
st.sidebar.header("💡 גופי תאורה")
n_lamps = st.sidebar.number_input("מספר גופים", 1, 10, 2)
lamps = []
for i in range(int(n_lamps)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X_{i+1}", 0.0, float(room_w), float(room_w)/2)
        ly = st.slider(f"Y_{i+1}", 0.0, float(room_d), float(room_d)/2)
        lz = st.slider(f"Z_{i+1}", 1.5, float(room_h), float(room_h)-0.2)
        lp = st.slider(f"Power_{i+1}", 10, 500, 150)
        lb = st.slider(f"Beam_{i+1}", 10, 160, 60)
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': lb})

def run_photometry(x_net, y_net, z_p, lamps_in, rho, rw, rd):
    out = np.zeros_like(x_net)
    for l in lamps_in:
        dz = abs(l['z'] - z_p)
        sq_d = (x_net - l['x'])**2 + (y_net - l['y'])**2 + dz**2
        d = np.sqrt(sq_d)
        ct = dz / (d + 0.001)
        br = np.radians(l['beam'])
        ag = np.arccos(np.clip(ct, -1, 1))
        bf = np.exp(-(ag**2) / (2 * (br/2.355)**2))
        out += (l['p'] * 50 * ct * bf) / (sq_d + 0.1)
    return out + (sum(l['p'] for l in lamps_in) * rho * 6 / (rw * rd))

# בניית רשת
res = 65
X, Y = np.meshgrid(np.linspace(0, room_w, res), np.linspace(0, room_d, res))
mask = np.ones_like(X)
if r_shape == "צורת L (L-Shape)":
    mask[(X > room_w/2) & (Y > room_d/2)] = 0

lux_map = run_photometry(X, Y, sensor_h, lamps, rho_w, room_w, room_d) * mask
if sun_on: lux_map[(X < 0.5) & (mask > 0)] += sun_lux

# צללים
if sensor_h < bh: lux_map[(X >= bx) & (X <= bx+1.6) & (Y >= by) & (Y <= by+2.0)] *= 0.15
if sensor_h < dh: lux_map[(X >= dx) & (X <= dx+1.2) & (Y >= dy) & (Y <= dy+0.7)] *= 0.15

# אור על רהיטים
rf = 15
Xb, Yb = np.meshgrid(np.linspace(bx, bx+1.6, rf), np.linspace(by, by+2.0, rf))
lux_b = run_photometry(Xb, Yb, bh, lamps, rho_w, room_w, room_d)
Xt, Yt = np.meshgrid(np.linspace(dx, dx+1.2, rf), np.linspace(dy, dy+0.7, rf))
lux_t = run_photometry(Xt, Yt, dh, lamps, rho_w, room_w, room_d)

# ==========================================
# 7. תצוגה גרפית (3D Studio + Hover)
# ==========================================
avg_lux = np.mean(lux_map[mask > 0])
ugr = 8 * np.log10(max(1, np.mean(lux_map[mask > 0]) / 40))

t_3d, t_2d = st.tabs(["🎮 3D Engineering Studio", "📊 מפת חום ותקינה"])

with t_3d:
    fig = go.Figure()
    # רצפה + Hover
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), 
                             surfacecolor=np.where(mask==1, lux_map, np.nan), 
                             colorscale='Turbo', customdata=lux_map,
                             hovertemplate='<b>עוצמה: %{customdata:.0f} Lux</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>'))
    
    # מיטה + שולחן
    fig.add_trace(go.Surface(x=Xb, y=Yb, z=np.full_like(Xb, bh), surfacecolor=lux_b, colorscale='Turbo', showscale=False, customdata=lux_b, hovertemplate='<b>Lux מיטה: %{customdata:.0f}</b><extra></extra>'))
    fig.add_trace(go.Surface(x=Xt, y=Yt, z=np.full_like(Xt, dh), surfacecolor=lux_t, colorscale='Turbo', showscale=False, customdata=lux_t, hovertemplate='<b>Lux שולחן: %{customdata:.0f}</b><extra></extra>'))

    # מנורות
    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers', marker=dict(size=12, color='gold', symbol='diamond'), name="מנורה"))

    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h])), height=750, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with t_2d:
    st.subheader("מדדי תקינה הנדסיים")
    c1, c2, c3 = st.columns(3)
    c1.metric("LUX ממוצע", f"{int(avg_lux)}")
    c2.metric("מדד סנוור (UGR)", f"{ugr:.1f}")
    c3.metric("סטטוס", "תקין ✅" if avg_lux > 280 else "נמוך ❌")
    
    st.plotly_chart(go.Figure(data=go.Contour(z=np.where(mask==1, lux_map, np.nan), x=np.linspace(0, room_w, res), y=np.linspace(0, room_d, res), colorscale='Turbo')), use_container_width=True)

# ==========================================
# 8. דוח Daniel Halfon
# ==========================================
st.divider()
rep = f"""<html dir="rtl"><body style="font-family:Arial; padding:30px;">
<h1>דוח תאורה - LightPlan 3D</h1>
<h3>מתכנן: דניאל חלפון (Daniel Halfon)</h3><hr>
<p>פרויקט: {p_name} | LUX ממוצע: {int(avg_lux)} | UGR: {ugr:.1f}</p>
<p>מידות: {room_w}x{room_d} מ'. חומר: {wall_mat}.</p>
</body></html>"""
st.download_button("🖨️ הורד דוח HTML לאדריכל", data=rep.encode('utf-8'), file_name=f"Daniel_Report_{p_name}.html")
