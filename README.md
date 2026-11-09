# 影有回声 · AI互动皮影戏台

比赛最终版，整理于2026-11-10。以《狐假虎威》为首个Demo，结合皮影动画、喜庆音乐、屏幕反射结构和有限分支互动。

## 视频与最终交付

- [43秒项目宣传片](https://github.com/xiang010086/shadow-echo-theater-open-source/releases/download/v1.0.0/project-promo.mp4)：正式路演版本，含配音和字幕，舞台展示为设计示意与演出剪辑，并非实机拍摄。
- [2分37秒完整演出](https://github.com/xiang010086/shadow-echo-theater-open-source/releases/download/v1.0.0/full-performance.mp4)：固定路线成片，不识别观众回答。
- [45秒揽客片](https://github.com/xiang010086/shadow-echo-theater-open-source/releases/download/v1.0.0/lure-45s.mp4)。
- [最终路演PPT](presentation/15队-影之回音队.pptx)，含视频和讲者备注；[可编辑网页演讲](presentation/web/index.html)。
- [完整运行资源包](https://github.com/xiang010086/shadow-echo-theater-open-source/releases/download/v1.0.0/shadow-echo-runtime.zip)，包含代码及本地演出素材，不包含密钥、模型或录音。
- [全部发行附件](https://github.com/xiang010086/shadow-echo-theater-open-source/releases/tag/v1.0.0)。

## 现场操作

启动后全屏揽客，**鼠标左键开戏、右键返回揽客**。两处互动可语音回答，也可点击狐狸/老虎、藏好/独自过去；没听清可点击“点击再说一次”。右键会取消当前收音与回应。谢幕后回揽客等待下次点击。

视频、配乐、鼠标分支在本地运行。识别清楚的短选择使用本地Vosk和缓存回应；复杂表达需要自己配置联网理解服务。未配置服务时仍能用鼠标选项完整演示。场景词辅助只对已观测的狐狸误词做保守纠错，不代表任意自由回答可靠。

## 运行

验证平台为DshanPi-A1 / RK3576 / Ubuntu24.04 Armbian厂商镜像，Python3.12，GTK4/WebKit6。其他平台未完整实机验收。源码入口在src/。

1. 使用Python虚拟环境安装src/requirements.txt；Linux图形启动另需系统已有GTK4、WebKit6、Python GI、arecord和pactl。
2. 从[Vosk官方模型页](https://alphacephei.com/vosk/models)下载vosk-model-small-cn-0.22，解压至src/models/vosk-model-small-cn-0.22；模型按自身许可证使用，未打包。
3. 在src目录执行`bash start_dshan.sh`。图形桌面须已登录；HDMI输出与板载ES8388输入按该镜像设置。普通本地页面调试可运行`python runtime.py`后访问127.0.0.1:8765。
4. 如需语音/AI，按[配置说明](docs/配置与验收.md)使用自己的服务密钥。默认不配置任何凭据，不会自动调用付费服务。

没有设置开机自启；实体USER键未接入。项目未实现人体感应自动揽客。

## 目录

- src/：最终运行程序、14段喜庆演出素材、缓存回应和回归测试。
- hardware/：最后一版分块打印设计与重建源码；以其README中的试件和实物验证要求为准。
- presentation/：最终PPT与HTML源稿。
- docs/：产品方案、商业验证、配置和素材署名。

## 验证与实际限制

代码回归与浏览器模拟通过；完整视频已解码核验。用户确认板载麦克风可采集实际人声，但展会环境下自由语音识别仍不稳定，**两处任意自由回答的整场真人验收没有完成**。鼠标点选作为展示兜底。源码里的各阶段视频音量为100%，但最后一次板端100%同步因网络失败未完成，不能据源码声称现场当时已全部调满。

软件按MIT许可开源；第三方音乐、模型及素材按各自条件使用，见[署名与许可](THIRD_PARTY_NOTICES.md)。本仓库不包含比赛Key、个人MiniMax凭据、原始真人录音、浏览器会话或旧私有Git历史。
