import React, { useState, useEffect } from 'react'
import { Layout, Card, Form, Input, Button, Typography, Space, Alert, Divider, Row, Col, Tabs, message, Select, Tag, AutoComplete, Modal, List, Switch, InputNumber } from 'antd'
import { KeyOutlined, SaveOutlined, ApiOutlined, SettingOutlined, InfoCircleOutlined, UserOutlined, RobotOutlined, SyncOutlined, AudioOutlined } from '@ant-design/icons'
import { settingsApi, speechRecognitionApi } from '../services/api'
import BilibiliManager from '../components/BilibiliManager'
import './SettingsPage.css'

const { Content } = Layout
const { Title, Text, Paragraph } = Typography
const { TabPane } = Tabs

const SettingsPage: React.FC = () => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [showBilibiliManager, setShowBilibiliManager] = useState(false)
  const [availableModels, setAvailableModels] = useState<any>({})
  const [currentProvider, setCurrentProvider] = useState<any>({})
  const [selectedProvider, setSelectedProvider] = useState('dashscope')
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelSelectionVisible, setModelSelectionVisible] = useState(false)

  // ASR状态
  const [asrStatus, setAsrStatus] = useState<any>(null)
  const [asrTesting, setAsrTesting] = useState(false)
  const [selectedAsrMethod, setSelectedAsrMethod] = useState('bcut_asr')

  // 提供商配置
  const providerConfig = {
    dashscope: {
      name: '阿里通义千问',
      icon: <RobotOutlined />,
      color: '#1890ff',
      description: '阿里云通义千问大模型服务',
      apiKeyField: 'dashscope_api_key',
      placeholder: '请输入通义千问API密钥'
    },
    openai: {
      name: 'OpenAI',
      icon: <RobotOutlined />,
      color: '#52c41a',
      description: 'OpenAI GPT系列模型',
      apiKeyField: 'openai_api_key',
      placeholder: '请输入OpenAI API密钥'
    },
    gemini: {
      name: 'Google Gemini',
      icon: <RobotOutlined />,
      color: '#faad14',
      description: 'Google Gemini大模型',
      apiKeyField: 'gemini_api_key',
      placeholder: '请输入Gemini API密钥'
    },
    siliconflow: {
      name: '硅基流动',
      icon: <RobotOutlined />,
      color: '#722ed1',
      description: '硅基流动模型服务',
      apiKeyField: 'siliconflow_api_key',
      placeholder: '请输入硅基流动API密钥'
    }
  }

  // 加载数据
  useEffect(() => {
    loadData()
    fetchAsrStatus()
  }, [])

  const fetchAsrStatus = async () => {
    try {
      const status = await speechRecognitionApi.getStatus()
      setAsrStatus(status)
    } catch (error) {
      console.error('获取语音识别状态失败:', error)
      message.error('获取语音识别状态失败')
    }
  }

  const loadData = async () => {
    try {
      const [settings, provider] = await Promise.all([
        settingsApi.getSettings(),
        settingsApi.getCurrentProvider()
      ])
      
      setCurrentProvider(provider)
      setSelectedProvider(settings.llm_provider || 'dashscope')
      setSelectedAsrMethod(settings.asr_method || 'bcut_asr')
      
      // 设置表单初始值
      form.setFieldsValue(settings)
    } catch (error) {
      console.error('加载数据失败:', error)
    }
  }

  const fetchModels = async () => {
    try {
      setModelsLoading(true)
      const models = await settingsApi.getAvailableModels()
      setAvailableModels(models)
      message.success('模型列表刷新成功')
      setModelSelectionVisible(true)
    } catch (error) {
      message.error('获取模型列表失败')
    } finally {
      setModelsLoading(false)
    }
  }

  const handleModelSelect = (modelName: string) => {
    form.setFieldsValue({ model_name: modelName })
    setModelSelectionVisible(false)
  }

  // 保存配置
  const handleSave = async (values: any) => {
    try {
      setLoading(true)
      await settingsApi.updateSettings(values)
      message.success('配置保存成功！')
      await loadData() // 重新加载数据
    } catch (error: any) {
      message.error('保存失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // 测试API密钥
  const handleTestApiKey = async () => {
    const apiKey = form.getFieldValue(providerConfig[selectedProvider as keyof typeof providerConfig].apiKeyField)
    const modelName = form.getFieldValue('model_name')
    const baseUrl = selectedProvider === 'openai' ? form.getFieldValue('openai_base_url') : undefined
    
    if (!apiKey) {
      message.error('请先输入API密钥')
      return
    }

    if (!modelName) {
      message.error('请先选择模型')
      return
    }

    try {
      setLoading(true)
      const result = await settingsApi.testApiKey(selectedProvider, apiKey, modelName, baseUrl)
      if (result.success) {
        message.success('API密钥测试成功！')
      } else {
        message.error('API密钥测试失败: ' + (result.error || '未知错误'))
      }
    } catch (error: any) {
      message.error('测试失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // 测试ASR配置
  const handleAsrTest = async () => {
    try {
      setAsrTesting(true)
      const values = form.getFieldsValue()
      const config = {
        method: values.asr_method,
        language: values.asr_language,
        model: values.asr_model,
        timeout: values.asr_timeout,
        output_format: values.asr_output_format,
        enable_timestamps: values.asr_enable_timestamps,
        enable_punctuation: values.asr_enable_punctuation,
        enable_speaker_diarization: values.asr_enable_speaker_diarization,
        openai_api_key: values.asr_openai_api_key,
        openai_base_url: values.asr_openai_base_url
      }
      
      await speechRecognitionApi.testConfig(config)
      message.success('语音识别配置验证通过')
    } catch (error: any) {
      message.error('配置验证失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      setAsrTesting(false)
    }
  }

  // 提供商切换
  const handleProviderChange = (provider: string) => {
    setSelectedProvider(provider)
    form.setFieldsValue({ llm_provider: provider })
  }

  return (
    <Content className="settings-page">
      <div className="settings-container">
        <Title level={2} className="settings-title">
          <SettingOutlined /> 系统设置
        </Title>
        
        <Tabs defaultActiveKey="api" className="settings-tabs">
          <TabPane tab="AI 模型配置" key="api">
            <Card title="AI 模型配置" className="settings-card">
              <Alert
                message="多模型提供商支持"
                description="系统现在支持多个AI模型提供商，您可以根据需要选择不同的服务商和模型。"
                type="info"
                showIcon
                className="settings-alert"
              />
              
              <Form
                form={form}
                layout="vertical"
                className="settings-form"
                onFinish={handleSave}
                initialValues={{
                  llm_provider: 'dashscope',
                  model_name: 'qwen-plus',
                  chunk_size: 5000,
                  min_score_threshold: 0.7,
                  max_clips_per_collection: 5
                }}
              >
                {/* 当前提供商状态 */}
                {currentProvider.available && (
                  <Alert
                    message={`当前使用: ${currentProvider.display_name} - ${currentProvider.model}`}
                    type="success"
                    showIcon
                    style={{ marginBottom: 24 }}
                  />
                )}

                {/* 提供商选择 */}
                <Form.Item
                  label="选择AI模型提供商"
                  name="llm_provider"
                  className="form-item"
                  rules={[{ required: true, message: '请选择AI模型提供商' }]}
                >
                  <Select
                    value={selectedProvider}
                    onChange={handleProviderChange}
                    className="settings-input"
                    placeholder="请选择AI模型提供商"
                  >
                    {Object.entries(providerConfig).map(([key, config]) => (
                      <Select.Option key={key} value={key}>
                        <Space>
                          <span style={{ color: config.color }}>{config.icon}</span>
                          <span>{config.name}</span>
                          <Tag color={config.color} size="small">{config.description}</Tag>
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                {/* 动态API密钥输入 */}
                <Form.Item
                  label={`${providerConfig[selectedProvider as keyof typeof providerConfig].name} API Key`}
                  name={providerConfig[selectedProvider as keyof typeof providerConfig].apiKeyField}
                  className="form-item"
                  rules={[
                    { required: true, message: '请输入API密钥' },
                    { min: 10, message: 'API密钥长度不能少于10位' }
                  ]}
                >
                  <Input.Password
                    placeholder={providerConfig[selectedProvider as keyof typeof providerConfig].placeholder}
                    prefix={<KeyOutlined />}
                    className="settings-input"
                  />
                </Form.Item>

                {/* OpenAI Base URL 输入 (仅OpenAI显示) */}
                {selectedProvider === 'openai' && (
                  <Form.Item
                    label="OpenAI Base URL (可选)"
                    name="openai_base_url"
                    className="form-item"
                    tooltip="如果您使用自定义的OpenAI接口代理，请在此输入Base URL"
                  >
                    <Input
                      placeholder="例如: https://api.openai-proxy.com/v1"
                      prefix={<ApiOutlined />}
                      className="settings-input"
                    />
                  </Form.Item>
                )}

                {/* 模型选择 */}
                <Form.Item
                  label="选择模型"
                  className="form-item"
                  required
                >
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <Form.Item
                      name="model_name"
                      noStyle
                      rules={[{ required: true, message: '请选择或输入模型' }]}
                    >
                      <AutoComplete
                        className="settings-input"
                        placeholder="请选择或输入模型"
                        style={{ flex: 1 }}
                        options={availableModels[selectedProvider]?.map((model: any) => ({
                          value: model.name,
                          label: (
                            <Space>
                              <span>{model.display_name}</span>
                              <Tag size="small">最大{model.max_tokens} tokens</Tag>
                            </Space>
                          ),
                        }))}
                        filterOption={(inputValue, option) =>
                          option!.value.toUpperCase().indexOf(inputValue.toUpperCase()) !== -1
                        }
                      />
                    </Form.Item>
                    <Button
                      icon={<SyncOutlined />}
                      onClick={fetchModels}
                      loading={modelsLoading}
                    >
                      刷新模型列表
                    </Button>
                  </div>
                </Form.Item>

                {/* 模型选择弹窗 */}
                <Modal
                  title={`选择${providerConfig[selectedProvider as keyof typeof providerConfig]?.name || ''}模型`}
                  open={modelSelectionVisible}
                  onCancel={() => setModelSelectionVisible(false)}
                  footer={null}
                  width={600}
                >
                  <List
                    dataSource={availableModels[selectedProvider] || []}
                    renderItem={(item: any) => (
                      <List.Item
                        className="model-list-item"
                        onClick={() => handleModelSelect(item.name)}
                        style={{ color: '#ffffff', cursor: 'pointer', padding: '12px', borderRadius: '4px', transition: 'background 0.3s' }}
                      >
                        <List.Item.Meta
                          title={
                            <Space>
                              <span>{item.display_name}</span>
                              <Tag color="blue">{item.name}</Tag>
                            </Space>
                          }
                          description={
                            <Space>
                              <Tag>最大上下文: {item.max_tokens}</Tag>
                            </Space>
                          }
                        />
                      </List.Item>
                    )}
                    locale={{ emptyText: '暂无可用模型，请检查API Key或网络连接' }}
                  />
                </Modal>

                <Form.Item className="form-item">
                  <Space>
                    <Button
                      type="default"
                      icon={<ApiOutlined />}
                      className="test-button"
                      onClick={handleTestApiKey}
                      loading={loading}
                    >
                      测试连接
                    </Button>
                  </Space>
                </Form.Item>

                <Divider className="settings-divider" />

                <Title level={4} className="section-title">模型配置</Title>
                
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="模型名称"
                      name="model_name"
                      className="form-item"
                    >
                      <Input placeholder="qwen-plus" className="settings-input" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="文本分块大小"
                      name="chunk_size"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        placeholder="5000" 
                        addonAfter="字符" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="最低评分阈值"
                      name="min_score_threshold"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        step="0.1" 
                        min="0" 
                        max="1" 
                        placeholder="0.7" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="每个合集最大切片数"
                      name="max_clips_per_collection"
                      className="form-item"
                    >
                      <Input 
                        type="number" 
                        placeholder="5" 
                        addonAfter="个" 
                        className="settings-input"
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item className="form-item">
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SaveOutlined />}
                    size="large"
                    className="save-button"
                    loading={loading}
                  >
                    保存配置
                  </Button>
                </Form.Item>
              </Form>
            </Card>

            <Card title="使用说明" className="settings-card">
              <Space direction="vertical" size="large" className="instructions-space">
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 1. 选择AI模型提供商
                  </Title>
                  <Paragraph className="instruction-text">
                    系统支持多个AI模型提供商：
                    <br />• <Text strong>阿里通义千问</Text>：访问阿里云控制台获取API密钥
                    <br />• <Text strong>OpenAI</Text>：访问 platform.openai.com 获取API密钥
                    <br />• <Text strong>Google Gemini</Text>：访问 ai.google.dev 获取API密钥
                    <br />• <Text strong>硅基流动</Text>：访问 docs.siliconflow.cn 获取API密钥
                  </Paragraph>
                </div>
                
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 2. 配置参数说明
                  </Title>
                  <Paragraph className="instruction-text">
                    • <Text strong>文本分块大小</Text>：影响处理速度和精度，建议5000字符<br />
                    • <Text strong>评分阈值</Text>：只有高于此分数的片段才会被保留<br />
                    • <Text strong>合集切片数</Text>：控制每个主题合集包含的片段数量
                  </Paragraph>
                </div>
                
                <div className="instruction-item">
                  <Title level={5} className="instruction-title">
                    <InfoCircleOutlined /> 3. 测试连接
                  </Title>
                  <Paragraph className="instruction-text">
                    保存前建议先测试API密钥是否有效，确保服务正常运行
                  </Paragraph>
                </div>
              </Space>
            </Card>
          </TabPane>

          <TabPane tab="语音识别配置" key="asr">
            <Card title="语音识别配置" className="settings-card">
              <Alert
                message="语音识别服务"
                description="配置语音识别服务，用于将视频中的语音转换为字幕。支持本地Whisper、BcutASR等多种方式。"
                type="info"
                showIcon
                icon={<AudioOutlined />}
                className="settings-alert"
              />
              
              <Form
                form={form}
                layout="vertical"
                className="settings-form"
                onFinish={handleSave}
              >
                {/* 识别方法 */}
                <Form.Item
                  label="语音识别方法"
                  name="asr_method"
                  className="form-item"
                  rules={[{ required: true, message: '请选择语音识别方法' }]}
                >
                  <Select
                    onChange={setSelectedAsrMethod}
                    className="settings-input"
                  >
                    {asrStatus?.available_methods && Object.entries(asrStatus.available_methods).map(([method, available]) => (
                      <Select.Option key={method} value={method} disabled={!available}>
                        {method} {!available && '(未安装)'}
                      </Select.Option>
                    ))}
                  </Select>
                </Form.Item>

                {/* 语言选择 */}
                <Form.Item
                  label="目标语言"
                  name="asr_language"
                  className="form-item"
                >
                  <Select
                    showSearch
                    className="settings-input"
                    options={asrStatus?.supported_languages?.map((lang: string) => ({ label: lang, value: lang }))}
                  />
                </Form.Item>

                {/* Whisper模型 (仅当method为whisper_local时显示) */}
                {selectedAsrMethod === 'whisper_local' && (
                  <Form.Item
                    label="Whisper模型"
                    name="asr_model"
                    className="form-item"
                    tooltip="模型越大准确率越高，但速度越慢"
                  >
                    <Select
                      className="settings-input"
                      options={asrStatus?.whisper_models?.map((model: string) => ({ label: model, value: model }))}
                    />
                  </Form.Item>
                )}

                {/* OpenAI API 配置 (仅当method为openai_api时显示) */}
                {selectedAsrMethod === 'openai_api' && (
                  <>
                    <Form.Item
                      label="OpenAI API Key"
                      name="asr_openai_api_key"
                      className="form-item"
                      rules={[{ required: true, message: '请输入OpenAI API Key' }]}
                    >
                      <Input.Password
                        placeholder="sk-..."
                        prefix={<KeyOutlined />}
                        className="settings-input"
                      />
                    </Form.Item>
                    <Form.Item
                      label="OpenAI Base URL (可选)"
                      name="asr_openai_base_url"
                      className="form-item"
                      tooltip="如果使用代理，请填写Base URL"
                    >
                      <Input
                        placeholder="https://api.openai.com/v1"
                        prefix={<ApiOutlined />}
                        className="settings-input"
                      />
                    </Form.Item>
                    <Form.Item
                      label="OpenAI 模型"
                      name="asr_model"
                      className="form-item"
                      tooltip="默认为 whisper-1"
                    >
                      <Input
                        placeholder="whisper-1"
                        className="settings-input"
                      />
                    </Form.Item>
                  </>
                )}

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      label="超时时间(秒)"
                      name="asr_timeout"
                      className="form-item"
                      tooltip="0表示无限制"
                    >
                      <InputNumber min={0} className="settings-input" style={{ width: '100%' }} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      label="输出格式"
                      name="asr_output_format"
                      className="form-item"
                    >
                      <Select className="settings-input">
                        <Select.Option value="srt">SRT字幕</Select.Option>
                        <Select.Option value="vtt">VTT字幕</Select.Option>
                        <Select.Option value="txt">纯文本</Select.Option>
                        <Select.Option value="json">JSON数据</Select.Option>
                      </Select>
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={8}>
                    <Form.Item
                      label="生成时间戳"
                      name="asr_enable_timestamps"
                      valuePropName="checked"
                      className="form-item"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      label="添加标点符号"
                      name="asr_enable_punctuation"
                      valuePropName="checked"
                      className="form-item"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                  <Col span={8}>
                    <Form.Item
                      label="说话人分离"
                      name="asr_enable_speaker_diarization"
                      valuePropName="checked"
                      className="form-item"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item className="form-item">
                  <Space>
                    <Button
                      type="default"
                      icon={<ApiOutlined />}
                      onClick={handleAsrTest}
                      loading={asrTesting}
                    >
                      测试配置
                    </Button>
                    <Button
                      type="primary"
                      htmlType="submit"
                      icon={<SaveOutlined />}
                      loading={loading}
                    >
                      保存配置
                    </Button>
                  </Space>
                </Form.Item>
              </Form>
            </Card>
          </TabPane>

          <TabPane tab="B站管理" key="bilibili">
            <Card title="B站账号管理" className="settings-card">
              <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                <div style={{ marginBottom: '24px' }}>
                  <UserOutlined style={{ fontSize: '48px', color: '#1890ff', marginBottom: '16px' }} />
                  <Title level={3} style={{ color: '#ffffff', margin: '0 0 8px 0' }}>
                    B站账号管理
                  </Title>
                  <Text type="secondary" style={{ color: '#b0b0b0', fontSize: '16px' }}>
                    管理您的B站账号，支持多账号切换和快速投稿
                  </Text>
                </div>
                
                <Space size="large">
                  <Button
                    type="primary"
                    size="large"
                    icon={<UserOutlined />}
                    onClick={() => message.info('开发中，敬请期待', 3)}
                    style={{
                      borderRadius: '8px',
                      background: 'linear-gradient(45deg, #1890ff, #36cfc9)',
                      border: 'none',
                      fontWeight: 500,
                      height: '48px',
                      padding: '0 32px',
                      fontSize: '16px'
                    }}
                  >
                    管理B站账号
                  </Button>
                </Space>
                
                <div style={{ marginTop: '32px', textAlign: 'left', maxWidth: '600px', margin: '32px auto 0' }}>
                  <Title level={4} style={{ color: '#ffffff', marginBottom: '16px' }}>
                    功能特点
                  </Title>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '16px' }}>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#1890ff' }}>多账号支持</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        支持添加多个B站账号，方便管理和切换
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#52c41a' }}>安全登录</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        使用Cookie导入，避免风控，安全可靠
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#faad14' }}>快速投稿</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        在切片详情页直接选择账号投稿，操作简单
                      </Text>
                    </div>
                    <div style={{ 
                      padding: '16px', 
                      background: 'rgba(255,255,255,0.05)', 
                      borderRadius: '8px',
                      border: '1px solid #404040'
                    }}>
                      <Text strong style={{ color: '#722ed1' }}>批量管理</Text>
                      <br />
                      <Text type="secondary" style={{ color: '#b0b0b0' }}>
                        支持批量上传多个切片，提高效率
                      </Text>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </TabPane>
        </Tabs>

        {/* B站管理弹窗 */}
        <BilibiliManager
          visible={showBilibiliManager}
          onClose={() => setShowBilibiliManager(false)}
          onUploadSuccess={() => {
            message.success('操作成功')
          }}
        />
      </div>
    </Content>
  )
}

export default SettingsPage