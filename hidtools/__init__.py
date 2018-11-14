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
