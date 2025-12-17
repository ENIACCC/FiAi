import ReactECharts from 'echarts-for-react';
import { useStore } from '../store/useStore';

export const StockChart = ({ data }: { data: any[] }) => {
  const isDark = useStore(state => state.isDark);
  
  if (!data || data.length === 0) {
    return (
      <div style={{ 
        height: 300, 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        color: isDark ? '#ccc' : '#999',
        fontSize: 14
      }}>
        暂无数据 (Tushare API 未响应)
      </div>
    );
  }

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '今日涨幅榜 Top 10',
      left: 'center',
      textStyle: { color: isDark ? '#fff' : '#333' }
    },
    tooltip: { 
      trigger: 'axis',
      formatter: (params: any) => {
        const item = params[0];
        const dataItem = data[item.dataIndex];
        return `${item.name}<br/>代码: ${dataItem.code}<br/>涨幅: ${item.value}%<br/>现价: ${dataItem.price}`;
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { 
      type: 'category',
      data: data.map(i => i.name),
      axisLabel: { color: isDark ? '#ccc' : '#333', interval: 0, rotate: 30 },
      splitLine: { show: false }
    },
    yAxis: { 
      type: 'value',
      axisLabel: { color: isDark ? '#ccc' : '#333', formatter: '{value}%' },
      splitLine: { lineStyle: { color: isDark ? '#444' : '#eee' } }
    },
    series: [{
      data: data.map(i => i.value),
      type: 'bar',
      itemStyle: { 
        color: (params: any) => {
           return params.value > 0 ? '#cf1322' : '#3f8600';
        },
        borderRadius: [4, 4, 0, 0]
      },
      label: {
        show: true,
        position: 'top',
        valueAnimation: true,
        color: isDark ? '#fff' : '#333',
        formatter: '{c}%'
      }
    }]
  };

  return <ReactECharts option={option} theme={isDark ? 'dark' : undefined} style={{ height: 300 }} />;
};
