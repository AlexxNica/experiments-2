# Copyright 2014 Florian Bruhin (The Compiler) <mail@qutebrowser.org>
#
# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.

"""Utils regarding URL handling."""

import re
import os.path
import urllib.parse

from PyQt5.QtCore import QUrl
from PyQt5.QtNetwork import QHostInfo

import qutebrowser.config.config as config
from qutebrowser.utils.log import url as logger


# FIXME: we probably could raise some exceptions on invalid URLs


def _get_search_url(txt):
    """Get a search engine URL for a text.

    Args:
        txt: Text to search for.

    Return:
        The search URL as a QUrl.

    Raise:
        SearchEngineError if there is no template or no search term was found.
    """
    logger.debug("Finding search engine for '{}'".format(txt))
    r, group = config.get('general', 'search-regex')
    m = r.search(txt)
    if m:
        engine = m.group(group)
        try:
            template = config.get('searchengines', engine)
        except config.NoOptionError:
            template = config.get('searchengines', 'DEFAULT')
        term = ''.join(m.groups()[:group-1] + m.groups()[group:])
        logger.debug("engine {}, term '{}'".format(engine, term))
    else:
        template = config.get('searchengines', 'DEFAULT')
        term = txt
        logger.debug("engine: default, term '{}'".format(txt))
    if not term:
        raise SearchEngineError("No search term given")
    return QUrl.fromUserInput(template.format(urllib.parse.quote(term)))


def _is_url_naive(url):
    """Naive check if given URL is really a URL.

    Args:
        url: The URL to check for.

    Return:
        True if the URL really is a URL, False otherwise.
    """
    protocols = ['http', 'https']
    u = qurl(url)
    urlstr = urlstring(url)
    if isinstance(url, QUrl):
        u = url
    else:
        u = QUrl.fromUserInput(url)
    # We don't use u here because fromUserInput appends http:// automatically.
    if any(urlstr.startswith(proto) for proto in protocols):
        return True
    elif '.' in u.host():
        return True
    elif u.host() == 'localhost':
        return True
    else:
        return False


def _is_url_dns(url):
    """Check if a URL (QUrl) is really a URL via DNS.

    Args:
        url: The URL to check for.

    Return:
        True if the URL really is a URL, False otherwise.
    """
    host = url.host()
    logger.debug("DNS request for {}".format(host))
    if not host:
        return False
    info = QHostInfo.fromName(host)
    return not info.error()


def qurl(url):
    """Get a QUrl from a URL string.

    Args:
        The URL as string or QUrl.

    Return:
        The URL as string.
    """
    return url if isinstance(url, QUrl) else QUrl(url)


def urlstring(url):
    """Get an QUrl as string.

    Args:
        qurl: URL as string or QUrl.

    Return:
        The URL as string
    """
    return url.toString() if isinstance(url, QUrl) else url


def fuzzy_url(url):
    """Get a QUrl based on an user input which is URL or search term.

    Args:
        url: URL to load as QUrl or string.

    Return:
        A target QUrl to a searchpage or the original URL.
    """
    urlstr = urlstring(url)
    if is_url(urlstr):
        # probably an address
        logger.debug("URL is a fuzzy address")
        newurl = QUrl.fromUserInput(urlstr)
    else:  # probably a search term
        logger.debug("URL is a fuzzy search term")
        try:
            newurl = _get_search_url(urlstr)
        except ValueError:  # invalid search engine
            newurl = QUrl.fromUserInput(urlstr)
    logger.debug("Converting fuzzy term {} to URL -> {}".format(
                 urlstr, urlstring(newurl)))
    return newurl


def is_special_url(url):
    """Return True if url is an about:... or other special URL."""
    special_schemes = ['about', 'qute', 'file']
    return qurl(url).scheme() in special_schemes


def is_url(url):
    """Check if url seems to be a valid URL.

    Args:
        url: The URL as QUrl or string.

    Return:
        True if it is a valid URL, False otherwise.

    Raise:
        ValueError if the autosearch config value is invalid.
    """
    urlstr = urlstring(url)

    autosearch = config.get('general', 'auto-search')

    logger.debug("Checking if '{}' is a URL (autosearch={}).".format(
                 urlstr, autosearch))

    if not autosearch:
        # no autosearch, so everything is a URL.
        return True

    if ' ' in urlstr:
        # A URL will never contain a space
        logger.debug("Contains space -> no URL")
        return False
    elif is_special_url(url):
        # Special URLs are always URLs, even with autosearch=False
        logger.debug("Is an special URL.")
        return True
    elif os.path.exists(url):
        # local file
        return True
    elif autosearch == 'dns':
        logger.debug("Checking via DNS")
        return _is_url_dns(QUrl.fromUserInput(urlstr))
    elif autosearch == 'naive':
        logger.debug("Checking via naive check")
        return _is_url_naive(url)
    else:
        raise ValueError("Invalid autosearch value")


class SearchEngineError(Exception):

    """Exception raised when a search engine wasn't found."""

    pass
