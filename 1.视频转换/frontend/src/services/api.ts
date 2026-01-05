/**
 * API 服务 - 与后端通信
 */
import axios, { AxiosResponse } from 'axios';
import { FileInfo, TaskInfo, ConvertOptions, ApiResponse } from '../types';

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * 上传文件
 */
export const uploadFiles = async (files: File[]): Promise<FileInfo[]> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  try {
    const response: AxiosResponse<FileInfo[]> = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.error) {
      throw new Error(error.response.data.error.message);
    }
    throw new Error('上传失败，请重试');
  }
};

/**
 * 开始转换
 */
export const convertFiles = async (
  fileIds: string[],
  options?: ConvertOptions
): Promise<string[]> => {
  try {
    const response: AxiosResponse<{ taskIds: string[] }> = await api.post('/convert', {
      files: fileIds,
      options: options || {},
    });
    return response.data.taskIds;
  } catch (error: any) {
    if (error.response?.data?.error) {
      throw new Error(error.response.data.error.message);
    }
    throw new Error('启动转换失败，请重试');
  }
};

/**
 * 获取任务状态
 */
export const getTaskStatus = async (taskId: string): Promise<TaskInfo> => {
  try {
    const response: AxiosResponse<TaskInfo> = await api.get(`/status?taskId=${taskId}`);
    return response.data;
  } catch (error: any) {
    if (error.response?.data?.error) {
      throw new Error(error.response.data.error.message);
    }
    throw new Error('获取任务状态失败');
  }
};

/**
 * 下载单个文件
 */
export const downloadFile = async (fileId: string): Promise<Blob> => {
  try {
    const response: AxiosResponse<Blob> = await api.get(`/download?fileId=${fileId}`, {
      responseType: 'blob',
    });
    return response.data;
  } catch (error: any) {
    throw new Error('下载文件失败');
  }
};

/**
 * 批量下载文件
 */
export const batchDownload = async (taskIds: string[]): Promise<Blob> => {
  try {
    const response: AxiosResponse<Blob> = await api.post('/batch-download', 
      { taskIds },
      { responseType: 'blob' }
    );
    return response.data;
  } catch (error: any) {
    throw new Error('批量下载失败');
  }
};

/**
 * 健康检查
 */
export const healthCheck = async (): Promise<any> => {
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    throw new Error('服务不可用');
  }
};
