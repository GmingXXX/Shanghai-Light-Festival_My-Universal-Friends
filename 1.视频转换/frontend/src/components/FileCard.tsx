/**
 * 文件卡片组件 - 显示文件信息、处理状态、预览和下载
 */
import React, { useState, useEffect } from 'react';
import { Card, Progress, Button, Tag, Space, Modal } from 'antd';
import { DownloadOutlined, EyeOutlined, DeleteOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { FileProcessingState } from '../types';
import { formatFileSize, formatDuration, getStatusColor, getStatusText, downloadBlob } from '../utils';
import { downloadFile } from '../services/api';

interface FileCardProps {
  file: FileProcessingState;
  onRemove: (fileId: string) => void;
  onDownload?: (fileId: string) => void;
}

const FileCard: React.FC<FileCardProps> = ({ file, onRemove, onDownload }) => {
  const [downloading, setDownloading] = useState(false);
  const [previewVisible, setPreviewVisible] = useState(false);
  const [pendingProgress, setPendingProgress] = useState(0);

  // 为待处理状态添加动画效果
  useEffect(() => {
    if (file.status === 'PENDING') {
      const interval = setInterval(() => {
        setPendingProgress(prev => {
          const next = prev + 2;
          return next > 20 ? 0 : next; // 在0-20%之间循环
        });
      }, 200); // 每200ms更新一次

      return () => clearInterval(interval);
    } else {
      setPendingProgress(0);
    }
  }, [file.status]);

  const handleDownload = async () => {
    if (!file.file.fileId || file.status !== 'SUCCESS') return;

    try {
      setDownloading(true);
      const blob = await downloadFile(file.file.fileId);
      const filename = `${file.file.name.split('.')[0]}_transparent.webm`;
      downloadBlob(blob, filename);
      
      if (onDownload) {
        onDownload(file.file.fileId);
      }
    } catch (error: any) {
      console.error('Download failed:', error);
    } finally {
      setDownloading(false);
    }
  };

  const handlePreview = () => {
    if (file.status === 'SUCCESS' && file.resultUrl) {
      setPreviewVisible(true);
    }
  };

  const renderStatus = () => {
    const color = getStatusColor(file.status);
    const text = getStatusText(file.status);

    // 为待处理和运行中状态显示进度条
    if (file.status === 'PENDING' || file.status === 'RUNNING') {
      const progressPercent = file.status === 'PENDING' ? pendingProgress : file.progress;
      const progressStatus = file.status === 'PENDING' ? 'normal' : 'active';
      
      return (
        <div className={file.status === 'PENDING' ? 'pending-progress' : 'running-progress'}>
          <Progress 
            percent={progressPercent} 
            size="small" 
            status={progressStatus}
            strokeColor={file.status === 'PENDING' ? '#faad14' : '#1890ff'}
            format={(percent) => {
              if (file.status === 'PENDING') {
                return (
                  <span>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {text} - 排队等待中
                  </span>
                );
              }
              return `${text} ${percent}%`;
            }}
          />
        </div>
      );
    }

    // 其他状态显示标签
    return (
      <Tag color={color}>
        {text}
        {file.error && ` - ${file.error}`}
      </Tag>
    );
  };

  const renderActions = () => {
    const actions = [];

    // 预览按钮
    if (file.status === 'SUCCESS' && file.resultUrl) {
      actions.push(
        <Button
          key="preview"
          type="text"
          icon={<EyeOutlined />}
          onClick={handlePreview}
          size="small"
        >
          预览
        </Button>
      );
    }

    // 下载按钮
    if (file.status === 'SUCCESS') {
      actions.push(
        <Button
          key="download"
          type="primary"
          icon={<DownloadOutlined />}
          onClick={handleDownload}
          loading={downloading}
          size="small"
        >
          下载
        </Button>
      );
    }

    // 删除按钮
    actions.push(
      <Button
        key="remove"
        type="text"
        danger
        icon={<DeleteOutlined />}
        onClick={() => onRemove(file.file.fileId)}
        size="small"
      >
        移除
      </Button>
    );

    return actions;
  };

  return (
    <>
      <Card
        size="small"
        title={
          <div style={{ fontSize: '14px', fontWeight: 'normal' }}>
            {file.file.name}
          </div>
        }
        extra={
          <Space size="small">
            {renderActions()}
          </Space>
        }
      >
        <div style={{ marginBottom: 8 }}>
          <Space size="large">
            <span>大小: {formatFileSize(file.file.size)}</span>
            <span>时长: {formatDuration(file.file.duration)}</span>
          </Space>
        </div>
        
        {renderStatus()}
      </Card>

      {/* 预览模态框 */}
      <Modal
        title="预览透明视频"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={[
          <Button key="close" onClick={() => setPreviewVisible(false)}>
            关闭
          </Button>,
          <Button 
            key="download" 
            type="primary" 
            onClick={handleDownload}
            loading={downloading}
          >
            下载
          </Button>,
        ]}
        width={800}
      >
        {file.resultUrl && (
          <div 
            style={{ 
              background: 'url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3QgPDhsqDZubLgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAqSURBVBjTY/z//z8DAwMDAxAzMjKyMDY2NjEwMDAyMjIyMTY2NjEwMDAAGQAJAAE=) repeat',
              padding: '20px',
              textAlign: 'center'
            }}
          >
            <video
              controls
              loop
              style={{ maxWidth: '100%', maxHeight: '400px' }}
              src={file.resultUrl}
            >
              您的浏览器不支持视频播放
            </video>
          </div>
        )}
      </Modal>
    </>
  );
};

export default FileCard;
