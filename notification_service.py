"""Centralized notification helper using Apprise.

This module provides a small wrapper around Apprise so the rest of the
application can send notifications without depending on provider-specific
APIs. It expects a list of Apprise URLs (strings) describing where to send
notifications: email, Slack, MS Teams, SMS, webhooks, etc.
"""

from __future__ import annotations

from typing import Iterable, Optional

import apprise


def send_notification(
    targets: Iterable[str],
    title: str,
    body: str,
    tag: Optional[str] = None,
) -> bool:
    """Send a notification to one or more Apprise target URLs.

    Parameters
    ----------
    targets:
        Iterable of Apprise URLs (e.g. mailto://, slack://, tgram://, etc.).
    title:
        Short title for the notification.
    body:
        Main message body.
    tag:
        Optional tag / context (e.g. "job.completed"). Included in the body
        for easier filtering at the destination.

    Returns
    -------
    bool
        True if at least one notification was successfully delivered.
    """

    targets = list(targets or [])
    if not targets:
        return False

    app = apprise.Apprise()
    for url in targets:
        if not url:
            continue
        try:
            app.add(url)
        except Exception:
            # Ignore invalid URLs; Apprise will handle/send to the rest.
            continue

    if not app:
        return False

    full_body = body
    if tag:
        full_body = f"[{tag}] {body}"

    try:
        return bool(app.notify(title=title, body=full_body))
    except Exception:
        # In production you may want to log this instead of swallowing it.
        return False
