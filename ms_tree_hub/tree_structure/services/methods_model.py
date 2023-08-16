import logging

from django.db import transaction, DatabaseError, connection
from django.db.models.functions import Length
from rest_framework import status
from rest_framework.exceptions import ValidationError

from ..models import Node
from ..serializers import NodeSerializer, NewNodeSerializer, UpdateNodeSerializer
from .validate_fields_model import Validate, ValidateError


logger = logging.getLogger('main_info')

def get_node(data: dict, pk: int) -> dict:
    """Функция получения узла из модели Node"""

    validate = Validate(data, pk=pk)
    validate()

    instance = Node.objects.filter(
        pk=pk,
        project_id=data.get('project_id'),
        item_type=data.get('item_type'),
        item=data.get('item'),
    ) \
        .exclude(hidden=True) \
        .first()

    if not instance:
        logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ}')
        raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ}, status=status.HTTP_404_NOT_FOUND)

    serializer = NodeSerializer(instance, many=False).data
    return serializer


def get_nodes(data: dict, pk: int) -> dict:
    """Функция вывода узлов дерева из модели Node"""
    if not pk:
        result = get_tree(data)
        return result
    else:
        result = get_descendants(data, pk)
        return result


def get_tree(data: dict) -> dict:
    """Функция вывода всех узлов дерева из модели Node"""

    fields_allowed = ['sort_by_id', ]
    validate = Validate(data)
    validate(fields_allowed=fields_allowed)

    sort_by_id = data.get('sort_by_id', False)
    sort_by = 'id' if sort_by_id else 'inner_order'

    instance = Node.objects.filter(
        project_id=data['project_id'],
        item_type=data['item_type'],
        item=data['item'],
    ) \
        .exclude(hidden=True) \
        .order_by(sort_by)

    result = NodeSerializer(instance, many=True).data
    return result


def get_descendants(data: dict, pk: int) -> dict:
    """Функция вывода всех дочерних узлов из модели Node"""

    fields_allowed = ['sort_by_id', 'depth', ]
    validate = Validate(data, pk=pk)
    validate(fields_allowed=fields_allowed)

    instance = Node.objects.filter(
        pk=pk,
        project_id=data['project_id'],
        item_type=data['item_type'],
        item=data['item'],
    ) \
        .exclude(hidden=True) \
        .first()

    if not instance:
        logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ}')
        raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ}, status=status.HTTP_404_NOT_FOUND)

    # получаем path родителя
    path = instance.path
    # формируем path дочерних узлов
    path += '0' * (10 - len(str(instance.id))) + str(instance.id)

    sort_by_id = data.get('sort_by_id', False)
    sort_by = 'id' if sort_by_id else 'inner_order'

    depth = int(data.get('depth')) if data.get('depth') else 9999999999

    instance = Node.objects.filter(
        path__startswith=path[:-10],
        project_id=data['project_id'],
        item_type=data['item_type'],
        item=data['item']
    ) \
        .annotate(path_len=Length('path')) \
        .exclude(path=instance.path) \
        .exclude(hidden=True) \
        .filter(path_len__lt=(len(instance.path) + 1 + 10 * depth)) \
        .order_by(sort_by)

    result = NodeSerializer(instance, many=True).data
    return result


def create_root_node(data: dict, path: str) -> object:
    try:
        with transaction.atomic():
            amount_nodes = Node.objects.select_for_update().filter(
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item'],
            ) \
                .annotate(path_len=Length('path')) \
                .filter(path_len__lt=11).count()

            inner_order = '0' * (10 - len(str(amount_nodes + 1))) + str(amount_nodes + 1)

            node_new = Node.objects.create(
                path=path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item'],
                inner_order=inner_order,
                attributes=data.get('attributes'),
            )

            path = '0' * (10 - len(str(node_new.id))) + str(node_new.id)
            node_new.path = path
            node_new.save()

    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidateError({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return node_new


def create_child_node(data: dict, path: str, parent_inner_order: str) -> object:
    try:
        with transaction.atomic():
            amount_nodes = Node.objects.select_for_update().filter(
                path__startswith=path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item'],
            ) \
                .annotate(path_len=Length('path')) \
                .exclude(path=path) \
                .filter(path_len__lt=len(path) + 11) \
                .count()

            inner_order = parent_inner_order + ('0' * (10 - len(str(amount_nodes + 1))) + str(amount_nodes + 1))

            node_new = Node.objects.create(
                path=path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item'],
                inner_order=inner_order,
                attributes=data.get('attributes'),
            )

            path = '0' * (10 - len(str(node_new.id))) + str(node_new.id)
            node_new.path += path
            node_new.save()

    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidationError({'error': e})

    return node_new


def create_node(data: dict, pk: int):
    """Метод создания нового узла в модели Node
    Если в url запроса передается <id>,
    то будет создан дочерний узел родителя.
    Если в url запроса отсутствует <id>,
    то будет создан корневой узел.
    """

    fields_allowed = ['attributes']

    try:
        with transaction.atomic():
            if pk:
                validate = Validate(data, pk=pk)
                validate(fields_allowed=fields_allowed)

                instance = Node.objects.select_for_update().filter(
                    pk=pk,
                    project_id=data['project_id'],
                    item_type=data['item_type'],
                    item=data['item']
                ) \
                    .exclude(hidden=True) \
                    .order_by('inner_order') \
                    .first()

                if not instance:
                    logger.info(f'{validate.ERR_OBJ_NOT_RECEIVED}')
                    raise ValidateError({'error': validate.ERR_OBJ_NOT_RECEIVED},
                                        status=status.HTTP_404_NOT_FOUND)

                kwargs = {
                    'project_id': instance.project_id,
                    'item_type': instance.item_type,
                    'item': instance.item,
                    'path': instance.path,
                    'id': instance.id
                }
                validate.validate_value_fields_for_create_child(**kwargs)

                node_new = create_child_node(data, instance.path, instance.inner_order)
            else:
                validate = Validate(data)
                validate(fields_allowed=fields_allowed)

                node_new = create_root_node(data, "9999999999")
    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidationError({'error': e})

    return NewNodeSerializer(node_new).data


def change_inner_order_attr_node(data: dict, pk: int, internal_use: bool = False):
    """Функция смены inner_order"""

    fields_required = [*data.keys()] if internal_use else ['destination_node_id', ]
    validate = Validate(data, pk=pk)
    validate(fields_required=fields_required)

    # проверяем наличие поля destination_node_id, если internal_use = True, то устанавливаем в destination_node_id
    # последний узел
    if not data.get('destination_node_id'):
        if internal_use:
            parent_path = Node.objects.filter(id=pk).first().path[:-10]
            destination_node_id = Node.objects.filter(
                path__startswith=parent_path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .annotate(path_len=Length('path')) \
                .exclude(path=parent_path) \
                .exclude(hidden=True) \
                .filter(path_len__lt=len(parent_path) + 11) \
                .order_by('inner_order') \
                .last() \
                .id

            data.update({
                'destination_node_id': destination_node_id
            })
        else:
            logger.info(f'{validate.ERR_DESTINATION_ID_NOT_NONE}')
            raise ValidateError({'error': validate.ERR_DESTINATION_ID_NOT_NONE},
                                status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    if pk == int(data.get("destination_node_id")) and not internal_use:
        logger.info(f'{validate.ERR_MOVE_ID_NOT_EQUAL_DESTINATION_ID}')
        raise ValidateError({'error': validate.ERR_MOVE_ID_NOT_EQUAL_DESTINATION_ID},
                            status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # получаем узел, который двигаем
            movable_instance = Node.objects.select_for_update().filter(
                id=pk,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .exclude(hidden=True) \
                .first()

            if not movable_instance:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=pk)}')
                raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=pk)},
                                    status=status.HTTP_404_NOT_FOUND)

            # получаем узел, на место которого двигаем
            destination_instance = Node.objects.select_for_update().filter(
                id=data['destination_node_id'],
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .exclude(hidden=True) \
                .first()

            if not destination_instance:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=data.get("destination_node_id"))}')
                raise ValidateError(
                    {
                        'error': validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=data.get("destination_node_id"))
                    },
                    status=status.HTTP_404_NOT_FOUND
                )

            if movable_instance.path[:-10] != destination_instance.path[:-10]:
                logger.info(f'{validate.ERR_OBJ_NOT_BELONG_PARENT.format(destination_obj=data.get("destination_node_id"), parent_obj=pk)}')
                raise ValidateError(
                    {
                        'error': validate.ERR_OBJ_NOT_BELONG_PARENT.format(
                            destination_obj=data.get("destination_node_id"), parent_obj=pk)
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

            parent_path = destination_instance.path[:-10]

            # если двигаем узел вниз
            if int(movable_instance.inner_order[-10:]) < int(destination_instance.inner_order[-10:]):

                with connection.cursor() as cursor:

                    sql_params = f"""
UPDATE tree_structure_node
    SET inner_order = CASE
        WHEN 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) AS TEXT)) >
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) - 1 AS TEXT))
        THEN
            LEFT(inner_order, LENGTH('{destination_instance.inner_order}') - 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) AS TEXT)))||'0'||
            CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) - 1 AS TEXT)||
            RIGHT(inner_order, -LENGTH('{destination_instance.inner_order}'))
        ELSE
            LEFT(inner_order, LENGTH('{destination_instance.inner_order}') - 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10)
            AS INTEGER) - 1 AS TEXT)))||
            CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) - 1 AS TEXT)||
            RIGHT(inner_order, -LENGTH('{destination_instance.inner_order}'))
        END
    WHERE path LIKE '{parent_path}%' 
        AND path != '{parent_path}'
        AND (hidden IS NULL OR hidden = false)
        AND inner_order BETWEEN '{movable_instance.inner_order}' AND '{destination_instance.inner_order}'
        OR inner_order LIKE '{destination_instance.inner_order}%';


UPDATE tree_structure_node
    SET inner_order = '{destination_instance.inner_order}'||RIGHT(inner_order, -LENGTH('{movable_instance.inner_order}'))
    WHERE path LIKE '{movable_instance.path}%'
    RETURNING *;
                    """

                    cursor.execute(sql_params)

                    columns = [col[0] for col in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # если двигаем узел вверх
            elif int(movable_instance.inner_order[-10:]) > int(destination_instance.inner_order[-10:]):

                with connection.cursor() as cursor:

                    sql_params = f"""
UPDATE tree_structure_node
    SET inner_order = CASE
        WHEN 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) AS TEXT)) <
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) + 1 AS TEXT))
        THEN
            LEFT(inner_order, LENGTH('{destination_instance.inner_order}') - 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) AS TEXT)) - 1)||
            CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) + 1 AS TEXT)||
            RIGHT(inner_order, -LENGTH('{destination_instance.inner_order}'))
        ELSE
            LEFT(inner_order, LENGTH('{destination_instance.inner_order}') - 
            LENGTH(CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) AS TEXT)))||
            CAST(CAST(SUBSTR(inner_order, LENGTH('{destination_instance.inner_order}') - 9, 10) 
            AS INTEGER) + 1 AS TEXT)||
            RIGHT(inner_order, -LENGTH('{destination_instance.inner_order}'))
        END
    WHERE path LIKE '{parent_path}%' 
        AND path != '{parent_path}'
        AND (hidden IS NULL OR hidden = false)
        AND inner_order BETWEEN '{destination_instance.inner_order}' AND '{movable_instance.inner_order}'
        OR inner_order LIKE '{destination_instance.inner_order}%';


UPDATE tree_structure_node
    SET inner_order = '{destination_instance.inner_order}'||
        RIGHT(inner_order, -LENGTH('{movable_instance.inner_order}'))
    WHERE path LIKE '{movable_instance.path}%'
    RETURNING *;
                                        """

                    cursor.execute(sql_params)

                    columns = [col[0] for col in cursor.description]
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]

            elif not internal_use:
                logger.info(f'{validate.ERR_MOVE_ORDER_NOT_EQUAL_DESTINATION_ORDER}')
                raise ValidateError({'error': validate.ERR_MOVE_ORDER_NOT_EQUAL_DESTINATION_ORDER},
                                    status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            else:
                return None
    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidateError({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return f'Node {movable_instance.id} moved on node\'s {destination_instance.id} position'


def change_attributes_attr_node(data: dict, pk: int):
    """Функция изменения значения поля attributes в модели Node"""

    fields_required = ['attributes', ]
    validate = Validate(data, pk=pk)
    validate(fields_required=fields_required)

    try:
        with transaction.atomic():
            instance = Node.objects.select_for_update().filter(
                id=pk,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .exclude(hidden=True) \
                .first()

            if not instance:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ}')
                raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ},
                                    status=status.HTTP_404_NOT_FOUND)

            instance.attributes = data.get('attributes')
            instance.save(update_fields=['attributes'])
    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidateError({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return UpdateNodeSerializer(instance).data


def change_hidden_attr_node(data: dict, pk: int):
    fields_allowed = ['affect_descendants', ]
    fields_required = ['hidden', ]
    validate = Validate(data, pk=pk)
    validate(fields_required=fields_required, fields_allowed=fields_allowed)

    hidden = data.get('hidden')

    # узнаем, надо ли влиять на потомков
    affect_descendants = data.get('affect_descendants', True)

    try:
        with transaction.atomic():
            instance = Node.objects.select_for_update().filter(
                id=pk,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ).first()

            if not instance:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ}')
                raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ}, status=status.HTTP_404_NOT_FOUND)

            if instance.hidden == hidden:
                logger.info(f'hidden is already set to {instance.hidden}')
                raise ValidateError({'error': f'hidden is already set to {instance.hidden}'},
                                    status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            else:
                # перед удалением помещаем узел в конец
                if hidden:
                    change_inner_order_attr_node(data, pk, internal_use=True)

                # проверяем, надо ли влиять на потомков
                if affect_descendants:
                    Node.objects.filter(
                        path__startswith=instance.path,
                        project_id=data['project_id'],
                        item_type=data['item_type'],
                        item=data['item']
                    ) \
                        .update(hidden=hidden)
                else:
                    instance.hidden = hidden
                    instance.save()

                # после восстановления помещаем узел в конец
                if hidden is None:
                    change_inner_order_attr_node(data, pk, internal_use=True)
    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidateError({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if hidden:
        return 'Node(s) deleted'
    else:
        return 'Node(s) restored'


def change_parent_node(data: dict, pk: int):
    fields_required = ['new_parent_id', ]
    validate = Validate(data, pk=pk)
    validate(fields_required=fields_required)

    try:
        with transaction.atomic():
            movable_instance = Node.objects.select_for_update().filter(
                id=pk,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .exclude(hidden=True) \
                .first()

            if not movable_instance:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=pk)}')
                raise ValidateError({'error': validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=pk)},
                                    status=status.HTTP_404_NOT_FOUND)

            # проверяем, что новый родитель не является старым родителем
            old_parent_id = int(movable_instance.path[-20:-10])

            if data['new_parent_id'] == old_parent_id:
                logger.info(f'This parent is already set')
                raise ValidateError({'error': 'This parent is already set'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # проверяем, что новый родитель не является перемещаемым узлом
            if data['new_parent_id'] == pk:
                logger.info(f'New parent can\'t be movable instance itself')
                raise ValidateError({'error': 'New parent can\'t be movable instance itself'},
                                    status=status.HTTP_400_BAD_REQUEST)

            # проверяем, что новый родитель не является потомком перемещаемого узла
            descendant_list = Node.objects.filter(
                path__startswith=movable_instance.path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .values_list('id', flat=True)

            if data['new_parent_id'] in descendant_list:
                logger.info(f'New parent can\'t be movable instance\'s descendant')
                raise ValidateError({'error': 'New parent can\'t be movable instance\'s descendant'},
                                    status=status.HTTP_400_BAD_REQUEST)

            new_parent = Node.objects.select_for_update().filter(
                id=data['new_parent_id'],
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .exclude(hidden=True) \
                .first()

            if not new_parent:
                logger.info(f'{validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=data.get("new_parent_id"))}')
                raise ValidateError(
                    {'error': validate.ERR_DOES_NOT_EXIST_OBJ_ID.format(obj_id=data.get("new_parent_id"))},
                    status=status.HTTP_404_NOT_FOUND)

            new_siblings_quantity = Node.objects.select_for_update().filter(
                path__startswith=new_parent.path,
                project_id=data['project_id'],
                item_type=data['item_type'],
                item=data['item']
            ) \
                .annotate(path_len=Length('path')) \
                .exclude(path=new_parent.path) \
                .exclude(hidden=True) \
                .filter(path_len__lt=(len(new_parent.path) + 11)) \
                .count()

            new_inner_order = ('0' * (10 - len(str(new_siblings_quantity + 1))) + str(new_siblings_quantity + 1))

            # до перемещения помещаем узел в конец, чтобы не ломать сортировку
            change_inner_order_attr_node(data, pk, internal_use=True)

            with connection.cursor() as cursor:
                sql_params = f"""
UPDATE tree_structure_node
    SET path = '{new_parent.path}'||RIGHT(path, -LENGTH('{movable_instance.path[:-10]}')),
        inner_order = '{new_parent.inner_order}'||'{new_inner_order}'
        ||RIGHT(inner_order, -LENGTH('{movable_instance.inner_order}'))
    WHERE path LIKE '{movable_instance.path}%'
    RETURNING *;
                """
                cursor.execute(sql_params)

                columns = [col[0] for col in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
    except DatabaseError as e:
        logger.error(f'{e}')
        raise ValidateError({'error': e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return f'Node {movable_instance.id} changed it\'s parent to node {new_parent.id}'
