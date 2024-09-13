#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
# SPDX-FileCopyrightText: 2024 Kienan Stewart <kstewart@efficios.com>
"""
"""

import prometheus_client
import prometheus_client.core
import prometheus_client.registry
import redminelib


class RedmineCollector(prometheus_client.registry.Collector):
    """ """

    def __init__(self, config):
        self.last_update = 0
        self.redmine_connection = None
        super().__init__()

    def collect(self):
        """ """
        yield

    def describe(self):
        """ """
        return []


def _default_config():
    return {
        "LISTEN_PORT": 9169,
        "REDMINE_API_KEY": "",
        "REDMINE_PASSWORD": "",
        "REDMINE_URL": "",
        "REDMINE_USER": "",
        "REDMINE_VERSION": "",
        "TLS_VERIFY": True,
        "CACHE_TIME_SECONDS": 0,
    }


def _get_config():
    config = _default_config()


if __name__ == "__main__":
    config = _get_config()
    prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
    redmine_collector = RedmineCollector(config)
    prometheus_client.core.REGISTRY.register(redmine_collector)
    server, server_thread = prometheus_client.start_http_server(9169)
    server_thread.join()
