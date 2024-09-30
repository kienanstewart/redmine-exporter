#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
# SPDX-FileCopyrightText: 2024 Kienan Stewart <kstewart@efficios.com>
"""
"""

import logging
import os

import prometheus_client
import prometheus_client.core
import prometheus_client.registry
import redminelib


class RedmineCollector(prometheus_client.registry.Collector):
    """ """

    def __init__(self, redmine_config, *args, **kwargs):
        self.last_update = 0
        self.redmine_connection = None
        self.config = redmine_config
        super().__init__(*args, **kwargs)

    def connect(self):
        if not self.config["REDMINE_URL"]:
            raise Exception("No redmine URL")

        connect_kwargs = {}
        if self.config["REDMINE_PASSWORD"] and self.config["REDMINE_USER"]:
            connect_kwargs += {
                "user": self.config["REDMINE_USER"],
                "password": self.config["REDMINE_PASSWORD"],
            }
        elif self.config["REDMINE_API_KEY"]:
            connect_kwargs["key"] = self.config["REDMINE_API_KEY"]
        else:
            raise Exception("No connection method")

        if self.redmine_connection is None:
            self.redmine_connection = redminelib.Redmine(
                self.config["REDMINE_URL"], **connect_kwargs
            )

        # Test connection?

    def _redmine_issues_total(self):
        g2 = prometheus_client.core.GaugeMetricFamily(
            "redmine_issues_total",
            "Redmine Issue Count",
            labels=[
                "instance_url",
                "project_id",
                "project_name",
                "tracker_id",
                "tracker_name",
                "status_id",
                "status_name",
            ],
        )

        if len(self.config["ISSUES_FOR_PROJECTS"]) == 0:
            return g2

        projects = self.redmine_connection.project.all(
            include=["trackers", "issue_categories"]
        )
        statuses = self.redmine_connection.issue_status.all()
        trackers = self.redmine_connection.tracker.all()

        metrics_added = False
        for project in projects:
            if not (
                project.name in self.config["ISSUES_FOR_PROJECTS"]
                or str(project.id) in self.config["ISSUES_FOR_PROJECTS"]
            ):
                logging.info(
                    "Project '{}' id '{}' not in issues_for_projects list".format(
                        project.name, project.id
                    )
                )
                continue
            if "issue_tracking" not in project.enabled_modules:
                logging.info(
                    "Project '{}' id '{}' not not have issue_tracking enabled".format(
                        project.name, project.id
                    )
                )
                continue
            for tracker in trackers:
                for status in statuses:
                    try:
                        g2.add_metric(
                            [
                                self.config["REDMINE_URL"],
                                str(project.id),
                                project.name,
                                str(tracker.id),
                                tracker.name,
                                str(status.id),
                                status.name,
                            ],
                            len(
                                self.redmine_connection.issue.filter(
                                    project_id=project.id,
                                    tracker_id=tracker.id,
                                    status_id=status.id,
                                )
                            ),
                        )
                        metrics_added = True
                    except Exception as e:
                        logging.critical(
                            project.id,
                            project.name,
                            tracker.id,
                            0,
                            str(e),
                        )
                        break
        return g2

    def _redmine_projects_total(self):
        projects = self.redmine_connection.project.all(
            include=["trackers", "issue_categories"]
        )
        g1 = prometheus_client.core.GaugeMetricFamily(
            "redmine_projects_total",
            "Redmine Project Count",
            labels=["instance_url", "public_state"],
        )
        g1.add_metric(
            [self.config["REDMINE_URL"], "private"],
            len(projects.filter(is_public=False)),
        )
        g1.add_metric(
            [self.config["REDMINE_URL"], "public"], len(projects.filter(is_public=True))
        )
        return g1

    def collect(self):
        """ """
        self.connect()
        yield self._redmine_projects_total()
        yield self._redmine_issues_total()

    def describe(self):
        """ """
        return []


def _default_config():
    return {
        "BIND_ADDRESS": os.getenv("BIND_ADDRESS", "localhost"),
        "LISTEN_PORT": int(os.getenv("LISTEN_PORT", "9169")),
        "REDMINE_API_KEY": os.getenv("REDMINE_API_KEY", ""),
        "REDMINE_PASSWORD": os.getenv("REDMINE_PASSWORD", ""),
        "REDMINE_URL": os.getenv("REDMINE_URL", ""),
        "REDMINE_USER": os.getenv("REDMINE_USER", ""),
        "ISSUES_FOR_PROJECTS": [
            x for x in os.getenv("ISSUES_FOR_PROJECTS", "").split(",") if x != ""
        ],
        "VERBOSE": bool(os.getenv("VERBOSE", False)),
        "DEBUG": bool(os.getenv("DEBUG", False)),
    }


def _get_config():
    config = _default_config()
    return config


if __name__ == "__main__":
    logging.basicConfig()
    config = _get_config()

    logger = logging.getLogger()
    if config["VERBOSE"]:
        logger.setLevel(logging.INFO)

    if config["DEBUG"]:
        logger.setLevel(logging.DEBUG)

    prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
    prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)
    redmine_collector = RedmineCollector(config)
    prometheus_client.core.REGISTRY.register(redmine_collector)
    server, server_thread = prometheus_client.start_http_server(
        port=config["LISTEN_PORT"], addr=config["BIND_ADDRESS"]
    )
    server_thread.join()
