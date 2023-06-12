from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from octoploy.config.Config import RootConfig

from octoploy.k8s.BaseObj import BaseObj
from octoploy.processing.TreeWalker import TreeProcessor


class NamespaceProcessor(TreeProcessor):
    _root: RootConfig

    def __init__(self, root: RootConfig):
        self._root = root

    def process(self, k8s_object: BaseObj):
        self._update_namespace(k8s_object)

    def _update_namespace(self, k8s_object: BaseObj):
        """
        Updates the namespace meta-data of this object.
        If no namespace is defined this will use the globaly defined namespace of the octoploy project
        :param k8s_object: Object
        """
        # An object might be in a different namespace than the current context
        namespace = k8s_object.namespace
        if namespace is None:
            namespace = self._root.get_namespace_name()
        k8s_object.set_namespace(namespace)  # Make sure the object points to the correct namespace
