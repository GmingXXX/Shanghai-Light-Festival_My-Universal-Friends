/**
 * 文件上传组件
 */
import React, { useState } from 'react';
import { Upload, Button, message } from 'antd';
import { InboxOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { validateFileType, validateFileSize } from '../utils';

const { Dragger } = Upload;

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  loading?: boolean;
  maxFiles?: number;
  maxSizeMB?: number;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  loading = false,
  maxFiles = 10,
  maxSizeMB = 50,
}) => {
  const [fileList, setFileList] = useState<File[]>([]);

  const uploadProps: UploadProps = {
    name: 'files',
    multiple: true,
    accept: '.mp4,.mov,.webm,video/mp4,video/quicktime,video/webm',
    beforeUpload: (file, files) => {
      // 校验文件类型
      if (!validateFileType(file)) {
        message.error(`${file.name} 不是支持的视频格式`);
        return false;
      }

      // 校验文件大小
      if (!validateFileSize(file, maxSizeMB)) {
        message.error(`${file.name} 文件大小超过 ${maxSizeMB}MB 限制`);
        return false;
      }

      // 校验文件数量
      const totalFiles = fileList.length + files.length;
      if (totalFiles > maxFiles) {
        message.error(`最多只能上传 ${maxFiles} 个文件`);
        return false;
      }

      return false; // 阻止自动上传
    },
    onChange: (info) => {
      const { fileList } = info;
      const validFiles = fileList
        .filter(file => file.originFileObj)
        .map(file => file.originFileObj as File);
      
      setFileList(validFiles);
      onFilesSelected(validFiles);
    },
    onDrop: (e) => {
      console.log('Dropped files', e.dataTransfer.files);
    },
    showUploadList: {
      showPreviewIcon: false,
      showRemoveIcon: true,
      showDownloadIcon: false,
    },
  };

  const handleClearAll = () => {
    setFileList([]);
    onFilesSelected([]);
  };

  return (
    <div className="file-upload-container">
      <Dragger {...uploadProps} disabled={loading}>
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽视频文件到此区域上传</p>
        <p className="ant-upload-hint">
          支持 MP4、MOV、WebM 格式，单个文件不超过 {maxSizeMB}MB，最多 {maxFiles} 个文件
        </p>
      </Dragger>
      
      {fileList.length > 0 && (
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Button onClick={handleClearAll} disabled={loading}>
            清空所有文件
          </Button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
