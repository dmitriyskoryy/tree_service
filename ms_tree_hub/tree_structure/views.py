from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from core.decorators import custom_exception_handler
from .services import methods_model


class NodeApiView(APIView):

    # v1/node/<int:pk>/
    @custom_exception_handler
    def get(self, request, pk: int = None):
        """
        Получить узел по id(pk)
        :param pk: id получаемого узла
        :param request: в параметрах get запроса принимает следующие параметры:
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        :return: объект
        """

        result = methods_model.get_node(request.GET, pk)
        return Response(result, status=status.HTTP_200_OK)

    # v1/node/
    @custom_exception_handler
    def post(self, request, pk: int = None):
        """
        Создание нового узла. Запрос post.
        :param pk: id родителя, передается при создании дочернего (некорневого) узла
        :param request: в теле запроса принимает следующие параметры:
        project_id: uuid проекта, обязательный параметр, при создании дочернего узла сверяется с соответствующим
        полем (project_id) родителя, при несоответствии возвращает ответ 400
        item_type: обязательный параметр, при создании дочернего узла сверяется с соответствующим полем (item_type)
        родителя, при несоответствии возвращает ответ 400
        item: обязательный параметр, при создании дочернего узла сверяется с соответствующим полем (item) родителя,
        при несоответствии возвращает ответ 400
        :return: при успешном выполнении запроса возвращает созданный объект, в ином случае - ошибку
        """

        result = methods_model.create_node(request.data, pk)
        return Response(result, status=status.HTTP_201_CREATED)


class NodesApiView(APIView):

    # v1/nodes/
    @custom_exception_handler
    def get(self, request, pk: int = None):
        """
        Получить потомков узла, если в url передан id(pk), иначе получить дерево узлов
        по 'project_id' 'item_type' 'item'
        :param pk: опциональный параметр, при передаче возвращает потомков узла с этим id
        :param request: в параметрах get запроса принимает следующие параметры:
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        sort_by_id: опциональный параметр, надо ли сортировать по полю id (если параметр не передан, то
        сортировка идет по полю inner_order), принимает значение true
        depth: опциональный параметр, задается для выдачи детей определенного уровня вложенности по отношению
        к исходному узлу(параметр актуален только для метода get_descendants)
        :return: список объектов
        """

        result = methods_model.get_nodes(request.GET, pk)
        return Response(result, status=status.HTTP_200_OK)


class ChangeAttributesNodeApiView(APIView):

    # v1/node/<int:pk>/attributes/
    @custom_exception_handler
    def patch(self, request, pk: int = None):
        """
        Изменить поле attributes в модели Node
        :param pk: id изменяемого узла
        :param request:
         - В параметрах put запроса в url принимает pk.
         - В параметрах тела запроса:
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        attributes: json
        :return: объект
        """

        result = methods_model.change_attributes_attr_node(request.data, pk)
        return Response(result, status=status.HTTP_201_CREATED)


class ChangeInnerOrderNodeApiView(APIView):

    # v1/node/<int:pk>/order/
    @custom_exception_handler
    def patch(self, request, pk: int = None):
        """
        Изменить поле inner_order в модели Node
        :param pk: id изменяемого узла
        :param request:
         - В параметрах put запроса в url принимает pk.
         - В параметрах тела запроса:
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        destination_node_id: id узла, на место которого ставим
        :return: сообщение
        """
        result = methods_model.change_inner_order_attr_node(request.data, pk)
        return Response(result, status=status.HTTP_201_CREATED)


class DeleteRestoreNodeApiView(APIView):

    # v1/node/<int:pk>/hidden/
    @custom_exception_handler
    def patch(self, request, pk: int = None):
        """
        Скрыть или восстановить узел (установить поле hidden)
        :param pk: id удаляемого узла
        :param request: в теле запроса принимает следующие параметры:
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        hidden: обязательный параметр, принимает возможные значения True или None (для удаления необходимо передать
        True, для восстановления - None)
        affect_descendants: опциональный параметр, необходимость удалять/восстанавливать всех потомков, принимает
        значения True или False, по дефолту установлено True
        :return: при восстановлении - восстановленный объект, при удалении - строка с результатом
        .
        """

        result = methods_model.change_hidden_attr_node(request.data, pk)
        return Response(result, status=status.HTTP_200_OK)


class ChangeParentNodeApiView(APIView):

    # v1/node/<int:pk>/parent/
    @custom_exception_handler
    def patch(self, request, pk: int = None):
        """
        Переместить узел к другому родителю. Все потомки перемещаемого узла перемещаются вместе с ним.
        :param pk: id перемещаемого узла
        :param request: в теле запроса принимает следующие параметры:
        new_parent_id: id нового родителя, обязательный параметр
        project_id: uuid проекта, обязательный параметр
        item_type: обязательный параметр
        item: обязательный параметр
        :return: перемещаемый объект
        """
        result = methods_model.change_parent_node(request.data, pk)
        return Response(result, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def test_server(request):
    return Response('mxnzEgBjbUQSNE9i8dfk')
