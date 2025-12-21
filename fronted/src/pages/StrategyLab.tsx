import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { App, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Statistic, Table } from 'antd';
import { MainLayout } from '../layout/MainLayout';
import * as api from '../api';
import ReactECharts from 'echarts-for-react';
import { useStore } from '../store/useStore';

type BacktestResult = {
  config: any;
  metrics: any;
  evaluation?: any;
  rule_draft?: any;
  equity_curve: Array<{ date: string; equity: number; cash: number; position_value: number; shares: number }>;
  trades: Array<any>;
};

export const StrategyLab = () => {
  const { message } = App.useApp();
  const isDark = useStore((s) => s.isDark);
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const template = Form.useWatch('template', form);

  const templateOptions = [
    { value: 'S1', label: 'S1 趋势跟随（MA 交叉）' },
    { value: 'S2', label: 'S2 突破 + 成交量确认' },
    { value: 'S3', label: 'S3 均值回归（RSI 超卖）' },
    { value: 'S4', label: 'S4 事件驱动（按生效时间）' },
    { value: 'S5', label: 'S5 多因子（海龟+均线+量价+MACD+KDJ）' },
  ];

  const equityOption = useMemo(() => {
    const series = (result?.equity_curve || []).map((p) => [p.date, p.equity]);
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
  }, [result, isDark]);

  const onRun = async () => {
    const values = await form.validateFields();
    setRunning(true);
    try {
      const res = await api.runBacktest({
        symbol: values.symbol,
        template: values.template,
        params: values.params || {},
        start_date: values.start_date || undefined,
        end_date: values.end_date || undefined,
        oos_start_date: values.oos_start_date || undefined,
        initial_cash: values.initial_cash,
        commission_rate: values.commission_rate,
        stamp_duty_rate: values.stamp_duty_rate,
        slippage_bps: values.slippage_bps,
        lot_size: values.lot_size,
      });
      if (res.data?.status === 'success') {
        setResult(res.data.data);
        try {
          localStorage.setItem('last_backtest', JSON.stringify(res.data.data));
        } catch {}
      } else {
        message.error(res.data?.message || '回测失败');
      }
    } catch (e: any) {
      const msg = e?.response?.data?.message || '回测失败';
      message.error(msg);
    } finally {
      setRunning(false);
    }
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

  return (
    <MainLayout>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card title="策略实验室" variant="borderless">
            <Form
              form={form}
              layout="vertical"
              initialValues={{
                symbol: '000001.SZ',
                template: 'S1',
                start_date: '',
                end_date: '',
                oos_start_date: '',
                initial_cash: 100000,
                commission_rate: 0.0003,
                stamp_duty_rate: 0.001,
                slippage_bps: 5,
                lot_size: 100,
                params: { ma_fast: 20, ma_slow: 60, entry_n: 20, exit_n: 10, vol_ratio_th: 1.2, atr_pct_max: 10 },
              }}
            >
              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="symbol" label="标的（ts_code）" rules={[{ required: true, message: '请输入 ts_code' }]}>
                    <Input placeholder="例如 000001.SZ" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="template" label="模板" rules={[{ required: true, message: '请选择模板' }]}>
                    <Select options={templateOptions} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={12}>
                <Col span={12}>
                  <Form.Item name="start_date" label="开始日期（可选）">
                    <Input placeholder="YYYY-MM-DD 或 YYYYMMDD" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="end_date" label="结束日期（可选）">
                    <Input placeholder="YYYY-MM-DD 或 YYYYMMDD" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="oos_start_date" label="样本外起始（可选）">
                    <Input placeholder="YYYY-MM-DD 或 YYYYMMDD" />
                  </Form.Item>
                </Col>
              </Row>

              <Card size="small" title="交易参数" variant="borderless">
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item name="initial_cash" label="初始资金">
                      <InputNumber style={{ width: '100%' }} min={1000} step={1000} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item name="lot_size" label="最小交易股数">
                      <InputNumber style={{ width: '100%' }} min={1} step={1} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="commission_rate" label="佣金率">
                      <InputNumber style={{ width: '100%' }} min={0} step={0.0001} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="stamp_duty_rate" label="印花税率">
                      <InputNumber style={{ width: '100%' }} min={0} step={0.0001} />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item name="slippage_bps" label="滑点（bp）">
                      <InputNumber style={{ width: '100%' }} min={0} step={1} />
                    </Form.Item>
                  </Col>
                </Row>
              </Card>

              <Card size="small" title="模板参数" variant="borderless" style={{ marginTop: 12 }}>
                {template === 'S1' ? (
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item name={['params', 'ma_fast']} label="MA_fast">
                        <InputNumber style={{ width: '100%' }} min={2} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'ma_slow']} label="MA_slow">
                        <InputNumber style={{ width: '100%' }} min={5} step={1} />
                      </Form.Item>
                    </Col>
                  </Row>
                ) : template === 'S2' ? (
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item name={['params', 'breakout_n']} label="突破窗口N">
                        <InputNumber style={{ width: '100%' }} min={5} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'vol_window']} label="成交量窗口">
                        <InputNumber style={{ width: '100%' }} min={10} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'vol_quantile']} label="成交量分位（0~1）">
                        <InputNumber style={{ width: '100%' }} min={0} max={1} step={0.05} />
                      </Form.Item>
                    </Col>
                  </Row>
                ) : template === 'S3' ? (
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item name={['params', 'rsi_window']} label="RSI 窗口">
                        <InputNumber style={{ width: '100%' }} min={5} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'rsi_entry']} label="入场阈值">
                        <InputNumber style={{ width: '100%' }} min={1} max={99} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'rsi_exit']} label="出场阈值">
                        <InputNumber style={{ width: '100%' }} min={1} max={99} step={1} />
                      </Form.Item>
                    </Col>
                  </Row>
                ) : template === 'S4' ? (
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item name={['params', 'event_type']} label="事件类型（可选）">
                        <Input placeholder="例如 earnings / buyback / test" />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'hold_days']} label="持有天数">
                        <InputNumber style={{ width: '100%' }} min={1} step={1} />
                      </Form.Item>
                    </Col>
                  </Row>
                ) : template === 'S5' ? (
                  <Row gutter={12}>
                    <Col span={12}>
                      <Form.Item name={['params', 'entry_n']} label="海龟突破窗口N">
                        <InputNumber style={{ width: '100%' }} min={10} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'exit_n']} label="海龟退出窗口N">
                        <InputNumber style={{ width: '100%' }} min={5} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'ma_fast']} label="MA_fast">
                        <InputNumber style={{ width: '100%' }} min={5} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'ma_slow']} label="MA_slow">
                        <InputNumber style={{ width: '100%' }} min={10} step={1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'vol_ratio_th']} label="量比阈值（20日）">
                        <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                      </Form.Item>
                    </Col>
                    <Col span={12}>
                      <Form.Item name={['params', 'atr_pct_max']} label="最大 ATR%（过滤高波动）">
                        <InputNumber style={{ width: '100%' }} min={0} step={0.5} />
                      </Form.Item>
                    </Col>
                  </Row>
                ) : null}
              </Card>

              <Space style={{ marginTop: 12 }}>
                <Button type="primary" onClick={onRun} loading={running}>
                  运行回测
                </Button>
                <Button onClick={() => navigate('/backtest-report')} disabled={!result || running}>
                  查看报告
                </Button>
                <Button
                  onClick={() => {
                    form.resetFields();
                    setResult(null);
                  }}
                  disabled={running}
                >
                  重置
                </Button>
              </Space>
            </Form>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card title="回测结果" variant="borderless" loading={running}>
            {!result ? (
              <div>运行一次回测后展示报告</div>
            ) : (
              <Space direction="vertical" style={{ width: '100%' }} size={16}>
                <Row gutter={16}>
                  <Col xs={12} md={6}>
                    <Statistic title="总收益" value={(result.metrics.total_return * 100).toFixed(2)} suffix="%" />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="年化" value={(result.metrics.cagr * 100).toFixed(2)} suffix="%" />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="最大回撤" value={(result.metrics.max_drawdown * 100).toFixed(2)} suffix="%" />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="Sharpe" value={Number(result.metrics.sharpe).toFixed(2)} />
                  </Col>
                </Row>
                <Row gutter={16}>
                  <Col xs={12} md={6}>
                    <Statistic title="Calmar" value={Number(result.metrics.calmar).toFixed(2)} />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="交易次数" value={result.metrics.trades} />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="胜率" value={(result.metrics.win_rate * 100).toFixed(0)} suffix="%" />
                  </Col>
                  <Col xs={12} md={6}>
                    <Statistic title="期末权益" value={Number(result.metrics.end_equity).toFixed(0)} />
                  </Col>
                </Row>
                <Card size="small" title="权益曲线" variant="borderless">
                  <ReactECharts option={equityOption} theme={isDark ? 'dark' : undefined} style={{ height: 280 }} />
                </Card>
                <Card size="small" title="交易明细" variant="borderless">
                  <Table
                    rowKey={(r) => `${r.entry_date || 'na'}-${r.exit_date}-${r.exit_price}`}
                    dataSource={result.trades}
                    columns={tradesColumns as any}
                    pagination={{ pageSize: 8 }}
                    size="small"
                  />
                </Card>
              </Space>
            )}
          </Card>
        </Col>
      </Row>
    </MainLayout>
  );
};
