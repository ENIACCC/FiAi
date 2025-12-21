import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App, Button, Card, Col, Descriptions, Row, Space, Statistic, Table, Tag } from 'antd';
import ReactECharts from 'echarts-for-react';
import { MainLayout } from '../layout/MainLayout';
import { useStore } from '../store/useStore';

export const BacktestReport = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const isDark = useStore((s) => s.isDark);

  const [report] = useState<any>(() => {
    try {
      const raw = localStorage.getItem('last_backtest');
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });

  const equityOption = useMemo(() => {
    const curve = (report?.equity_curve || []) as Array<{ date: string; equity: number }>;
    const series = curve.map((p) => [p.date, p.equity]);
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      grid: { left: 40, right: 20, top: 20, bottom: 40 },
      xAxis: { type: 'category', data: series.map((x) => x[0]), axisLabel: { color: isDark ? '#ccc' : '#333' } },
      yAxis: { type: 'value', axisLabel: { color: isDark ? '#ccc' : '#333' }, splitLine: { lineStyle: { color: isDark ? '#444' : '#eee' } } },
      series: [
        {
          name: '权益',
          type: 'line',
          showSymbol: false,
          data: series.map((x) => x[1]),
          lineStyle: { width: 2 },
        },
      ],
    };
  }, [report, isDark]);

  const warnings: Array<any> = report?.evaluation?.warnings || [];
  const hasL3 = warnings.some((w) => w?.level === 'L3');

  const downloadRuleDraft = () => {
    const draft = report?.rule_draft;
    if (!draft) {
      message.error('无规则草案可导出');
      return;
    }
    const blob = new Blob([JSON.stringify(draft, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rule_draft_${draft.symbol || 'unknown'}_${draft.template || 'unknown'}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const tradesColumns = [
    { title: '买入日', dataIndex: 'entry_date', key: 'entry_date' },
    { title: '买入价', dataIndex: 'entry_price', key: 'entry_price', render: (v: any) => (typeof v === 'number' ? v.toFixed(3) : '-') },
    { title: '卖出日', dataIndex: 'exit_date', key: 'exit_date' },
    { title: '卖出价', dataIndex: 'exit_price', key: 'exit_price', render: (v: any) => (typeof v === 'number' ? v.toFixed(3) : '-') },
    { title: '股数', dataIndex: 'shares', key: 'shares' },
    { title: '收益%', dataIndex: 'return_pct', key: 'return_pct', render: (v: any) => (typeof v === 'number' ? `${(v * 100).toFixed(2)}%` : '-') },
    { title: 'PnL', dataIndex: 'pnl', key: 'pnl', render: (v: any) => (typeof v === 'number' ? v.toFixed(2) : '-') },
  ];

  if (!report) {
    return (
      <MainLayout>
        <Card title="回测报告" variant="borderless" extra={<Button onClick={() => navigate('/strategy')}>返回策略实验室</Button>}>
          <div>暂无回测报告，请先在策略实验室运行一次回测。</div>
        </Card>
      </MainLayout>
    );
  }

  const metrics = report.metrics || {};
  const ins = report.evaluation?.in_sample || null;
  const oos = report.evaluation?.out_of_sample || null;

  return (
    <MainLayout>
      <Card
        title="回测报告"
        variant="borderless"
        extra={
          <Space>
            <Button onClick={() => navigate('/strategy')}>返回策略实验室</Button>
            <Button type="primary" onClick={downloadRuleDraft}>
              导出规则草案
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          {warnings.length > 0 ? (
            <Card size="small" title="风险提示" variant="borderless">
              <Space wrap>
                {warnings.map((w, idx) => (
                  <Tag key={idx} color={w.level === 'L3' ? 'red' : 'orange'}>
                    {w.level} {w.message}
                  </Tag>
                ))}
              </Space>
              {hasL3 ? <div style={{ marginTop: 8 }}>存在阻断级问题（L3），不建议导出可执行规则到模拟盘。</div> : null}
            </Card>
          ) : null}

          <Card size="small" title="配置" variant="borderless">
            <Descriptions column={2} size="small">
              <Descriptions.Item label="标的">{report.config?.symbol}</Descriptions.Item>
              <Descriptions.Item label="模板">{report.config?.template}</Descriptions.Item>
              <Descriptions.Item label="开始">{report.config?.start_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="结束">{report.config?.end_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="样本外起始">{report.config?.oos_start_date || '-'}</Descriptions.Item>
              <Descriptions.Item label="参数">{JSON.stringify(report.config?.params || {})}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card size="small" title="核心指标（全样本）" variant="borderless">
            <Row gutter={16}>
              <Col xs={12} md={6}>
                <Statistic title="总收益" value={(Number(metrics.total_return || 0) * 100).toFixed(2)} suffix="%" />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="年化" value={(Number(metrics.cagr || 0) * 100).toFixed(2)} suffix="%" />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="最大回撤" value={(Number(metrics.max_drawdown || 0) * 100).toFixed(2)} suffix="%" />
              </Col>
              <Col xs={12} md={6}>
                <Statistic title="Sharpe" value={Number(metrics.sharpe || 0).toFixed(2)} />
              </Col>
            </Row>
          </Card>

          {ins && oos ? (
            <Card size="small" title="样本内 / 样本外" variant="borderless">
              <Row gutter={[16, 16]}>
                <Col xs={24} md={12}>
                  <Card size="small" title="样本内" variant="borderless">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic title="总收益" value={(Number(ins.total_return || 0) * 100).toFixed(2)} suffix="%" />
                      </Col>
                      <Col span={12}>
                        <Statistic title="最大回撤" value={(Number(ins.max_drawdown || 0) * 100).toFixed(2)} suffix="%" />
                      </Col>
                      <Col span={12}>
                        <Statistic title="Sharpe" value={Number(ins.sharpe || 0).toFixed(2)} />
                      </Col>
                      <Col span={12}>
                        <Statistic title="Calmar" value={Number(ins.calmar || 0).toFixed(2)} />
                      </Col>
                    </Row>
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card size="small" title="样本外" variant="borderless">
                    <Row gutter={16}>
                      <Col span={12}>
                        <Statistic title="总收益" value={(Number(oos.total_return || 0) * 100).toFixed(2)} suffix="%" />
                      </Col>
                      <Col span={12}>
                        <Statistic title="最大回撤" value={(Number(oos.max_drawdown || 0) * 100).toFixed(2)} suffix="%" />
                      </Col>
                      <Col span={12}>
                        <Statistic title="Sharpe" value={Number(oos.sharpe || 0).toFixed(2)} />
                      </Col>
                      <Col span={12}>
                        <Statistic title="Calmar" value={Number(oos.calmar || 0).toFixed(2)} />
                      </Col>
                    </Row>
                  </Card>
                </Col>
              </Row>
            </Card>
          ) : null}

          <Card size="small" title="权益曲线" variant="borderless">
            <ReactECharts option={equityOption} theme={isDark ? 'dark' : undefined} style={{ height: 320 }} />
          </Card>

          <Card size="small" title="交易明细" variant="borderless">
            <Table
              rowKey={(r) => `${r.entry_date || 'na'}-${r.exit_date}-${r.exit_price}`}
              dataSource={report.trades || []}
              columns={tradesColumns as any}
              pagination={{ pageSize: 10 }}
              size="small"
            />
          </Card>
        </Space>
      </Card>
    </MainLayout>
  );
};

