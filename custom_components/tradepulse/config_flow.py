from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api.insider import InsiderClient
from .api.price import PriceClient
from .const import (
    CONF_FINNHUB_API_KEY,
    CONF_LANGUAGE,
    CONF_NEWS_COUNT,
    CONF_NEWS_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONF_SYMBOLS,
    DEFAULT_LANGUAGE,
    DEFAULT_NEWS_COUNT,
    DEFAULT_NEWS_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

_SUPPORTED_LANGUAGES = ["en", "it", "de", "fr", "es"]


def _parse_symbols(raw: str) -> list[str]:
    separators = raw.replace("\n", ",").replace(";", ",")
    return list(dict.fromkeys(s.strip().upper() for s in separators.split(",") if s.strip()))


async def _validate_symbols(
    client: PriceClient, tickers: list[str]
) -> tuple[dict[str, dict], list[str]]:
    valid: dict[str, dict] = {}
    invalid: list[str] = []
    for ticker in tickers:
        try:
            meta = await client.validate_symbol(ticker)
            valid[ticker] = meta
        except Exception:
            invalid.append(ticker)
    return valid, invalid


class TradePulseConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw = user_input.get(CONF_SYMBOLS, "")
            tickers = _parse_symbols(raw)

            if not tickers:
                errors[CONF_SYMBOLS] = "no_symbols"
            else:
                client = PriceClient()
                valid, invalid = await _validate_symbols(client, tickers)

                if invalid:
                    errors[CONF_SYMBOLS] = "invalid_symbols"
                    errors["invalid_list"] = ", ".join(invalid)
                elif valid:
                    await self.async_set_unique_id("tradepulse_main")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title="TradePulse",
                        data={CONF_SYMBOLS: valid},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SYMBOLS): TextSelector(
                        TextSelectorConfig(
                            type=TextSelectorType.TEXT,
                            multiline=True,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "invalid_list": errors.get("invalid_list", ""),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> TradePulseOptionsFlow:
        return TradePulseOptionsFlow(config_entry)


class TradePulseOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        return self.async_show_menu(
            step_id="init",
            menu_options=["symbols", "options", "api_keys"],
        )

    async def async_step_symbols(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        current_symbols: dict[str, dict] = (
            self._config_entry.options.get(CONF_SYMBOLS)
            or self._config_entry.data.get(CONF_SYMBOLS, {})
        )
        errors: dict[str, str] = {}

        if user_input is not None:
            updated = dict(current_symbols)

            remove = user_input.get("remove_symbols", [])
            for ticker in remove:
                updated.pop(ticker, None)

            raw_add = user_input.get("add_symbols", "").strip()
            if raw_add:
                new_tickers = _parse_symbols(raw_add)
                client = PriceClient()
                valid, invalid = await _validate_symbols(client, new_tickers)
                if invalid:
                    errors["add_symbols"] = "invalid_symbols"
                    errors["invalid_list"] = ", ".join(invalid)
                else:
                    updated.update(valid)

            if not errors:
                new_options = {**self._config_entry.options, CONF_SYMBOLS: updated}
                return self.async_create_entry(title="", data=new_options)

        current_tickers = list(current_symbols.keys())
        schema = vol.Schema(
            {
                vol.Optional("remove_symbols", default=[]): SelectSelector(
                    SelectSelectorConfig(
                        options=current_tickers,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                    )
                ),
                vol.Optional("add_symbols", default=""): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=True,
                    )
                ),
            }
        )
        return self.async_show_form(
            step_id="symbols",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "invalid_list": errors.get("invalid_list", ""),
            },
        )

    async def async_step_options(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        opts = self._config_entry.options

        if user_input is not None:
            new_options = {
                **opts,
                CONF_NEWS_COUNT: user_input[CONF_NEWS_COUNT],
                CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                CONF_NEWS_INTERVAL: user_input[CONF_NEWS_INTERVAL],
                CONF_LANGUAGE: user_input[CONF_LANGUAGE],
            }
            return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NEWS_COUNT,
                    default=opts.get(CONF_NEWS_COUNT, DEFAULT_NEWS_COUNT),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=50)),
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    CONF_NEWS_INTERVAL,
                    default=opts.get(CONF_NEWS_INTERVAL, DEFAULT_NEWS_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=15, max=120)),
                vol.Optional(
                    CONF_LANGUAGE,
                    default=opts.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=_SUPPORTED_LANGUAGES,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="options", data_schema=schema)

    async def async_step_api_keys(
        self, user_input: dict[str, Any] | None = None
    ) -> dict:
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_key = user_input.get(CONF_FINNHUB_API_KEY, "").strip()
            new_options = {**self._config_entry.options}

            if raw_key:
                session = async_get_clientsession(self.hass)
                client = InsiderClient(session)
                if not await client.validate_finnhub_key(raw_key):
                    errors[CONF_FINNHUB_API_KEY] = "invalid_finnhub_key"
                else:
                    new_options[CONF_FINNHUB_API_KEY] = raw_key
            else:
                new_options.pop(CONF_FINNHUB_API_KEY, None)

            if not errors:
                return self.async_create_entry(title="", data=new_options)

        schema = vol.Schema(
            {
                vol.Optional(CONF_FINNHUB_API_KEY, default=""): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="api_keys",
            data_schema=schema,
            errors=errors,
        )
