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
# 1. ניהול מצב המערכת (State Management)
# ==========================================
st.set_page_config(page_title="LightPlan 3D - Daniel Halfon", layout="wide")

# אתחול משתני זיכרון לסנכרון בין ה-AI לסליידרים
if 'room_w' not in st.session_state: st.session_state['room_w'] = 6.0
if 'room_d' not in st.session_state: st.session_state['room_d'] = 8.0
if 'room_h' not in st.session_state: st.session_state['room_h'] = 2.8
if 'wall_mat' not in st.session_state: st.session_state['wall_mat'] = "טיח לבן"
if 'wall_color_hex' not in st.session_state: st.session_state['wall_color_hex'] = "#FFFFFF"
if 'has_sofa' not in st.session_state: st.session_state['has_sofa'] = False
if 'sofa_pos' not in st.session_state: st.session_state['sofa_pos'] = {"x": 2.0, "y": 2.0}

st.title("🏙️ הסטודיו המקצועי של דניאל חלפון (Daniel Halfon)")
st.subheader("מערכת LightPlan 3D Ultimate: הנדסת תאורה משולבת AI וענן")
st.caption("פיתוח מקורי - מנוע Daniel-Vision v2.0 וסנכרון MongoDB Atlas")

# ==========================================
# 2. חיבור למסד הנתונים MongoDB (Cloud Storage)
# ==========================================
@st.cache_resource
def init_connection():
    try:
        # התחברות באמצעות ה-Secret המאובטח מהגדרות Streamlit
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception as e:
        st.error(f"שגיאת חיבור למסד הנתונים: {e}")
        return None

client = init_connection()
if client:
    db = client["LightPlanDB"]
    projects_col = db["Projects"]

# ==========================================
# 3. מנוע AI Vision 2.0 - ניתוח אדריכלי עמוק
# ==========================================
with st.sidebar.expander("🤖 סריקת חדר אוטומטית (AI Vision 2.0)", expanded=True):
    st.write("העלה תמונה וה-AI ינתח מידות, צבעי קירות ומיקומי רהיטים.")
    uploaded_img = st.file_uploader("בחר תמונה (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    
    if st.button("🔍 נתח חלל וסנכרן מערכת"):
        if not uploaded_img:
            st.error("אנא בחר תמונה תחילה.")
        else:
            with st.spinner("מנוע Daniel-Vision מנתח פרופורציות וצבעים..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    
                    # מנגנון חכם למציאת מודל זמין למניעת שגיאות 404
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    except:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        
                    img = Image.open(uploaded_img)
                    
                    # הנחיה הנדסית מפורטת לקבלת JSON מדויק
                    deep_prompt = """
                    You are Daniel-Vision v2.0, an Architectural Engineering AI. 
                    Analyze the image and return ONLY a valid JSON object.
                    Rules:
                    1. Dimensions: Estimate width (room_w) and depth (room_d) in meters (2.0 - 15.0).
                    2. Color: Identify the wall color. Return the Hex code (wall_color_hex).
                    3. Material: Choose from ["טיח לבן", "קיר צבעוני", "בטון", "עץ", "זכוכית"].
                    4. Sofa: Detect if a sofa/bed exists and its (x, y) center position in meters.

                    JSON Format:
                    {"room_w": float, "room_d": float, "room_h": 2.8, "wall_mat": "string", "wall_color_hex": "#hex", "sofa": {"detected": bool, "x": float, "y": float}}
                    """
                    
                    response = model.generate_content([deep_prompt, img])
                    clean_json = response.text.replace("```json", "").replace("```", "").strip()
                    res = json.loads(clean_json)
                    
                    # עדכון מצב המערכת
                    st.session_state['room_w'] = float(res.get('room_w', 6.0))
                    st.session_state['room_d'] = float(res.get('room_d', 8.0))
                    st.session_state['wall_mat'] = res.get('wall_mat', "טיח לבן")
                    st.session_state['wall_color_hex'] = res.get('wall_color_hex', "#FFFFFF")
                    
                    if res.get('sofa', {}).get('detected'):
                        st.session_state['has_sofa'] = True
                        st.session_state['sofa_pos'] = {"x": res['sofa']['x'], "y": res['sofa']['y']}
                    
                    st.success("✅ ניתוח AI הושלם! המערכת הותאמה לתמונה.")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאת AI: {e}")

# ==========================================
# 4. סרגל צד: ארכיטקטורה, צבעים ואור יום
# ==========================================
st.sidebar.header("📐 גיאומטריה ומרקמים")
sensor_h = st.sidebar.slider("גובה חיישן מדידה (Z)", 0.0, 3.0, 0.75, help="0 = רצפה, 0.75 = שולחן/ספה")

room_shape = st.sidebar.selectbox("צורת החלל", ["מלבן", "צורת L (L-Shape)"])
room_w = st.sidebar.slider("רוחב מקסימלי (X)", 2.0, 15.0, key='room_w')
room_d = st.sidebar.slider("עומק מקסימלי (Y)", 2.0, 15.0, key='room_d')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, key='room_h')

st.sidebar.subheader("🎨 צבע ורפלקציה (Albedo)")
albedo_map = {"טיח לבן": 0.85, "קיר צבעוני": 0.60, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
wall_mat = st.sidebar.selectbox("חומר קירות", list(albedo_map.keys()), 
                                 index=list(albedo_map.keys()).index(st.session_state['wall_mat']))
rho_w = albedo_map[wall_mat]
picked_color = st.sidebar.color_picker("צבע קירות (ריאליסטי)", value=st.session_state['wall_color_hex'])

st.sidebar.header("☀️ סימולציית שמש")
sun_on = st.sidebar.toggle("הפעל אור יום", value=False)
sun_lux = 0
if sun_on:
    hour = st.sidebar.slider("שעה ביום", 6, 18, 12)
    sun_lux = 1400 * max(0, np.sin(np.radians((hour - 6) * 15)))

# ==========================================
# 5. רהיטים וניהול פרויקטים בענן
# ==========================================
st.sidebar.header("🪑 ריהוט ונפח (צללים)")
with st.sidebar.expander("𛛏 הגדרות ספה / מיטה", expanded=st.session_state['has_sofa']):
    bx = st.slider("X מיקום", 0.0, float(room_w-1.6), st.session_state['sofa_pos']['x'])
    by = st.slider("Y מיקום", 0.0, float(room_d-2.0), st.session_state['sofa_pos']['y'])
    bh = 0.5 # גובה סטנדרטי

with st.sidebar.expander("🖥️ הגדרות שולחן עבודה"):
    dx = st.slider("X שולחן", 0.0, float(room_w-1.2), float(room_w-1.5))
    dy = st.slider("Y שולחן", 0.0, float(room_d-0.7), float(room_d-1.0))
    dh = 0.75

st.sidebar.header("☁️ שמירה לענן (Daniel's Server)")
p_id = st.sidebar.text_input("שם הפרויקט:", value=f"Project_Daniel_{datetime.now().strftime('%H%M')}")
if st.sidebar.button("💾 סנכרן עם MongoDB"):
    if client:
        try:
            p_doc = {
                "author": "Daniel Halfon",
                "project_id": p_id,
                "config": {"w": room_w, "d": room_d, "h": room_h, "color": picked_color},
                "timestamp": datetime.now()
            }
            projects_col.update_one({"project_id": p_id}, {"$set": p_doc}, upsert=True)
            st.sidebar.success(f"הפרויקט '{p_id}' נשמר בהצלחה בענן!")
        except Exception as e: st.sidebar.error(e)
    else: st.sidebar.error("אין חיבור למסד הנתונים.")

# ==========================================
# 6. מנוע פוטומטרי (The Light Engine)
# ==========================================
st.sidebar.header("💡 גופי תאורה")
num_l = st.sidebar.number_input("מספר גופים", 1, 12, 2)
lamps = []
for i in range(int(num_l)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx, ly = st.slider(f"X_{i+1}", 0.0, float(room_w), float(room_w)/2), st.slider(f"Y_{i+1}", 0.0, float(room_d), float(room_d)/2)
        lz = st.slider(f"Z_{i+1}", 1.0, float(room_h), float(room_h)-0.2)
        lp, lb = st.slider(f"Watts_{i+1}", 10, 500, 150), st.slider(f"Beam_{i+1}", 10, 160, 60)
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': lb})

def solve_lux(x_in, y_in, z_target, lamps_list, rho, rw, rd):
    val = np.zeros_like(x_in)
    for l in lamps_list:
        dz = abs(l['z'] - z_target)
        d_sq = (x_in - l['x'])**2 + (y_in - l['y'])**2 + dz**2
        d = np.sqrt(d_sq)
        cos_t = dz / (d + 0.001)
        beam_r = np.radians(l['beam'])
        ang = np.arccos(np.clip(cos_t, -1, 1))
        b_f = np.exp(-(ang**2) / (2 * (beam_r/2.355)**2))
        val += (l['p'] * 50 * cos_t * b_f) / (d_sq + 0.1)
    # החזרים מהקירות (Lambertian approximation)
    return val + (sum(l['p'] for l in lamps_list) * rho * 6 / (rw * rd))

# יצירת רשת נתונים
res = 65
x_ax = np.linspace(0, room_w, res)
y_ax = np.linspace(0, room_d, res)
X, Y = np.meshgrid(x_ax, y_ax)

# מסיכה לצורת L
mask = np.ones_like(X)
if room_shape == "צורת L (L-Shape)":
    mask[(X > room_w/2) & (Y > room_d/2)] = 0

lux_main = solve_lux(X, Y, sensor_h, lamps, rho_w, room_w, room_d) * mask

# אור יום וצללים
if sun_on: lux_main[(X < 0.5) & (mask > 0)] += sun_lux
if sensor_h < bh: lux_main[(X >= bx) & (X <= bx+1.6) & (Y >= by) & (Y <= by+2.0)] *= 0.15
if sensor_h < dh: lux_main[(X >= dx) & (X <= dx+1.2) & (Y >= dy) & (Y <= dy+0.7)] *= 0.15

# חישוב Lux על משטחי הרהיטים (Hover מדויק)
res_f = 15
Xb, Yb = np.meshgrid(np.linspace(bx, bx+1.6, res_f), np.linspace(by, by+2.0, res_f))
lux_bed = solve_lux(Xb, Yb, bh, lamps, rho_w, room_w, room_d)
Xt, Yt = np.meshgrid(np.linspace(dx, dx+1.2, res_f), np.linspace(dy, dy+0.7, res_f))
lux_table = solve_lux(Xt, Yt, dh, lamps, rho_w, room_w, room_d)

# ==========================================
# 7. תצוגה גרפית (3D Studio + Hover)
# ==========================================
valid_lux = lux_main[mask > 0]
avg_l = np.mean(valid_lux) if len(valid_lux) > 0 else 0
ugr = 8 * np.log10(max(1, np.mean(valid_lux) / 45))

t3, t2 = st.tabs(["🎮 3D Engineering Studio", "📊 מפת חום ותקינה"])

with t3:
    fig = go.Figure()
    lux_hide = np.where(mask==1, lux_main, np.nan)
    
    # רצפה + Hover
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), surfacecolor=lux_hide, 
                             colorscale='Turbo', name="Floor", customdata=lux_hide,
                             hovertemplate='<b>עוצמה: %{customdata:.0f} Lux</b><br>X: %{x:.1f}m<br>Y: %{y:.1f}m<extra></extra>'))
    # רהיטים
    fig.add_trace(go.Surface(x=Xb, y=Yb, z=np.full_like(Xb, bh), surfacecolor=lux_bed, colorscale='Turbo', showscale=False, customdata=lux_bed, hovertemplate='<b>Lux ספה: %{customdata:.0f}</b><extra></extra>'))
    fig.add_trace(go.Surface(x=Xt, y=Yt, z=np.full_like(Xt, dh), surfacecolor=lux_table, colorscale='Turbo', showscale=False, customdata=lux_table, hovertemplate='<b>Lux שולחן: %{customdata:.0f}</b><extra></extra>'))

    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers', marker=dict(size=12, color='gold', symbol='diamond'), name="מנורה"))

    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h]), xaxis=dict(backgroundcolor=picked_color), yaxis=dict(backgroundcolor=picked_color)), height=750, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with t2:
    st.subheader("מדדי תקינה הנדסיים")
    c1, c2, c3 = st.columns(3)
    c1.metric("LUX ממוצע", f"{int(avg_l)}", delta=f"{int(avg_l - 300)}")
    c2.metric("מדד סנוור (UGR)", f"{ugr:.1f}")
    c3.metric("סטטוס תקינה", "עומד בתקן ✅" if avg_l > 270 else "תאורה לקויה ❌")
    
    st.plotly_chart(go.Figure(data=go.Contour(z=lux_hide, x=x_ax, y=y_ax, colorscale='Turbo', customdata=lux_hide, hovertemplate='<b>%{customdata:.0f} Lux</b><extra></extra>')), use_container_width=True)

# ==========================================
# 8. דוח הנדסי (Daniel Halfon)
# ==========================================
st.divider()
rep_html = f"""<html dir="rtl"><body style="font-family:Arial; padding:40px; border: 5px solid {picked_color};">
<h1>דוח תאורה הנדסי - LightPlan 3D Ultimate</h1>
<h3>מתכנן ראשי: דניאל חלפון (Daniel Halfon)</h3><hr>
<p><strong>פרויקט:</strong> {p_id} | <strong>עוצמת אור ממוצעת:</strong> {int(avg_l)} Lux</p>
<p>מידות: {room_w}x{room_d} מ'. חומר: {wall_mat}. צבע קירות: {picked_color}</p>
<p><em>הופק באמצעות מנוע Daniel-Vision v2.0 המשולב ב-Streamlit Cloud.</em></p>
</body></html>"""
st.download_button("🖨️ הורד דוח PDF לאדריכל", data=rep_html.encode('utf-8'), file_name=f"Daniel_Halfon_Report_{p_id}.html")
