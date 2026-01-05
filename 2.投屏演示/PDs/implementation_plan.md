# 项目开发方案：多视频海洋生物动态壁纸

这是一份旨在开发一个高性能、纯前端、支持多视频同时播放的动态网页壁纸的开发方案。该方案将实现一个允许用户上传透明背景视频（如海洋生物），并在一个动态的海洋背景上自由漂浮的效果。最终交付物将是一个无需任何环境配置的单一HTML文件。

#### **1. 核心技术选型**

为了在不依赖任何后端或复杂环境配置的情况下，实现高性能的动态效果，我们将采用以下纯前端技术：

*   **HTML5 Canvas API**: 这是本方案的核心。直接在DOM中操作80个以上的`<video>`标签会造成极其严重的性能问题。使用`<canvas>`，我们可以将每个视频的当前帧“绘制”到画布上。这样做的好处是，浏览器只需要渲染一个`<canvas>`元素，而不是80多个独立的视频元素，从而极大地提升了渲染效率和流畅度，这是实现您需求的关键。
*   **JavaScript (ES6+)**: 用于处理所有动态逻辑，包括：
    *   视频对象的物理状态（位置、速度）。
    *   动画循环的实现 (`requestAnimationFrame`)。
    *   边界碰撞检测。
    *   文件拖拽上传和处理。
*   **HTML5 & CSS3**:
    *   使用HTML5的`<video>`标签作为背景。
    *   使用CSS3来布局页面，确保背景视频和Canvas画布能够全屏显示且层级正确。
    *   使用HTML5的File API和Drag and Drop API来处理文件上传。

#### **2. 开发步骤详解**

我们将把整个项目分解为以下几个清晰的步骤：

##### **第一步：搭建基础HTML结构**

这是网页的骨架，非常简洁。我们将所有代码都内联到一个HTML文件中。

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>海洋生物动态壁纸</title>
    <!-- CSS样式将写在这里 -->
</head>
<body>
    <!-- 1. 背景视频 -->
    <video id="background-video" autoplay loop muted src="background/UNIVERSE.mp4"></video>

    <!-- 2. 核心画布，所有海洋生物将在这里绘制 -->
    <canvas id="creature-canvas"></canvas>
    
    <!-- 3. 文件上传的入口 (一个隐藏的input，通过JS触发) -->
    <input type="file" id="video-uploader" multiple accept=".webm" style="display: none;">
    
    <!-- 4. 一个可点击的小按钮，或者整个页面作为拖拽区域 -->
    <div id="upload-button" title="点击或拖拽文件到此处添加海洋生物">+</div>

    <!-- JavaScript逻辑将写在这里 -->
</body>
</html>
```
*注意：为实现单文件交付，`src="background/UNIVERSE.mp4"` 需要被转换为Base64编码或要求用户将其放置在同一目录下。最简单的方案是假设文件在相对路径下。*

##### **第二步：设计CSS样式**

我们需要让背景视频和Canvas画布都铺满整个屏幕，并且层级关系正确。

*   将`<body>`的`margin`和`padding`设为0。
*   将背景视频`<video>`设置为`position: fixed`，`z-index: -1`，并使用`object-fit: cover`来保证它全屏且不变形。
*   将`<canvas>`设置为`position: absolute`，`top: 0`, `left: 0`，使其覆盖在背景视频之上。
*   设计一个非常小且不显眼的上传按钮样式，放置在角落。

##### **第三步：实现核心JavaScript逻辑**

这是整个项目的灵魂，我们将在这里实现所有动态效果。

1.  **初始化**:
    *   获取`<canvas>`元素和它的2D渲染上下文(`getContext('2d')`)。
    *   设置画布大小与浏览器窗口大小一致，并监听窗口尺寸变化以自适应调整。
    *   创建一个数组，例如`let creatures = []`，用来存储所有海洋生物（视频）对象。

2.  **创建“海洋生物”对象**:
    *   每当一个视频文件被加载，我们就创建一个JavaScript对象来代表它。这个对象需要包含以下属性：
        *   `videoElement`: 在内存中创建的`<video>`元素，用于播放视频。
        *   `x`, `y`: 在画布上的当前位置。
        *   `dx`, `dy`: 水平和垂直方向的移动速度（非常小的值，以实现缓慢漂浮）。
        *   `width`, `height`: 视频的尺寸。

3.  **文件处理（拖拽与点击上传）**:
    *   为整个`<body>`或`upload-button`添加`dragover`和`drop`事件监听器，以实现文件拖入功能。
    *   在`drop`事件的回调函数中，读取拖入的`.webm`文件。
    *   为`upload-button`添加`click`事件，触发隐藏的`<input type="file">`的点击事件。
    *   无论是拖拽还是点击，获取到文件后，使用`URL.createObjectURL(file)`为每个文件创建一个临时的URL。
    *   对于每个URL，在内存中`new Video()`创建一个视频元素，设置其`src`为该URL，并配置`autoplay`, `loop`, `muted`属性。
    *   视频加载后，创建一个上述的“海洋生物”对象，为其赋予随机的初始位置(`x`, `y`)和随机的初始速度(`dx`, `dy`)，然后将其`push`到`creatures`数组中。

4.  **实现动画循环**:
    *   我们将使用`requestAnimationFrame(update)`来创建主循环函数`update()`。这是现代浏览器中最高效的动画实现方式。
    *   在`update`函数中，每一帧都执行以下操作：
        a. **清空画布**: `ctx.clearRect(0, 0, canvas.width, canvas.height)`。
        b. **遍历并更新**: 遍历`creatures`数组中的每一个生物对象。
        c. **更新位置**: `creature.x += creature.dx; creature.y += creature.dy;`
        d. **边界碰撞检测**:
           *   如果`creature.x < 0`或`creature.x + creature.width > canvas.width`，则将其水平速度反向：`creature.dx *= -1;`
           *   如果`creature.y < 0`或`creature.y + creature.height > canvas.height`，则将其垂直速度反向：`creature.dy *= -1;`
        e. **绘制视频帧**: 使用`ctx.drawImage(creature.videoElement, creature.x, creature.y, creature.width, creature.height)`将该生物视频的当前帧绘制到画布上的新位置。
        f. **循环调用**: 在`update`函数的末尾再次调用`requestAnimationFrame(update)`，形成无限循环。

#### **3. 性能优化与注意事项**

*   **视频文件要求**: 您的视频文件必须是带有Alpha通道（透明背景）的`.webm`格式。同时，为了性能，视频的分辨率不宜过大，比特率也应适当压缩。
*   **音频静音**: 所有动态加载的视频必须设置为`muted`（静音）。解码音频会消耗额外的CPU资源。
*   **跨域问题**: 如果在本地直接打开HTML文件，浏览器可能会有安全限制。最好的测试方式是使用一个简单的本地服务器（如VS Code的`Live Server`插件）。但最终交付的单HTML文件，由于所有资源都是用户本地提供，理论上不会有跨域问题。
*   **视频间碰撞**：按照您的要求，视频间相互穿过，无需实现复杂的碰撞检测，这大大降低了计算的复杂度。

#### **4. 实时文件夹监听功能**

为了实现自动监听video文件夹并即时显示新视频的功能，我们添加了以下特性：

*   **智能文件扫描**: 系统每3秒自动扫描video文件夹，检测新增的webm视频文件
*   **文件去重机制**: 通过维护已知文件列表，避免重复加载相同视频
*   **动态文件名识别**: 支持多种命名模式的视频文件，包括：
    *   原有格式：`001 (X)_transparent.webm`
    *   新增格式：`creature_X.webm`, `marine_X.webm`, `new_creature_X.webm`
*   **性能优化**: 
    *   使用短超时检测（1.5秒）提高响应速度
    *   记录不存在的文件，避免重复检查
    *   异步并行检查多个文件
*   **用户控制**: 
    *   按M键可开启/关闭文件夹监听功能
    *   实时状态显示在信息面板中
    *   新视频发现时显示通知动画

**使用方法**：
1. 将新的webm视频文件放入video文件夹
2. 系统会在3秒内自动检测并加载新视频
3. 新海洋生物会立即出现在屏幕上开始游动
4. 支持热插拔，无需重启应用

#### **5. 最终交付物**

根据您的第8点要求，我会将上述所有的HTML结构、CSS样式和JavaScript逻辑全部整合到一个`index.html`文件中。您只需要获得这一个文件，用任意现代浏览器（如Chrome, Firefox, Edge）打开，即可直接使用，无需安装任何依赖或进行任何配置。

新增的实时监听功能完全基于前端技术实现，无需任何服务器或后端支持。

#### **6. 兼容性和故障排除**

**协议检测和自适应**：
*   **FILE协议模式**（直接双击HTML文件）：
    *   自动检测并启用兼容模式
    *   降低扫描频率（每5秒）和批次大小，避免浏览器限制
    *   使用更宽松的文件检测策略
    *   显示协议相关使用提示
*   **HTTP协议模式**（通过服务器访问）：
    *   使用标准高效的检测机制
    *   更高的扫描频率（每3秒）和更大的批次处理

**故障排除方案**：
1. **如果自动检测不工作**：
   - 按 **F** 键手动刷新文件夹检测
   - 按 **A** 键手动输入文件名加载
   - 检查浏览器控制台的详细日志

2. **推荐的文件命名**：
   - `test_1.webm`, `test_2.webm`...
   - `creature_1.webm`, `creature_2.webm`...
   - `marine_1.webm`, `fish_1.webm`...
   - 支持数字编号1-20的所有常见模式

3. **浏览器兼容性**：
   - Chrome/Edge：完全支持
   - Firefox：完全支持
   - Safari：基本支持（可能需要手动操作）

**调试信息**：
打开浏览器开发者工具（F12）→ Console标签，可以看到详细的检测日志：
- `🔍 检测到FILE协议，启用兼容模式`
- `✓ [FILE协议] 发现新视频文件: filename.webm`
- `✗ [FILE协议] 文件不存在: filename.webm`
