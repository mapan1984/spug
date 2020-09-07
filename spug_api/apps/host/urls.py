# Copyright: (c) OpenSpug Organization. https://github.com/openspug/spug
# Copyright: (c) <spug.dev@gmail.com>
# Released under the AGPL-3.0 License.
from django.urls import path

from .views import HostView, post_import, get_categories, post_parse

urlpatterns = [
    path('', HostView.as_view()),
    path('import/', post_import),
    path('parse/', post_parse),
    path('category/', get_categories),
]
