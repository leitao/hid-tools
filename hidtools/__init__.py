class HidUsagePage(dict):
    """
    A dictionary of HID Usages, using the Usage number as index and the
    string name as value.

    .. attribute:: page_id

        The Page ID for this Usage Page, e.g. ``01`` (Generic Desktop)

    .. attribute:: page_name

        The assigned name for this usage Page, e.g. "Generic Desktop"

    This object a dictionary, use like this: ::

        > print(usage_page.page_name)
        Generic Desktop
        > print(usage_page.page_id)
        1
        > print(usage_page[0x02])
        Mouse
        > print(usage_page.from_name["Mouse"])
        2

    """
    @property
    def page_id(self):
        """
        The numerical page ID for this usage page
        """
        return self._page_id

    @page_id.setter
    def page_id(self, page_id):
        self._page_id = page_id

    @property
    def page_name(self):
        """
        The assigned name for this Usage Page
        """
        return self._name

    @page_name.setter
    def page_name(self, name):
        self._name = name

    @property
    def from_name(self):
        """
        A dictionary using ``{ name: usage }`` mapping, to look up the usage
        based on a name.
        """
        try:
            return self._inverted
        except AttributeError:
            self._inverted = {}
            for k, v in self.items():
                self._inverted[v] = k
            return self._inverted

    @property
    def from_usage(self):
        """
        A dictionary using ``{ usage: name }`` mapping, to look up the name
        based on a page ID . This is the same as using the object itself.
        """
        return self


class HidUsages(dict):
    """
    This is a dictionary wrapper that all HID Usages known to man. Or to
    this module at least.

    This dict is laid out as ``{page_id : usage_page_object}``
    (:class:`hidtools.HidUsagePage`)

    This object a dictionary, use like this: ::

        > print(usages[0x01].page_name)
        Generic Desktop
        > print(usages.usage_pages[0x01].page_name)
        Generic Desktop
        > print(usages[0x01].page_id)
        1
        > print(usages.usage_page_from_name('Generic Desktop').page_id)
        1
        > print(usages.usage_page_from_page_id(0x01).page_name)
        Generic Desktop
    """

    @property
    def usage_pages(self):
        """
        A dictionary mapping `{page_id : object}`.
        """
        return self

    def usage_page_from_name(self, page_name):
        """
        Look up the usage page based on the page name (e.g. "Generic
        Desktop").

        :return: the :meth:`hidtools.hid.HidUsagePage` or None
        """
        for k, v in self.items():
            if v.page_name == page_name:
                return v
        return None

    def usage_page_from_page_id(self, page_id):
        """
        Look up the usage page based on the page ID. This is identical to
        calling::

                self.usage_pages[page_id]

        except that this function returns None if the page ID is unknown.

        :return: the :meth:`hidtools.hid.HidUsagePage` or None
        """
        try:
            return self[page_id]
        except KeyError:
            return None
