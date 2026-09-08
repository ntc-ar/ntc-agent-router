"""Keep API credentials in the OS credential store, never in host configuration."""

import os

SERVICE = "ntc-openrouter"
ACCOUNT = "api-key"


def vault():
    import keyring

    backend = keyring.get_keyring()
    module = type(backend).__module__
    if not module.startswith(("keyring.backends.Windows", "keyring.backends.macOS",
                              "keyring.backends.SecretService", "keyring.backends.kwallet")):
        raise ValueError("A supported OS credential store is required; use OPENROUTER_API_KEY otherwise.")
    return backend


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY") or vault().get_password(SERVICE, ACCOUNT)
    if not key or not key.strip():
        raise ValueError("OpenRouter credential is missing. Run the credential setup command.")
    return key.strip()


def save_key(key):
    if not isinstance(key, str) or not key.startswith("sk-or-") or any(c.isspace() for c in key):
        raise ValueError("Expected an OpenRouter API key.")
    vault().set_password(SERVICE, ACCOUNT, key)
