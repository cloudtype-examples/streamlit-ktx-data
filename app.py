import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

@st.cache_data
def load_data():
    try:
        df = pd.read_csv('ktx.csv', encoding='euc-kr')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv('ktx.csv', encoding='cp949')
        except UnicodeDecodeError:
            st.error("파일 인코딩을 확인할 수 없습니다. 파일이 'euc-kr' 또는 'cp949' 인코딩인지 확인해주세요.")
            return pd.DataFrame()
    except FileNotFoundError:
        st.error("ktx.csv 파일을 찾을 수 없습니다. 파일이 올바른 위치에 있는지 확인해주세요.")
        return pd.DataFrame()
    
    df['운행년월'] = pd.to_datetime(df['운행년월'])
    return df

def main():
    st.title('KTX 승하차 인원 데이터 시각화')

    df = load_data()

    if df.empty:
        st.stop()

    all_stations = sorted(df['정차역'].unique())
    default_stations = ['서울', '부산', '동대구', '대전', '광주송정']
    default_stations = [station for station in default_stations if station in all_stations]

    if len(default_stations) < 5:
        st.warning(f"데이터에서 다음 역을 찾을 수 없습니다: {set(['서울', '부산', '동대구', '대전', '광주송정']) - set(default_stations)}")

    selected_stations = st.sidebar.multiselect('정차역 선택', all_stations, default=default_stations)

    min_date = df['운행년월'].min().date()
    max_date = df['운행년월'].max().date()
    
    default_start_date = max(min_date, max_date - timedelta(days=365))
    default_end_date = max_date

    start_date = st.sidebar.date_input('시작 날짜', default_start_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input('종료 날짜', default_end_date, min_value=start_date, max_value=max_date)

    if start_date > end_date:
        st.error('시작 날짜가 종료 날짜보다 늦습니다. 다시 선택해주세요.')
        st.stop()

    filtered_df = df[(df['정차역'].isin(selected_stations)) & 
                     (df['운행년월'].dt.date >= start_date) & 
                     (df['운행년월'].dt.date <= end_date)].copy()

    if filtered_df.empty:
        st.warning('선택한 조건에 해당하는 데이터가 없습니다. 다른 조건을 선택해주세요.')
        st.stop()

    st.header('1. 시간에 따른 승하차 인원 변화')
    fig_time = go.Figure()

    for station in selected_stations:
        station_data = filtered_df[filtered_df['정차역'] == station]
        
        fig_time.add_trace(go.Scatter(x=station_data['운행년월'], y=station_data['하행_승차인원수'],
                                      mode='lines', name=f'{station} 하행 승차', line=dict(dash='solid')))
        fig_time.add_trace(go.Scatter(x=station_data['운행년월'], y=station_data['하행_하차인원수'],
                                      mode='lines', name=f'{station} 하행 하차', line=dict(dash='solid')))
        
        fig_time.add_trace(go.Scatter(x=station_data['운행년월'], y=station_data['상행_승차인원수'],
                                      mode='lines', name=f'{station} 상행 승차', line=dict(dash='dash')))
        fig_time.add_trace(go.Scatter(x=station_data['운행년월'], y=station_data['상행_하차인원수'],
                                      mode='lines', name=f'{station} 상행 하차', line=dict(dash='dash')))

    fig_time.update_layout(title='선택된 역의 시간에 따른 승하차 인원 변화',
                           xaxis_title='날짜',
                           yaxis_title='인원 수')
    st.plotly_chart(fig_time)

    st.header('2. 역별 평균 승하차 인원 비교')
    avg_data = filtered_df.groupby('정차역')[['하행_승차인원수', '하행_하차인원수', '상행_승차인원수', '상행_하차인원수']].mean().reset_index()
    fig_bar = px.bar(avg_data, x='정차역', 
                     y=['하행_승차인원수', '하행_하차인원수', '상행_승차인원수', '상행_하차인원수'], 
                     barmode='group',
                     title='역별 평균 승하차 인원')
    st.plotly_chart(fig_bar)

    st.header('3. 역별 총 승차 인원 비율')
    total_data = filtered_df.groupby('정차역')[['하행_승차인원수', '상행_승차인원수']].sum().reset_index()
    total_data['총_승차인원수'] = total_data['하행_승차인원수'] + total_data['상행_승차인원수']
    fig_pie = px.pie(total_data, values='총_승차인원수', names='정차역', 
                     title='역별 총 승차 인원 비율')
    st.plotly_chart(fig_pie)

    st.header('4. 월별 승차 인원 히트맵')
    heatmap_data = filtered_df.copy()
    heatmap_data['월'] = heatmap_data['운행년월'].dt.strftime('%Y-%m')
    heatmap_data['총_승차인원수'] = heatmap_data['하행_승차인원수'] + heatmap_data['상행_승차인원수']
    heatmap_data = heatmap_data.groupby(['월', '정차역'])['총_승차인원수'].mean().unstack()
    fig_heatmap = px.imshow(heatmap_data, title='월별 평균 승차 인원 히트맵',
                            labels=dict(x="정차역", y="월", color="평균 승차 인원"))
    st.plotly_chart(fig_heatmap)

    st.header('5. 하행 vs 상행 승차 인원 산점도')
    fig_scatter = px.scatter(filtered_df, x='하행_승차인원수', y='상행_승차인원수', color='정차역',
                             title='하행 vs 상행 승차 인원', trendline="ols")
    st.plotly_chart(fig_scatter)

    st.header('6. 데이터 테이블')
    st.dataframe(filtered_df)

    st.header('7. 추가 통계 정보')
    
    st.subheader('역별 총 승하차 인원')
    total_passengers = filtered_df.groupby('정차역')[['하행_승차인원수', '하행_하차인원수', '상행_승차인원수', '상행_하차인원수']].sum().reset_index()
    total_passengers = total_passengers.round(0).astype({col: int for col in total_passengers.columns if col != '정차역'})
    total_passengers = total_passengers.reset_index(drop=True)
    st.dataframe(total_passengers.style.format({col: '{:,}' for col in total_passengers.columns if col != '정차역'}))

    st.subheader('월평균 승하차 인원')
    monthly_avg = filtered_df.groupby('정차역')[['하행_승차인원수', '하행_하차인원수', '상행_승차인원수', '상행_하차인원수']].mean().reset_index()
    monthly_avg = monthly_avg.round(0).astype({col: int for col in monthly_avg.columns if col != '정차역'})
    monthly_avg = monthly_avg.reset_index(drop=True)
    st.dataframe(monthly_avg.style.format({col: '{:,}' for col in monthly_avg.columns if col != '정차역'}))

    st.header('8. 승하차 인원 차이 분석')
    filtered_df['하행_승하차차이'] = filtered_df['하행_승차인원수'] - filtered_df['하행_하차인원수']
    filtered_df['상행_승하차차이'] = filtered_df['상행_승차인원수'] - filtered_df['상행_하차인원수']
    fig_diff = px.box(filtered_df.melt(id_vars=['정차역'], value_vars=['하행_승하차차이', '상행_승하차차이'], 
                                        var_name='방향', value_name='승하차차이'),
                      x='정차역', y='승하차차이', color='방향',
                      title='역별 승하차 인원 차이 분포')
    st.plotly_chart(fig_diff)

    st.header('9. 상위 5개 역 분석')
    top_5_stations = filtered_df.groupby('정차역')['하행_승차인원수'].sum().nlargest(5).index
    top_5_data = filtered_df[filtered_df['정차역'].isin(top_5_stations)]
    fig_top5 = px.line(top_5_data, x='운행년월', y=['하행_승차인원수', '상행_승차인원수'], color='정차역',
                       title='상위 5개 역의 승차 인원 추이')
    st.plotly_chart(fig_top5)

if __name__ == "__main__":
    main()