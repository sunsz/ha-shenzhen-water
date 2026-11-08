# 深圳水务 HA 集成

用于 Home Assistant 的深圳水务自定义集成，按 `ha-shenzhen-gas` 的模式重做：通过微信小程序接口读取水务账单，不再使用短信登录、网厅登录或短期 Ctoken 流程。

## 功能

* 支持 Home Assistant UI 添加集成
* 使用“环水管家”微信小程序抓包得到的 OpenId
* 支持用 OpenId 调用小程序自动登录接口刷新 Utoken/GUID
* 自动读取已绑定水务户号，多个户号时提供选择
* 使用小程序账单接口获取本期账单、用水量、水表读数、缴费状态等信息
* 默认每 6 小时同步一次，避免高频请求
* 保留原深圳水务实体

## 实体

当前会创建以下传感器：

* 账单月份
* 缴费状态
* 到期日
* 本期用水量
* 当前水表读数
* 本期总费用
* 应缴金额
* 自来水费
* 污水处理费
* 垃圾费
* 上期账单月份
* 上期用水量
* 上期总费用

## 安装

通过 HACS 自定义仓库安装：

```text
https://github.com/sunsz/ha-shenzhen-water
```

类型选择：

```text
Integration
```

安装后重启 Home Assistant。

## 配置

1. 打开 Home Assistant
2. 进入“设置” -> “设备与服务”
3. 点击“添加集成”
4. 搜索“深圳水务”
5. 输入从“环水管家”微信小程序抓到的 OpenId
6. 如果这个 OpenId 绑定了多个户号，选择要添加的户号

添加时会请求一次小程序账单接口校验信息是否可用。

## 抓包提示

用 Charles 打开微信小程序“环水管家”，进入账单或户号页面，关注 `szgk.sz-water.com.cn` 下的请求。通常可在登录后的账单请求头里找到：

* `OpenId`

`customercode`、`Utoken`、`GUID` 不需要填写，集成会自动读取或刷新。

详细步骤见 [抓包说明](docs/capture-guide.md)。

## OpenID 登录失效时

新版小程序改成「先用 `wx.login` 的 code 换 OpenID，再登录」之后，服务端不再接受仅凭 OpenID 调用 `AutomaticLoginV20`，会返回 `不能识别用户i`。此时可以跳过登录，直接注入抓到的会话：在配置目录放置 `shenzhen_water_auth.json`

```json
{"utoken": "抓到的 Utoken", "guid": "抓到的 GUID"}
```

然后重载集成即可。注意同一账号只保留一个有效会话——你在微信里重新打开小程序会把这枚 `Utoken` 顶掉，集成会变成 `unavailable` 并留下一条持久通知，重新抓取覆盖该文件就能恢复。详见 [抓包说明](docs/capture-guide.md#openid-登录失效后注入会话)。

## 免责声明

本项目为非官方 Home Assistant 自定义集成，仅用于个人学习和家庭自动化使用。

本项目与深圳水务官方无任何关联。接口可能因官方调整而失效，请勿高频请求。

## License

MIT
