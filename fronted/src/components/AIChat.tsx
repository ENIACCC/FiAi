import { useState, useEffect, useRef, type ReactNode } from 'react';
import { Button, Input, App } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import { analyzeWatchlist, chatAI } from '../api';
import { useStore } from '../store/useStore';
import { useNavigate } from 'react-router-dom';

interface Message {
  role: 'ai' | 'user';
  content: string | ReactNode;
}

export const AIChat = ({ onClose, isMobile }: { open: boolean; onClose: () => void; isMobile?: boolean }) => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const activeGroupId = useStore(state => state.activeGroupId);
  const aiContext = useStore(state => state.aiContext);
  const setAiContext = useStore(state => state.setAiContext);
  const [currentStock, setCurrentStock] = useState<any>(null);
  const [messages, setMessages] = useState<Message[]>([
    { role: 'ai', content: '您好，我是您的智能投资助手。我可以帮您分析自选股，或者回答市场相关问题。' }
  ]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const processedContextRef = useRef<any>(null);

  const toApiMessages = (extraUserText?: string) => {
    const base = messages
      .filter(m => typeof m.content === 'string')
      .map(m => ({
        role: m.role === 'user' ? 'user' : 'assistant',
        content: m.content as string,
      }));
    if (extraUserText) {
      base.push({ role: 'user', content: extraUserText });
    }
    return base;
  };

  const sendText = async (text: string, stock?: any) => {
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    try {
      const res = await chatAI({ messages: toApiMessages(text), stock });
      if (res?.data?.status === 'success') {
        setMessages(prev => [...prev, { role: 'ai', content: res.data.data.message }]);
        return;
      }

      if (res?.data?.code === 'missing_api_key') {
        message.warning('未配置 AI API Key，请前往 设置 页面进行配置');
        return;
      }

      message.error(res?.data?.message || 'AI 服务暂时不可用');
    } catch (error) {
      const err: any = error;
      const msg = err?.response?.data?.message || '发送失败';
      message.error(msg);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (aiContext && aiContext.type === 'stock' && aiContext.data) {
       if (processedContextRef.current === aiContext) return;
       processedContextRef.current = aiContext;

       const stockName = aiContext.data.name;
       const stockCode = aiContext.data.ts_code || aiContext.data.symbol || aiContext.data.code;
       const initialMsg = aiContext.message || `我想聊聊 ${stockName} (${stockCode})`;
       setCurrentStock(aiContext.data);
       setAiContext(null);
       sendText(initialMsg, aiContext.data);
    }
  }, [aiContext, setAiContext]);

  const handleAnalyze = async () => {
    setLoading(true);
    const groupText = activeGroupId === 'default' ? '默认分组' : '当前分组';
    setMessages(prev => [...prev, { role: 'user', content: `分析${groupText}自选股` }]);
    try {
      const res = await analyzeWatchlist(activeGroupId === 'default' ? undefined : activeGroupId);
      if (res?.data?.status === 'success') {
        setMessages(prev => [...prev, { role: 'ai', content: res.data.data.message }]);
        return;
      }

      if (res?.data?.code === 'missing_api_key') {
        message.warning('未配置 AI API Key，请前往 设置 页面进行配置');
        navigate('/settings');
        if (isMobile) onClose();
        return;
      }

      message.error(res?.data?.message || '分析服务暂时不可用');
    } catch (error) {
      const err: any = error;
      const msg = err?.response?.data?.message || '分析失败';
      message.error(msg);
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = () => {
    if (!input.trim()) return;
    const text = input.trim();
    setInput('');
    sendText(text, currentStock);
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
