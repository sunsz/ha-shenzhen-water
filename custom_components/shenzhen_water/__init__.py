from __future__ import annotations

import json
import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ShenzhenWaterApi
from .const import (
    CONF_CUSTOMER_CODE,
    CONF_OPENID,
    DOMAIN,
    PLATFORMS,
    SESSION_FILE,
)
from .coordinator import ShenzhenWaterCoordinator

_LOGGER = logging.getLogger(__name__)


def _load_session(path: str) -> dict:
    """读取可选的会话文件（同步实现，由 executor 调用）。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh) or {}
    except (OSError, ValueError) as err:
        _LOGGER.warning("读取 %s 失败: %s", SESSION_FILE, err)
        return {}
    return data if isinstance(data, dict) else {}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Shenzhen Water from a config entry."""
    session = async_get_clientsession(hass)

    # 可选：<config>/shenzhen_water_auth.json
    #   {"utoken": "...", "guid": "..."}
    # 新版小程序不再支持纯 OpenID 自动登录，可在登录失效时直接注入抓到的会话。
    auth = await hass.async_add_executor_job(
        _load_session, hass.config.path(SESSION_FILE)
    )

    api = ShenzhenWaterApi(
        session,
        customer_code=entry.data[CONF_CUSTOMER_CODE],
        openid=entry.data.get(CONF_OPENID, ""),
        utoken=str(auth.get("utoken") or ""),
        guid=str(auth.get("guid") or ""),
    )

    coordinator = ShenzhenWaterCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Shenzhen Water config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
