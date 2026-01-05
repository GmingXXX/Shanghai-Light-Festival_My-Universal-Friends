/**
 * 前端性能优化工具
 */

// 防抖函数
export const debounce = <T extends (...args: any[]) => any>(
  func: T,
  wait: number
): ((...args: Parameters<T>) => void) => {
  let timeout: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(null, args), wait);
  };
};

// 节流函数
export const throttle = <T extends (...args: any[]) => any>(
  func: T,
  limit: number
): ((...args: Parameters<T>) => void) => {
  let inThrottle: boolean;
  
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func.apply(null, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
};

// 性能监控
export class PerformanceMonitor {
  private metrics: Map<string, number[]> = new Map();

  // 记录性能指标
  recordMetric(name: string, value: number): void {
    if (!this.metrics.has(name)) {
      this.metrics.set(name, []);
    }
    
    const values = this.metrics.get(name)!;
    values.push(value);
    
    // 只保留最近100个数据点
    if (values.length > 100) {
      values.shift();
    }
    
    console.log(`Performance: ${name} = ${value}ms`);
  }

  // 获取平均值
  getAverage(name: string): number {
    const values = this.metrics.get(name) || [];
    if (values.length === 0) return 0;
    
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }

  // 获取百分位数
  getPercentile(name: string, percentile: number = 95): number {
    const values = this.metrics.get(name) || [];
    if (values.length === 0) return 0;
    
    const sorted = [...values].sort((a, b) => a - b);
    const index = Math.ceil((percentile / 100) * sorted.length) - 1;
    return sorted[Math.max(0, index)];
  }

  // 清除指标
  clearMetrics(name?: string): void {
    if (name) {
      this.metrics.delete(name);
    } else {
      this.metrics.clear();
    }
  }
}

// 全局性能监控器
export const performanceMonitor = new PerformanceMonitor();

// 性能监控装饰器
export const monitorPerformance = (metricName: string) => {
  return (target: any, propertyKey: string, descriptor: PropertyDescriptor) => {
    const originalMethod = descriptor.value;
    
    descriptor.value = async function (...args: any[]) {
      const startTime = performance.now();
      
      try {
        const result = await originalMethod.apply(this, args);
        const duration = performance.now() - startTime;
        performanceMonitor.recordMetric(metricName, duration);
        return result;
      } catch (error) {
        const duration = performance.now() - startTime;
        performanceMonitor.recordMetric(`${metricName}_error`, duration);
        throw error;
      }
    };
    
    return descriptor;
  };
};

// 图片懒加载
export const lazyLoadImage = (img: HTMLImageElement, src: string): void => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        img.src = src;
        observer.unobserve(img);
      }
    });
  });
  
  observer.observe(img);
};

// 虚拟滚动帮助函数
export const calculateVisibleItems = (
  containerHeight: number,
  itemHeight: number,
  scrollTop: number,
  totalItems: number,
  overscan: number = 5
) => {
  const visibleStart = Math.floor(scrollTop / itemHeight);
  const visibleEnd = Math.min(
    visibleStart + Math.ceil(containerHeight / itemHeight),
    totalItems - 1
  );
  
  return {
    startIndex: Math.max(0, visibleStart - overscan),
    endIndex: Math.min(totalItems - 1, visibleEnd + overscan),
    offsetY: Math.max(0, visibleStart - overscan) * itemHeight
  };
};

// 内存使用监控
export const monitorMemoryUsage = (): void => {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    
    console.log('Memory Usage:', {
      used: `${Math.round(memory.usedJSHeapSize / 1024 / 1024)}MB`,
      total: `${Math.round(memory.totalJSHeapSize / 1024 / 1024)}MB`,
      limit: `${Math.round(memory.jsHeapSizeLimit / 1024 / 1024)}MB`
    });
  }
};

// 网络状态监控
export const getNetworkInfo = (): any => {
  if ('connection' in navigator) {
    const connection = (navigator as any).connection;
    
    return {
      effectiveType: connection.effectiveType,
      downlink: connection.downlink,
      rtt: connection.rtt,
      saveData: connection.saveData
    };
  }
  
  return null;
};

// 预加载资源
export const preloadResource = (url: string, type: 'script' | 'style' | 'image' = 'image'): Promise<void> => {
  return new Promise((resolve, reject) => {
    let element: HTMLElement;
    
    switch (type) {
      case 'script':
        element = document.createElement('script');
        (element as HTMLScriptElement).src = url;
        break;
      case 'style':
        element = document.createElement('link');
        (element as HTMLLinkElement).rel = 'stylesheet';
        (element as HTMLLinkElement).href = url;
        break;
      case 'image':
      default:
        element = document.createElement('img');
        (element as HTMLImageElement).src = url;
        break;
    }
    
    element.onload = () => resolve();
    element.onerror = () => reject(new Error(`Failed to preload ${url}`));
    
    // 对于样式表和脚本，需要添加到DOM中
    if (type === 'script' || type === 'style') {
      document.head.appendChild(element);
    }
  });
};

// 批量操作优化
export const batchOperations = <T>(
  items: T[],
  operation: (batch: T[]) => Promise<void>,
  batchSize: number = 10
): Promise<void[]> => {
  const batches: T[][] = [];
  
  for (let i = 0; i < items.length; i += batchSize) {
    batches.push(items.slice(i, i + batchSize));
  }
  
  return Promise.all(batches.map(batch => operation(batch)));
};

// Web Worker 帮助函数
export const createWorker = (workerFunction: Function): Worker => {
  const blob = new Blob([`(${workerFunction.toString()})()`], {
    type: 'application/javascript'
  });
  
  return new Worker(URL.createObjectURL(blob));
};

// 检测浏览器性能
export const getBrowserPerformance = () => {
  const timing = performance.timing;
  
  return {
    pageLoadTime: timing.loadEventEnd - timing.navigationStart,
    domReadyTime: timing.domContentLoadedEventEnd - timing.navigationStart,
    firstPaintTime: performance.getEntriesByType('paint')[0]?.startTime || 0,
    resourceLoadTime: timing.loadEventStart - timing.domContentLoadedEventEnd
  };
};
