import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import json
import io
from datetime import datetime
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. ניהול מצב המערכת (State Management)
# קריטי כדי שה-AI יוכל לעדכן את הסליידרים אוטומטית
# ==========================================
st.set_page_config(page_title="LightPlan 3D Ultimate", layout="wide")

# אתחול משתני הדיפולט אם הם עדיין לא קיימים
defaults = {
    'room_w': 6.0, 'room_d': 8.0, 'room_h': 2.8,
    'wall_mat': "טיח לבן",
    'project_id': f"DK-{datetime.now().strftime('%H%M%S')}"
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

st.title(f"🏗️ LightPlan 3D Ultimate: {st.session_state['project_id']}")
st.caption("מערכת הנדסית משולבת AI - פיתוח: דניאל חלפון")

# ==========================================
# 2. AI Vision Assistant (מנוע הראייה הממוחשבת)
# ==========================================
with st.sidebar.expander("🤖 AI Room Scanner (Gemini Vision)", expanded=False):
    st.write("העלה תמונה של החלל, וה-AI יבנה את הגיאומטריה אוטומטית.")
    uploaded_img = st.file_uploader("בחר תמונה (JPG/PNG)", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_img is not None:
        if st.button("🔍 נתח תמונה באמצעות AI"):
            with st.spinner('ה-AI של דניאל מנתח את עומק החדר...'):
                try:
                    # הגדרת ה-API של גוגל (הכנס את המפתח שלך כאן כדי שזה יעבוד)
                    # genai.configure(api_key="YOUR_GEMINI_API_KEY") 
                    
                    # --- קוד לסימולציה של AI (כדי שהאפליקציה לא תקרס בלי מפתח API) ---
                    # בעולם האמיתי, כאן קוראים למודל: model.generate_content([prompt, img])
                    import time
                    time.sleep(2) # מדמה זמן חשיבה של השרת
                    
                    # נניח שה-AI זיהה חדר קטן מבטון
                    ai_results = {
                        "room_w": 4.0, "room_d": 4.5, "room_h": 2.5, "wall_mat": "בטון"
                    }
                    
                    # עדכון אוטומטי של המערכת
                    st.session_state['room_w'] = ai_results['room_w']
                    st.session_state['room_d'] = ai_results['room_d']
                    st.session_state['room_h'] = ai_results['room_h']
                    st.session_state['wall_mat'] = ai_results['wall_mat']
                    
                    st.success("✅ ה-AI זיהה את מידות החדר והגדיר את הסליידרים!")
                    st.rerun() # מרענן את העמוד כדי להציג את התוצאות החדשות
                except Exception as e:
                    st.error(f"שגיאת AI: {e}")

# ==========================================
# 3. סרגל צד: גיאומטריה ומרקמים (מחובר ל-State)
# ==========================================
st.sidebar.header("📐 גיאומטריה ומרקמים")

room_shape = st.sidebar.selectbox("צורת חדר", ["מלבן", "צורת L (L-Shape)", "תקרה משופעת"])
# הסליידרים מושכים את הערך שלהם מה-session_state, כך שה-AI יכול לשלוט בהם
room_w = st.sidebar.slider("רוחב (X)", 2.0, 15.0, st.session_state['room_w'], key='room_w_slider')
room_d = st.sidebar.slider("עומק (Y)", 2.0, 15.0, st.session_state['room_d'], key='room_d_slider')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, st.session_state['room_h'], key='room_h_slider')

st.sidebar.subheader("🎨 חומרים (Reflection)")
mat_options = ["טיח לבן", "בטון", "עץ", "זכוכית"]
mat_idx = mat_options.index(st.session_state['wall_mat']) if st.session_state['wall_mat'] in mat_options else 0
wall_mat = st.sidebar.selectbox("חומר קירות", mat_options, index=mat_idx)
st.session_state['wall_mat'] = wall_mat

# מקדמי החזר אור פיזיקליים (Albedo)
albedo_map = {"טיח לבן": 0.85, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
rho_w = albedo_map[wall_mat]

# ==========================================
# 4. אור יום דינמי (Daylighting)
# ==========================================
st.sidebar.header("☀️ אור יום (Solar Engine)")
daylight_toggle = st.sidebar.toggle("הפעל סימולציית שמש", value=True)
sun_lux = 0
if daylight_toggle:
    hour = st.sidebar.slider("שעה ביום (06:00-18:00)", 6, 18, 12)
    sun_alt = np.sin(np.radians((hour - 6) * 15))
    sun_lux = 1500 * max(0, sun_alt)

# ==========================================
# 5. מערכת תאורה (IES & Beam Angle)
# ==========================================
st.sidebar.header("💡 גופי תאורה (IES Ready)")
sensor_h = st.sidebar.slider("גובה מישור המדידה (Z-Plane)", 0.0, 2.5, 0.75, help="0 = רצפה, 0.75 = שולחן עבודה")
num_lamps = st.sidebar.number_input("מספר גופים", 1, 10, 2)

lamps = []
for i in range(int(num_lamps)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X_{i+1}", 0.0, float(room_w), float(room_w)/2)
        ly = st.slider(f"Y_{i+1}", 0.0, float(room_d), float(room_d)/2)
        lz = st.slider(f"Z_{i+1}", 1.0, float(room_h), float(room_h) - 0.2)
        lp = st.slider(f"Watts_{i+1}", 10, 400, 100)
        l_beam = st.slider(f"זווית הארה (Beam)_{i+1}", 10, 160, 60)
        lamps.append({'id': i+1, 'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': l_beam})

# ==========================================
# 6. מנוע חישוב הנדסי (The Core Engine)
# ==========================================
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
    # מרחק מהמנורה לנקודת המדידה במישור ה-Z
    dz = abs(l['z'] - sensor_h)
    dist_sq = (X - l['x'])**2 + (Y - l['y'])**2 + dz**2
    dist = np.sqrt(dist_sq)
    cos_theta = dz / (dist + 0.001) # מניעת חלוקה באפס
    
    # חישוב פיזור קרן האור (Gaussian Beam Profile)
    beam_rad = np.radians(l['beam'])
    angle_from_axis = np.arccos(np.clip(cos_theta, -1.0, 1.0))
    beam_factor = np.exp(-(angle_from_axis**2) / (2 * (beam_rad/2.355)**2))
    
    # חישוב Lux לפי חוק ריבוע המרחק ההפוך (Inverse Square Law)
    lamp_lux = (l['p'] * 50 * cos_theta * beam_factor) / (dist_sq + 0.1)
    lux_grid += lamp_lux * mask
    
    # רכיב חישוב סנוור
    ugr_comp += (lamp_lux**2) / (dz**2 + 0.1)

# אור יום והחזרים (Radiosity)
if daylight_toggle:
    lux_grid[(X < 0.5) & mask.astype(bool)] += sun_lux
reflection = (sum(l['p'] for l in lamps) * rho_w * 6) / (room_w * room_d)
lux_grid += reflection * mask

# ==========================================
# 7. תקינה ישראלית (Compliance 8995)
# ==========================================
valid_lux_values = lux_grid[mask > 0]
avg_lux = np.mean(valid_lux_values) if len(valid_lux_values) > 0 else 0
uniformity = np.min(valid_lux_values) / avg_lux if avg_lux > 0 else 0
ugr_val = 8 * np.log10(max(1, np.mean(ugr_comp[mask > 0]) / 50))

# ==========================================
# 8. תצוגה ויזואלית
# ==========================================
tab_3d, tab_2d = st.tabs(["🎮 3D Engineering Studio", "📊 מפת חום ותקינה"])

with tab_3d:
    fig = go.Figure()
    
    # משטח המדידה הצף (מציג את האור בדיוק בגובה החיישן)
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), surfacecolor=lux_grid, 
                             colorscale='Turbo', name=f"Sensor Plane @ {sensor_h}m", opacity=0.9))
    
    # רצפה שקופה
    fig.add_trace(go.Surface(x=X, y=Y, z=np.zeros_like(X), colorscale='Greys', opacity=0.1, showscale=False))
    
    # מיקום גופי התאורה
    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers',
                                   marker=dict(size=10, color='gold', symbol='diamond'), name=f"מנורה {l['id']}"))
    
    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h])), height=700,
                      margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

with tab_2d:
    st.subheader("מדדי תקינה הנדסיים")
    target_lux = 300 # יעד ממוצע למשרד/מטבח
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LUX ממוצע", f"{int(avg_lux)}", delta=f"{int(avg_lux - target_lux)}")
    c2.metric("אחידות (Uo)", f"{uniformity:.2f}", delta="תקין" if uniformity > 0.4 else "לקוי")
    c3.metric("מדד סנוור (UGR)", f"{ugr_val:.1f}", delta="מסנוור" if ugr_val > 19 else "תקין", delta_color="inverse")
    c4.metric("סטטוס כללי", "עובר ✅" if avg_lux >= target_lux * 0.9 else "נכשל ❌")
    
    fig_heat = go.Figure(data=go.Contour(z=lux_grid, x=x, y=y, colorscale='Turbo', 
                                         contours=dict(showlabels=True, labelfont=dict(color='white'))))
    fig_heat.update_layout(title="חתך דו-מימדי (Heatmap)")
    st.plotly_chart(fig_heat, use_container_width=True)

# ==========================================
# 9. ייצוא נתונים מובנה
# ==========================================
st.divider()
def export_csv_report():
    output = io.StringIO()
    output.write(f"--- PROJECT: {st.session_state['project_id']} ---\n")
    output.write(f"SYSTEM: LightPlan 3D Ultimate (Daniel Khalfon)\n\n")
    
    pd.DataFrame({"פרמטר": ["רוחב", "עומק", "גובה תקרה", "גובה חיישן", "חומר קיר", "LUX ממוצע", "UGR (סנוור)"],
                  "ערך": [room_w, room_d, room_h, sensor_h, wall_mat, int(avg_lux), round(ugr_val, 1)]}).to_csv(output, index=False)
    
    output.write("\n--- LAMPS BOM (Bill of Materials) ---\n")
    pd.DataFrame(lamps).to_csv(output, index=False)
    return output.getvalue().encode('utf-8-sig')

col_ex1, col_ex2 = st.columns(2)
col_ex1.download_button("📥 הורד דוח הנדסי אקסל (CSV)", data=export_csv_report(), file_name=f"{st.session_state['project_id']}_report.csv")
col_ex2.button("🖨️ הפק דוח PDF לאדריכלים (דורש אינטגרציית שרת)")
