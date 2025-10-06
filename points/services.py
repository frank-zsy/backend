"""积分系统的业务逻辑服务层, 提供积分发放和消费功能."""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.utils.text import slugify

from .models import PointSource, PointTransaction, Tag

User = get_user_model()
logger = logging.getLogger(__name__)


# 定义一个自定义异常，便于上层逻辑捕获
class InsufficientPointsError(Exception):
    """当用户积分不足时抛出此异常."""

    pass


@transaction.atomic
def grant_points(
    user: User,
    points: int,
    description: str,
    tag_names: list[str],
    source_object=None,
) -> PointSource:
    """
    为用户发放积分.

    这是一个原子操作.

    Args:
        user (User): 获得积分的用户.
        points (int): 发放的积分数量, 必须为正数.
        description (str): 积分来源描述, 将记录在流水中.
        tag_names (list[str]): 一个包含标签名称的列表. 如果标签不存在, 会自动创建.
        source_object (models.Model, optional): 关联的源对象, 用于追溯.

    Returns:
        PointSource: 新创建的积分来源对象.

    Raises:
        ValueError: 如果 points 不是正数.

    """
    if not isinstance(points, int) or points <= 0:
        msg = "发放的积分必须是正整数。"
        raise ValueError(msg)

    # 1. 处理标签：获取或创建（Get or Create）
    # 支持使用 name 或 slug 来查找标签
    tags_to_add = []
    for name_or_slug in tag_names:
        # 先尝试通过 slug 或 name 查找
        tag = Tag.objects.filter(Q(slug=name_or_slug) | Q(name=name_or_slug)).first()

        if tag is None:
            # 如果不存在，创建新标签（使用输入作为 name，生成 slug）
            tag_slug = slugify(name_or_slug)
            # 如果 slug 为空（如纯中文），使用原值
            if not tag_slug:
                tag_slug = name_or_slug
            tag, _ = Tag.objects.get_or_create(
                name=name_or_slug, defaults={"slug": tag_slug}
            )

        tags_to_add.append(tag)

    # 2. 创建积分来源（积分桶）
    new_source = PointSource.objects.create(
        user=user,
        initial_points=points,
        remaining_points=points,
    )
    # 关联标签
    new_source.tags.set(tags_to_add)

    # 3. 记录积分流水（账本）
    PointTransaction.objects.create(
        user=user,
        points=points,  # 正数表示增加
        transaction_type=PointTransaction.TransactionType.EARN,
        description=description,
    )

    logger.info(
        "积分发放成功: 用户=%s (ID=%s), 积分=%s, 标签=%s, 描述=%s",
        user.username,
        user.id,
        points,
        tag_names,
        description,
    )

    return new_source


@transaction.atomic
def spend_points(
    user: User,
    amount: int,
    description: str,
    priority_tag_name: str | None = None,
) -> PointTransaction:
    """
    消费用户的积分.

    这是一个原子操作, 并实现了优先扣除逻辑.

    Args:
        user (User): 消费积分的用户.
        amount (int): 消费的积分数量, 必须为正数.
        description (str): 消费描述, 将记录在流水中.
        priority_tag_name (str | None, optional): 优先扣除的标签名称.

    Returns:
        PointTransaction: 新创建的消费流水对象.

    Raises:
        ValueError: 如果 amount 不是正数.
        InsufficientPointsError: 如果用户总积分不足以消费.

    """
    if not isinstance(amount, int) or amount <= 0:
        msg = "消费的积分必须是正整数。"
        raise ValueError(msg)

    # 1. 快速失败：先检查总余额是否足够（使用行级锁确保并发安全）
    # 锁定所有可用的积分来源，防止并发修改
    all_sources = PointSource.objects.filter(
        user=user, remaining_points__gt=0
    ).select_for_update()

    # 计算总余额
    current_balance = sum(source.remaining_points for source in all_sources)
    if current_balance < amount:
        msg = f"积分不足。当前余额: {current_balance}, 需要: {amount}"
        logger.warning(
            "积分消费失败（余额不足）: 用户=%s (ID=%s), 需要=%s, 当前余额=%s, 描述=%s",
            user.username,
            user.id,
            amount,
            current_balance,
            description,
        )
        raise InsufficientPointsError(msg)

    amount_to_deduct = amount
    consumed_sources_list = []

    # 辅助函数，用于从给定的查询集中扣除积分 (DRY - Don't Repeat Yourself)
    def _deduct_from_sources(queryset, needed):
        consumed = []
        # 使用 select_for_update() 锁定行，防止并发修改
        for source in queryset.select_for_update():
            if needed <= 0:
                break

            deduct_amount = min(source.remaining_points, needed)

            # 使用 F() 表达式防止竞态条件
            source.remaining_points = F("remaining_points") - deduct_amount
            source.save(update_fields=["remaining_points"])

            needed -= deduct_amount
            consumed.append(source)
        return needed, consumed

    # 2. 优先扣除特定标签的积分
    if priority_tag_name:
        priority_sources = PointSource.objects.filter(
            user=user,
            remaining_points__gt=0,
            tags__name=priority_tag_name,
        ).order_by("created_at")  # FIFO

        amount_to_deduct, consumed = _deduct_from_sources(
            priority_sources, amount_to_deduct
        )
        consumed_sources_list.extend(consumed)

    # 3. 如果还不够，扣除默认标签的积分
    if amount_to_deduct > 0:
        default_sources = (
            PointSource.objects.filter(
                user=user, remaining_points__gt=0, tags__is_default=True
            )
            .exclude(id__in=[s.id for s in consumed_sources_list])
            .order_by("created_at")
        )

        amount_to_deduct, consumed = _deduct_from_sources(
            default_sources, amount_to_deduct
        )
        consumed_sources_list.extend(consumed)

    # 4. 如果仍然不够，从任意剩余积分中扣除 (兜底逻辑)
    if amount_to_deduct > 0:
        any_remaining_sources = (
            PointSource.objects.filter(user=user, remaining_points__gt=0)
            .exclude(id__in=[s.id for s in consumed_sources_list])
            .order_by("created_at")
        )

        amount_to_deduct, consumed = _deduct_from_sources(
            any_remaining_sources, amount_to_deduct
        )
        consumed_sources_list.extend(consumed)

    # 安全检查：理论上此时 amount_to_deduct 应该为 0
    if amount_to_deduct > 0:  # pragma: no cover
        # 这个异常不应该被触发，如果触发了说明初始余额检查和扣除逻辑之间存在不一致，
        # 可能是由于非常高的并发导致，但 @transaction.atomic 已经提供了很强的保护。
        msg = "积分扣除逻辑异常：最终应扣除额度大于0。"
        raise Exception(msg)

    # 5. 创建消费流水记录
    spend_transaction = PointTransaction.objects.create(
        user=user,
        points=-amount,  # 负数表示减少
        transaction_type=PointTransaction.TransactionType.SPEND,
        description=description,
    )
    # 关联此次消费涉及到的所有积分来源
    spend_transaction.consumed_sources.set(consumed_sources_list)

    logger.info(
        "积分消费成功: 用户=%s (ID=%s), 消费=%s, 剩余=%s, 消费源数量=%s, 优先标签=%s, 描述=%s",
        user.username,
        user.id,
        amount,
        current_balance - amount,
        len(consumed_sources_list),
        priority_tag_name or "无",
        description,
    )

    return spend_transaction
