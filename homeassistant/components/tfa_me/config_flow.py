"""TFA.me station integration: config_flow.py."""

import logging
from typing import Any, override

from tfa_me_ha_local.client import (
    TFAmeClient,
    TFAmeConnectionError,
    TFAmeException,
    TFAmeHTTPError,
    TFAmeJSONError,
    TFAmeTimeoutError,
)
from tfa_me_ha_local.validators import TFAmeValidator
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_IP_ADDRESS
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_STATION_NAME, DOMAIN
from .helper import resolve_tfa_host

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_ADDRESS, default=""): str,
    }
)


class TFAmeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for TFA.me."""

    VERSION = 1
    MINOR_VERSION = 1

    @override
    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_IP_ADDRESS]
            validator = TFAmeValidator()

            if not validator.is_valid_ip_or_tfa_me(address):
                errors[CONF_IP_ADDRESS] = "invalid_ip_host"
            else:
                host = resolve_tfa_host(address)
                session = async_get_clientsession(self.hass)
                client = TFAmeClient(
                    host,
                    "sensors",
                    log_level=1,
                    session=session,
                )

                try:
                    json_data = await client.async_get_sensors()
                except TFAmeTimeoutError:
                    errors["base"] = "timeout_connect"
                except TFAmeConnectionError:
                    errors["base"] = "cannot_connect"
                except TFAmeHTTPError, TFAmeJSONError:
                    errors["base"] = "invalid_response"
                except TFAmeException:
                    errors["base"] = "unknown"
                except Exception:
                    _LOGGER.exception(
                        "Unexpected exception while validating TFA.me host"
                    )
                    errors["base"] = "unknown"
                else:
                    if not isinstance(json_data, dict):
                        errors["base"] = "invalid_response"
                    else:
                        identifier = json_data.get("gateway_id")

                        if not isinstance(identifier, str) or not identifier:
                            errors["base"] = "invalid_response"
                        else:
                            await self.async_set_unique_id(identifier)
                            self._abort_if_unique_id_configured(
                                updates={CONF_IP_ADDRESS: host},
                            )

                            title = f"{DEFAULT_STATION_NAME} '{identifier.upper()}'"

                            return self.async_create_entry(
                                title=title,
                                data={CONF_IP_ADDRESS: host},
                            )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
