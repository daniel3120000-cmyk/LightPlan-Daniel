import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import json
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. ניהול מצב (State Management)
# ==========================================
st.set_page_config(page_title="LightPlan 3D - Ayala Hakofa", layout="wide")

# אתחול משתנים עבור ה-AI כדי שיוכל לעדכן את הסליידרים
if 'room_w' not in st.session_state: st.session_state['room_w'] = 6.0
if 'room_d' not in st.session_state: st.session_state['room_d'] = 8.0
if 'room_h' not in st.session_state: st.session_state['room_h'] = 2.8
if 'wall_mat' not in st.session_state: st.session_state['wall_mat'] = "טיח לבן"

st.title("🏙️ LightPlan 3D: הסטודיו המקצועי של איילה הקופה")
st.caption("מערכת הנדסית משולבת AI - תאורה, תקינה, וסימולציה מרחבית")

# ==========================================
# 2. מנוע AI (Gemini Vision)
# ==========================================
with st.sidebar.expander("🤖 סריקת חדר אוטומטית (AI Vision)", expanded=False):
    st.write("העלי תמונה של החדר וה-AI יזהה את המידות והחומרים.")
    api_key = st.text_input("הכניסי מפתח API (Gemini):", type="password")
    uploaded_img = st.file_uploader("בחרי תמונה", type=['jpg', 'jpeg', 'png'])
    
    if st.button("🔍 נתח תמונה ועדכן נתונים"):
        if not api_key or not uploaded_img:
            st.error("חובה להכניס מפתח API ותמונה.")
        else:
            with st.spinner("מנתח את גיאומטריית החדר..."):
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    img = Image.open(uploaded_img)
                    prompt = """Analyze this room. Return ONLY a valid JSON. No markdown. Keys:
                    "room_w": float (width in meters, 2.0-15.0),
                    "room_d": float (depth in meters, 2.0-15.0),
                    "wall_mat": string (choose exactly one: "טיח לבן", "בטון", "עץ", "זכוכית")"""
                    
                    response = model.generate_content([prompt, img])
                    data = json.loads(response.text.replace("```json", "").replace("```", "").strip())
                    
                    st.session_state['room_w'] = float(data.get('room_w', 5.0))
                    st.session_state['room_d'] = float(data.get('room_d', 5.0))
                    st.session_state['wall_mat'] = data.get('wall_mat', "טיח לבן")
                    st.success("✅ הנתונים עודכנו בהצלחה!")
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בניתוח התמונה: {e}")

# ==========================================
# 3. סרגל צד: אדריכלות ורהיטים
# ==========================================
st.sidebar.header("📐 אדריכלות ותקינה")
sensor_h = st.sidebar.slider("גובה חיישן (Z-Plane)", 0.0, 3.0, 0.0, help="גובה אפס יציג את צל הרהיטים")

room_w = st.sidebar.slider("רוחב (X)", 2.0, 15.0, key='room_w')
room_d = st.sidebar.slider("עומק (Y)", 2.0, 15.0, key='room_d')
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.2, 5.0, key='room_h')

albedo_map = {"טיח לבן": 0.85, "בטון": 0.35, "עץ": 0.40, "זכוכית": 0.90}
mat_options = list(albedo_map.keys())
wall_mat = st.sidebar.selectbox("חומר קירות", mat_options, index=mat_options.index(st.session_state['wall_mat']))
st.session_state['wall_mat'] = wall_mat
rho_w = albedo_map[wall_mat]

st.sidebar.header("🪑 ריהוט ונפח (יוצרים צללים)")
with st.sidebar.expander("𛛏 מיטה זוגית"):
    bx = st.slider("X מיטה", 0.0, room_w-1.6, 0.5)
    by = st.slider("Y מיטה", 0.0, room_d-2.0, 0.5)
    bh = 0.5 # גובה מיטה
with st.sidebar.expander("🖥️ שולחן עבודה"):
    dx = st.slider("X שולחן", 0.0, room_w-1.2, room_w-1.5)
    dy = st.slider("Y שולחן", 0.0, room_d-0.7, room_d-1.0)
    dh = 0.75 # גובה שולחן

# ==========================================
# 4. מערכת תאורה הנדסית
# ==========================================
st.sidebar.header("💡 גופי תאורה")
num_lamps = st.sidebar.number_input("מספר גופים", 1, 10, 2)
lamps = []
for i in range(int(num_lamps)):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X_{i+1}", 0.0, room_w, room_w/2 + (i*0.5))
        ly = st.slider(f"Y_{i+1}", 0.0, room_d, room_d/2)
        lz = st.slider(f"Z_{i+1}", 1.0, room_h, room_h - 0.2)
        lp = st.slider(f"Watts_{i+1}", 10, 400, 150)
        l_beam = st.slider(f"זווית הארה_{i+1}", 10, 160, 60)
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': l_beam})

# ==========================================
# 5. מנוע פיזיקלי משולב (Lux Function)
# ==========================================
def calc_lux(x_grid, y_grid, target_z, lamps, rho_w, w, d):
    lux = np.zeros_like(x_grid)
    for l in lamps:
        dz = abs(l['z'] - target_z)
        dist_sq = (x_grid - l['x'])**2 + (y_grid - l['y'])**2 + dz**2
        dist = np.sqrt(dist_sq)
        cos_theta = dz / (dist + 0.001)
        
        beam_rad = np.radians(l['beam'])
        angle = np.arccos(np.clip(cos_theta, -1.0, 1.0))
        beam_factor = np.exp(-(angle**2) / (2 * (beam_rad/2.355)**2))
        
        lux += (l['p'] * 50 * cos_theta * beam_factor) / (dist_sq + 0.1)
    
    reflection = (sum(l['p'] for l in lamps) * rho_w * 6) / (w * d)
    return lux + reflection

# רשתות נתונים
res = 60
X, Y = np.meshgrid(np.linspace(0, room_w, res), np.linspace(0, room_d, res))
lux_main = calc_lux(X, Y, sensor_h, lamps, rho_w, room_w, room_d)

# החלת צללים על הרצפה אם החיישן נמוך מהרהיט
if sensor_h < bh:
    lux_main[(X >= bx) & (X <= bx+1.6) & (Y >= by) & (Y <= by+2.0)] *= 0.15
if sensor_h < dh:
    lux_main[(X >= dx) & (X <= dx+1.2) & (Y >= dy) & (Y <= dy+0.7)] *= 0.15

# חישוב אור נפרד לחלק העליון של הרהיטים (כדי לראות עליהם את ה-Lux!)
res_furn = 15
X_bed, Y_bed = np.meshgrid(np.linspace(bx, bx+1.6, res_furn), np.linspace(by, by+2.0, res_furn))
lux_bed = calc_lux(X_bed, Y_bed, bh, lamps, rho_w, room_w, room_d)

X_tab, Y_tab = np.meshgrid(np.linspace(dx, dx+1.2, res_furn), np.linspace(dy, dy+0.7, res_furn))
lux_tab = calc_lux(X_tab, Y_tab, dh, lamps, rho_w, room_w, room_d)

# ==========================================
# 6. תצוגה ויזואלית
# ==========================================
tab_3d, tab_2d = st.tabs(["🎮 3D Studio", "📊 דוחות וייצוא"])

with tab_3d:
    fig = go.Figure()
    
    # מישור החיישן הראשי (עם Hover מדויק)
    fig.add_trace(go.Surface(x=X, y=Y, z=np.full_like(X, sensor_h), surfacecolor=lux_main, 
                             colorscale='Turbo', name="Sensor Plane",
                             hovertemplate='X: %{x:.2f}m<br>Y: %{y:.2f}m<br><b>Lux: %{surfacecolor:.0f}</b><extra></extra>'))
    
    # פונקציה ליצירת גוף הרהיט
    def add_mesh(fig, x, y, z, w, l, h, color, name):
        fig.add_trace(go.Mesh3d(
            x=[x,x+w,x+w,x,x,x+w,x+w,x], y=[y,y,y+l,y+l,y,y,y+l,y+l], z=[z,z,z,z,z+h,z+h,z+h,z+h],
            i=[0,0,4,7,1,2,2,3,4,0,4,5], j=[1,2,5,6,2,3,6,7,0,4,5,6], k=[2,3,6,7,5,6,7,4,1,5,6,7],
            color=color, opacity=0.9, name=name, hoverinfo='skip'))

    # מיטה - גוף תחתון כהה, ומשטח עליון מואר דינמית!
    add_mesh(fig, bx, by, 0, 1.6, 2.0, bh-0.01, '#2c3e50', 'גוף מיטה')
    fig.add_trace(go.Surface(x=X_bed, y=Y_bed, z=np.full_like(X_bed, bh), surfacecolor=lux_bed, 
                             colorscale='Turbo', showscale=False,
                             hovertemplate='<b>Lux על המיטה: %{surfacecolor:.0f}</b><extra></extra>'))

    # שולחן
    add_mesh(fig, dx, dy, 0, 1.2, 0.7, dh-0.01, '#8e44ad', 'גוף שולחן')
    fig.add_trace(go.Surface(x=X_tab, y=Y_tab, z=np.full_like(X_tab, dh), surfacecolor=lux_tab, 
                             colorscale='Turbo', showscale=False,
                             hovertemplate='<b>Lux על השולחן: %{surfacecolor:.0f}</b><extra></extra>'))

    # מנורות
    for l in lamps:
        fig.add_trace(go.Scatter3d(x=[l['x']], y=[l['y']], z=[l['z']], mode='markers',
                                   marker=dict(size=10, color='gold', symbol='diamond'), hoverinfo='skip'))

    fig.update_layout(scene=dict(aspectmode='data', zaxis=dict(range=[0, room_h])), height=700, margin=dict(l=0, r=0, b=0, t=0))
    st.plotly_chart(fig, use_container_width=True)

with tab_2d:
    avg_lux = np.mean(lux_main)
    st.metric("LUX ממוצע בחלל", f"{int(avg_lux)}")
    
    # יצירת דוח HTML (התחליף המושלם ל-PDF בעברית)
    html_report = f"""
    <html dir="rtl">
    <head>
        <meta charset="utf-8">
        <title>דוח תאורה - איילה הקופה</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 40px; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: right; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>דוח סימולציית תאורה פוטומטרית</h1>
        <h3>מתכננת: הסטודיו של איילה הקופה</h3>
        <p><strong>מידות חלל:</strong> {room_w} מטר רוחב X {room_d} מטר עומק.</p>
        <p><strong>חומר קירות:</strong> {wall_mat}</p>
        <p><strong>LUX ממוצע בשטח:</strong> {int(avg_lux)} Lux</p>
        
        <h2>פירוט גופי תאורה הנדרשים:</h2>
        <table>
            <tr><th>מספר גוף</th><th>הספק (Watts)</th><th>זווית הארה (Beam)</th><th>מיקום (X,Y,Z)</th></tr>
            {"".join([f"<tr><td>מנורה {i+1}</td><td>{l['p']}W</td><td>{l['beam']}°</td><td>({l['x']:.1f}, {l['y']:.1f}, {l['z']:.1f})</td></tr>" for i, l in enumerate(lamps)])}
        </table>
        <br><p><em>הדוח הופק באמצעות מערכת LightPlan 3D</em></p>
    </body>
    </html>
    """
    
    st.info("💡 המלצה: פתחי את הדוח בדפדפן ולחצי Ctrl+P (או 'הדפס') ובחרי ב-'שמור כ-PDF'. זה יבטיח שהעברית תצא מושלמת.")
    st.download_button("🖨️ הורד דוח מוכן להדפסה (HTML -> PDF)", data=html_report.encode('utf-8'), file_name="Ayala_Hakofa_Report.html", mime="text/html")
