# 心岛漫游设计 QA

## Comparison target

- Source visual truth: `C:\Users\31795\.codex\generated_images\01a022bd-7794-7f20-a859-96ad33344392\exec-6f18324d-0543-41a5-8833-cc69bede5367.png`
- Implementation: `http://127.0.0.1:5175/` 中学生端“探索 → 进入心岛漫游”
- Implementation screenshot: `D:\桌面文件\大学文件\一些比赛\讯飞杯\shengyu-web\design-qa-prototype-final.jpg`
- Mobile implementation screenshot: `D:\桌面文件\大学文件\一些比赛\讯飞杯\shengyu-web\design-qa-mobile.png`
- Combined comparison: `D:\桌面文件\大学文件\一些比赛\讯飞杯\shengyu-web\design-qa-comparison.jpg`
- Viewport: 1366 × 900 CSS px，device scale factor 1；另检查 390 × 844 移动端。
- Source pixels: 1536 × 1024；implementation pixels: 1366 × 900。
- Normalization: comparison preview统一到 720 px 高度，源图约 1080 × 720，实装约 1093 × 720，中间 8 px 分隔；未裁切关键 UI。
- State: 设备本地时间对应白天光景；Agent 轨迹展开，学生与咕团完成二维寻路并到达月光钓鱼湾。

## Full-view comparison evidence

- 实装保留了选定图的第三人称斜俯视岛屿、暖木建筑、陶土屋顶、琥珀光、深靛蓝外壳、学生与宠物同行、右侧 Agent 轨迹和低干扰玻璃界面。
- 因新增“白天 / 傍晚 / 夜晚”要求，实装在顶部显示当前自动光景与适用时段；五个目的地保持同一地图和坐标，不因跨时段更新重置。
- 实装比源图略微拉远，以便同屏保留五个可到达区域和快捷导航。这是可玩性约束下的有意调整，没有改变核心视觉方向。

## Focused-region comparison evidence

- Typography: 使用现有中文系统字体栈；标题、地点标签与 Agent 小字均保持清晰层级，没有溢出或异常换行。
- Spacing and rhythm: 顶部控制、地图、地点导航形成三层稳定结构；地图覆盖层不遮挡主要路径，关闭按钮和 Agent 轨迹保持可见。
- Colors and tokens: 傍晚使用陶土橙与薰衣草暮色，夜晚使用靛蓝与琥珀灯光，白天回到柔和金色日照；控制选中态同时使用文字和高对比底色。
- Image quality: 地图为原创高清像素资产；学生角色与咕团均使用真实位图资产，像素边缘清晰，无占位图、字符画或临时方块。
- Copy: 保留“主动选择、不用解释原因、非诊断”的产品边界；Agent 只展示可核验状态，不展示私有思维链。

## Findings

- 当前没有残留 P0 / P1 / P2 视觉问题。
- [P3] 实装为保证五个地点可达，比源图少一些近景电影感；如后续增加镜头跟随，可在不改变地图坐标的情况下进一步接近源图。
- [P3] 当前 Product Design 参考为桌面图；移动端已实现五地点网格、触控方向键、安全区和折叠 Agent，但本轮没有同源移动端视觉稿可做逐像素比较。
- 本轮端到端测试发现并修复两个真实交互缺陷：角色空闲动画与坐标寻路竞争导致卡在首个路点；到达卡片被地点导航遮挡导致主按钮无法点击。修复后桌面与移动端完整流程均通过。

## Comparison history

1. 初次比较发现旧版方块学生角色与高清场景不一致，且地图上方留白过多（P2）。
2. 修复：生成并接入透明背景学生像素角色；地图改为顶部对齐；地点导航紧接地图；咕团继续跟随角色。
3. 第二次比较曾尝试将地图放大至 118%，导致任务卡和 Agent 轨迹在窄桌面视口被裁切（P2 回归）。
4. 修复：恢复 100% 地图宽度并保留顶部对齐。最终截图确认任务卡、Agent、五个目的地和地点导航均完整可见，页面无横向溢出。

## Primary interactions checked

- 白天、傍晚、夜晚按本地时间解析、跨时段自动更新与无障碍状态播报。
- WASD / 方向键移动、Enter 互动、地点快捷寻路。
- 二维八方向自由移动、障碍物碰撞、A* 绕行，以及从月光钓鱼湾直接进入慢钓台。
- 小田园、慢钓台、幸福交换三种实际玩法；幸福小事可写入、换卡、保存与删除。
- Agent 轨迹展开、Esc 关闭、焦点可见状态。
- 本地页面加载、地图与角色资产加载、版本徽标 `5.1.0-alpha.10`；浏览器交互过程中未出现页面级错误。

## Implementation checklist

- [x] 保持暖色像素主视觉和液态玻璃控制层。
- [x] 同一地图依据本地时间自动进入白天、傍晚、夜晚连续阶段，无手动覆盖入口。
- [x] 学生与咕团真实位图角色进入地图。
- [x] 五个地点、Agent 轨迹、键盘和触控入口完整。
- [x] 五个地点均接入实际功能；移动端显示全部地点与 3×3 八方向控制，不依赖隐藏横向滚动。
- [x] 修复所有 P0 / P1 / P2 并完成二次视觉比较。

final result: passed
