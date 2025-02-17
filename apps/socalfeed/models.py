from django.db import models
from apps.user.models import User

class SocalFeed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="post_user")
    text = models.TextField()
    block = models.BooleanField(default=False)
    block_by = models.CharField(max_length=5, default="Admin")
    about_block = models.TextField(null=True, blank=True)
    number_comment = models.IntegerField(default=0)
    number_like = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Ensure to call the parent class save method
        super().save(*args, **kwargs)

    def update_comment_count(self):
        self.number_comment = self.post_comment.count()
        self.save()

    def update_like_count(self):
        self.number_like = self.post_like.count()
        self.save()

class FeedFile(models.Model):
    post = models.ForeignKey(SocalFeed, on_delete=models.CASCADE, related_name="post_file")
    file = models.FileField(upload_to="socal_feed/", blank=True, null=True)

class CommentFeed(models.Model):
    post = models.ForeignKey(SocalFeed, on_delete=models.CASCADE, related_name="post_comment")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comment_user")
    comment_text = models.TextField()
    parent_comment = models.ForeignKey("CommentFeed", on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.post.update_comment_count()

class LikeFeed(models.Model):
    post = models.ForeignKey(SocalFeed, on_delete=models.CASCADE, related_name="post_like")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="like_user")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.post.update_like_count()
