/**
 * 类型定义
 */

// 文件信息
export interface FileInfo {
  fileId: string;
  name: string;
  size: number;
  duration: number;
}

// 任务状态
export type TaskStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED';

// 任务信息
export interface TaskInfo {
  taskId: string;
  status: TaskStatus;
  progress?: number;
  resultUrl?: string;
  errorCode?: string;
  errorMessage?: string;
}

// 转换选项
export interface ConvertOptions {
  color?: string;
  tolerance?: number;
  feather?: number;
  applyToAll?: boolean;
  // 新增：高级边界处理选项
  edgeEnhancement?: boolean;
  edgeThresholdLow?: number;
  edgeThresholdHigh?: number;
  morphologyIterations?: number;
  // 新增：去水印（左上角）
  removeWatermark?: boolean; // 默认 true
  wmX?: number; // 百分比 0-100，默认 1
  wmY?: number; // 百分比 0-100，默认 1
  wmW?: number; // 百分比 0-100，默认 18
  wmH?: number; // 百分比 0-100，默认 8
}

// 文件处理状态
export interface FileProcessingState {
  file: FileInfo;
  taskId?: string;
  status: TaskStatus;
  progress: number;
  resultUrl?: string;
  error?: string;
}

// API 错误响应
export interface ApiError {
  code: string;
  message: string;
}

// API 响应基类
export interface ApiResponse<T = any> {
  data?: T;
  error?: ApiError;
}
