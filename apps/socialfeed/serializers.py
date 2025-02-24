from rest_framework import serializers
from .models import *

class FeedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedFile
        fields = ['id', 'file']

class CommentFeedSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = CommentFeed
        fields = ['id', 'post', 'user', 'comment_text', 'parent_comment', 'created_at']

class LikeFeedSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = LikeFeed
        fields = ['id', 'post', 'user', 'created_at']

class socialFeedSerializer(serializers.ModelSerializer):
    post_file = FeedFileSerializer(many=True, read_only=True)

    class Meta:
        model = socialFeed
        fields = ['id', 'user', 'text', 'number_comment', 'number_like', 'created_at', 'post_file']


class MysocialFeedSerializer(serializers.ModelSerializer):
    post_file = FeedFileSerializer(many=True, read_only=True)

    class Meta:
        model = socialFeed
        fields = ["id", "user", "text", "block", "block_by", "about_block", "number_comment", "number_like", "created_at", "post_file"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not instance.block:  # If block is False
            data["block_by"] = None
            data["about_block"] = None
        return data

class socialFeedDetailsSerializer(serializers.ModelSerializer):
    post_file = FeedFileSerializer(many=True, read_only=True)
    comments = CommentFeedSerializer(many=True, read_only=True, source="post_comment")
    likes = LikeFeedSerializer(many=True, read_only=True, source="post_like")

    class Meta:
        model = socialFeed
        fields = [
            'id',
            'user',
            'text',
            'number_comment',
            'number_like',
            'created_at',
            'post_file',
            'comments',
            'likes',
        ]
