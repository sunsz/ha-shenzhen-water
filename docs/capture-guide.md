# 深圳水务抓包说明

本文用于确认 Home Assistant 集成需要填写哪些字段，以及如何在 Charles 里找到它们。

> **注意（2026-11 更新）**：新版「环水管家」小程序把登录拆成了两步——
> 先用 `wx.login` 的 code 调 `GetOpenidV20` 换取 OpenID，再用它调
> `AutomaticLoginV20` 拿 `Utoken`。服务端把第一步建立的验证状态做成短时/一次性标记，
> 被小程序自己消耗掉之后，**仅凭 OpenID 调用 `AutomaticLoginV20` 会被拒绝**，
> 返回 `{"code":1,"message":"不能识别用户i"}`。旧的 `AutomaticLogin`/`V2`/`V10`/`login`
> 端点均已下线。因此单纯填 OpenID 现在通常无法完成首次配置，
> 需要改用下面的「注入会话」方案。

## 需要填写

当前配置表单需要 1 个必填字段：

* OpenId

水务户号、`Utoken`、`GUID` 不需要填写。集成会尝试用 `OpenId` 调用小程序 `AutomaticLoginV20` 自动刷新 `Utoken` 和 `GUID`，再通过 `GetUsersV20` 自动读取已绑定户号。

本次抓包确认：`OpenId` 在登录后的深圳水务请求头和请求体里可以抓到；`GUID` 由 `AutomaticLoginV20` 返回，不再作为配置项。

OpenID 登录被服务端拒绝时，改用下一节的会话文件方式。

## 抓包步骤

1. 打开 Charles，并确保手机或电脑微信流量已经走 Charles 代理。
2. 打开微信小程序“环水管家”。
3. 进入户号或账单页面，触发一次账单查询。
4. 在 Charles 左侧找到域名：

```text
szgk.sz-water.com.cn
```

5. 优先查看下面几个登录后的请求：

```text
/api/wechat/op/user/GetUsersV20
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
```

6. 点开请求后，优先复制：

```text
OpenId
```

注意：登录前的请求里 `OpenId` 和 `Utoken` 可能是空的。要看 `AutomaticLoginV20` 之后的请求，也就是 `GetUsersV20` 或账单接口。

## 户号在哪里

户号不需要手动填写。集成会从 `GetUsersV20` 响应里的用户列表拿 `customerCode`。

如果需要人工核对，也可以从小程序页面直接看，或在 Charles 里找类似请求：

```text
/api/wechat/op/Customer/checkFaceInfoNew/wxxcx/{户号}/{手机号}
```

其中 `{户号}` 就是水务户号。

## 已确认的接口

本次 HAR 确认小程序账单相关接口路径是：

```text
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/BillInfo/GetLatestBillDetailsV30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
/api/wechat/op/user/CustomerInfo/GetCustomerDetailV20
```

当前集成使用：

```text
/api/wechat/op/BillInfo/GetLatestBillDetails2V30
/api/wechat/op/user/billInfo/BillingInfoBycustomerCodesV30
```

这两个路径和抓包一致。

## 已确认的加密方式

小程序 `wxxcx` 渠道的 POST 请求体和响应都是加密字符串，与旧网厅 `wt` 渠道的 AES 密钥常量不同。

本次从 `wx987545bf02573f61` 小程序包确认：

* 请求头 `04A52C9F` 是 32 位大写字母/数字
* AES key 为 `CD3AA097 + 04A52C9F[8:24] + CE92AD77`
* AES 模式为 ECB，填充为 PKCS7
* 响应密文需要做段位交换：`body[:7] + body[20:] + body[7:20]`

如果 Home Assistant 里添加集成时报连接失败，优先检查 `OpenId` 是否取自登录后的请求，以及户号是否是 `GetUsersV20` 返回的 `customerCode`。

## OpenID 登录失效后：注入会话

当 `AutomaticLoginV20` 一直返回「不能识别用户i」时，可以跳过登录，直接注入小程序当前的会话。

### 1. 抓 `Utoken` 和 `GUID`

在 Charles / mitmproxy 里抓一次正常的账单请求（例如 `GetUsersV20`），从**请求头**里取：

```text
Utoken: 00000000-1111-2222-3333-444444444444
```

`GUID` 是稳定的用户 id，不随登录变化，可以从同一个请求的解密请求体里的 `guid` 字段取。

### 2. 写入会话文件

在 Home Assistant 配置目录（`/config`，宿主机通常是 `/root/HomeAssistant`）下新建：

```json
{
  "utoken": "抓到的 Utoken",
  "guid": "抓到的 GUID"
}
```

文件名固定为 `shenzhen_water_auth.json`。建议限制权限：

```bash
chmod 600 /config/shenzhen_water_auth.json
```

### 3. 生效

重载集成或重启 Home Assistant 即可。集成会优先使用这个文件里的会话，不再调用 `AutomaticLoginV20`。

### 4. 已知限制

* 深圳水务同一账号只保留**一个有效会话**。你在微信里重新打开小程序会把这枚 `Utoken` 顶掉，集成随即变成 `unavailable`。
* 会话有效期不确定（实测可达数周）。失效时按上面步骤重新抓一次覆盖文件即可。
* 不要在配置文件里保留 `openid` 之外的任何个人数据，也不要把它提交到版本库。

