import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { App, Button, Card, Col, Descriptions, List, Row, Space, Spin, Tag } from 'antd';
import { MainLayout } from '../layout/MainLayout';
import * as api from '../api';
import { useStore } from '../store/useStore';

export const StockResearch = () => {
  const { ts_code } = useParams();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { activeGroupId, setAiChatOpen, setAiContext } = useStore();

  const symbol = useMemo(() => {
    if (!ts_code) return '';
    return String(ts_code).split('.')[0];
  }, [ts_code]);

  const [loading, setLoading] = useState(false);
  const [stock, setStock] = useState<any | null>(null);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  const [signalsLoading, setSignalsLoading] = useState(false);
  const [signals, setSignals] = useState<any[]>([]);
  const [timingReport, setTimingReport] = useState<any | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!symbol) return;
      setLoading(true);
      try {
        const res = await api.getStocks(symbol);
        const list = res.data?.status === 'success' ? res.data.data : [];
        const item = Array.isArray(list) && list.length > 0 ? list[0] : null;
        if (!cancelled) setStock(item);
      } catch (e) {
        message.error('加载个股信息失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!ts_code) return;
      setEventsLoading(true);
      try {
        const res = await api.getEvents({ symbol: String(ts_code) });
        const list = res.data?.status === 'success' ? res.data.data : [];
        if (!cancelled) setEvents(Array.isArray(list) ? list : []);
      } catch (e) {
        message.error('加载事件失败');
      } finally {
        if (!cancelled) setEventsLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [ts_code]);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (!ts_code) return;
      setSignalsLoading(true);
      try {
        const res = await api.getSignals({ symbol: String(ts_code) });
        const list = res.data?.status === 'success' ? res.data.data?.signals : [];
        const timing = res.data?.status === 'success' ? res.data.data?.timing_report : null;
        if (!cancelled) setSignals(Array.isArray(list) ? list : []);
        if (!cancelled) setTimingReport(timing || null);
      } catch (e) {
        message.error('加载信号解释失败');
      } finally {
        if (!cancelled) setSignalsLoading(false);
      }
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [ts_code]);

  const handleAddToWatchlist = async () => {
    if (!stock?.ts_code || !stock?.name) return;
    try {
      const groupId = activeGroupId === 'default' ? undefined : activeGroupId;
      const res = await api.addToWatchlist({
        ts_code: stock.ts_code,
        name: stock.name,
        group_id: groupId,
      });
      if (res.data?.status === 'success') {
        message.success('已添加到自选');
      } else if (res.data?.status === 'info') {
        message.info('该股票已在当前分组');
      } else {
        message.error('添加失败');
      }
    } catch (e) {
      message.error('添加失败');
    }
  };

  const handleAiChat = () => {
    if (!stock) return;
    setAiContext({ type: 'stock', data: stock });
    setAiChatOpen(true);
  };

  const formatSample = (m: any) => {
    if (!m || !m.n) return 'N=0';
    const win = typeof m.win_rate === 'number' ? `${(m.win_rate * 100).toFixed(0)}%` : '-';
    const avg = typeof m.avg === 'number' ? `${(m.avg * 100).toFixed(2)}%` : '-';
    const p10 = typeof m.p10 === 'number' ? `${(m.p10 * 100).toFixed(2)}%` : '-';
    const p90 = typeof m.p90 === 'number' ? `${(m.p90 * 100).toFixed(2)}%` : '-';
    return `N=${m.n} 胜率=${win} 均值=${avg} P10=${p10} P90=${p90}`;
  };

  return (
    <MainLayout>
      <Card
        variant="borderless"
        title={stock ? `${stock.name}（${stock.ts_code}）` : (ts_code ? `个股研究（${ts_code}）` : '个股研究')}
        extra={
          <Space>
            <Button onClick={() => navigate('/watchlist')}>返回自选</Button>
            <Button type="primary" onClick={handleAddToWatchlist} disabled={!stock}>
              加入当前分组
            </Button>
            <Button type="primary" ghost onClick={handleAiChat} disabled={!stock}>
              AI聊股
            </Button>
          </Space>
        }
      >
        {loading ? (
          <Spin />
        ) : !stock ? (
          <div>暂无数据</div>
        ) : (
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={12}>
              <Card title="基础信息" variant="borderless">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="行业">{stock.industry || '-'}</Descriptions.Item>
                  <Descriptions.Item label="上市时间">{stock.listing_date || '-'}</Descriptions.Item>
                  <Descriptions.Item label="总市值">{stock.market_cap || '-'}</Descriptions.Item>
                  <Descriptions.Item label="总股本">{stock.total_shares || '-'}</Descriptions.Item>
                  <Descriptions.Item label="流通股">{stock.circulating_shares || '-'}</Descriptions.Item>
                  <Descriptions.Item label="流通市值">{stock.circulating_market_cap || '-'}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card title="行情概览" variant="borderless">
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="最新价">{stock.price ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="涨跌幅%">{stock.change_pct ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="成交量">{stock.volume ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="换手率%">{stock.turnover_rate ?? '-'}</Descriptions.Item>
                  <Descriptions.Item label="PE">{stock.pe ?? '-'}</Descriptions.Item>
                </Descriptions>
              </Card>
            </Col>
            <Col xs={24}>
              <Card title="买卖时机综合分析" variant="borderless" loading={signalsLoading}>
                {!timingReport ? (
                  <div>暂无分析结果</div>
                ) : (
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    <Space size={8} wrap>
                      {timingReport.decision?.buy_bias ? <Tag color="green">偏买入</Tag> : <Tag>非强买点</Tag>}
                      {timingReport.decision?.sell_bias ? <Tag color="red">偏卖出</Tag> : <Tag>非强卖点</Tag>}
                      <Tag>
                        收盘 {Number(timingReport.snapshot?.close || 0).toFixed(2)}（{(Number(timingReport.snapshot?.change_pct || 0) * 100).toFixed(2)}%）
                      </Tag>
                      {typeof timingReport.snapshot?.atr_pct_14 === 'number' ? <Tag>ATR% {Number(timingReport.snapshot.atr_pct_14).toFixed(2)}%</Tag> : null}
                      {typeof timingReport.snapshot?.vol_ratio_20 === 'number' ? <Tag>量比20 {Number(timingReport.snapshot.vol_ratio_20).toFixed(2)}</Tag> : null}
                      {timingReport.indicators?.chanlun?.trend ? <Tag>缠论(简) {timingReport.indicators.chanlun.trend}</Tag> : null}
                    </Space>
                    <Descriptions size="small" column={2}>
                      <Descriptions.Item label="MA20">{timingReport.indicators?.ma?.ma20?.toFixed?.(2) || '-'}</Descriptions.Item>
                      <Descriptions.Item label="MA60">{timingReport.indicators?.ma?.ma60?.toFixed?.(2) || '-'}</Descriptions.Item>
                      <Descriptions.Item label="MACD柱">{timingReport.indicators?.macd?.hist?.toFixed?.(4) || '-'}</Descriptions.Item>
                      <Descriptions.Item label="KDJ(K/D)">
                        {typeof timingReport.indicators?.kdj?.k === 'number' && typeof timingReport.indicators?.kdj?.d === 'number'
                          ? `${timingReport.indicators.kdj.k.toFixed(1)}/${timingReport.indicators.kdj.d.toFixed(1)}`
                          : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="BOLL%">{timingReport.indicators?.boll?.pctb?.toFixed?.(2) || '-'}</Descriptions.Item>
                      <Descriptions.Item label="海龟(高20/低10)">
                        {typeof timingReport.indicators?.turtle?.high20 === 'number' && typeof timingReport.indicators?.turtle?.low10 === 'number'
                          ? `${timingReport.indicators.turtle.high20.toFixed(2)} / ${timingReport.indicators.turtle.low10.toFixed(2)}`
                          : '-'}
                      </Descriptions.Item>
                    </Descriptions>
                    <Row gutter={[16, 8]}>
                      <Col xs={24} lg={12}>
                        <Card size="small" title="偏买入理由" variant="borderless">
                          {(timingReport.decision?.buy_reasons || []).length > 0 ? (
                            <List
                              size="small"
                              dataSource={timingReport.decision.buy_reasons}
                              renderItem={(x: any) => <List.Item>{String(x)}</List.Item>}
                            />
                          ) : (
                            <div>暂无</div>
                          )}
                        </Card>
                      </Col>
                      <Col xs={24} lg={12}>
                        <Card size="small" title="偏卖出/转弱理由" variant="borderless">
                          {(timingReport.decision?.sell_reasons || []).length > 0 ? (
                            <List
                              size="small"
                              dataSource={timingReport.decision.sell_reasons}
                              renderItem={(x: any) => <List.Item>{String(x)}</List.Item>}
                            />
                          ) : (
                            <div>暂无</div>
                          )}
                        </Card>
                      </Col>
                      <Col xs={24}>
                        <Card size="small" title="风控与注意事项" variant="borderless">
                          <List
                            size="small"
                            dataSource={[
                              ...(timingReport.decision?.risk_controls || []),
                              ...(timingReport.decision?.notice || []),
                            ]}
                            renderItem={(x: any) => <List.Item>{String(x)}</List.Item>}
                          />
                        </Card>
                      </Col>
                    </Row>
                  </Space>
                )}
              </Card>
            </Col>
            <Col xs={24}>
              <Card title="信号解释" variant="borderless" loading={signalsLoading}>
                <List
                  dataSource={signals}
                  locale={{ emptyText: '暂无信号（数据不足或尚未触发）' }}
                  renderItem={(item: any) => {
                    const horizons = item?.similar_samples?.horizons || {};
                    return (
                      <List.Item>
                        <List.Item.Meta
                          title={
                            <Space size={8} wrap>
                              <span>{item.name || item.template}</span>
                              {item.status === 'triggered' ? <Tag color="green">触发</Tag> : <Tag>未触发</Tag>}
                              {item.risk_level ? (
                                <Tag color={item.risk_level === 'L2' ? 'orange' : 'default'}>{item.risk_level}</Tag>
                              ) : null}
                            </Space>
                          }
                          description={
                            <Space direction="vertical" size={4} style={{ width: '100%' }}>
                              <div>最近触发：{item.last_trigger_date || '-'}</div>
                              <div>触发因素：{Array.isArray(item.trigger_factors) ? item.trigger_factors.join('；') : '-'}</div>
                              <div>关键证据：{Array.isArray(item.evidence) ? item.evidence.join('；') : '-'}</div>
                              <div>
                                历史相似样本（未来收益）：
                                <div>5日：{formatSample(horizons['5'])}</div>
                                <div>10日：{formatSample(horizons['10'])}</div>
                                <div>20日：{formatSample(horizons['20'])}</div>
                              </div>
                              <div>风险点：{Array.isArray(item.risks) ? item.risks.join('；') : '-'}</div>
                              <div>失效条件：{Array.isArray(item.invalidation) ? item.invalidation.join('；') : '-'}</div>
                            </Space>
                          }
                        />
                      </List.Item>
                    );
                  }}
                />
              </Card>
            </Col>
            <Col xs={24}>
              <Card title="事件时间线" variant="borderless" loading={eventsLoading}>
                <List
                  dataSource={events}
                  locale={{ emptyText: '暂无事件（你可以先通过接口写入测试事件）' }}
                  renderItem={(item: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space size={8} wrap>
                            <span>{item.title}</span>
                            {item.event_type ? <Tag>{item.event_type}</Tag> : null}
                            {item.source ? <Tag color="blue">{item.source}</Tag> : null}
                          </Space>
                        }
                        description={
                          <Space direction="vertical" size={4} style={{ width: '100%' }}>
                            <div>
                              生效时间：{item.market_effective_time || '-'}，事件时间：{item.event_time || '-'}
                            </div>
                            {item.evidence ? <div style={{ color: 'rgba(0,0,0,0.65)' }}>{item.evidence}</div> : null}
                            {item.source_url ? (
                              <a href={item.source_url} target="_blank" rel="noreferrer">
                                查看来源
                              </a>
                            ) : null}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        )}
      </Card>
    </MainLayout>
  );
};
