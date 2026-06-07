import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re

# Set Page Configuration
st.set_page_config(
    page_title="MHP CRM - DID Group Analytics",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Custom CSS Injection for Glassmorphic & Modern Theme
with open("components/style.html", "r", encoding="utf-8") as f:
    st.markdown(f.read(), unsafe_allow_html=True)



# ==========================================
# 1. DATA LOAD & CLEANING PIPELINE
# ==========================================

@st.cache_data
def load_and_clean_data(file_path):
    # Load dataset
    df = pd.read_csv(file_path)
    
    # Trim all string columns
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
        
    # Helper to parse Indonesian Rupiah strings
    def clean_rupiah(val):
        if pd.isna(val) or val == "" or val == "nan":
            return 0.0
        val_str = str(val)
        # Remove 'Rp', dots (thousands separator), and spaces
        val_str = re.sub(r'[Rp\s]', '', val_str)
        if not val_str:
            return 0.0
        
        # Format commas for decimal conversion (Indonesian currency uses ,00 for cents)
        if ',' in val_str:
            parts = val_str.split(',')
            if len(parts) == 2 and len(parts[1]) == 2:
                # E.g. '1.000.000,00' -> '1000000.00'
                val_str = parts[0].replace('.', '') + '.' + parts[1]
            else:
                val_str = val_str.replace('.', '').replace(',', '.')
        else:
            val_str = val_str.replace('.', '')
            
        try:
            return float(val_str)
        except:
            return 0.0

    # Clean currency columns
    currency_cols = ['Total', 'Harga', 'Fee Driver', 'BBM', 'Tol + Parkir']
    for col in currency_cols:
        clean_col_name = f"Clean_{col}".replace(" ", "_").replace("+", "_")
        clean_col_name = re.sub(r'_+', '_', clean_col_name)
        df[clean_col_name] = df[col].apply(clean_rupiah)
        
    # Clean and Normalize Unit types
    def normalize_unit(unit):
        u = str(unit).upper()
        if u in ["ZENIX G", "ZENIXG"]:
            return "Zenix G"
        elif u in ["ZENIX Q", "ZENIXQ", "ZENIQ Q"]:
            return "Zenix Q"
        elif u == "REBORN":
            return "Reborn"
        elif u == "ZENIX Q / G":
            return "Zenix Q / G"
        return str(unit).title()

    df['Clean_Unit'] = df['Unit'].apply(normalize_unit)
    
    # Normalize Penyewa (Renter) names for proper CRM loyalties
    def normalize_penyewa(name):
        n = str(name).upper()
        # Group duplicates or variations
        if n in ["AMIEN", "AMIEN RENT", "AMIEN TRANS", "AMIN", "AMINRENT", "AMIN TRANS", "DEBBY/ AMIEN"]:
            return "Amin Rent"
        elif n in ["ASY", "ASY TRANS", "ASY/HAMS", "ASHYHAMS"]:
            return "ASY Trans"
        elif n in ["BENDOS HAMS", "BENDOS HAMZ"]:
            return "Bendos Hamz"
        elif n in ["CAKRA BETON", "CAKTRA BETON"]:
            return "Cakra Beton"
        elif n in ["JAWA DWIPA", "JAWADWIPA", "POER / JAWADWIPA"]:
            return "Jawa Dwipa"
        elif n in ["KRESNA", "KRESNA ZEN", "GRESS GUSTIN / KRISNA"]:
            return "Kresna"
        elif n in ["SBY TRANS", "SBY TRANS / ST"]:
            return "SBY Trans"
        elif n in ["SINYO", "SINYO HAMS", "SINYO HAMZ"]:
            return "Sinyo Hamz"
        elif n in ["STENLEY", "STENLEY FIF", "STANLEY", "STENLEY FIF"]:
            return "Stanley"
        elif n in ["VIAHAMS", "VIAHAMS/ FAIZAL"]:
            return "Via Hamz"
        elif n in ["YUDI TAGUS", "YUDI TRANS"]:
            return "Yudi Trans"
        elif n in ["ARIF AAT", "ARIFAAT"]:
            return "Arif AAT"
        elif n in ["DAVA", "DAVA FRIEND"]:
            return "Dava"
        return str(name).title()

    df['Clean_Penyewa'] = df['Penyewa'].apply(normalize_penyewa)
    
    # Standardize Status
    def clean_status(stat):
        s = str(stat).upper()
        status_map = {
            "LK": "Lepas Kunci (Self)",
            "KONTRAK": "Kontrak",
            "INCLUDE ALL": "Include All",
            "INCLUDE": "Include Driver"
        }
        return status_map.get(s, s.title())
        
    df['Clean_Status'] = df['Status'].apply(clean_status)
    
    # Date Handling
    month_map = {
        "Okt": 10, "Nov": 11, "Des": 12,
        "Jan": 1, "Feb": 2, "Mar": 3
    }
    df['Month_Num'] = df['Bulan'].map(month_map)
    # Since dates span 2025 (Okt, Nov, Des) and 2026 (Jan, Feb, Mar)
    # We assign custom sorting order
    df['Chronological_Sort'] = df.apply(
        lambda r: (r['Tahun'] * 100) + r['Month_Num'], axis=1
    )
    df['Bulan_Tahun'] = df['Bulan'] + " " + df['Tahun'].astype(str)
    
    # New vs Returning Customer Classification
    df = df.sort_values('Chronological_Sort')
    first_months = df.groupby('Clean_Penyewa')['Chronological_Sort'].min().reset_index()
    first_months.rename(columns={'Chronological_Sort': 'First_Month_Val'}, inplace=True)
    df = df.merge(first_months, on='Clean_Penyewa', how='left')
    df['Customer_Type'] = df.apply(
        lambda r: 'New' if r['Chronological_Sort'] == r['First_Month_Val'] else 'Returning', axis=1
    )
    
    return df

# Load and cache raw dataset
csv_path = "full-data-did-group.csv"
try:
    df_raw = load_and_clean_data(csv_path)
except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.stop()


# ==========================================
# 2. SIDEBAR CONTROLS & FILTERING
# ==========================================

st.sidebar.markdown(
    "<h2 style='text-align: center; color: #EA3A3A; font-weight: 800; margin-bottom: 24px;'>CRM FILTERS</h2>",
    unsafe_allow_html=True
)

# Year-Month Range Selection (Chronological order)
sorted_months = df_raw.sort_values('Chronological_Sort')['Bulan_Tahun'].unique().tolist()
selected_months = st.sidebar.multiselect(
    "Rentang Bulan",
    options=sorted_months,
    default=sorted_months,
    help="Pilih bulan transaksi yang ingin dianalisis"
)

# Vehicle Unit Filter
sorted_units = sorted(df_raw['Clean_Unit'].unique().tolist())
selected_units = st.sidebar.multiselect(
    "Pilihan Armada",
    options=sorted_units,
    default=sorted_units,
    help="Filter data berdasarkan jenis kendaraan"
)

# Status Filter
sorted_statuses = sorted(df_raw['Clean_Status'].unique().tolist())
selected_statuses = st.sidebar.multiselect(
    "Status Sewa",
    options=sorted_statuses,
    default=sorted_statuses,
    help="Filter berdasarkan cara transaksi sewa"
)

# Client Search
renter_search = st.sidebar.text_input(
    "Cari Nama Penyewa",
    placeholder="Cari client...",
    help="Cari nama penyewa spesifik secara langsung"
)

# Apply filters
df_filtered = df_raw.copy()

if selected_months:
    df_filtered = df_filtered[df_filtered['Bulan_Tahun'].isin(selected_months)]
if selected_units:
    df_filtered = df_filtered[df_filtered['Clean_Unit'].isin(selected_units)]
if selected_statuses:
    df_filtered = df_filtered[df_filtered['Clean_Status'].isin(selected_statuses)]
if renter_search:
    df_filtered = df_filtered[df_filtered['Clean_Penyewa'].str.contains(renter_search, case=False)]


# ==========================================
# 3. HEADER & HERO
# ==========================================

col_logo, col_title = st.columns([1, 8])
with col_logo:
    with open("components/logo.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)

with col_title:
    with open("components/title.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)

with open("components/style/header-hero.html", "r", encoding="utf-8") as f:
    st.markdown(f.read(), unsafe_allow_html=True)


# ==========================================
# 4. KEY METRICS ROW (KPI CARDS)
# ==========================================

# Calculate Metrics
total_revenue = df_filtered['Clean_Total'].sum()
total_transactions = len(df_filtered)
total_days = df_filtered['Durasi (Day)'].sum()
unique_renters = df_filtered['Clean_Penyewa'].nunique()

# KPI Metric Columns
col1, col2, col3, col4 = st.columns(4)

def format_rupiah(value):
    return f"Rp {value:,.0f}".replace(",", ".")

# Revenue Card
with col1:
    with open("components/revenue-card.html", "r", encoding="utf-8") as f:
        st.markdown(f.read().format(total_revenue_fmt=format_rupiah(total_revenue)), unsafe_allow_html=True)


# Transactions Card
with col2:
    with open("components/transaction-card.html", "r", encoding="utf-8") as f:
        st.markdown(f.read().format(total_transactions=total_transactions), unsafe_allow_html=True)

# Rental Duration Card
with col3:
    with open("components/rental-duration-card.html", "r", encoding="utf-8") as f:
        st.markdown(f.read().format(total_days=int(total_days)), unsafe_allow_html=True)

# Unique Renters Card
with col4:
    with open("components/unique-renters-card.html", "r", encoding="utf-8") as f:
        st.markdown(f.read().format(unique_renters=unique_renters), unsafe_allow_html=True)



# ==========================================
# 5. DATA VISUALIZATIONS SECTION
# ==========================================

# -----------------
# VISUALISASI 1: Performa Unit & Utilisasi (Pendapatan vs. Hari Terpakai)
# -----------------
with open("components/style/visualize-1.html", "r", encoding="utf-8") as f:
    st.markdown(f.read(), unsafe_allow_html=True)

tab_unit, tab_trend = st.tabs(["Ringkasan per Unit", "Tren Bulanan Performa"])

with tab_unit:
    # Aggregation per Clean_Unit
    df_unit = df_filtered.groupby('Clean_Unit').agg(
        Total_Revenue=('Clean_Total', 'sum'),
        Total_Days=('Durasi (Day)', 'sum'),
        Transaction_Count=('Clean_Unit', 'count')
    ).reset_index()
    
    # Create Subplot with Dual Y-Axis
    fig_unit = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add Revenue Bar Chart
    fig_unit.add_trace(
        go.Bar(
            x=df_unit['Clean_Unit'],
            y=df_unit['Total_Revenue'],
            name="Pemasukan Bersih (IDR)",
            marker_color="#EA3A3A",
            hovertemplate="Armada: %{x}<br>Pendapatan: Rp %{y:,.0f}<extra></extra>",
            opacity=0.85
        ),
        secondary_y=False
    )
    
    # Add Duration Line Chart
    fig_unit.add_trace(
        go.Scatter(
            x=df_unit['Clean_Unit'],
            y=df_unit['Total_Days'],
            name="Durasi Sewa (Hari)",
            mode="lines+markers+text",
            marker=dict(size=10, color="#4B5563"),
            line=dict(width=3, color="#4B5563"),
            text=df_unit['Total_Days'],
            textposition="top center",
            hovertemplate="Armada: %{x}<br>Total Sewa: %{y} Hari<extra></extra>"
        ),
        secondary_y=True
    )
    
    # Update layout properties
    fig_unit.update_layout(
        title=dict(text="<b>Rasio ROI per Jenis Unit (Pendapatan vs Hari Terpakai)</b>", font=dict(size=16, color="#111827")),
        font=dict(family="Outfit, sans-serif", color="#4B5563"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="rgba(0,0,0,0.08)", font=dict(family="Outfit, sans-serif", size=13, color="#111827")),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(0,0,0,0.06)", borderwidth=1),
        margin=dict(l=40, r=40, t=60, b=40),
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", showline=True, linecolor="rgba(0,0,0,0.08)", tickfont=dict(color="#4B5563")),
        yaxis=dict(
            title=dict(text="Pemasukan Bersih (IDR)", font=dict(color="#EA3A3A")),
            tickfont=dict(color="#4B5563"),
            gridcolor="rgba(0,0,0,0.06)",
            showgrid=True
        ),
        yaxis2=dict(
            title=dict(text="Durasi Sewa (Hari)", font=dict(color="#4B5563")),
            tickfont=dict(color="#4B5563"),
            showgrid=False
        )
    )
    
    st.plotly_chart(fig_unit, use_container_width=True)

with tab_trend:
    # Aggregation per Bulan_Tahun (with custom chronological sort)
    df_trend = df_filtered.groupby(['Chronological_Sort', 'Bulan_Tahun']).agg(
        Total_Revenue=('Clean_Total', 'sum'),
        Total_Days=('Durasi (Day)', 'sum')
    ).reset_index().sort_values('Chronological_Sort')
    
    fig_trend = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_trend.add_trace(
        go.Bar(
            x=df_trend['Bulan_Tahun'],
            y=df_trend['Total_Revenue'],
            name="Pendapatan Bulanan (IDR)",
            marker_color="#EA3A3A",
            hovertemplate="Bulan: %{x}<br>Pendapatan: Rp %{y:,.0f}<extra></extra>",
            opacity=0.85
        ),
        secondary_y=False
    )
    
    fig_trend.add_trace(
        go.Scatter(
            x=df_trend['Bulan_Tahun'],
            y=df_trend['Total_Days'],
            name="Durasi Rental Bulanan (Hari)",
            mode="lines+markers",
            marker=dict(size=8, color="#4B5563"),
            line=dict(width=3, color="#4B5563"),
            hovertemplate="Bulan: %{x}<br>Durasi Rental: %{y} Hari<extra></extra>"
        ),
        secondary_y=True
    )
    
    fig_trend.update_layout(
        title=dict(text="<b>Tren Pendapatan & Durasi Sewa Bulanan (DID Group)</b>", font=dict(size=16, color="#111827")),
        font=dict(family="Outfit, sans-serif", color="#4B5563"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="rgba(0,0,0,0.08)", font=dict(family="Outfit, sans-serif", size=13, color="#111827")),
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.9)", bordercolor="rgba(0,0,0,0.06)", borderwidth=1),
        xaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#4B5563")),
        yaxis=dict(title=dict(text="Pendapatan (IDR)", font=dict(color="#EA3A3A")), tickfont=dict(color="#4B5563"), gridcolor="rgba(0,0,0,0.06)"),
        yaxis2=dict(title=dict(text="Total Hari Rental", font=dict(color="#4B5563")), tickfont=dict(color="#4B5563"))
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)


# -----------------
# VISUALISASI 2 & 3: Loyalitas Pelanggan (Top Renters) & Distribusi Tujuan
# -----------------
col_left, col_right = st.columns([5, 4])

with col_left:
    with open("components/style/visualize-2.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)
    
    # Aggregate client profiles
    df_renter = df_filtered.groupby('Clean_Penyewa').agg(
        Frekuensi=('Clean_Penyewa', 'count'),
        Total_Belanja=('Clean_Total', 'sum'),
        Rata_Rata_Hari=('Durasi (Day)', 'mean')
    ).reset_index()
    
    df_renter = df_renter.sort_values(by='Total_Belanja', ascending=False).reset_index(drop=True)
    
    # Format currency for displaying
    df_display = df_renter.copy()
    df_display['Total Belanja (Clean)'] = df_display['Total_Belanja'] # Keep float for sorting inside Streamlit table
    df_display['Total Belanja'] = df_display['Total_Belanja'].apply(format_rupiah)
    df_display['Rata-rata Durasi'] = df_display['Rata_Rata_Hari'].round(1).astype(str) + " Hari"
    
    # Rename columns for presentation
    df_display = df_display.rename(columns={
        'Clean_Penyewa': 'Nama Pelanggan',
        'Frekuensi': 'Frekuensi Sewa'
    })
    
    # Draw interactive leaderboard table
    st.dataframe(
        df_display[['Nama Pelanggan', 'Frekuensi Sewa', 'Total Belanja', 'Rata-rata Durasi']],
        use_container_width=True,
        hide_index=True
    )

    # VIP Retentive Insights Card
    with open("components/rentetive-insight-card.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)  # static card, no variables


with col_right:
    with open("components/style/visualize-3.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)
    
    # Aggregate destinations
    df_tujuan = df_filtered.groupby('Tujuan').agg(
        Total_Transaksi=('Tujuan', 'count'),
        Total_Pemasukan=('Clean_Total', 'sum')
    ).reset_index()
    
    # Plotly Donut Chart
    fig_donut = px.pie(
        df_tujuan,
        values='Total_Transaksi',
        names='Tujuan',
        hole=0.5,
        color_discrete_sequence=['#EA3A3A', '#4B5563', '#9CA3AF'],
        labels={'Total_Transaksi': 'Frekuensi', 'Tujuan': 'Destinasi'}
    )
    
    fig_donut.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate="Tujuan: %{label}<br>Jumlah Perjalanan: %{value} kali<br>Share: %{percent}<extra></extra>"
    )
    
    fig_donut.update_layout(
        title=None,
        showlegend=True,
        font=dict(family="Outfit, sans-serif", color="#4B5563"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(color="#4B5563")),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="rgba(0,0,0,0.08)", font=dict(family="Outfit, sans-serif", size=13, color="#111827")),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=10, b=40)
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)
    
    # Display Destination Stats Table
    df_tujuan_disp = df_tujuan.copy().sort_values('Total_Transaksi', ascending=False)
    df_tujuan_disp['Total Pendapatan'] = df_tujuan_disp['Total_Pemasukan'].apply(format_rupiah)
    st.dataframe(
        df_tujuan_disp[['Tujuan', 'Total_Transaksi', 'Total Pendapatan']].rename(columns={'Total_Transaksi': 'Perjalanan'}),
        use_container_width=True,
        hide_index=True
    )



# -----------------
# VISUALISASI 4: Analisis Retensi & Akuisisi (Time-Series Chart)
# -----------------
with open("components/style/visualize-4.html", "r", encoding="utf-8") as f:
    st.markdown(f.read(), unsafe_allow_html=True)

# Group monthly unique customers by type
df_monthly_cust = df_filtered.groupby(['Chronological_Sort', 'Bulan_Tahun', 'Clean_Penyewa'])['Customer_Type'].first().reset_index()
df_retention = df_monthly_cust.groupby(['Chronological_Sort', 'Bulan_Tahun', 'Customer_Type']).size().unstack(fill_value=0).reset_index().sort_values('Chronological_Sort')

# Make sure New and Returning columns exist even if one is empty in filtered view
if 'New' not in df_retention.columns:
    df_retention['New'] = 0
if 'Returning' not in df_retention.columns:
    df_retention['Returning'] = 0

# Create Line/Area Chart using Plotly go
fig_ret = go.Figure()
fig_ret.add_trace(go.Scatter(
    x=df_retention['Bulan_Tahun'],
    y=df_retention['New'],
    name="Pelanggan Baru (New Customers)",
    mode="lines+markers+text",
    marker=dict(size=8, color="#EA3A3A"),
    line=dict(width=3, color="#EA3A3A"),
    text=df_retention['New'],
    textposition="top center",
    hovertemplate="Bulan: %{x}<br>Pelanggan Baru: %{y} orang<extra></extra>"
))
fig_ret.add_trace(go.Scatter(
    x=df_retention['Bulan_Tahun'],
    y=df_retention['Returning'],
    name="Pelanggan Lama (Returning Customers)",
    mode="lines+markers+text",
    marker=dict(size=8, color="#4B5563"),
    line=dict(width=3, color="#4B5563"),
    text=df_retention['Returning'],
    textposition="top center",
    hovertemplate="Bulan: %{x}<br>Pelanggan Lama: %{y} orang<extra></extra>"
))

fig_ret.update_layout(
    title=dict(text="<b>Tren Perbandingan Pelanggan Baru vs Pelanggan Lama per Bulan</b>", font=dict(size=15, color="#111827")),
    font=dict(family="Outfit, sans-serif", color="#4B5563"),
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="rgba(0,0,0,0.08)", font=dict(family="Outfit, sans-serif", size=13, color="#111827")),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color="#4B5563")),
    margin=dict(l=40, r=40, t=50, b=50),
    xaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#4B5563")),
    yaxis=dict(gridcolor="rgba(0,0,0,0.06)", tickfont=dict(color="#4B5563"), title="Jumlah Pelanggan Unik")
)

# Display chart and context
st.plotly_chart(fig_ret, use_container_width=True)

# Brief CRM Context Card
# Calculate current ratio of returning vs total
total_new = df_retention['New'].sum()
total_ret = df_retention['Returning'].sum()
ret_ratio = (total_ret / (total_new + total_ret) * 100) if (total_new + total_ret) > 0 else 0
    
with open("components/CRM-context-card.html", "r", encoding="utf-8") as f:
    st.markdown(
        f.read().format(
            total_new=int(total_new),
            total_ret=int(total_ret),
            ret_ratio=ret_ratio
        ),
        unsafe_allow_html=True
    )

# ==========================================
# 6. CRM ACTIONABLE INSIGHTS PANEL
# ==========================================
with open("components/style/visualize-6.html", "r", encoding="utf-8") as f:
    st.markdown(f.read(), unsafe_allow_html=True)

# Generate Dynamic Insights
top_unit_rev = df_unit.sort_values(by='Total_Revenue', ascending=False).iloc[0]['Clean_Unit'] if not df_unit.empty else "N/A"
top_unit_util = df_unit.sort_values(by='Total_Days', ascending=False).iloc[0]['Clean_Unit'] if not df_unit.empty else "N/A"
top_client_name = df_renter.iloc[0]['Clean_Penyewa'] if not df_renter.empty else "N/A"
top_client_spend = df_renter.iloc[0]['Total_Belanja'] if not df_renter.empty else 0.0

col_ins1, col_ins2, col_ins3 = st.columns(3)

with col_ins1:
    with open("components/insight-1.html", "r", encoding="utf-8") as f:
        st.markdown(
            f.read().format(
                top_unit_rev=top_unit_rev,
                top_unit_util=top_unit_util
            ),
            unsafe_allow_html=True
        )

with col_ins2:
    with open("components/insight-2.html", "r", encoding="utf-8") as f:
        st.markdown(
            f.read().format(
                top_client_name=top_client_name,
                top_client_spend_fmt=format_rupiah(top_client_spend)
            ),
            unsafe_allow_html=True
        )

with col_ins3:
    with open("components/insight-3.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)  # static card

# ==========================================
# 7. RAW DATA EXPLORER & EXPORT
# ==========================================
with st.expander("Lihat / Ekspor Data Transaksi Bersih"):
    with open("components/style/visualize-7.html", "r", encoding="utf-8") as f:
        st.markdown(f.read(), unsafe_allow_html=True)
    st.dataframe(
        df_filtered[[
            'Clean_Unit', 'Bulan_Tahun', 'No.Pol', 'Clean_Penyewa', 'Clean_Status', 
            'Tujuan', 'Durasi (Day)', 'Clean_Total', 'Clean_Harga', 'Clean_Fee_Driver', 'Clean_BBM', 'Clean_Tol_Parkir'
        ]].rename(columns={
            'Clean_Unit': 'Unit',
            'Bulan_Tahun': 'Bulan-Tahun',
            'Clean_Penyewa': 'Penyewa',
            'Clean_Status': 'Status',
            'Clean_Total': 'Total Bersih (IDR)',
            'Clean_Harga': 'Harga Unit (IDR)',
            'Clean_Fee_Driver': 'Fee Driver (IDR)',
            'Clean_BBM': 'BBM (IDR)',
            'Clean_Tol_Parkir': 'Tol & Parkir (IDR)'
        }),
        use_container_width=True
    )
    
    # CSV download trigger
    csv_data = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Unduh Data Terfilter (.csv)",
        data=csv_data,
        file_name="filtered_mhp_crm_data.csv",
        mime="text/csv",
        help="Unduh data terfilter di atas dalam format CSV"
    )
