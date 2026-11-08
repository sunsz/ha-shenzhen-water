from __future__ import annotations

from datetime import timedelta
import inspect
import logging

from homeassistant.components import persistent_notification
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ShenzhenWaterApi,
    ShenzhenWaterApiError,
    ShenzhenWaterAuthError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

AUTH_NOTIFY_ID = f"{DOMAIN}_auth_expired"

AUTH_FAIL_TITLE = "深圳水务登录凭证失效"
AUTH_FAIL_MSG = (
    "深圳水务的登录凭证已失效，相关实体当前为 unavailable。\n\n"
    "新版小程序不再支持仅凭 OpenID 自动登录。如果已在配置目录放置 "
    "`shenzhen_water_auth.json`，请重新抓包更新其中的 `utoken` 与 `guid`，"
    "然后重载集成或重启 Home Assistant；否则请重新获取 OpenID 并重新添加集成。"
)


class ShenzhenWaterCoordinator(DataUpdateCoordinator):
    """Shenzhen Water data coordinator."""

    def __init__(self, hass, api: ShenzhenWaterApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=360),
        )
        self.api = api

    async def _set_persistent(self, create: bool) -> None:
        """创建/撤销「凭证失效」持久通知。

        同一个 notification_id 天然幂等，反复刷新不会堆积。这里不发手机推送，
        因为首次刷新可能在 HA 启动早期执行，此时 notify.mobile_app_* 尚未注册，
        推送会静默丢失；需要推送的用户可以自行用自动化监听该通知或实体状态。
        """
        try:
            if create:
                result = persistent_notification.async_create(
                    self.hass,
                    AUTH_FAIL_MSG,
                    title=AUTH_FAIL_TITLE,
                    notification_id=AUTH_NOTIFY_ID,
                )
            else:
                result = persistent_notification.async_dismiss(
                    self.hass, AUTH_NOTIFY_ID
                )
            if inspect.isawaitable(result):
                await result
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("操作持久通知失败: %s", err)

    async def _async_update_data(self):
        try:
            data = await self.api.async_get_all()
        except ShenzhenWaterAuthError as err:
            _LOGGER.warning("深圳水务凭证失效: %s", err)
            await self._set_persistent(True)
            raise UpdateFailed(str(err)) from err
        except ShenzhenWaterApiError as err:
            raise UpdateFailed(str(err)) from err

        await self._set_persistent(False)
        return data

    @property
    def bill(self) -> dict:
        data = self.data or {}
        current = data.get("current") or {}
        rows = current.get("data") or []
        if not rows:
            return {}
        return rows[0]

    @property
    def meter(self) -> dict:
        meters = self.bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]

    @property
    def previous_bill(self) -> dict:
        data = self.data or {}
        previous = data.get("previous") or {}
        rows = previous.get("data") or []
        if not rows:
            return {}
        return rows[0]

    @property
    def previous_meter(self) -> dict:
        meters = self.previous_bill.get("meterWaterUses") or []
        if not meters:
            return {}
        return meters[0]
