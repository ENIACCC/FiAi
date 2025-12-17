import { MainLayout } from '../layout/MainLayout';
import { useState, useEffect } from 'react';
import { Card, Form, Input, Button, Tabs, message, Typography, Alert, Select } from 'antd';
import { UserOutlined, LockOutlined, ApiOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;

export const Settings = () => {
  const [form] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<any>(null);

  const fetchUserInfo = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const res = await axios.get('http://127.0.0.1:8000/api/user/info/', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(res.data);
      form.setFieldsValue({
        username: res.data.username,
        email: res.data.email,
        ai_api_key: res.data.profile?.ai_api_key,
        ai_model: res.data.profile?.ai_model || 'deepseek-chat'
      });
    } catch (error) {
      console.error("Failed to fetch user info", error);
      message.error("无法获取用户信息");
    }
  };

  useEffect(() => {
    fetchUserInfo();
  }, []);

  const handleInfoUpdate = async (values: any) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      // Structure the data to match serializer expectation
      const updateData = {
        email: values.email,
        profile: {
            ai_api_key: values.ai_api_key,
            ai_model: values.ai_model
        }
      };

      await axios.patch('http://127.0.0.1:8000/api/user/info/', updateData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      message.success('设置已更新');
      fetchUserInfo();
    } catch (error) {
      console.error("Update failed", error);
      message.error('更新失败');
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
      const token = localStorage.getItem('token');
      await axios.post('http://127.0.0.1:8000/api/user/change-password/', {
        old_password: values.old_password,
        new_password: values.new_password
      }, {
        headers: { Authorization: `Bearer ${token}` }
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
      label: (<span><UserOutlined /> 基本信息 & AI 配置</span>),
      children: (
        <Form
          form={form}
          layout="vertical"
          onFinish={handleInfoUpdate}
          initialValues={user}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item label="用户名" name="username">
              <Input disabled />
            </Form.Item>
            <Form.Item label="邮箱" name="email">
              <Input />
            </Form.Item>
          </div>

          <Form.Item 
            label="AI 模型" 
            name="ai_model"
            initialValue="deepseek-chat"
            extra="选择用于股票分析的 AI 模型"
          >
            <Select>
                <Select.Option value="deepseek-chat">DeepSeek-V3</Select.Option>
                <Select.Option value="deepseek-reasoner">DeepSeek-R1 (推理版)</Select.Option>
                <Select.Option value="gpt-4o">GPT-4o</Select.Option>
                <Select.Option value="claude-3-5-sonnet">Claude 3.5 Sonnet</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item 
            label="AI API Key" 
            name="ai_api_key"
            extra="配置用于 AI 分析的大模型 API Key"
          >
            <Input.Password prefix={<ApiOutlined />} placeholder="sk-..." />
          </Form.Item>

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
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <Title level={2} style={{ marginBottom: 24 }}>账户设置</Title>
        <Card bordered={false} className="shadow-sm">
          <Tabs defaultActiveKey="1" items={items} />
        </Card>
      </div>
    </MainLayout>
  );
};
