(function(){
  let ffmpeg;
  let ffReady = false;

  async function ensureFFmpeg() {
    if (ffReady) return ffmpeg;
    try {
      // 经典 Worker 通过 importScripts 拉取 UMD 版本；适配 file:// 场景
      self.importScripts('https://cdn.jsdelivr.net/npm/@ffmpeg/ffmpeg@0.12.10/dist/ffmpeg.min.js');
      // UMD 暴露为 self.FFmpeg
      if (!self.FFmpeg || !self.FFmpeg.createFFmpeg) throw new Error('FFmpeg UMD not available');
      const v = '0.12.6';
      const corePath = `https://cdn.jsdelivr.net/npm/@ffmpeg/core@${v}/dist/ffmpeg-core.js`; // 单线程核心，避免 SAB 依赖
      ffmpeg = self.FFmpeg.createFFmpeg({ log: false, corePath });
      await ffmpeg.load();
      ffReady = true;
      return ffmpeg;
    } catch (e) {
      throw e;
    }
  }

  function hexToRgbObj(hex){
    const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return r ? { r: parseInt(r[1],16), g: parseInt(r[2],16), b: parseInt(r[3],16) } : { r:0,g:0,b:0 };
  }

  async function runFFmpegColorKey(inputU8, fileName, settings) {
    const ff = await ensureFFmpeg();
    // 写入输入文件
    ff.FS('writeFile', fileName, inputU8);

    // 颜色键参数（近似）：使用 colorkey 滤镜与 feather 近似软边，容差按 0..1
    const rgb = hexToRgbObj(settings.color || '#000000');
    const tol = Math.min(1, Math.max(0, (settings.tolerance || 50) / 100));
    const feather = Math.max(0, settings.feather || 0); // 0..10（大致），映射到 blur 半径

    // colorkey 使用 YUV 空间阈值，近似用 tol；
    // 软边可叠加 boxblur 在 alpha 上（使用 alphamerge/alphaextract 管线较复杂，这里用 colorkey 提供的软化参数相对简化）
    const targetColor = `0x${rgb.r.toString(16).padStart(2,'0')}${rgb.g.toString(16).padStart(2,'0')}${rgb.b.toString(16).padStart(2,'0')}`;

    // 可选去水印：以 ROI 区域将 alpha 置 0（使用 geq 在 alpha 平面上裁切较复杂，简化为 overlay 透明像素遮罩：使用 colorkey 不便直接裁剪 alpha 区域）
    // 这里先只做背景抠像；水印 ROI 仍由主线程画布方案处理或后续扩展。

    const args = [
      '-i', fileName,
      '-vf', `colorkey=${targetColor}:${tol}:0.1`,
      '-c:v', 'libvpx-vp9',
      '-b:v', '1.8M',
      '-pix_fmt', 'yuva420p',
      '-an',
      'out.webm'
    ];

    // 后台持续：ffmpeg.wasm 在 Worker 执行，不依赖页面可见性
    await ff.run(...args);
    const out = ff.FS('readFile', 'out.webm');
    return out;
  }

  self.onmessage = async function(e){
    const { type, payload } = e.data || {};
    try {
      if (type === 'probe') {
        await ensureFFmpeg();
        self.postMessage({ type: 'probe:ok', payload: { crossOriginIsolated: self.crossOriginIsolated === true } });
        return;
      }
      if (type === 'convert') {
        const { fileBuffer, fileName, settings } = payload;
        const inputU8 = new Uint8Array(fileBuffer);
        const outU8 = await runFFmpegColorKey(inputU8, fileName || 'input.mp4', settings || {});
        // Transferable 返回
        self.postMessage({ type: 'convert:ok', payload: { buffer: outU8.buffer } }, [outU8.buffer]);
        return;
      }
    } catch (err) {
      self.postMessage({ type: 'error', payload: { message: err && err.message ? err.message : String(err) } });
    }
  };
})();


