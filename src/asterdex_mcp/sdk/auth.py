"""
EIP-712 signing for AsterDEX V3 API.

This module abstracts away the entire signing flow so you never have to
think about typed data, nonce generation, or param ordering again.

Zero dependency on web3 — uses eth_utils + eth_abi + eth_account only.
"""

from __future__ import annotations

import time
import threading
import urllib.parse
from typing import Any

from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_abi import encode
from eth_utils import keccak


# EIP-712 domain — hardcoded per Aster spec
DOMAIN_DATA = {
    "name": "AsterSignTransaction",
    "version": "1",
    "chainId": 1666,
    "verifyingContract": "0x0000000000000000000000000000000000000000",
}

MESSAGE_TYPES = {
    "Message": [
        {"name": "msg", "type": "string"},
    ],
}

# Strict key ordering for futures (from official test_spot_standalone_cycle.js)
FUTURES_STRICT_KEYS = [
    "symbol", "side", "type", "quantity", "price", "timeInForce",
    "leverage", "orderId",
]

# Spot key ordering
SPOT_STRICT_KEYS = [
    "symbol", "side", "type", "quantity", "quoteOrderQty", "price",
    "timeInForce", "orderId",
]


class _NonceGenerator:
    """Thread-safe microsecond nonce with collision avoidance."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_us = 0
        self._seq = 0

    def __call__(self) -> str:
        with self._lock:
            now_us = int(time.time() * 1_000_000)
            if now_us <= self._last_us:
                self._seq += 1
                now_us = self._last_us + self._seq
            else:
                self._seq = 0
                self._last_us = now_us
            return str(now_us)


_nonce = _NonceGenerator()


def sign_request(
    private_key: str,
    params: dict[str, Any],
) -> str:
    """
    Sign a dict of request params using EIP-712 typed data and return the
    0x-prefixed hex signature.

    Per the official Aster V3 API spec, the signed message is the
    URL-encoded query string of all params (including nonce and signer).
    """
    param_str = urllib.parse.urlencode(params)

    signable = encode_typed_data(
        domain_data=DOMAIN_DATA,
        message_types=MESSAGE_TYPES,
        message_data={"msg": param_str},
    )
    signed = Account.sign_message(signable, private_key=private_key)
    return "0x" + signed.signature.hex()


def inject_auth(
    params: dict[str, Any],
    user: str,
    signer: str,
    private_key: str,
    strict_keys: list[str] | None = None,
) -> dict[str, Any]:
    """
    Inject user, signer, nonce, and signature into a params dict.
    Returns a new dict ready to send as request body/query string.

    The signature covers ALL params including nonce and signer,
    matching the official Aster V3 API authentication flow.
    """
    nonce = _nonce()
    auth_params = dict(params)
    auth_params["nonce"] = nonce
    auth_params["signer"] = signer

    sig = sign_request(private_key, auth_params)
    auth_params["signature"] = sig
    return auth_params


def generate_agent_wallet() -> dict[str, str]:
    """
    Generate a fresh agent/signer keypair.

    Returns {"address": "0x...", "private_key": "0x..."}.
    Use the address as signer and approve it via POST /fapi/v3/approveAgent.
    """
    acct = Account.create()
    pk = acct.key.hex() if isinstance(acct.key, bytes) else acct.key
    if not pk.startswith("0x"):
        pk = "0x" + pk
    return {
        "address": acct.address,
        "private_key": pk,
    }
