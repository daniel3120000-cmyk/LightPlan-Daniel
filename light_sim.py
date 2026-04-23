import streamlit as st
import numpy as np
import plotly.graph_objects as go
import pandas as pd
import sys
import io

# הגדרות דף ומיתוג אישי
st.set_page_config(page_title="LightPlan 3D - Daniel Khalfon Edition", layout="wide")
st.title("🏙️ LightPlan 3D: הסטודיו של דניאל חלפון")
st.caption("פותח עבור הסטודיו לתכנון של דניאל חלפון")

# ==========================================
# קטגוריה 1: אדריכלות והמלצות
# ==========================================
st.sidebar.header("📐 אדריכלות והמלצות")
room_type = st.sidebar.selectbox(
    "ייעוד החדר (תקן מומלץ)",
    ["חדר שינה (150 Lux)", "סלון (200 Lux)", "חדר עבודה (500 Lux)", "מטבח (300 Lux)", "מעבדה (1000 Lux)"]
)
target_lux = int(room_type.split("(")[1].split(" ")[0])

room_w = st.sidebar.slider("רוחב חדר (X)", 2.0, 10.0, 5.0)
room_d = st.sidebar.slider("עומק חדר (Y)", 2.0, 10.0, 5.0)
room_h = st.sidebar.slider("גובה תקרה (Z)", 2.0, 5.0, 2.8)

# ==========================================
# קטגוריה 2: עיצוב וחומרים
# ==========================================
st.sidebar.header("🎨 עיצוב וחומרים")
col_wall, col_floor = st.sidebar.columns(2)
wall_mat = col_wall.selectbox("צבע קיר", ["לבן בהיר", "בז'", "אפור", "כחול כהה", "שחור"])
floor_mat = col_floor.selectbox("חומר רצפה", ["קרמיקה", "פרקט", "בטון", "שטיח כהה"])

refl_map = {
    "לבן בהיר": 0.85, "בז'": 0.65, "אפור": 0.4, "כחול כהה": 0.15, "שחור": 0.05,
    "קרמיקה": 0.75, "פרקט": 0.4, "בטון": 0.3, "שטיח כהה": 0.1
}
rho_w = refl_map[wall_mat]

# ==========================================
# קטגוריה 3: אור טבעי וחלונות
# ==========================================
st.sidebar.header("☀️ אור טבעי")
has_window = st.sidebar.checkbox("הוסף חלון", value=True)
sun_int = 0
win_data = {"קיים": "לא"}
if has_window:
    with st.sidebar.expander("🖼️ הגדרות חלון"):
        win_w = st.slider("רוחב חלון", 0.5, 3.0, 1.5)
        win_h = st.slider("גובה חלון", 0.5, 2.0, 1.2)
        win_y = st.slider("מיקום על ציר Y", 0.0, room_d - win_w, room_d/2 - win_w/2)
        win_z = st.slider("גובה מהרצפה", 0.1, room_h - win_h, 1.0)
        sun_int = st.slider("עוצמת אור שמש (Lux)", 0, 1000, 300)
        win_data = {"קיים": "כן", "רוחב": win_w, "גובה": win_h, "מיקום_Y": win_y, "גובה_Z": win_z}

# ==========================================
# קטגוריה 4: ריהוט ונפח (3D)
# ==========================================
st.sidebar.header("🪑 ריהוט ונפח")
with st.sidebar.expander("𛛏 הגדרות מיטה"):
    bx, by, bh = st.slider("מיקום X (מיטה)", 0.0, room_w-1.6, room_w-2.0), st.slider("מיקום Y (מיטה)", 0.0, room_d-2.0, 0.5), st.slider("גובה מיטה", 0.1, 1.2, 0.5)
with st.sidebar.expander("🖥️ הגדרות שולחן"):
    dx, dy, dh = st.slider("מיקום X (שולחן)", 0.0, room_w-1.2, 0.5), st.slider("מיקום Y (שולחן)", 0.0, room_d-0.7, room_d-1.5), st.slider("גובה שולחן", 0.1, 1.5, 0.75)

# ==========================================
# קטגוריה 5: מערכת תאורה
# ==========================================
st.sidebar.header("💡 מערכת תאורה")
num_lamps = st.sidebar.number_input("מספר מנורות", 1, 4, 1)

lamps = []
for i in range(num_lamps):
    with st.sidebar.expander(f"מנורה {i+1}", expanded=(i==0)):
        l_shape = st.selectbox(f"צורת גוף {i+1}", ["מלבן", "עיגול", "נקודה"])
        l_temp = st.select_slider(f"טמפרטורת צבע {i+1}", options=[2700, 3000, 4000, 6000], value=3000)
        l_w = st.slider(f"רוחב/רדיוס {i+1}", 0.1, 2.5, 0.6)
        l_d = st.slider(f"עומק {i+1}", 0.1, 1.5, 0.3) if l_shape == "מלבן" else l_w
        lx = st.slider(f"מיקום X {i+1}", 0.0, room_w, room_w/2)
        ly = st.slider(f"מיקום Y {i+1}", 0.0, room_d, room_d/2)
        lz = st.slider(f"גובה Z {i+1}", 0.5, room_h, 2.5)
        lp = st.slider(f"הספק (Watts) {i+1}", 10, 500, 150)
        
        temp_colors = {2700: 'orange', 3000: 'gold', 4000: 'white', 6000: 'lightblue'}
        lamps.append({'id': i+1, 'x': lx, 'y': ly, 'z': lz, 'p': lp, 'shape': l_shape, 'w': l_w, 'd': l_d, 'color': temp_colors[l_temp], 'kelvin': l_temp})

# --- מנוע פיזיקלי ---
grid_res = 60
X, Y = np.meshgrid(np.linspace(0, room_w, grid_res), np.linspace(0, room_d, grid_res))
total_intensity = np.zeros_like(X)

for l in lamps:
    points_res = 2 if l['shape'] != "נקודה" else 1
    for px in np.linspace(l['x'] - l['w']/2, l['x'] + l['w']/2, points_res):
        for py in np.linspace(l['y'] - l['d']/2, l['y'] + l['d']/2, points_res):
            r_sq = (X - px)**2 + (Y - py)**2 + l['z']**2
            lamp_int = (l['p']/(points_res**2) * 30 * l['z']) / (r_sq**1.5 + 0.1)
            def shadow(intens, ox, oy, ow, ol, oh):
                t = (l['z'] - oh) / (l['z'] + 0.001)
                sx, sy = px + (X - px) * t, py + (Y - py) * t
                mask = (sx >= ox) & (sx <= ox + ow) & (sy >= oy) & (sy <= oy + ol) & (l['z'] > oh)
                intens[mask] *= 0.15
                return intens
            lamp_int = shadow(lamp_int, bx, by, 1.6, 2.0, bh)
            lamp_int = shadow(lamp_int, dx, dy, 1.2, 0.7, dh)
            total_intensity += lamp_int

if has_window:
    total_intensity[(X < 1.0) & (Y > win_y) & (Y < win_y + win_w)] += sun_int
reflection_boost = (sum(l['p'] for l in lamps) * rho_w * 7) / (room_w * room_d)
total_intensity += reflection_boost

# --- תצוגה גרפית ---
fig = go.Figure()
fig.add_trace(go.Surface(
    x=X, y=Y, z=np.zeros_like(X), surfacecolor=total_intensity, colorscale='Hot',
    hovertemplate='<b>X:</b> %{x:.2f}m, <b>Y:</b> %{y:.2f}m<br><b>עוצמה:</b> %{surfacecolor:.0f} Lux<extra></extra>',
    colorbar=dict(title="Lux")
))
def add_solid(fig, x, y, z, w, l, h, color, name):
    fig.add_trace(go.Mesh3d(x=[x,x+w,x+w,x,x,x+w,x+w,x], y=[y,y,y+l,y+l,y,y,y+l,y+l], z=[z,z,z,z,z+h,z+h,z+h,z+h],
                           i=[0,0,4,7,1,2,2,3,4,0,4,5], j=[1,2,5,6,2,3,6,7,0,4,5,6], k=[2,3,6,7,5,6,7,4,1,5,6,7],
                           color=color, opacity=0.9, name=name, flatshading=True, hoverinfo='name'))
add_solid(fig, bx, by, 0, 1.6, 2.0, bh, 'teal', "מיטה")
add_solid(fig, dx, dy, 0, 1.2, 0.7, dh, 'brown', "שולחן")
for i, l in enumerate(lamps):
    add_solid(fig, l['x']-l['w']/2, l['y']-l['d']/2, l['z'], l['w'], l['d'], 0.1, l['color'], f"מנורה {i+1}")
if has_window:
    fig.add_trace(go.Mesh3d(x=[0, 0.05, 0.05, 0], y=[win_y, win_y, win_y+win_w, win_y+win_w], 
                           z=[win_z, win_z, win_z+win_h, win_z+win_h], color='skyblue', name="חלון"))
fig.update_layout(scene=dict(xaxis=dict(range=[0,room_w]), yaxis=dict(range=[0,room_d]), zaxis=dict(range=[0,room_h]), aspectmode='data'), margin=dict(l=0, r=0, b=0, t=40))
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# קטגוריה 6: מדדים ודוח מובנה להורדה
# ==========================================
st.divider()
avg_lux = np.mean(total_intensity)
c1, c2, c3, c4 = st.columns(4)
c1.metric("ממוצע אור", f"{int(avg_lux)} Lux", delta=f"{int(avg_lux - target_lux)} מהיעד")
c2.metric("החזר מהקירות", f"+{int(reflection_boost)} Lux")
c3.metric("יעד תקן", f"{target_lux} Lux")

# --- בניית הדוח המובנה (Structured Report) ---
# טבלה 1: סיכום חדר
summary_data = {
    "קטגוריה": ["ייעוד", "רוחב", "עומק", "גובה", "צבע קיר", "חומר רצפה", "LUX ממוצע", "LUX יעד"],
    "ערך": [room_type, room_w, room_d, room_h, wall_mat, floor_mat, int(avg_lux), target_lux]
}
# טבלה 2: מנורות
lamp_report = pd.DataFrame([
    {"מנורה": l['id'], "X": l['x'], "Y": l['y'], "Z": l['z'], "Watts": l['p'], "צורה": l['shape'], "Kelvin": l['kelvin']}
    for l in lamps
])
# טבלה 3: רהיטים
furniture_report = pd.DataFrame([
    {"פריט": "מיטה", "X": bx, "Y": by, "גובה": bh},
    {"פריט": "שולחן", "X": dx, "Y": dy, "גובה": dh}
])

# פונקציית ייצוא לקובץ CSV אחד עם כותרות
def create_csv_report():
    output = io.StringIO()
    output.write("--- דוח תכנון תאורה: דניאל חלפון ---\n\n")
    output.write("CATEGORY: ROOM SUMMARY\n")
    pd.DataFrame(summary_data).to_csv(output, index=False)
    output.write("\nCATEGORY: LAMPS DATA\n")
    lamp_report.to_csv(output, index=False)
    output.write("\nCATEGORY: FURNITURE DATA\n")
    furniture_report.to_csv(output, index=False)
    if has_window:
        output.write("\nCATEGORY: WINDOW DATA\n")
        pd.DataFrame([win_data]).to_csv(output, index=False)
    return output.getvalue()

c4.download_button(
    label="📥 הורד דוח מובנה (CSV)",
    data=create_csv_report(),
    file_name='Daniel_Khalfon_Report.csv',
    mime='text/csv'
)

if avg_lux >= target_lux * 0.9:
    st.success(f"✅ תכנון מעולה ל{room_type}!")
else:
    st.warning(f"⚠️ עוצמת האור חלשה מהיעד.")