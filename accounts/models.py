"""User models for accounts app."""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model extending AbstractUser."""

    is_active = models.BooleanField(default=True)


class UserProfile(models.Model):
    """User profile model with bio and social links."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,  # 将 user 字段设为主键，可以提升查询性能
        verbose_name="用户",
    )
    bio = models.TextField(max_length=500, blank=True, verbose_name="个人简介")
    birth_date = models.DateField(null=True, blank=True, verbose_name="生日")
    github_url = models.URLField(max_length=200, blank=True, verbose_name="GitHub 地址")
    homepage_url = models.URLField(max_length=200, blank=True, verbose_name="个人主页")
    blog_url = models.URLField(max_length=200, blank=True, verbose_name="博客地址")
    twitter_url = models.URLField(
        max_length=200,
        blank=True,
        verbose_name="Twitter 地址",
    )
    linkedin_url = models.URLField(
        max_length=200,
        blank=True,
        verbose_name="LinkedIn 地址",
    )
    company = models.CharField(max_length=100, blank=True, verbose_name="公司")
    location = models.CharField(max_length=100, blank=True, verbose_name="位置")

    def __str__(self):
        """Return username as string representation."""
        return self.user.username


class WorkExperience(models.Model):
    """Work experience model for user profiles."""

    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="work_experiences",  # 允许 user.profile.work_experiences.all()
        verbose_name="所属用户",
    )
    company_name = models.CharField(max_length=100, verbose_name="公司名称")
    title = models.CharField(max_length=100, verbose_name="职位")
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="结束日期",
    )  # null=True 表示仍在职
    description = models.TextField(blank=True, verbose_name="工作描述")

    class Meta:
        """Meta configuration for WorkExperience."""

        ordering = ["-start_date"]  # 默认按开始日期降序排列
        verbose_name = "工作经历"
        verbose_name_plural = verbose_name


class Education(models.Model):
    """Education model for user profiles."""

    profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="educations",  # 允许 user.profile.educations.all()
        verbose_name="所属用户",
    )
    institution_name = models.CharField(max_length=100, verbose_name="学校/机构名称")
    degree = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="学位",
    )  # 例如：本科, 硕士
    field_of_study = models.CharField(max_length=100, verbose_name="专业领域")
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(null=True, blank=True, verbose_name="结束日期")

    class Meta:
        """Meta configuration for Education."""

        ordering = ["-start_date"]
        verbose_name = "学习经历"
        verbose_name_plural = verbose_name
