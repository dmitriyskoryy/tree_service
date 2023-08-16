from rest_framework import serializers

from .models import Node


class NodeSerializer(serializers.ModelSerializer):
    level_node = serializers.IntegerField(source='get_level_node', read_only=True)

    class Meta:
        model = Node
        fields = ('id', 'path', 'project_id', 'item_type', 'item', 'inner_order', 'attributes', 'level_node',)


class NewNodeSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    inner_order = serializers.CharField(read_only=True)
    level_node = serializers.IntegerField(source='get_level_node', read_only=True)

    class Meta:
        model = Node
        fields = ('id', 'path', 'project_id', 'item_type', 'item', 'inner_order', 'attributes', 'level_node')


class UpdateNodeSerializer(serializers.ModelSerializer):
    path = serializers.CharField(read_only=True)
    inner_order = serializers.CharField(read_only=True)
    level_node = serializers.IntegerField(source='get_level_node', read_only=True)

    class Meta:
        model = Node
        fields = ('id', 'path', 'project_id', 'item_type', 'item', 'inner_order', 'attributes', 'level_node')


class DeleteNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = ('project_id', 'item_type', 'item', 'hidden')
