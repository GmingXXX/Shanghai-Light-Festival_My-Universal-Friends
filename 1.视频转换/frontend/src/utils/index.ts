/**
 * 工具函数
 */

/**
 * 格式化文件大小
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/**
 * 格式化时长（秒转为 mm:ss）
 */
export const formatDuration = (seconds: number): string => {
  if (seconds === 0) return '0:00';
  
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

/**
 * 下载 Blob 文件
 */
export const downloadBlob = (blob: Blob, filename: string): void => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

/**
 * 校验文件类型
 */
export const validateFileType = (file: File): boolean => {
  const allowedTypes = ['video/mp4', 'video/quicktime', 'video/webm'];
  return allowedTypes.includes(file.type);
};

/**
 * 校验文件大小（MB）
 */
export const validateFileSize = (file: File, maxSizeMB: number = 50): boolean => {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
};

/**
 * 获取文件扩展名
 */
export const getFileExtension = (filename: string): string => {
  return filename.split('.').pop()?.toLowerCase() || '';
};

/**
 * 生成唯一ID
 */
export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
};

/**
 * 延迟函数
 */
export const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * 获取状态颜色
 */
export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'PENDING':
      return '#faad14';
    case 'RUNNING':
      return '#1890ff';
    case 'SUCCESS':
      return '#52c41a';
    case 'FAILED':
      return '#ff4d4f';
    default:
      return '#d9d9d9';
  }
};

/**
 * 获取状态文本
 */
export const getStatusText = (status: string): string => {
  switch (status) {
    case 'PENDING':
      return '待处理';
    case 'RUNNING':
      return '处理中';
    case 'SUCCESS':
      return '处理完成';
    case 'FAILED':
      return '处理失败';
    default:
      return '未知状态';
  }
};
