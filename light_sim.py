import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import sys
import io

# הגדרות דף ומיתוג
st.set_page_config(page_title="LightPlan 3D - Pro Edition (Daniel Khalfon)", layout="wide")
st.title("🏙️ LightPlan 3D: הסטודיו המקצועי של דניאל חלפון")
st.caption("גרסת Pro - כוללת חישובי זווית הארה ומצב דו-מימד")

# ==========================================
# קטגוריה 1: הגדרות תצוגה (חדש!)
# ==========================================
st.sidebar.header("🔄 הגדרות תצוגה")
view_mode = st.sidebar.radio("מצב תצוגה", ["תלת-מימד (3D Surface)", "דו-מימד (2D Heatmap)"])

# ==========================================
# קטגוריה 2: אדריכלות וחומרים (משודרג)
# ==========================================
st.sidebar.header("📐 אדריכלות וחומרים")
room_type = st.sidebar.selectbox(
    "ייעוד החדר",
    ["חדר שינה (150 Lux)", "סלון (200 Lux)", "חדר עבודה (500 Lux)", "מטבח (300 Lux)", "מעבדה (1000 Lux)"]
)
target_lux = int(room_type.split("(")[1].split(" ")[0])

room_w = st.sidebar.slider("רוחב חדר (X)", 2.0, 10.0, 5.0)
room_d = st.sidebar.slider("עומק חדר (Y)", 2.0, 10.0, 5.0)
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.0, 5.0, 2.8)

# ספריית חומרים מקצועית
mat_options = {
    "לבן קלאסי (Albedo 0.85)": 0.85,
    "בטון חשוף (Albedo 0.35)": 0.35,
    "עץ אלון (Albedo 0.45)": 0.45,
    "אפור גרפיט (Albedo 0.15)": 0.15,
    "זכוכית/מראה (Albedo 0.90)": 0.90
}
wall_mat = st.sidebar.selectbox("חומר/צבע קירות", list(mat_options.keys()))
rho_w = mat_options[wall_mat]

# ==========================================
# קטגוריה 3: אור טבעי
# ==========================================
st.sidebar.header("☀️ אור טבעי")
has_window = st.sidebar.checkbox("הוסף חלון", value=True)
sun_int = 0
if has_window:
    with st.sidebar.expander("🖼️ הגדרות חלון"):
        win_w = st.slider("רוחב חלון", 0.5, 3.0, 1.5)
        win_h = st.slider("גובה חלון", 0.5, 2.0, 1.2)
        win_y = st.slider("מיקום על ציר Y", 0.0, room_d - win_w, room_d/2 - win_w/2)
        win_z = st.slider("גובה Z", 0.1, room_h - win_h, 1.0)
        sun_int = st.slider("עוצמת שמש (Lux)", 0, 1000, 300)

# ==========================================
# קטגוריה 4: ריהוט (נפח 3D)
# ==========================================
st.sidebar.header("🪑 ריהוט ונפח")
with st.sidebar.expander("𛛏 מיטה"):
    bx, by, bh = st.slider("מיקום X", 0.0, room_w-1.6, room_w-2.0), st.slider("מיקום Y", 0.0, room_d-2.0, 0.5), 0.5
with st.sidebar.expander("🖥️ שולחן"):
    dx, dy, dh = st.slider("מיקום X ", 0.0, room_w-1.2, 0.5), st.slider("מיקום Y ", 0.0, room_d-0.7, room_d-1.5), 0.75

# ==========================================
# קטגוריה 5: מערכת תאורה (כולל Beam Angle)
# ==========================================
st.sidebar.header("💡 תאורה הנדסית")
num_lamps = st.sidebar.number_input("מספר מנורות", 1, 4, 1)

lamps = []
for i in range(num_lamps):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        lx = st.slider(f"X {i+1}", 0.0, room_w, room_w/2)
        ly = st.slider(f"Y {i+1}", 0.0, room_d, room_d/2)
        lz = st.slider(f"גובה Z {i+1}", 1.5, room_h, 2.6)
        lp = st.slider(f"הספק (W) {i+1}", 10, 500, 150)
        # חידוש: זווית הארה
        l_beam = st.slider(f"זווית הארה (Beam Angle) {i+1}", 10, 120, 60)
        l_temp = st.select_slider(f"גוון {i+1}", options=[2700, 3000, 4000, 6000], value=3000)
        
        temp_colors = {2700: 'orange', 3000: 'gold', 4000: 'white', 6000: 'lightblue'}
        lamps.append({'x': lx, 'y': ly, 'z': lz, 'p': lp, 'beam': l_beam, 'color': temp_colors[l_temp]})

# --- מנוע פיזיקלי משודרג (עם חוק הקוסינוס של Lambert) ---
grid_res = 65
x_vals = np.linspace(0, room_w, grid_res)
y_vals = np.linspace(0, room_d, grid_res)
X, Y = np.meshgrid(x_vals, y_vals)
total_intensity = np.zeros_like(X)

for l in lamps:
    dx_lamp = X - l['x']
    dy_lamp = Y - l['y']
    dist_sq = dx_lamp**2 + dy_lamp**2 + l['z']**2
    dist = np.sqrt(dist_sq)
    
    # חישוב זווית מהאנך (Theta)
    cos_theta = l['z'] / dist
    
    # נוסחת פיזור מבוססת Beam Angle (קירוב גאוסיאני)
    beam_rad = np.radians(l['beam'])
    sigma = beam_rad / 2.355 # המרה מזווית לסטיית תקן
    angle_from_center = np.arccos(cos_theta)
    beam_multiplier = np.exp(-(angle_from_center**2) / (2 * sigma**2))
    
    # עוצמת אור משולבת
    lamp_int = (l['p'] * 40 * cos_theta * beam_multiplier) / (dist_sq + 0.1)
    
    # צללים
    def apply_shadow(intens, ox, oy, ow, ol, oh):
        t = (l['z'] - oh) / (l['z'] + 0.001)
        sx, sy = l['x'] + (X - l['x']) * t, l['y'] + (Y - l['y']) * t
        mask = (sx >= ox) & (sx <= ox + ow) & (sy >= oy) & (sy <= oy + ol) & (l['z'] > oh)
        intens[mask] *= 0.1
        return intens
    
    lamp_int = apply_shadow(lamp_int, bx, by, 1.6, 2.0, 0.5)
    lamp_int = apply_shadow(lamp_int, dx, dy, 1.2, 0.7, 0.75)
    total_intensity += lamp_int

# אור חלון והחזרי קיר
if has_window:
    total_intensity[(X < 0.5) & (Y > win_y) & (Y < win_y + win_w)] += sun_int
reflection_boost = (sum(l['p'] for l in lamps) * rho_w * 8) / (room_w * room_d)
total_intensity += reflection_boost

# ==========================================
# תצוגה גרפית (3D או 2D לפי בחירה)
# ==========================================
fig = go.Figure()

if view_mode == "תלת-מימד (3D Surface)":
    fig.add_trace(go.Surface(x=X, y=Y, z=np.zeros_like(X), surfacecolor=total_intensity, colorscale='Viridis',
                             hovertemplate='Lux: %{surfacecolor:.0f}<extra></extra>'))
    
    # הוספת גופים תלת-ממדיים
    def add_box(fig, x, y, z, w, l, h, color, name):
        fig.add_trace(go.Mesh3d(x=[x,x+w,x+w,x,x,x+w,x+w,x], y=[y,y,y+l,y+l,y,y,y+l,y+l], z=[z,z,z,z,z+h,z+h,z+h,z+h],
                               i=[0,0,4,7,1,2,2,3,4,0,4,5], j=[1,2,5,6,2,3,6,7,0,4,5,6], k=[2,3,6,7,5,6,7,4,1,5,6,7],
                               color=color, opacity=0.8, name=name))
    add_box(fig, bx, by, 0, 1.6, 2.0, 0.5, 'teal', "מיטה")
    add_box(fig, dx, dy, 0, 1.2, 0.7, 0.75, 'brown', "שולחן")
    for i, l in enumerate(lamps):
        add_box(fig, l['x']-0.2, l['y']-0.2, l['z'], 0.4, 0.4, 0.1, l['color'], f"מנורה {i+1}")
else:
    # מצב דו-מימד (Heatmap)
    fig.add_trace(go.Contour(x=x_vals, y=y_vals, z=total_intensity, colorscale='Viridis', 
                             contours=dict(showlabels=True, labelfont=dict(size=12, color='white'))))
    # סימון רהיטים בדו-מימד
    fig.add_shape(type="rect", x0=bx, y0=by, x1=bx+1.6, y1=by+2.0, line=dict(color="white"), name="מיטה")
    fig.add_shape(type="rect", x0=dx, y0=dy, x1=dx+1.2, y1=dy+0.7, line=dict(color="white"), name="שולחן")

fig.update_layout(scene=dict(xaxis=dict(range=[0,room_w]), yaxis=dict(range=[0,room_d]), zaxis=dict(range=[0,room_h]), aspectmode='data'),
                  margin=dict(l=0, r=0, b=0, t=0), height=600)
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# דוח הנדסי (Daniel Khalfon Pro Report)
# ==========================================
st.divider()
avg_lux = np.mean(total_intensity)
c1, c2, c3, c4 = st.columns(4)
c1.metric("ממוצע Lux", f"{int(avg_lux)}")
c2.metric("מצב תצוגה", view_mode)
c3.metric("יעד", f"{target_lux} Lux")

def create_pro_report():
    output = io.StringIO()
    output.write("--- LightPlan 3D PRO REPORT: DANIEL KHALFON ---\n\n")
    output.write("1. נתוני חלל וחומרים\n")
    pd.DataFrame({"פרמטר": ["ייעוד", "מידות (WxDxH)", "חומר קיר", "Lux יעד"],
                  "ערך": [room_type, f"{room_w}x{room_d}x{room_h}", wall_mat, target_lux]}).to_csv(output, index=False)
    output.write("\n2. פירוט גופי תאורה\n")
    pd.DataFrame([{"מנורה": i+1, "מיקום (X,Y,Z)": f"{l['x']},{l['y']},{l['z']}", "Beam Angle": l['beam'], "Watts": l['p']} 
                  for i, l in enumerate(lamps)]).to_csv(output, index=False)
    return output.getvalue().encode('utf-8-sig')

c4.download_button("📥 הורד דוח הנדסי Pro (Excel)", data=create_pro_report(), file_name="Daniel_Khalfon_Pro_Report.csv", mime="text/csv")

if avg_lux >= target_lux * 0.9:
    st.success("✅ החלל עומד בתקן התאורה הנדרש.")
else:
    st.warning("⚠️ עוצמת התאורה נמוכה מהמומלץ.")
