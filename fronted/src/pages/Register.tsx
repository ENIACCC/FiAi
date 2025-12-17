import { Form, Input, Button, Card, App } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate, Link } from 'react-router-dom';
import * as api from '../api';
import { useState } from 'react';
import { useStore } from '../store/useStore';

export const Register = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();
  const { setAuth } = useStore();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const res = await api.register(values);
      console.log('Register response:', res); // Debug log

      if (res.data.status === 'success' && res.data.access) {
        message.success('注册成功，已自动登录');
        setAuth(res.data.access, res.data.refresh, values.username);
        // Delay navigation slightly to ensure state update? 
        // Usually not needed, but let's try strict ordering.
        setTimeout(() => navigate('/'), 0);
      } else {
        message.success('注册成功，请登录');
        navigate('/login');
      }
    } catch (error) {
      message.error('注册失败，用户名可能已存在');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#f0f2f5' }}>
      <Card title="Trae 金融 - 注册" style={{ width: 350 }} variant="outlined">
        <Form onFinish={onFinish}>
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" />
          </Form.Item>
          <Form.Item 
            name="password" 
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码长度不能少于6位' },
              { pattern: /^(?=.*[a-zA-Z])(?=.*\d).+$/, message: '密码需包含字母和数字' }
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="密码 (至少6位，包含字母数字)" />
          </Form.Item>
          <Form.Item 
            name="confirm" 
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              注册
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center' }}>
            已有账号？<Link to="/login">立即登录</Link>
          </div>
        </Form>
      </Card>
    </div>
  );
};
