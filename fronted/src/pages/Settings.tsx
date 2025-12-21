import { MainLayout } from '../layout/MainLayout';
import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Tabs, App, Alert, Select, Table, Tag, Space, Popconfirm } from 'antd';
import { UserOutlined, LockOutlined, ApiOutlined, SaveOutlined } from '@ant-design/icons';
import api from '../api';

export const Settings = () => {
  const [basicForm] = Form.useForm();
  const [aiForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const { message } = App.useApp();

  const fetchUserInfo = async () => {
    try {
      const res = await api.get('user/info/');
      setUser(res.data || null);
      basicForm.setFieldsValue({
        username: res.data?.username,
        email: res.data?.email,
      });
      aiForm.setFieldsValue({
        provider: res.data?.profile?.ai_provider || 'deepseek',
        base_url: res.data?.profile?.ai_base_url || 'https://api.deepseek.com',
        model: res.data?.profile?.ai_model || 'deepseek-chat',
        api_key: '',
      });
    } catch (error) {
      console.error("Failed to fetch user info", error);
      message.error("无法获取用户信息");
    }
  };

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const handleBasicUpdate = async (values: any) => {
    setLoading(true);
    try {
      await api.patch('user/info/', { email: values.email });
      message.success('设置已更新');
      await fetchUserInfo();
    } catch (error) {
      console.error("Update failed", error);
      message.error('更新失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAIConfigSave = async (values: any) => {
    setLoading(true);
    try {
      const resp = await api.post('ai-models/', {
        provider: values.provider || 'deepseek',
        base_url: values.base_url || 'https://api.deepseek.com',
        model: values.model || 'deepseek-chat',
        api_key: values.api_key,
        set_active: true,
      });
      const status = resp?.data?.status;
      const code = resp?.data?.code;
      const msg = resp?.data?.message;
      if (status === 'info' && code === 'duplicate') {
        message.warning(msg || '该模型配置已存在，请勿重复添加');
      } else {
        message.success('AI 模型已保存');
      }
      await fetchUserInfo();
      aiForm.setFieldsValue({ api_key: '' });
    } catch (error: any) {
      const msg = error?.response?.data?.message || '保存失败';
      console.error("AI config save failed", error);
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (values: any) => {
    if (values.new_password !== values.confirm_password) {
      message.error('两次输入的密码不一致');
      return;
    }
    
    setLoading(true);
    try {
      await api.post('user/change-password/', {
        old_password: values.old_password,
        new_password: values.new_password
      });
      message.success('密码修改成功');
      passwordForm.resetFields();
    } catch (error: any) {
        const msg = error.response?.data?.message || '密码修改失败';
        message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const items = [
    {
      key: '1',
      label: (<span><UserOutlined /> 基本信息</span>),
      children: (
        <Form form={basicForm} layout="vertical" onFinish={handleBasicUpdate}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item label="用户名" name="username">
              <Input disabled />
            </Form.Item>
            <Form.Item label="邮箱" name="email">
              <Input />
            </Form.Item>
          </div>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading}>
              保存更改
            </Button>
          </Form.Item>
        </Form>
      ),
    },
    {
      key: '2',
      label: (<span><ApiOutlined /> AI 配置</span>),
      children: (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Form form={aiForm} layout="vertical" onFinish={handleAIConfigSave}>
            <Form.Item label="AI 模型" name="model" initialValue="deepseek-chat" extra="选择用于股票分析的 AI 模型">
              <Select>
                <Select.Option value="deepseek-chat">deepseek-chat (DeepSeek-V3.2)</Select.Option>
                <Select.Option value="deepseek-reasoner">deepseek-reasoner (DeepSeek-V3.2 思考模式)</Select.Option>
              </Select>
            </Form.Item>

            <Form.Item label="AI Base URL" name="base_url" initialValue="https://api.deepseek.com">
              <Input />
            </Form.Item>

            <Form.Item name="provider" initialValue="deepseek" hidden>
              <Input />
            </Form.Item>

            <Form.Item
              label="AI API Key"
              name="api_key"
              extra="必填；Key 为空时不允许保存"
              rules={[
                { required: true, message: '请输入 API Key' },
                {
                  validator: async (_, v) => {
                    if (typeof v !== 'string' || !v.trim()) {
                      return Promise.reject(new Error('请输入 API Key'));
                    }
                    return Promise.resolve();
                  },
                },
              ]}
            >
              <Input.Password prefix={<ApiOutlined />} placeholder="sk-..." />
            </Form.Item>

            <Form.Item shouldUpdate>
              {() => {
                const v = aiForm.getFieldValue('api_key');
                const disabled = typeof v !== 'string' || !v.trim() || aiForm.getFieldsError().some((f) => f.errors.length);
                return (
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={loading} disabled={disabled}>
                    保存模型
                  </Button>
                );
              }}
            </Form.Item>
          </Form>

          <Card size="small" title="已添加的 AI 模型" variant="borderless">
            <Table
              size="small"
              pagination={false}
              rowKey={(r) => r.id}
              dataSource={(user?.profile?.ai_models || []).map((m: any) => ({
                id: m.id,
                provider: m.provider,
                base_url: m.base_url,
                model: m.model,
                key_configured: !!m.api_key_configured,
                key_preview: m.api_key_preview || '-',
                is_active: String(user?.profile?.active_ai_model_id || '') === String(m.id),
              }))}
              columns={[
                { title: 'Provider', dataIndex: 'provider', key: 'provider' },
                { title: 'Base URL', dataIndex: 'base_url', key: 'base_url' },
                { title: '模型', dataIndex: 'model', key: 'model' },
                {
                  title: 'Key',
                  dataIndex: 'key_configured',
                  key: 'key_configured',
                  render: (vv: any, row: any) => (
                    <Space size={8}>
                      {row.is_active ? <Tag color="blue">当前</Tag> : null}
                      {vv ? <Tag color="green">已配置</Tag> : <Tag>未配置</Tag>}
                      <span>{row.key_preview}</span>
                    </Space>
                  ),
                },
                {
                  title: '操作',
                  key: 'actions',
                  render: (_: any, row: any) => (
                    <Space size={8}>
                      <Button
                        size="small"
                        disabled={row.is_active}
                        onClick={async () => {
                          try {
                            await api.post(`ai-models/${row.id}/select/`, {});
                            message.success('已切换当前模型');
                            await fetchUserInfo();
                          } catch (error) {
                            console.error('Select AI model failed', error);
                            message.error('切换失败');
                          }
                        }}
                      >
                        设为当前
                      </Button>
                      <Popconfirm
                        title="确定删除该模型配置？"
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                        onConfirm={async () => {
                          try {
                            await api.delete(`ai-models/${row.id}/`);
                            message.success('已删除');
                            await fetchUserInfo();
                          } catch (error) {
                            console.error('Delete AI model failed', error);
                            message.error('删除失败');
                          }
                        }}
                      >
                        <Button size="small" danger>
                          删除
                        </Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
              locale={{ emptyText: '暂无已添加模型（先保存一次 AI 配置）' }}
            />
          </Card>
        </Space>
      ),
    },
    {
      key: '3',
      label: (<span><LockOutlined /> 安全设置</span>),
      children: (
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handlePasswordChange}
        >
          <Alert message="为了账号安全，请定期更换密码" type="info" showIcon style={{ marginBottom: 24 }} />
          
          <Form.Item 
            label="当前密码" 
            name="old_password" 
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password />
          </Form.Item>
          
          <Form.Item 
            label="新密码" 
            name="new_password"
            rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '密码长度至少6位' }]}
          >
            <Input.Password />
          </Form.Item>
          
          <Form.Item 
            label="确认新密码" 
            name="confirm_password"
            rules={[{ required: true, message: '请确认新密码' }]}
          >
            <Input.Password />
          </Form.Item>

          <Form.Item>
            <Button type="primary" danger htmlType="submit" loading={loading}>
              修改密码
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <MainLayout>
      <Card title="账户设置" variant="borderless">
        <Tabs defaultActiveKey="1" items={items} />
      </Card>
    </MainLayout>
  );
};
