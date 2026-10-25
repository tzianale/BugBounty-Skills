"""Per-engagement credential storage (storage only; no network, no login).

Accounts are kept in a JSON file that is chmod 0600 on every save.
"""
import json
import os

REQUIRED_FIELDS = ("id", "host", "username")
_DEFAULTS = {"label": "", "secret": "", "note": "", "manual_only": False}


def mask_secret(secret):
    """Show only the first 3 chars and the length; fully hide short secrets."""
    if not secret or len(secret) <= 3:
        return "****"
    return f"{secret[:3]}****(len={len(secret)})"


class CredStore:
    def __init__(self, path):
        self.path = path
        self._accounts = []
        if os.path.exists(path):
            with open(path) as f:
                self._accounts = json.load(f)

    def accounts(self):
        return self._accounts

    def add(self, account):
        for field in REQUIRED_FIELDS:
            if not account.get(field):
                raise ValueError(f"missing required field: {field}")
        if self.get(account["id"]) is not None:
            raise ValueError(f"duplicate account id: {account['id']}")
        entry = dict(_DEFAULTS)
        entry.update(account)
        self._accounts.append(entry)
        self.save()

    def get(self, acct_id):
        for acct in self._accounts:
            if acct["id"] == acct_id:
                return acct
        return None

    def remove(self, acct_id):
        kept = [a for a in self._accounts if a["id"] != acct_id]
        removed = len(kept) != len(self._accounts)
        self._accounts = kept
        if removed:
            self.save()
        return removed

    def save(self):
        # Create with 0600 so the secret is never briefly world-readable,
        # then chmod to cover a pre-existing file with looser permissions.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(self._accounts, f, indent=2)
        os.chmod(self.path, 0o600)
