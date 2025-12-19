import { useState } from 'react';
import { Button, Input, App } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { analyzeWatchlist } from '../api';
import { useStore } from '../store/useStore';

interface Message {
  role: 'ai' | 'user';
  content: string;
}

export const AIChat = ({ }: { open: boolean; onClose: () => void; isMobile?: boolean }) => {
  const { message } = App.useApp();
  const activeGroupId = useStore(state => state.activeGroupId);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: '您好，我是您的智能投资助手。我可以帮您分析自选股，或者回答市场相关问题。' }
  ]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');

  const handleAnalyze = async () => {
    setLoading(true);
    const groupText = activeGroupId === 'default' ? '默认分组' : '当前分组';
    setMessages(prev => [...prev, { role: 'user', content: `分析${groupText}自选股` }]);
    try {
      const res = await analyzeWatchlist(activeGroupId === 'default' ? undefined : activeGroupId);
      const aiMsg = res?.data?.data?.message || '分析完成';
      setMessages(prev => [...prev, { role: 'ai', content: aiMsg }]);
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
    <div className="chat-container">
      <div className="chat-header">
        <Button type="primary" icon={<ThunderboltOutlined />} onClick={handleAnalyze} loading={loading}>
          一键分析自选股
        </Button>
      </div>
      <div className="chat-stream">
        <div className="chat-inner">
          {messages.map((m, idx) => (
            <div key={idx} className={`chat-row ${m.role}`}>
              <div className={`bubble ${m.role}`}>
                <div className="chat-text">{m.content}</div>
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-row ai">
              <div className="bubble ai">
                <div className="typing">
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                  <span className="typing-dot" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      <div className="chat-input-panel">
        <Input.TextArea
          value={input}
          onChange={e => setInput(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="输入问题，Shift+Enter 换行"
          autoSize={{ minRows: 2, maxRows: 6 }}
          className="chat-textarea"
        />
        <div className="chat-actions">
          <Button type="primary" onClick={handleSend}>发送</Button>
        </div>
      </div>
    </div>
  );
};
