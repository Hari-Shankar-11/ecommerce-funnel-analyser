# app.py — eCommerce Funnel Drop-off Analyser
# run with: streamlit run app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb
import glob

# ── page config ──────────────────────────────────────────────
st.set_page_config(
    page_title = "Funnel Analyser",
    page_icon  = "🛒",
    layout     = "wide"
)

# ── load data (cached so it only loads once) ─────────────────
@st.cache_data
def load_data():
    # your exact path from your notebook
    files = glob.glob(r"C:\Users\Galbo\OneDrive\문서\data\*.csv")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)

    df = df[df['event_type'].isin(['view','cart','purchase'])].copy()
    df['event_time'] = pd.to_datetime(df['event_time'], utc=True)
    df = df.dropna(subset=['user_id','user_session'])
    df = df.drop_duplicates(subset=['user_session','event_type'])

    df['date']     = df['event_time'].dt.date
    df['hour']     = df['event_time'].dt.hour
    df['month']    = df['event_time'].dt.to_period('M').astype(str)
    df['dow']      = df['event_time'].dt.day_name()
    df['price']    = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['category'] = df['category_code'].fillna('unknown').str.split('.').str[0]
    return df

# show loading spinner while data loads
with st.spinner("Loading data... please wait (may take 2-3 minutes first time)"):
    df = load_data()

# ── sidebar filters ───────────────────────────────────────────
st.sidebar.title("🔧 Filters")

date_range = st.sidebar.date_input(
    "Date Range",
    value=[df['date'].min(), df['date'].max()],
    min_value=df['date'].min(),
    max_value=df['date'].max()
)

all_cats = sorted(df['category'].dropna().unique())
cats = st.sidebar.multiselect("Category", all_cats, default=all_cats)

all_brands = sorted(df['brand'].dropna().unique())
brands = st.sidebar.multiselect("Brand", all_brands, default=all_brands)

# apply filters
fdf = df.copy()
if len(date_range) == 2:
    fdf = fdf[(fdf['date'] >= date_range[0]) & (fdf['date'] <= date_range[1])]
if cats:
    fdf = fdf[fdf['category'].isin(cats)]
if brands:
    fdf = fdf[fdf['brand'].isin(brands)]

# ── header ────────────────────────────────────────────────────
st.title("🛒 eCommerce Funnel Drop-off Analyser")
st.caption(f"REES46 Cosmetics Shop  |  {len(fdf):,} events  |  {fdf['user_id'].nunique():,} users  |  {fdf['date'].min()} to {fdf['date'].max()}")
st.markdown("---")

# ── core funnel query ─────────────────────────────────────────
funnel = duckdb.query("""
    WITH
    v AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='view'),
    c AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='cart'),
    p AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='purchase')
    SELECT
        COUNT(DISTINCT v.user_session) AS viewed,
        COUNT(DISTINCT c.user_session) AS carted,
        COUNT(DISTINCT p.user_session) AS purchased
    FROM v
    LEFT JOIN c ON v.user_session = c.user_session
    LEFT JOIN p ON v.user_session = p.user_session
""").df().iloc[0]

v2c = round(100 * funnel.carted    / funnel.viewed,  1)
c2p = round(100 * funnel.purchased / funnel.carted,  1)
cvr = round(100 * funnel.purchased / funnel.viewed,  1)
dropped_cart     = int(funnel.viewed  - funnel.carted)
dropped_checkout = int(funnel.carted  - funnel.purchased)

# ── KPI cards ─────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Sessions",  f"{int(funnel.viewed):,}")
k2.metric("View → Cart",     f"{v2c}%",  delta=f"-{round(100-v2c,1)}% dropped", delta_color="inverse")
k3.metric("Cart → Purchase", f"{c2p}%",  delta=f"-{round(100-c2p,1)}% dropped", delta_color="inverse")
k4.metric("Overall CVR",     f"{cvr}%")
k5.metric("Lost at Cart",    f"{dropped_cart:,}")

st.markdown("---")

# ── auto insight ──────────────────────────────────────────────
if dropped_cart > dropped_checkout:
    st.error(f"🔴 Biggest drop-off: View → Cart — {round(100-v2c,1)}% of viewers leave without adding to cart. Fix: better product pages, add reviews, clearer buy button.")
else:
    st.error(f"🔴 Biggest drop-off: Cart → Purchase — {round(100-c2p,1)}% of carters never complete checkout. Fix: simplify checkout, guest login, show shipping cost upfront.")

# ── tabs ──────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Funnel Overview",
    "🏷️ Category & Brand",
    "📈 Trends",
    "💰 Revenue",
    "🔍 Deep Dive"
])

# ════════════════════════════════════════════════════════
# TAB 1 — FUNNEL OVERVIEW
# ════════════════════════════════════════════════════════
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Purchase Funnel")
        fig = go.Figure(go.Funnel(
            y = ['Viewed', 'Added to Cart', 'Purchased'],
            x = [int(funnel.viewed), int(funnel.carted), int(funnel.purchased)],
            textinfo = "value+percent previous",
            marker   = dict(color=['#4F46E5','#7C3AED','#A855F7'])
        ))
        fig.update_layout(height=350, margin=dict(l=150,r=30,t=30,b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Drop-off Waterfall")
        fig = go.Figure(go.Waterfall(
            orientation = 'v',
            measure = ['absolute','relative','relative','total'],
            x = ['Started','Lost at Cart','Lost at Checkout','Purchased'],
            y = [int(funnel.viewed), -dropped_cart, -dropped_checkout, 0],
            text = [f"{int(funnel.viewed):,}", f"-{dropped_cart:,}",
                    f"-{dropped_checkout:,}", f"{int(funnel.purchased):,}"],
            textposition = 'outside',
            increasing = dict(marker=dict(color='#10B981')),
            decreasing = dict(marker=dict(color='#EF4444')),
            totals     = dict(marker=dict(color='#6366F1'))
        ))
        fig.update_layout(height=350, showlegend=False, margin=dict(t=30,b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Event Type Distribution")
    event_counts = fdf['event_type'].value_counts().reset_index()
    event_counts.columns = ['event_type','count']
    fig = px.pie(event_counts, values='count', names='event_type',
                 color_discrete_sequence=['#4F46E5','#F59E0B','#10B981'], hole=0.4)
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════
# TAB 2 — CATEGORY & BRAND
# ════════════════════════════════════════════════════════
with tab2:

    cat_df = duckdb.query("""
        WITH p AS (
            SELECT user_session,
                   MAX(category) AS category,
                   MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                   MAX(CASE WHEN event_type='cart'     THEN 1 ELSE 0 END) AS carted,
                   MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
            FROM fdf GROUP BY user_session
        )
        SELECT category,
               SUM(viewed) AS sessions, SUM(carted) AS carted, SUM(purchased) AS purchased,
               ROUND(100.0*SUM(carted)    /NULLIF(SUM(viewed),0),1) AS v2c_pct,
               ROUND(100.0*SUM(purchased) /NULLIF(SUM(carted),0), 1) AS c2p_pct,
               ROUND(100.0*SUM(purchased) /NULLIF(SUM(viewed),0),1) AS cvr_pct
        FROM p WHERE category != 'unknown'
        GROUP BY category HAVING SUM(viewed)>=100
        ORDER BY sessions DESC
    """).df()

    st.subheader("Funnel by Category")
    fig = go.Figure()
    fig.add_trace(go.Bar(name='View→Cart %',     x=cat_df['category'], y=cat_df['v2c_pct'], marker_color='#6366F1'))
    fig.add_trace(go.Bar(name='Cart→Purchase %', x=cat_df['category'], y=cat_df['c2p_pct'], marker_color='#F59E0B'))
    fig.update_layout(barmode='group', height=400, xaxis_tickangle=-30,
                      legend=dict(orientation='h', y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    best  = cat_df.loc[cat_df['cvr_pct'].idxmax()]
    worst = cat_df.loc[cat_df['cvr_pct'].idxmin()]
    c1, c2 = st.columns(2)
    c1.success(f"✅ Best category: **{best['category']}** at {best['cvr_pct']}% CVR")
    c2.error(f"⚠️ Worst category: **{worst['category']}** at {worst['cvr_pct']}% CVR")

    st.markdown("---")

    brand_df = duckdb.query("""
        WITH p AS (
            SELECT user_session, MAX(brand) AS brand,
                   MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                   MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
            FROM fdf WHERE brand IS NOT NULL GROUP BY user_session
        )
        SELECT brand, SUM(viewed) AS sessions, SUM(purchased) AS purchased,
               ROUND(100.0*SUM(purchased)/NULLIF(SUM(viewed),0),1) AS cvr_pct
        FROM p GROUP BY brand HAVING SUM(viewed)>=300
        ORDER BY sessions DESC LIMIT 15
    """).df()

    st.subheader("CVR % by Brand (Top 15)")
    fig = px.bar(brand_df.sort_values('cvr_pct', ascending=True),
                 x='cvr_pct', y='brand', orientation='h',
                 color='cvr_pct', color_continuous_scale='Purples', text='cvr_pct')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.update_layout(height=500, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    best_b  = brand_df.loc[brand_df['cvr_pct'].idxmax()]
    worst_b = brand_df.loc[brand_df['cvr_pct'].idxmin()]
    b1, b2 = st.columns(2)
    b1.success(f"✅ Best brand: **{best_b['brand']}** at {best_b['cvr_pct']}% CVR")
    b2.error(f"⚠️ Worst brand: **{worst_b['brand']}** at {worst_b['cvr_pct']}% CVR")

# # ════════════════════════════════════════════════════════
# TAB 3 — TRENDS
# ════════════════════════════════════════════════════════
with tab3:

    monthly = duckdb.query("""
        WITH p AS (
            SELECT STRFTIME(ANY_VALUE(event_time),'%Y-%m') AS month,
                   user_session,
                   MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                   MAX(CASE WHEN event_type='cart'     THEN 1 ELSE 0 END) AS carted,
                   MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
            FROM fdf GROUP BY user_session
        )
        SELECT month, SUM(viewed) AS sessions,
               ROUND(100.0*SUM(carted)    /NULLIF(SUM(viewed),0),1) AS v2c_pct,
               ROUND(100.0*SUM(purchased) /NULLIF(SUM(carted),0), 1) AS c2p_pct,
               ROUND(100.0*SUM(purchased) /NULLIF(SUM(viewed),0),1) AS cvr_pct
        FROM p GROUP BY month ORDER BY month
    """).df()

    st.subheader("Monthly Conversion Rate Trend")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['v2c_pct'],
                  name='View→Cart %', mode='lines+markers',
                  line=dict(color='#6366F1', width=2.5), marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['c2p_pct'],
                  name='Cart→Purchase %', mode='lines+markers',
                  line=dict(color='#F59E0B', width=2.5), marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['cvr_pct'],
                  name='Overall CVR %', mode='lines+markers',
                  line=dict(color='#10B981', width=2.5, dash='dash'), marker=dict(size=8)))
    fig.update_layout(height=380, legend=dict(orientation='h', y=1.1))
    st.plotly_chart(fig, use_container_width=True)

    first = monthly.iloc[0]['cvr_pct']
    last  = monthly.iloc[-1]['cvr_pct']
    chg   = round(last - first, 1)
    if chg > 0:
        st.success(f"📈 CVR improved from {first}% → {last}%  (+{chg}pp over the period)")
    elif chg < 0:
        st.error(f"📉 CVR declined from {first}% → {last}%  ({chg}pp over the period)")
    else:
        st.info(f"➡️ CVR stayed flat at {first}%")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        hourly = duckdb.query("""
            WITH p AS (
                SELECT EXTRACT(HOUR FROM ANY_VALUE(event_time)) AS hour,
                       user_session,
                       MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                       MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
                FROM fdf GROUP BY hour, user_session
            )
            SELECT hour,
                   ROUND(100.0*SUM(purchased)/NULLIF(SUM(viewed),0),2) AS cvr_pct
            FROM p GROUP BY hour ORDER BY hour
        """).df()

        st.subheader("CVR % by Hour of Day")
        fig = px.bar(hourly, x='hour', y='cvr_pct',
                     color='cvr_pct', color_continuous_scale='Purples',
                     text=hourly['cvr_pct'].map(lambda x: f'{x}%'))
        fig.update_traces(textposition='outside')
        fig.update_layout(height=370, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
        peak = int(hourly.loc[hourly['cvr_pct'].idxmax(), 'hour'])
        st.info(f"⏰ Peak hour: **{peak:02d}:00** — schedule campaigns here")

    with col2:
        dow_order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
        dow = duckdb.query("""
            WITH p AS (
                SELECT DAYNAME(ANY_VALUE(event_time)) AS dow,
                       user_session,
                       MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                       MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
                FROM fdf GROUP BY user_session
            )
            SELECT dow,
                   ROUND(100.0*SUM(purchased)/NULLIF(SUM(viewed),0),2) AS cvr_pct
            FROM p GROUP BY dow
        """).df()
        dow['dow'] = pd.Categorical(dow['dow'], categories=dow_order, ordered=True)
        dow = dow.sort_values('dow')

        st.subheader("CVR % by Day of Week")
        fig = px.bar(dow, x='dow', y='cvr_pct',
                     color='cvr_pct', color_continuous_scale='Blues',
                     text=dow['cvr_pct'].map(lambda x: f'{x}%'))
        fig.update_traces(textposition='outside')
        fig.update_layout(height=370, coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)
        best_day = dow.loc[dow['cvr_pct'].idxmax(), 'dow']
        st.info(f"📅 Best day: **{best_day}** — highest purchase intent")

# ════════════════════════════════════════════════════════
# TAB 4 — REVENUE
# ════════════════════════════════════════════════════════
with tab4:

    rev = duckdb.query("""
        WITH
        carted    AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='cart'),
        purchased AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='purchase'),
        abandoned AS (
            SELECT fdf.user_session, fdf.price, fdf.category
            FROM fdf JOIN carted c ON fdf.user_session=c.user_session
            WHERE fdf.event_type='cart'
              AND fdf.user_session NOT IN (SELECT user_session FROM purchased)
        )
        SELECT COUNT(DISTINCT user_session) AS abandoned_carts,
               ROUND(SUM(price),2)         AS total_lost,
               ROUND(SUM(price)*0.10,2)    AS recovery_10pct,
               ROUND(AVG(price),2)         AS avg_cart_value
        FROM abandoned
    """).df().iloc[0]

    purchase_value = duckdb.query(
        "SELECT ROUND(SUM(price),2) AS val FROM fdf WHERE event_type='purchase'"
    ).df().iloc[0]['val']

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Abandoned Carts",     f"{int(rev.abandoned_carts):,}")
    r2.metric("Revenue Lost",        f"${float(rev.total_lost):,.0f}")
    r3.metric("Avg Abandoned Value", f"${float(rev.avg_cart_value):,.2f}")
    r4.metric("10% Recovery =",      f"${float(rev.recovery_10pct):,.0f}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Revenue: Captured vs Lost")
        fig = go.Figure(go.Pie(
            labels   = ['Revenue Captured','Revenue Lost (Abandoned)'],
            values   = [float(purchase_value), float(rev.total_lost)],
            hole     = 0.45,
            marker   = dict(colors=['#10B981','#EF4444']),
            textinfo = 'label+percent'
        ))
        fig.update_layout(height=360, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Abandoned Revenue by Category")
        cat_rev = duckdb.query("""
            WITH
            carted    AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='cart'),
            purchased AS (SELECT DISTINCT user_session FROM fdf WHERE event_type='purchase'),
            abandoned AS (
                SELECT fdf.category, fdf.price
                FROM fdf JOIN carted c ON fdf.user_session=c.user_session
                WHERE fdf.event_type='cart'
                  AND fdf.user_session NOT IN (SELECT user_session FROM purchased)
            )
            SELECT category, ROUND(SUM(price),2) AS revenue_lost
            FROM abandoned WHERE category != 'unknown'
            GROUP BY category ORDER BY revenue_lost DESC
        """).df()

        fig = px.bar(cat_rev, x='category', y='revenue_lost',
                     color='revenue_lost', color_continuous_scale='Reds',
                     text=cat_rev['revenue_lost'].map(lambda x: f'${x:,.0f}'))
        fig.update_traces(textposition='outside')
        fig.update_layout(height=360, coloraxis_showscale=False, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    top_cat = cat_rev.iloc[0]
    st.warning(f"💡 **'{top_cat['category']}'** has the most abandoned revenue at **${float(top_cat['revenue_lost']):,.0f}**. Target this category first with cart recovery emails.")

# ════════════════════════════════════════════════════════
# TAB 5 — DEEP DIVE
# ════════════════════════════════════════════════════════
with tab5:

    st.subheader("Do Higher-Price Products Convert Less?")
    price_df = duckdb.query("""
        WITH p AS (
            SELECT user_session, MAX(price) AS price,
                   MAX(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS viewed,
                   MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchased
            FROM fdf GROUP BY user_session
        )
        SELECT
            CASE WHEN price=0   THEN '1. Unknown'
                 WHEN price<10  THEN '2. Under $10'
                 WHEN price<30  THEN '3. $10-$30'
                 WHEN price<100 THEN '4. $30-$100'
                 ELSE                '5. Over $100' END AS price_bucket,
            COUNT(*)       AS sessions,
            SUM(purchased) AS purchased,
            ROUND(100.0*SUM(purchased)/NULLIF(COUNT(*),0),1) AS cvr_pct
        FROM p WHERE viewed=1
        GROUP BY price_bucket ORDER BY price_bucket
    """).df()

    fig = px.bar(price_df, x='price_bucket', y='cvr_pct',
                 text='cvr_pct', color='cvr_pct', color_continuous_scale='RdYlGn')
    fig.update_traces(texttemplate='%{text}%', textposition='outside')
    fig.update_layout(height=380, coloraxis_showscale=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("One-Time Buyers vs Repeat Buyers")
    user_df = duckdb.query("""
        SELECT user_id,
               COUNT(DISTINCT user_session) AS sessions,
               SUM(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchases,
               ROUND(SUM(price),2) AS total_spent
        FROM fdf GROUP BY user_id
    """).df()
    user_df['buyer_type'] = user_df['purchases'].apply(
        lambda x: 'Non-buyer' if x==0 else ('One-time' if x==1 else 'Repeat buyer')
    )
    summary = user_df.groupby('buyer_type').agg(
        users       =('user_id','count'),
        avg_sessions=('sessions','mean'),
        avg_spent   =('total_spent','mean')
    ).round(2).reset_index()

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(summary, values='users', names='buyer_type',
                     color_discrete_sequence=['#EF4444','#6366F1','#10B981'], hole=0.4)
        fig.update_layout(height=340)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.dataframe(summary, use_container_width=True, hide_index=True)
        repeat  = summary[summary['buyer_type']=='Repeat buyer']
        onetime = summary[summary['buyer_type']=='One-time']
        if not repeat.empty and not onetime.empty:
            lift = round(float(repeat['avg_spent'].values[0]) / float(onetime['avg_spent'].values[0]), 1)
            st.success(f"💡 Repeat buyers spend **{lift}x more** than one-time buyers")

    st.markdown("---")

    st.subheader("Most Viewed but Least Purchased Products")
    gap_df = duckdb.query("""
        WITH p AS (
            SELECT product_id,
                   SUM(CASE WHEN event_type='view'     THEN 1 ELSE 0 END) AS views,
                   SUM(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS purchases
            FROM fdf GROUP BY product_id
        )
        SELECT product_id, views, purchases,
               ROUND(100.0*purchases/NULLIF(views,0),2) AS cvr_pct
        FROM p WHERE views >= 50
        ORDER BY views DESC LIMIT 20
    """).df()

    fig = px.scatter(gap_df, x='views', y='purchases',
                     color='cvr_pct', size='views',
                     color_continuous_scale='RdYlGn',
                     hover_data=['product_id','cvr_pct'],
                     title='Each dot = one product  |  Color = CVR%  |  Size = views')
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)
    st.warning("💡 Products bottom-right (high views, low purchases) need urgent attention — attracting traffic but failing to convert.")

# ── footer ────────────────────────────────────────────────────
st.markdown("---")
st.caption("Built with Streamlit · DuckDB · Plotly  |  Data: REES46 Cosmetics Shop")