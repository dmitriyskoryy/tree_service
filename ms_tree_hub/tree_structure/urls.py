from django.urls import path, re_path

from .views import NodeApiView, \
    NodesApiView, \
    DeleteRestoreNodeApiView, \
    ChangeAttributesNodeApiView, \
    ChangeInnerOrderNodeApiView, \
    ChangeParentNodeApiView, \
    test_server

urlpatterns = [
    # get_tree
    path('v1/nodes/', NodesApiView.as_view()),
    # get_children
    path('v1/nodes/<int:pk>/', NodesApiView.as_view()),
    # create_node_root
    # path('v1/node/', NodeApiView.as_view()),
    re_path(r'v1/node/?$', NodeApiView.as_view()),

    # get_node, create_node_child
    path('v1/node/<int:pk>/', NodeApiView.as_view()),


    # put attributes
    path('v1/node/<int:pk>/attributes/', ChangeAttributesNodeApiView.as_view()),

    # put inner_order
    path('v1/node/<int:pk>/order/', ChangeInnerOrderNodeApiView.as_view()),

    # delete_node, restore_node
    path('v1/node/<int:pk>/hidden/', DeleteRestoreNodeApiView.as_view()),

    # change_parent
    path('v1/node/<int:pk>/parent/', ChangeParentNodeApiView.as_view()),

    # for devops
    path('healthcheck/', test_server),
]
