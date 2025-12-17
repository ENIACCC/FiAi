import { useState } from 'react';
import { Button, Input, List, Avatar, Spin, message } from 'antd';
import { RobotOutlined, UserOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { analyzeWatchlist } from '../api';

interface Message {
  role: 'ai' | 'user';
  content: string;
}

export const AIChat = ({ }: { open: boolean; onClose: () => void; isMobile?: boolean }) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: '您好，我是您的智能投资助手。我可以帮您分析自选股，或者回答市场相关问题。' }
  ]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');

  const handleAnalyze = async () => {
    setLoading(true);
    setMessages(prev => [...prev, { role: 'user', content: '分析自选股' }]);
    try {
      const res = await analyzeWatchlist();
      setMessages(prev => [...prev, { role: 'ai', content: res.data.analysis }]);
    } catch (error) {
      message.error('分析失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;
    setMessages(prev => [...prev, { role: 'user', content: input }]);
    setInput('');
    setTimeout(() => {
      setMessages(prev => [...prev, { role: 'ai', content: '这是一个模拟回复。实际功能需要接入大模型API。' }]);
    }, 1000);
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 16, borderBottom: '1px solid #f0f0f0' }}>
         <Button type="primary" block icon={<ThunderboltOutlined />} onClick={handleAnalyze} loading={loading}>
           一键分析自选股
         </Button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        <List
          itemLayout="horizontal"
          dataSource={messages}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                avatar={<Avatar icon={item.role === 'ai' ? <RobotOutlined /> : <UserOutlined />} style={{ backgroundColor: item.role === 'ai' ? '#1677ff' : '#87d068' }} />}
                title={item.role === 'ai' ? 'AI 助手' : '我'}
                description={<div style={{ whiteSpace: 'pre-wrap' }}>{item.content}</div>}
              />
            </List.Item>
          )}
        />
        {loading && <Spin tip="正在分析..." style={{ marginTop: 16 }} />}
      </div>
      <div style={{ padding: 16, borderTop: '1px solid #f0f0f0', display: 'flex', gap: 8 }}>
        <Input 
          value={input} 
          onChange={e => setInput(e.target.value)} 
          onPressEnter={handleSend} 
          placeholder="输入问题..." 
        />
        <Button type="primary" onClick={handleSend}>发送</Button>
      </div>
    </div>
  );
};
