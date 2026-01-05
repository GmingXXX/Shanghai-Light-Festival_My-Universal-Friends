/**
 * 主应用组件
 */
import React, { useState, useEffect } from 'react';
import { Layout, Typography, Button, Space, message, Divider } from 'antd';
import { SettingOutlined, PlayCircleOutlined, DownloadOutlined, ClearOutlined } from '@ant-design/icons';
import FileUpload from './components/FileUpload';
import FileCard from './components/FileCard';
import ConvertOptions from './components/ConvertOptions';
import { FileInfo, ConvertOptions as ConvertOptionsType, FileProcessingState, TaskInfo } from './types';
import { uploadFiles, convertFiles, getTaskStatus, batchDownload } from './services/api';
import { downloadBlob, delay } from './utils';
import './App.css';

const { Header, Content, Footer } = Layout;
const { Title, Paragraph } = Typography;

const App: React.FC = () => {
  const [files, setFiles] = useState<FileProcessingState[]>([]);
  const [uploading, setUploading] = useState(false);
  const [converting, setConverting] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [convertOptions, setConvertOptions] = useState<ConvertOptionsType>({
    color: '#000000',
    tolerance: 10,
    feather: 0.5,
    applyToAll: true,
    removeWatermark: true,
    wmX: 1.2,
    wmY: 1.2,
    wmW: 14.0,
    wmH: 5.5,
  });

  // 轮询任务状态
  useEffect(() => {
    // 检查是否有正在运行的任务
    const hasRunningTasks = files.some(f => f.status === 'RUNNING' || f.status === 'PENDING');
    
    if (hasRunningTasks) {
      // 有运行中的任务时，增加轮询频率
      const interval = setInterval(() => {
        pollTaskStatus();
      }, 1000); // 每1秒轮询一次

      return () => clearInterval(interval);
    } else {
      // 没有运行中的任务时，减少轮询频率
      const interval = setInterval(() => {
        pollTaskStatus();
      }, 5000); // 每5秒轮询一次

      return () => clearInterval(interval);
    }
  }, [files]);

  const pollTaskStatus = async () => {
    const activeTasks = files.filter(f => f.taskId && (f.status === 'RUNNING' || f.status === 'PENDING'));
    
    if (activeTasks.length === 0) return;

    try {
      const statusPromises = activeTasks.map(f => getTaskStatus(f.taskId!));
      const statusResults = await Promise.all(statusPromises);

      setFiles(prevFiles => 
        prevFiles.map(file => {
          const statusResult = statusResults.find(s => s.taskId === file.taskId);
          if (statusResult) {
            return {
              ...file,
              status: statusResult.status,
              progress: statusResult.progress || file.progress,
              resultUrl: statusResult.resultUrl || file.resultUrl,
              error: statusResult.errorMessage || file.error,
            };
          }
          return file;
        })
      );
    } catch (error) {
      console.error('轮询任务状态失败:', error);
    }
  };

  const handleFilesSelected = async (selectedFiles: File[]) => {
    if (selectedFiles.length === 0) {
      setFiles([]);
      return;
    }

    try {
      setUploading(true);
      message.loading('正在上传文件...', 0);

      const uploadedFiles = await uploadFiles(selectedFiles);
      
      const newFiles: FileProcessingState[] = uploadedFiles.map(file => ({
        file,
        status: 'PENDING',
        progress: 0,
      }));

      setFiles(newFiles);
      message.destroy();
      message.success(`成功上传 ${uploadedFiles.length} 个文件`);
    } catch (error: any) {
      message.destroy();
      message.error(error.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleStartConvert = async () => {
    const fileIds = files.map(f => f.file.fileId);
    
    if (fileIds.length === 0) {
      message.warning('请先上传视频文件');
      return;
    }

    try {
      setConverting(true);
      message.loading('正在启动转换任务...', 0);

      const taskIds = await convertFiles(fileIds, convertOptions);

      // 更新文件状态
      setFiles(prevFiles => 
        prevFiles.map((file, index) => ({
          ...file,
          taskId: taskIds[index],
          status: 'RUNNING',
          progress: 0,
        }))
      );

      message.destroy();
      message.success('转换任务已启动');
    } catch (error: any) {
      message.destroy();
      message.error(error.message || '启动转换失败');
    } finally {
      setConverting(false);
    }
  };

  const handleBatchDownload = async () => {
    const successfulTasks = files
      .filter(f => f.status === 'SUCCESS' && f.taskId)
      .map(f => f.taskId!);

    if (successfulTasks.length === 0) {
      message.warning('没有可下载的文件');
      return;
    }

    try {
      message.loading('正在打包下载...', 0);
      const blob = await batchDownload(successfulTasks);
      downloadBlob(blob, 'transparent_videos.zip');
      message.destroy();
      message.success('下载完成');
    } catch (error: any) {
      message.destroy();
      message.error('批量下载失败');
    }
  };

  const handleRemoveFile = (fileId: string) => {
    setFiles(prevFiles => prevFiles.filter(f => f.file.fileId !== fileId));
  };

  const handleClearAll = () => {
    setFiles([]);
  };

  const canStartConvert = files.length > 0 && !converting && !files.some(f => f.status === 'RUNNING');
  const hasSuccessfulFiles = files.some(f => f.status === 'SUCCESS');

  return (
    <Layout className="app-layout">
      <Header className="app-header">
        <div className="header-content">
          <Title level={2} style={{ color: 'white', margin: 0 }}>
            透明视频转换器
          </Title>
          <Paragraph style={{ color: 'rgba(255,255,255,0.8)', margin: 0 }}>
            将黑底视频一键转为透明背景，支持批量处理
          </Paragraph>
        </div>
      </Header>

      <Content className="app-content">
        <div className="content-container">
          {/* 上传区域 */}
          <FileUpload
            onFilesSelected={handleFilesSelected}
            loading={uploading}
            maxFiles={10}
            maxSizeMB={50}
          />

          {files.length > 0 && (
            <>
              <Divider />
              
              {/* 操作按钮 */}
              <div className="action-buttons">
                <Space size="middle">
                  <Button
                    icon={<SettingOutlined />}
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    {showAdvanced ? '隐藏' : '显示'}高级设置
                  </Button>
                  
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleStartConvert}
                    loading={converting}
                    disabled={!canStartConvert}
                    size="large"
                  >
                    开始转换
                  </Button>

                  {hasSuccessfulFiles && (
                    <Button
                      icon={<DownloadOutlined />}
                      onClick={handleBatchDownload}
                    >
                      全部下载
                    </Button>
                  )}

                  <Button
                    icon={<ClearOutlined />}
                    onClick={handleClearAll}
                    danger
                  >
                    全部清除
                  </Button>
                </Space>
              </div>

              {/* 高级设置 */}
              <ConvertOptions
                options={convertOptions}
                onChange={setConvertOptions}
                visible={showAdvanced}
              />

              {/* 文件列表 */}
              <div className="file-list">
                {files.map(file => (
                  <FileCard
                    key={file.file.fileId}
                    file={file}
                    onRemove={handleRemoveFile}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      </Content>

      <Footer className="app-footer">
        <div style={{ textAlign: 'center' }}>
          <Paragraph type="secondary" style={{ margin: 0 }}>
            © 2025 透明视频转换器 - 上传的文件将在24小时后自动删除
          </Paragraph>
        </div>
      </Footer>
    </Layout>
  );
};

export default App;
