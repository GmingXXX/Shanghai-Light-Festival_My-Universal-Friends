"""
Flask 应用主文件
"""
import os
from flask import Flask
from flask_cors import CORS

from .config import Config
from .api.routes import api_bp
from .utils.logger import setup_logger

logger = setup_logger()


def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(Config)
    
    # 配置上传文件大小限制
    app.config['MAX_CONTENT_LENGTH'] = Config.MAX_FILE_SIZE_MB * 1024 * 1024 * Config.MAX_FILES_PER_BATCH
    
    # 配置 CORS
    CORS(app, origins=Config.CORS_ORIGINS.split(',') if Config.CORS_ORIGINS != '*' else '*')
    
    # 注册蓝图
    app.register_blueprint(api_bp)
    
    # 创建存储目录（本地存储）
    if Config.STORAGE_PROVIDER == 'local':
        os.makedirs(Config.LOCAL_STORAGE_ROOT, exist_ok=True)
        logger.info("Local storage directory created", path=Config.LOCAL_STORAGE_ROOT)
    
    logger.info("Flask app created", 
                debug=app.debug, 
                storage_provider=Config.STORAGE_PROVIDER)
    
    return app


def main():
    """主函数 - 开发服务器入口"""
    app = create_app()
    
    # 开发环境下运行
    if Config.DEBUG:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 8000)),
            debug=True
        )
    else:
        logger.warning("Use a WSGI server for production deployment")


if __name__ == '__main__':
    main()
