import logging
import json
import uuid
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger('main_info')
class ValidateError(APIException):
    ERR_NOT_ALLOWED_FIELD = "field {field} not allowed"
    ERR_FIELD_IS_REQUIRED = "field {field} is required"
    ERR_WRONG_FORMAT_FIELD = "{field} has wrong format, must be {format}"
    ERR_DOES_NOT_EXIST_OBJ = "does not exist object(s)"
    ERR_DOES_NOT_EXIST_OBJ_ID = "does not exist object with id {obj_id}"
    ERR_OBJ_NOT_RECEIVED = "Objects for verification not received"
    ERR_PK_NOT_NONE = "pk can\'t be None"
    ERR_DESTINATION_ID_NOT_NONE = "destination_node_id can\'t be None"
    ERR_FIELD_REQUEST_NOT_EMPTY = "field {field} must not be empty"
    ERR_MOVE_ID_NOT_EQUAL_DESTINATION_ID = "moveable object must not be equal id destination object"
    ERR_MOVE_ORDER_NOT_EQUAL_DESTINATION_ORDER = "movable node\'s inner_order is equal to destination node\'s \
                                                inner_order"
    ERR_OBJ_NOT_BELONG_PARENT = "object id {destination_obj} does not belong to the parent of object id {parent_obj}"
    ERR_FIELD_INTEGER_POSITIVE = "{field} must be positive number"

    def __init__(self, detail=None, code=None, status=None):
        if status:
            self.status_code = status
            super().__init__(detail, code)


class Validate(ValidateError):
    """Класс для валидации переданных полей при работе с моделью Node"""
    FIELDS_REQUIRED = [
        'project_id',
        'item_type',
        'item',
    ]

    def __init__(self, request_data: dict, *args, **kwargs):
        self.request_data = request_data.copy()

        self.FIELDS_REQUIRED = Validate.FIELDS_REQUIRED.copy()

        self.fields_allowed = []

        if 'pk' in kwargs.keys():
            self.request_data['pk'] = kwargs.get('pk')
            self.fields_allowed.append('pk')

    def __call__(self, fields_required: list = None, fields_allowed: list = None, *args, **kwargs):
        """Метод проверяет, что в request.data переданы аргументы project_id, item_type, item,
                а также другие необходимые поля
        """

        if fields_required:
            self.FIELDS_REQUIRED += fields_required

        self.fields_allowed += self.FIELDS_REQUIRED

        if fields_allowed:
            self.fields_allowed += fields_allowed

        errors = []

        # Проверяем, переданы ли обязательные аргументы
        errors += [self.ERR_FIELD_IS_REQUIRED.format(field=attr) for attr in self.FIELDS_REQUIRED if
                   attr not in self.request_data]

        # Проверяем, не переданы ли лишние аргументы
        errors += [self.ERR_NOT_ALLOWED_FIELD.format(field=attr) for attr in self.request_data if
                   attr not in self.fields_allowed]

        if errors:
            logger.error(f'{errors}')
            raise ValidateError({'errors': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        errors += self._validate_fields_format()

        if errors:
            logger.error(f'{errors}')
            raise ValidateError({'errors': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        errors += self._validate_fields_values()

        if errors:
            logger.error(f'{errors}')
            raise ValidateError({'errors': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def validate_value_fields_for_create_child(self, **kwargs):
        """
        Метод сверяет переданные значения project_id, item_type, item со значениями этих полей у родителя,
        """

        errors = []
        if str(kwargs.get('project_id')) != str(self.request_data['project_id']):
            errors.append(f"Value 'project_id' must match the parent")
        if str(kwargs.get('item_type')) != str(self.request_data['item_type']):
            errors.append(f"Value 'item_type' must match the parent")
        if str(kwargs.get('item')) != str(self.request_data['item']):
            errors.append(f"Value 'item' must match the parent")
        if len(kwargs.get('path')) % 10 != 0:
            errors.append({'error': f'For object id {kwargs.get("id")} value field "path" not a multiple of 10. '
                                    f'Field "path" generation error.'})
        if errors:
            logger.error(f'{errors}')
            raise ValidateError({'errors': errors}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    def _validate_fields_format(self):
        """
        Метод проверяет типы (форматы) полей
        """
        errors = []

        # Проверка форматов переданных полей
        project_id = self.request_data.get('project_id')
        if not isinstance(project_id, uuid.UUID):
            try:
                uuid.UUID(project_id)
            except (AttributeError, ValueError, TypeError) as e:
                errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="project_id", format="uuid"))

        item_type = self.request_data.get('item_type')
        if not isinstance(item_type, str):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="item_type", format="str"))

        item = self.request_data.get('item')
        if not isinstance(item, str):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="item", format="str"))

        inner_order = self.request_data.get('inner_order')
        if inner_order and not isinstance(inner_order, str):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="inner_order", format="str"))

        attributes = self.request_data.get('attributes')
        if attributes:
            if isinstance(attributes, str):
                try:
                    attr_dict = json.loads(attributes)
                    if not isinstance(attr_dict, dict):
                        errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="attributes", format="json"))
                except json.decoder.JSONDecodeError:
                    errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="attributes", format="json"))
            else:
                errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="attributes", format="json"))

        destination_node_id = self.request_data.get('destination_node_id')
        if destination_node_id and not isinstance(destination_node_id, int):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="destination_node_id", format="int"))

        new_parent_id = self.request_data.get('new_parent_id')
        if new_parent_id and not isinstance(new_parent_id, int):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="new_parent_id", format="int"))

        if 'pk' in self.request_data.keys():
            _pk = self.request_data.get('pk')
            if not _pk or not isinstance(_pk, int):
                errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field="pk", format="int"))

        affect_descendants = self.request_data.get('affect_descendants')
        if affect_descendants is not None and not isinstance(affect_descendants, bool):
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field='affect_descendants', format='bool'))

        depth = self.request_data.get('depth')
        if depth is not None and not isinstance(depth, int):
            try:
                self.request_data['depth'] = int(depth)
            except ValueError:
                errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field='depth', format='int'))

        return errors

    def _validate_fields_values(self):
        """
        Метод проверяет значения полей
        """
        errors = []

        sort_by_id = self.request_data.get('sort_by_id')
        if sort_by_id is not None and sort_by_id.lower() != 'true':
            errors.append(self.ERR_WRONG_FORMAT_FIELD.format(field='sort_by_id', format='true'))

        hidden = self.request_data.get('hidden')
        if hidden is not None and hidden is not True:
            errors.append('hidden can be None or True')

        for attr in self.request_data:
            value = self.request_data[attr]
            if type(value) is int and value < 1:
                errors.append(self.ERR_FIELD_INTEGER_POSITIVE.format(field=attr))

            if type(value) is str and not value:
                errors.append(self.ERR_FIELD_REQUEST_NOT_EMPTY.format(field=attr))

        return errors
