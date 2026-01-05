/**
 * 转换选项组件 - 高级设置
 */
import React from 'react';
import { Card, Form, ColorPicker, Slider, Switch, Space, Typography, Divider, Tooltip } from 'antd';
import { ConvertOptions } from '../types';

const { Text, Title } = Typography;

interface ConvertOptionsProps {
  options: ConvertOptions;
  onChange: (options: ConvertOptions) => void;
  visible?: boolean;
}

const ConvertOptionsComponent: React.FC<ConvertOptionsProps> = ({
  options,
  onChange,
  visible = false,
}) => {
  const handleFieldChange = (field: keyof ConvertOptions, value: any) => {
    onChange({
      ...options,
      [field]: value,
    });
  };

  if (!visible) {
    return null;
  }

  return (
    <Card 
      title="高级设置" 
      size="small" 
      style={{ marginBottom: 16 }}
    >
      <Form layout="vertical" size="small">
        <Form.Item>
          <Space align="center">
            <Switch
              checked={options.removeWatermark !== false}
              onChange={(checked) => handleFieldChange('removeWatermark', checked)}
            />
            <Text>去除左上角水印（默认区域 1%×1%，宽18% 高8%）</Text>
          </Space>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              默认即可。如果想精细调整区域，告诉我我来加调节控件。
            </Text>
          </div>
        </Form.Item>

        <Form.Item label="背景颜色">
          <Space align="center">
            <ColorPicker
              value={options.color || '#000000'}
              onChange={(color) => handleFieldChange('color', color.toHexString())}
              showText
            />
            <Text type="secondary">选择要移除的背景颜色</Text>
          </Space>
        </Form.Item>

        <Form.Item label={`容差: ${options.tolerance || 10}`}>
          <Slider
            min={0}
            max={100}
            value={options.tolerance || 10}
            onChange={(value) => handleFieldChange('tolerance', value)}
            tooltip={{
              formatter: (value) => `${value}%`
            }}
          />
          <Text type="secondary">
            调整颜色匹配的灵敏度，值越大匹配范围越广
          </Text>
        </Form.Item>

        <Form.Item label={`边缘平滑: ${(options.feather || 0.5).toFixed(1)}`}>
          <Slider
            min={0}
            max={10}
            step={0.1}
            value={options.feather || 0.5}
            onChange={(value) => handleFieldChange('feather', value)}
            tooltip={{
              formatter: (value) => value?.toFixed(1)
            }}
          />
          <Text type="secondary">
            调整抠像后边缘的柔化程度，值越大边缘越柔和
          </Text>
        </Form.Item>

        <Form.Item>
          <Switch
            checked={options.applyToAll !== false}
            onChange={(checked) => handleFieldChange('applyToAll', checked)}
          />
          <Text style={{ marginLeft: 8 }}>应用到所有视频</Text>
        </Form.Item>

        <Divider />
        
        <Title level={5} style={{ margin: '0 0 16px 0' }}>
          🎯 边界优化设置
        </Title>
        
        <Form.Item>
          <Space align="center">
            <Switch
              checked={options.edgeEnhancement !== false}
              onChange={(checked) => handleFieldChange('edgeEnhancement', checked)}
            />
            <Text>启用边缘增强处理</Text>
            <Tooltip title="使用边缘检测和自适应阈值处理，显著改善主体边界的黑色残留问题">
              <Text type="secondary" style={{ cursor: 'help' }}>ⓘ</Text>
            </Tooltip>
          </Space>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              推荐开启，特别适用于发光效果、烟雾等复杂边界视频
            </Text>
          </div>
        </Form.Item>

        {options.edgeEnhancement !== false && (
          <>
            <Form.Item label={`边缘检测灵敏度: ${(options.edgeThresholdLow || 0.1).toFixed(2)}`}>
              <Slider
                min={0.05}
                max={0.3}
                step={0.01}
                value={options.edgeThresholdLow || 0.1}
                onChange={(value) => handleFieldChange('edgeThresholdLow', value)}
                tooltip={{
                  formatter: (value) => value?.toFixed(2)
                }}
              />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                调整边缘检测的灵敏度，值越小检测越精细
              </Text>
            </Form.Item>

            <Form.Item label={`边缘强度阈值: ${(options.edgeThresholdHigh || 0.4).toFixed(2)}`}>
              <Slider
                min={0.2}
                max={0.8}
                step={0.05}
                value={options.edgeThresholdHigh || 0.4}
                onChange={(value) => handleFieldChange('edgeThresholdHigh', value)}
                tooltip={{
                  formatter: (value) => value?.toFixed(2)
                }}
              />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                设置强边缘的判定阈值，影响边缘检测的准确性
              </Text>
            </Form.Item>

            <Form.Item label={`形态学处理强度: ${options.morphologyIterations || 1}`}>
              <Slider
                min={0}
                max={3}
                step={1}
                value={options.morphologyIterations || 1}
                onChange={(value) => handleFieldChange('morphologyIterations', value)}
                marks={{
                  0: '关闭',
                  1: '轻度',
                  2: '中度', 
                  3: '强度'
                }}
              />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                去除小的黑色斑点和噪点，值越大处理越强
              </Text>
            </Form.Item>
          </>
        )}

      </Form>
    </Card>
  );
};

export default ConvertOptionsComponent;
