"""Сервис управления категориями каталога."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, Part
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryUpdate


async def list_categories(db: AsyncSession) -> list[Category]:
    rows = (await db.execute(select(Category).order_by(Category.name))).scalars().all()
    return list(rows)


async def get_category(db: AsyncSession, category_id: UUID) -> Category | None:
    return (
        await db.execute(select(Category).where(Category.id == category_id))
    ).scalar_one_or_none()


async def get_by_slug(db: AsyncSession, slug: str) -> Category | None:
    return (
        await db.execute(select(Category).where(Category.slug == slug))
    ).scalar_one_or_none()


async def build_tree(db: AsyncSession) -> list[CategoryTreeNode]:
    """Собрать дерево категорий одним запросом."""
    all_categories = await list_categories(db)

    nodes: dict[UUID, CategoryTreeNode] = {
        c.id: CategoryTreeNode(id=c.id, name=c.name, slug=c.slug, parent_id=c.parent_id)
        for c in all_categories
    }

    roots: list[CategoryTreeNode] = []
    for c in all_categories:
        node = nodes[c.id]
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


async def create_category(db: AsyncSession, payload: CategoryCreate) -> Category:
    category = Category(
        name=payload.name, slug=payload.slug, parent_id=payload.parent_id
    )
    db.add(category)
    await db.flush()
    return category


async def update_category(
    db: AsyncSession, category: Category, payload: CategoryUpdate
) -> Category:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(category, field, value)
    await db.flush()
    return category


async def count_parts_in_category(db: AsyncSession, category_id: UUID) -> int:
    q = select(func.count()).select_from(Part).where(Part.category_id == category_id)
    return int((await db.execute(q)).scalar_one())


async def count_children(db: AsyncSession, category_id: UUID) -> int:
    q = (
        select(func.count())
        .select_from(Category)
        .where(Category.parent_id == category_id)
    )
    return int((await db.execute(q)).scalar_one())


async def get_descendant_ids(db: AsyncSession, root_id: UUID) -> list[UUID]:
    """Возвращает root_id и id всех его потомков (рекурсивно)."""
    all_cats = await list_categories(db)
    children_map: dict[UUID, list[UUID]] = {}
    for c in all_cats:
        if c.parent_id is not None:
            children_map.setdefault(c.parent_id, []).append(c.id)

    result: list[UUID] = [root_id]
    stack: list[UUID] = [root_id]
    while stack:
        node = stack.pop()
        for child in children_map.get(node, []):
            result.append(child)
            stack.append(child)
    return result


async def delete_category(db: AsyncSession, category: Category) -> None:
    await db.delete(category)
    await db.flush()
