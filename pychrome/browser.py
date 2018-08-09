#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import requests

from .tab import Tab


__all__ = ["Browser"]


class Browser(object):
    _all_tabs = {}

    def __init__(self, url="http://127.0.0.1:9222"):
        self.dev_url = url

        if self.dev_url not in self._all_tabs:
            self._tabs = self._all_tabs[self.dev_url] = {}
        else:
            self._tabs = self._all_tabs[self.dev_url]
        rp = requests.get("%s/json/version" % self.dev_url)
        version_data = rp.json()
        self.websocket_url = version_data['webSocketDebuggerUrl']
        self._connection = None  # type: Tab

    @property
    def connection(self):
        """
        The main websocket connection to the remote browser.
        If a connection is not active it will be created.

        :rtype: Tab
        """
        if self._connection is None:
            self._connection = Tab(
                id='browser', type='browser', webSocketDebuggerUrl=self.websocket_url)
            self._connection.start()
        return self._connection

    @connection.deleter
    def connection(self):
        if self._connection is not None:
            self._connection.stop()
            self._connection = None

    def new_tab(self, url=None, timeout=None):
        url = url or ''
        rp = requests.get("%s/json/new?%s" % (self.dev_url, url), json=True, timeout=timeout)
        tab = Tab(**rp.json())
        self._tabs[tab.id] = tab
        return tab

    def new_context_tab(self, url=None, timeout=None, browser_context=None):
        """
        Create a new tab in a new browser context. This tab will then have it's own
        cookies, storage etc. The Tab will have the 'browser_context' property set

        :param url: Url to start new tab with
        :param timeout: How long to wait for a response from the remote browser
        :param browser_context: If supplide reuses existing browser context to create tab
        :return: The Tab object for the new context
        :rtype: Tab
        """
        url = url or 'about:blank'
        connection = self.connection
        if not browser_context:
            context = connection.Target.createBrowserContext()
            browser_context = context['browserContextId']
        target = connection.Target.createTarget(
            url=url, browserContextId=browser_context)
        self.list_tab(timeout=timeout)
        if target['targetId'] in self._tabs:
            tab = self._tabs[target['targetId']]
            tab.browser_context = browser_context
        else:
            raise KeyError("Failed to find tab with target ID: {}".format(target['targetId']))
        return tab

    def list_tab(self, timeout=None):
        rp = requests.get("%s/json" % self.dev_url, json=True, timeout=timeout)
        tabs_map = {}
        for tab_json in rp.json():
            if tab_json['type'] != 'page':  # pragma: no cover
                continue

            if tab_json['id'] in self._tabs and self._tabs[tab_json['id']].status != Tab.status_stopped:
                tabs_map[tab_json['id']] = self._tabs[tab_json['id']]
            else:
                tabs_map[tab_json['id']] = Tab(**tab_json)

        self._tabs = tabs_map
        return list(self._tabs.values())

    def activate_tab(self, tab_id, timeout=None):
        if isinstance(tab_id, Tab):
            tab_id = tab_id.id

        rp = requests.get("%s/json/activate/%s" % (self.dev_url, tab_id), timeout=timeout)
        return rp.text

    def close_tab(self, tab_id, timeout=None):
        if isinstance(tab_id, Tab):
            tab_id = tab_id.id

        tab = self._tabs.pop(tab_id, None)
        if tab and tab.status == Tab.status_started:  # pragma: no cover
            tab.stop()

        rp = requests.get("%s/json/close/%s" % (self.dev_url, tab_id), timeout=timeout)
        return rp.text

    def version(self, timeout=None):
        rp = requests.get("%s/json/version" % self.dev_url, json=True, timeout=timeout)
        return rp.json()

    def __str__(self):
        return '<Browser %s>' % self.dev_url

    __repr__ = __str__
