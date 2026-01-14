import streamlit as st
import pandas as pd
import plotly.express as px
import json

# ==================== 页面配置 ====================
st.set_page_config(page_title="中国马拉松跑鞋品牌分析 2021-2025", layout="wide")
st.title("🇨🇳 中国马拉松跑鞋品牌市场份额分析（2021-2025）")
st.markdown("""
**数据来源：悦跑圈等平台统计**（涵盖厦门、上海、北京、无锡、广州马拉松）  
队列说明：**破3选手**（净成绩<3小时精英跑者） vs **全局跑者**（全体完赛者）  
""")

# ==================== 加载数据 ====================
@st.cache_data
def load_data():
    with open('marathon_shoe_data.json', 'r', encoding='utf-8') as f:
        raw = json.load(f)
    df = pd.DataFrame(raw['records'])
    brands = raw['brands']
    df['brand_en'] = df['brand'].map(lambda x: brands.get(x, {}).get('name_en', x))
    df['type_zh'] = df['brand_type'].map({'domestic': '国内', 'international': '国际', 'other': '其他'})
    return df, brands

df, brands = load_data()

# ==================== 侧边栏过滤器 ====================
st.sidebar.header("筛选条件")
events = st.sidebar.multiselect("赛事", options=sorted(df['event'].unique()), default=sorted(df['event'].unique()))
years = st.sidebar.slider("年份", min_value=2021, max_value=2025, value=(2021, 2025))
cohort = st.sidebar.radio("跑者队列", options=['全局跑者', '破3选手'], index=0)
aggregate_events = st.sidebar.checkbox("聚合所有选中赛事（取平均）", value=True)

# 数据过滤
mask = (
    df['event'].isin(events) &
    df['year'].between(years[0], years[1]) &
    (df['cohort'] == cohort)
)
data = df[mask].copy()

# ==================== Tab 分页 ====================
tab1, tab2, tab3, tab4 = st.tabs(["排行榜", "品牌趋势对比", "乔丹专区", "国内 vs 国际"])

with tab1:
    st.subheader(f"{cohort} · Top 20 品牌排行（最新年份 {years[1]}）")
    latest_year = data[data['year'] == years[1]]
    if aggregate_events:
        latest_year = latest_year.groupby(['brand', 'type_zh'])['share'].mean().reset_index()
    else:
        latest_year = latest_year.groupby(['event', 'brand', 'type_zh'])['share'].mean().reset_index()
    
    latest_year = latest_year.sort_values('share', ascending=False).head(20).copy()
    latest_year['排名'] = range(1, len(latest_year) + 1)
    latest_year['份额%'] = (latest_year['share'] * 100).round(1)
    display_df = latest_year[['排名', 'brand', 'type_zh', '份额%']]
    display_df.columns = ['排名', '品牌', '类型', '份额%']
    st.dataframe(display_df, use_container_width=True)

with tab2:
    st.subheader("品牌份额趋势对比")
    
    if aggregate_events:
        trend = data.groupby(['year', 'brand', 'brand_en', 'type_zh'])['share'].mean().reset_index()
    else:
        trend = data.groupby(['year', 'event', 'brand', 'brand_en', 'type_zh'])['share'].mean().reset_index()
    
    top10_brands = data.groupby('brand')['share'].mean().sort_values(ascending=False).head(10).index.tolist()
    default_brands = ['乔丹'] + [b for b in top10_brands if b != '乔丹']
    
    selected_brands = st.multiselect("选择要对比的品牌（可多选）", 
                                     options=sorted(data['brand'].unique()), 
                                     default=default_brands[:8])
    
    if selected_brands:
        plot_data = trend[trend['brand'].isin(selected_brands)]
        fig = px.line(plot_data, x='year', y='share', color='brand',
                      labels={'share': '市场份额', 'year': '年份'},
                      title="选中品牌份额变化趋势",
                      hover_data={'share': ':.1%'})
        fig.update_yaxes(tickformat='.1%')
        fig.update_xaxes(tickmode='array', tickvals=sorted(plot_data['year'].unique()))
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("### 📊 自动分析总结")
        summary_lines = []
        for brand in selected_brands:
            brand_data = plot_data[plot_data['brand'] == brand]
            if len(brand_data) >= 2:
                start = brand_data.iloc[0]['share']
                end = brand_data.iloc[-1]['share']
                change = end - start
                pct_change = (change / start * 100) if start > 0 else 0
                direction = "上升" if change > 0 else "下降"
                summary_lines.append(
                    f"- **{brand}**：份额从 {start:.1%} → {end:.1%}（{'+' if change > 0 else ''}{pct_change:.1f}%），整体{direction}。"
                )
        st.write("\n".join(summary_lines))
        if '乔丹' in selected_brands:
            st.info("乔丹在全局跑者中保持较稳定大众化地位，但在破3精英选手中的渗透率持续下滑，说明其在高端竞技领域的竞争力减弱。")

with tab3:
    st.subheader("乔丹跑鞋江湖地位分析")
    
    if aggregate_events:
        trend = data.groupby(['year', 'brand', 'type_zh'])['share'].mean().reset_index()
    else:
        trend = data.groupby(['year', 'event', 'brand', 'type_zh'])['share'].mean().reset_index()
    
    # 计算乔丹每年排名
    rank_data = trend.groupby('year').apply(
        lambda x: x.assign(rank=x['share'].rank(ascending=False, method='min'))
    ).reset_index(drop=True)
    qiaodan_trend = trend[trend['brand'] == '乔丹'].copy()
    qiaodan_rank = rank_data[rank_data['brand'] == '乔丹'][['year', 'rank']].copy()
    qiaodan_rank['rank'] = qiaodan_rank['rank'].astype(int)
    
    view_mode = st.radio("查看模式", options=['份额趋势', '排名趋势'], index=0, horizontal=True)
    
    if view_mode == '份额趋势':
        if not qiaodan_trend.empty:
            fig = px.line(qiaodan_trend, x='year', y='share', color='brand',
                          title="乔丹份额变化趋势",
                          labels={'share': '市场份额'})
            fig.update_yaxes(tickformat='.1%')
            fig.update_xaxes(tickmode='array', tickvals=sorted(qiaodan_trend['year'].unique()))
            st.plotly_chart(fig, use_container_width=True)
            
            start_share = qiaodan_trend.iloc[0]['share']
            end_share = qiaodan_trend.iloc[-1]['share']
            st.markdown(f"""
            **总结**：  
            乔丹份额从 {start_share:.1%} 下降到 {end_share:.1%}。  
            在全局跑者中仍保持大众化地位，但在破3选手队列中渗透率持续下滑。
            """)
    
    else:  # 排名趋势
        if not qiaodan_rank.empty:
            fig = px.line(qiaodan_rank, x='year', y='rank',
                          title="乔丹排名变化趋势（数字越小越好）",
                          labels={'rank': '排名'})
            fig.update_layout(yaxis_autorange="reversed")  # 排名倒置，1在最上面
            fig.update_xaxes(tickmode='array', tickvals=sorted(qiaodan_rank['year'].unique()))
            st.plotly_chart(fig, use_container_width=True)
            
            start_rank = qiaodan_rank.iloc[0]['rank']
            end_rank = qiaodan_rank.iloc[-1]['rank']
            st.markdown(f"""
            **总结**：  
            乔丹排名从第 {start_rank} 位下降到第 {end_rank} 位（数字越大代表排名越靠后）。  
            尤其在破3精英选手群体中，排名下滑明显，表明其在高端竞技领域的地位正在被其他国产品牌逐步蚕食。
            """)

with tab4:
    st.subheader("国内品牌 vs 国际品牌势力对比")
    if aggregate_events:
        trend = data.groupby(['year', 'brand', 'brand_en', 'type_zh'])['share'].mean().reset_index()
    domestic_international = trend.copy()
    domestic_international['group'] = domestic_international['type_zh'].map({'国内': '国内品牌总和', '国际': '国际品牌总和', '其他': '其他'})
    di_year = domestic_international.groupby(['year', 'group'])['share'].sum().reset_index()
    
    fig = px.area(di_year, x='year', y='share', color='group',
                  title="国内 vs 国际品牌总份额变化（100%堆叠）",
                  labels={'share': '总份额'})
    fig.update_yaxes(tickformat='.1%')
    fig.update_xaxes(tickmode='array', tickvals=sorted(di_year['year'].unique()))
    st.plotly_chart(fig, use_container_width=True)
    
    latest_di = di_year[di_year['year'] == years[1]]
    domestic_latest = latest_di[latest_di['group'] == '国内品牌总和']['share'].values[0] if len(latest_di) > 0 else 0
    st.markdown(f"""
    **2025年最新格局**：国内品牌总份额约 {domestic_latest:.1%}，国际品牌约 {(1-domestic_latest):.1%}。  
    过去5年，国内品牌实现了显著崛起，尤其在破3精英选手群体中占据绝对主导地位。
    """)
