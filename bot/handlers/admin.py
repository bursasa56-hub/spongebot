from __future__ import annotations

import html
import logging
import secrets
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from ..db.models import Broadcast, Sponsor, TaskItem, User, Withdrawal
from ..keyboards.admin import (
    admin_menu_kb,
    back_to_admin_kb,
    promos_admin_kb,
    settings_admin_kb,
    sponsor_channel_subtype_kb,
    sponsor_limit_kb,
    sponsor_type_kb,
    sponsors_admin_kb,
    task_channel_subtype_kb,
    task_duration_kb,
    task_quota_kb,
    task_type_kb,
    tasks_admin_kb,
)
from ..middlewares.admin_filter import IsAdmin
from ..services.promos import (
    PromoError,
    create_promo,
    delete_promo,
    list_promos,
)
from ..services.settings import API_BASE_URL_KEY, get_setting, set_setting
from ..services.snippets import build_snippet
from ..services.stats import get_stats
from ..services.subscriptions import (
    SponsorError,
    add_bot_sponsor,
    add_channel_sponsor,
    all_sponsors,
    cleanup_expired_sponsors,
    delete_sponsor,
    parse_chat_ref,
    sponsor_status,
)
from ..services.withdrawals import mark_paid
from ..utils.assets import replace_screen
from ..utils.stars import format_stars, stars_to_tenths
from ..utils.emoji import EMOJI_IDS

router_admin = Router()
logger = logging.getLogger(__name__)


class AdminStates(StatesGroup):
    sponsor_subtype = State()
    sponsor_link = State()
    sponsor_hours = State()
    sponsor_quota = State()
    task_type = State()
    task_subtype = State()
    task_link = State()
    task_title = State()
    task_reward = State()
    task_hours = State()
    task_quota = State()
    settings_api_url = State()
    broadcast_text = State()
    promo_code = State()
    promo_stars = State()
    promo_uses = State()
    reset_user_id = State()


def stats_text(stats) -> str:
    return (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: {stats.total_users}\n"
        f"🆕 Новых за сегодня: {stats.new_today}\n"
        f"📅 Новых за 7 дней: {stats.new_week}\n"
        f"🗓 Новых за месяц: {stats.new_month}\n"
        f"🤝 Приглашено друзей: {stats.referrals}\n"
        f"💰 Начислено: {format_stars(stats.earned_tenths)}\n"
        f"💸 Выплачено: {format_stars(stats.withdrawn_tenths)}\n"
        f"⏳ Активных заявок: {stats.pending_withdrawals}\n"
        f"✅ Выполнено заданий: {stats.tasks_done}"
    )


async def _send_snippet(message, session, api_key, *, task_id=None, sponsor_id=None) -> None:
    api_base = await get_setting(session, API_BASE_URL_KEY)
    snippet = build_snippet(api_base, api_key, task_id=task_id, sponsor_id=sponsor_id)
    await message.answer(
        "🔑 <b>Код для партнёрского бота:</b>\n<pre><code>"
        + html.escape(snippet)
        + "</code></pre>"
    )


@router_admin.message(Command("admin"), IsAdmin())
async def admin_panel(message: Message) -> None:
    await message.answer("🛠 <b>Админ-панель</b>", reply_markup=admin_menu_kb())


@router_admin.message(Command("emoji"), IsAdmin())
async def admin_emoji_info(message: Message, bot) -> None:
    try:
        sticker_set = await bot.get_sticker_set("vector_icons_by_fStikBot")
    except Exception as exc:
        await message.answer(f"❌ Не удалось получить набор: <code>{html.escape(str(exc))}</code>")
        return
    lines = [
        f"name={sticker_set.name}",
        f"type={getattr(sticker_set, 'sticker_type', '?')}",
        f"stickers={len(sticker_set.stickers)}",
        f"loaded={len(EMOJI_IDS)}",
        "",
    ]
    for st in sticker_set.stickers[:50]:
        lines.append(f"{getattr(st, 'emoji', None)} -> {getattr(st, 'custom_emoji_id', None)}")
    text = "\n".join(lines)
    for i in range(0, len(text), 3500):
        await message.answer(f"<pre>{html.escape(text[i:i + 3500])}</pre>")


@router_admin.callback_query(F.data == "admin:menu", IsAdmin())
async def admin_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await replace_screen(callback, "🛠 <b>Админ-панель</b>", admin_menu_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:reset", IsAdmin())
async def admin_reset_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminStates.reset_user_id)
    await replace_screen(
        callback,
        "Отправь Telegram ID пользователя, у которого нужно обнулить звёзды.",
        back_to_admin_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.reset_user_id, IsAdmin())
async def admin_reset_user(message: Message, state: FSMContext, session) -> None:
    try:
        user_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Отправь числовой ID.", reply_markup=back_to_admin_kb())
        return
    user = await session.get(User, user_id)
    if user is None:
        await message.answer(
            "❌ Пользователь не найден.", reply_markup=back_to_admin_kb()
        )
        return
    user.balance_tenths = 0
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Звёзды пользователя <code>{user_id}</code> обнулены.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data == "admin:stats", IsAdmin())
async def admin_stats(callback: CallbackQuery, session) -> None:
    stats = await get_stats(session)
    await replace_screen(callback, stats_text(stats), admin_menu_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:settings", IsAdmin())
async def admin_settings(callback: CallbackQuery, session) -> None:
    value = await get_setting(session, API_BASE_URL_KEY)
    shown = html.escape(value) if value else "не задан"
    await replace_screen(
        callback,
        f"⚙️ <b>Настройки</b>\n\nАдрес API: <code>{shown}</code>",
        settings_admin_kb(),
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:settings:api_url", IsAdmin())
async def admin_settings_api_url(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.settings_api_url)
    await replace_screen(
        callback,
        "Отправь базовый адрес API, например https://example.com",
        back_to_admin_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.settings_api_url, IsAdmin())
async def admin_settings_api_url_save(message: Message, state: FSMContext, session) -> None:
    value = (message.text or "").strip()
    if not value:
        await message.answer("Введи адрес.")
        return
    await set_setting(session, API_BASE_URL_KEY, value)
    await state.clear()
    await message.answer(
        f"✅ Адрес API сохранён: <code>{html.escape(value)}</code>",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data == "admin:sponsors", IsAdmin())
async def admin_sponsors(callback: CallbackQuery, session) -> None:
    await cleanup_expired_sponsors(session)
    sponsors = await all_sponsors(session)
    statuses = {s.id: await sponsor_status(session, s) for s in sponsors}
    await replace_screen(
        callback,
        "📢 <b>Обязательные спонсоры</b>",
        sponsors_admin_kb(sponsors, statuses),
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:add", IsAdmin())
async def admin_sponsor_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await replace_screen(callback, "Какого типа спонсор?", sponsor_type_kb())
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:sponsor:type:"), IsAdmin())
async def admin_sponsor_type(callback: CallbackQuery, state: FSMContext) -> None:
    sponsor_type = callback.data.split(":")[3]
    await state.update_data(type=sponsor_type)
    if sponsor_type == "channel":
        await state.set_state(AdminStates.sponsor_subtype)
        await replace_screen(
            callback, "Какой это канал?", sponsor_channel_subtype_kb()
        )
    else:
        await replace_screen(callback, "На сколько?", sponsor_limit_kb())
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:sponsor:subtype:"), IsAdmin())
async def admin_sponsor_subtype(callback: CallbackQuery, state: FSMContext) -> None:
    subtype = callback.data.split(":")[3]
    await state.update_data(subtype=subtype, type="channel")
    await replace_screen(callback, "На сколько?", sponsor_limit_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:limit:quota", IsAdmin())
async def admin_sponsor_limit_quota(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_quota)
    await replace_screen(callback, "Сколько прохождений?", back_to_admin_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:limit:time", IsAdmin())
async def admin_sponsor_limit_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.sponsor_hours)
    await replace_screen(callback, "Сколько часов?", back_to_admin_kb())
    await callback.answer()


@router_admin.callback_query(F.data == "admin:sponsor:limit:forever", IsAdmin())
async def admin_sponsor_limit_forever(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(hours=0, quota=0)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _ask_sponsor_link(callback.message, state)
    await callback.answer()


async def _ask_sponsor_link(message, state: FSMContext) -> None:
    data = await state.get_data()
    if data.get("type") == "channel" and data.get("subtype") == "private_request":
        prompt = "Отправь id частного чата/канала -100... (бот должен быть админом)."
    else:
        prompt = "Отправь ссылку (@username, t.me/... или id -100...)."
    await state.set_state(AdminStates.sponsor_link)
    await message.answer(prompt, reply_markup=back_to_admin_kb())


@router_admin.message(AdminStates.sponsor_hours, IsAdmin())
async def admin_sponsor_hours(message: Message, state: FSMContext) -> None:
    try:
        hours = int((message.text or "").strip())
        if hours < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(hours=hours, quota=0)
    await _ask_sponsor_link(message, state)


@router_admin.message(AdminStates.sponsor_quota, IsAdmin())
async def admin_sponsor_quota(message: Message, state: FSMContext) -> None:
    try:
        quota = int((message.text or "").strip())
        if quota < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(quota=quota, hours=0)
    await _ask_sponsor_link(message, state)


@router_admin.message(AdminStates.sponsor_link, IsAdmin())
async def admin_sponsor_link(message: Message, state: FSMContext, session, bot) -> None:
    await state.update_data(link=(message.text or "").strip())
    await _finish_sponsor(bot, message, state, session)


async def _finish_sponsor(bot, message, state: FSMContext, session) -> None:
    data = await state.get_data()
    hours = data.get("hours", 0)
    quota = data.get("quota", 0)
    link = data.get("link", "")
    sponsor_type = data.get("type", "channel")
    expires_at = datetime.utcnow() + timedelta(hours=hours) if hours else None
    try:
        if sponsor_type == "channel":
            sponsor = await add_channel_sponsor(
                session,
                bot,
                link,
                subtype=data.get("subtype", "public_channel"),
                expires_at=expires_at,
                max_completions=quota,
            )
        else:
            sponsor = await add_bot_sponsor(
                session,
                link,
                expires_at=expires_at,
                max_completions=quota,
            )
    except SponsorError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=admin_menu_kb())
        return
    await state.clear()
    await message.answer(
        f"✅ Спонсор «{html.escape(sponsor.title)}» добавлен в обязательные.",
        reply_markup=admin_menu_kb(),
    )
    if sponsor.type == "bot":
        await _send_snippet(message, session, sponsor.api_key, sponsor_id=sponsor.id)


@router_admin.callback_query(F.data.startswith("admin:sponsor:code:"), IsAdmin())
async def admin_sponsor_code(callback: CallbackQuery, session) -> None:
    sponsor_id = int(callback.data.split(":")[3])
    sponsor = await session.get(Sponsor, sponsor_id)
    if sponsor is None:
        await callback.answer("Спонсор не найден.", show_alert=True)
        return
    await _send_snippet(callback.message, session, sponsor.api_key, sponsor_id=sponsor.id)
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:sponsor:del:"), IsAdmin())
async def admin_del_sponsor(callback: CallbackQuery, session) -> None:
    await cleanup_expired_sponsors(session)
    sponsor_id = int(callback.data.split(":")[3])
    try:
        await delete_sponsor(session, sponsor_id)
    except Exception:
        await session.rollback()
        logger.exception("Failed to delete sponsor %s", sponsor_id)
        await callback.answer("❌ Не удалось удалить спонсора.", show_alert=True)
        return
    sponsors = await all_sponsors(session)
    statuses = {s.id: await sponsor_status(session, s) for s in sponsors}
    await replace_screen(
        callback,
        "📢 <b>Обязательные спонсоры</b>",
        sponsors_admin_kb(sponsors, statuses),
    )
    await callback.answer("Удалено")


@router_admin.callback_query(F.data == "admin:promos", IsAdmin())
async def admin_promos(callback: CallbackQuery, session) -> None:
    promos = await list_promos(session)
    await replace_screen(callback, "🎟 <b>Промокоды</b>", promos_admin_kb(promos))
    await callback.answer()


@router_admin.callback_query(F.data == "admin:promo:add", IsAdmin())
async def admin_promo_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AdminStates.promo_code)
    await replace_screen(callback, "Отправь текст промокода.", back_to_admin_kb())
    await callback.answer()


@router_admin.message(AdminStates.promo_code, IsAdmin())
async def admin_promo_code(message: Message, state: FSMContext) -> None:
    await state.update_data(code=(message.text or "").strip())
    await state.set_state(AdminStates.promo_stars)
    await message.answer(
        "Сколько звёзд даёт промокод? (целое число)",
        reply_markup=back_to_admin_kb(),
    )


@router_admin.message(AdminStates.promo_stars, IsAdmin())
async def admin_promo_stars(message: Message, state: FSMContext) -> None:
    try:
        stars = int((message.text or "").strip())
        if stars <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введи целое число больше 0.", reply_markup=back_to_admin_kb()
        )
        return
    await state.update_data(stars=stars)
    await state.set_state(AdminStates.promo_uses)
    await message.answer(
        "Лимит использований? (0 = без лимита)", reply_markup=back_to_admin_kb()
    )


@router_admin.message(AdminStates.promo_uses, IsAdmin())
async def admin_promo_uses(message: Message, state: FSMContext, session) -> None:
    try:
        max_uses = int((message.text or "").strip())
        if max_uses < 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введи целое число ≥ 0.", reply_markup=back_to_admin_kb()
        )
        return
    data = await state.get_data()
    try:
        promo = await create_promo(session, data["code"], data["stars"], max_uses)
    except PromoError as exc:
        await state.clear()
        await state.set_state(AdminStates.promo_code)
        await message.answer(
            f"❌ {exc}\nОтправь промокод заново.",
            reply_markup=back_to_admin_kb(),
        )
        return
    await state.clear()
    await message.answer(
        f"✅ Промокод <code>{html.escape(promo.code)}</code> создан.",
        reply_markup=admin_menu_kb(),
    )


@router_admin.callback_query(F.data.startswith("admin:promo:del:"), IsAdmin())
async def admin_promo_del(callback: CallbackQuery, session) -> None:
    promo_id = int(callback.data.split(":")[3])
    deleted = False
    try:
        deleted = await delete_promo(session, promo_id)
    except Exception:
        deleted = False
    promos = await list_promos(session)
    await replace_screen(callback, "🎟 <b>Промокоды</b>", promos_admin_kb(promos))
    await callback.answer("Удалено" if deleted else "Промокод не найден.")


@router_admin.callback_query(F.data == "admin:tasks", IsAdmin())
async def admin_tasks(callback: CallbackQuery, session) -> None:
    res = await session.execute(select(TaskItem).order_by(TaskItem.id))
    tasks = list(res.scalars().all())
    await replace_screen(callback, "📋 <b>Задания</b>", tasks_admin_kb(tasks))
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:del:"), IsAdmin())
async def admin_del_task(callback: CallbackQuery, session) -> None:
    task_id = int(callback.data.split(":")[3])
    task = await session.get(TaskItem, task_id)
    if task is not None:
        await session.delete(task)
        await session.commit()
    res = await session.execute(select(TaskItem))
    tasks = list(res.scalars().all())
    await replace_screen(callback, "📋 <b>Задания</b>", tasks_admin_kb(tasks))
    await callback.answer("Удалено")


@router_admin.callback_query(F.data.startswith("wd:paid:"), IsAdmin())
async def admin_mark_paid(callback: CallbackQuery, session, bot) -> None:
    withdrawal_id = int(callback.data.split(":")[2])
    withdrawal = await mark_paid(session, withdrawal_id)
    if withdrawal is None:
        await callback.answer("Уже выплачено или недостаточно баланса.", show_alert=True)
        return
    try:
        await callback.message.edit_text(
            callback.message.html_text + "\n\n✅ <b>Выплачено</b>"
        )
    except Exception:
        pass
    try:
        await bot.send_message(
            withdrawal.user_id,
            "🎁 Админ отправил вам подарок! Проверьте подарки в Telegram.",
        )
    except Exception:
        pass
    await callback.answer("Отмечено как выплачено")


@router_admin.callback_query(F.data.startswith("wd:paid:"))
async def admin_mark_paid_denied(callback: CallbackQuery) -> None:
    await callback.answer("❌ Недостаточно прав.", show_alert=True)


@router_admin.callback_query(F.data == "admin:withdrawals", IsAdmin())
async def admin_withdrawals(callback: CallbackQuery, session) -> None:
    res = await session.execute(
        select(Withdrawal)
        .where(Withdrawal.status == "pending")
        .order_by(Withdrawal.id)
    )
    items = list(res.scalars().all())
    if not items:
        text = "💸 Нет активных заявок."
    else:
        lines = ["💸 <b>Активные заявки на вывод:</b>\n"]
        for w in items:
            lines.append(
                f"#{w.id} — {w.gift_name} ({w.gift_stars}★) → @{w.username_to} "
                f"(id <code>{w.user_id}</code>)"
            )
        text = "\n".join(lines)

    rows = []
    for w in items:
        if w.admin_chat_id is not None and w.admin_msg_id is not None:
            internal = str(w.admin_chat_id).removeprefix("-100")
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"#{w.id}",
                        url=f"https://t.me/c/{internal}/{w.admin_msg_id}",
                    )
                ]
            )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    await replace_screen(
        callback, text, InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await callback.answer()


@router_admin.callback_query(F.data == "admin:task:add", IsAdmin())
async def admin_task_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await replace_screen(callback, "Что за задание?", task_type_kb())
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:type:"), IsAdmin())
async def admin_task_type(callback: CallbackQuery, state: FSMContext) -> None:
    task_type = callback.data.split(":")[3]
    await state.update_data(type=task_type)
    if task_type == "channel":
        await state.set_state(AdminStates.task_subtype)
        await replace_screen(
            callback, "Какой это канал?", task_channel_subtype_kb()
        )
    else:
        await state.set_state(AdminStates.task_link)
        await replace_screen(
            callback,
            "Отправь ссылку (@username или t.me/...).",
            back_to_admin_kb(),
        )
    await callback.answer()


@router_admin.callback_query(F.data.startswith("admin:task:subtype:"), IsAdmin())
async def admin_task_subtype(callback: CallbackQuery, state: FSMContext) -> None:
    subtype = callback.data.split(":")[3]
    await state.update_data(subtype=subtype, type="channel")
    await state.set_state(AdminStates.task_link)
    await replace_screen(
        callback,
        "Отправь ссылку на канал (@username, t.me/... или id -100...). "
        "Для частного канала отправь его id -100..., бот должен быть админом.",
        back_to_admin_kb(),
    )
    await callback.answer()


@router_admin.message(AdminStates.task_link, IsAdmin())
async def admin_task_link(message: Message, state: FSMContext) -> None:
    await state.update_data(url=(message.text or "").strip())
    await state.set_state(AdminStates.task_title)
    await message.answer(
        "Отправь название задания.", reply_markup=back_to_admin_kb()
    )


@router_admin.message(AdminStates.task_title, IsAdmin())
async def admin_task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(AdminStates.task_reward)
    await message.answer(
        "Сколько звёзд за задание? Например 0.5", reply_markup=back_to_admin_kb()
    )


@router_admin.message(AdminStates.task_reward, IsAdmin())
async def admin_task_reward(message: Message, state: FSMContext) -> None:
    try:
        reward = stars_to_tenths(float((message.text or "").replace(",", ".")))
    except ValueError:
        await message.answer("Введи число, например 0.5", reply_markup=back_to_admin_kb())
        return

    await state.update_data(reward=reward)
    await message.answer("Срок действия?", reply_markup=task_duration_kb())


@router_admin.callback_query(F.data.startswith("admin:task:duration:"), IsAdmin())
async def admin_task_duration(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[3]
    if value == "0":
        await state.update_data(hours=0)
        await replace_screen(callback, "Лимит прохождений?", task_quota_kb())
    else:
        await state.set_state(AdminStates.task_hours)
        await replace_screen(callback, "Сколько часов?", back_to_admin_kb())
    await callback.answer()


@router_admin.message(AdminStates.task_hours, IsAdmin())
async def admin_task_hours(message: Message, state: FSMContext) -> None:
    try:
        hours = int((message.text or "").strip())
        if hours < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(hours=hours)
    await message.answer("Лимит прохождений?", reply_markup=task_quota_kb())


@router_admin.callback_query(F.data.startswith("admin:task:quota:"), IsAdmin())
async def admin_task_quota_choice(
    callback: CallbackQuery, state: FSMContext, session, bot
) -> None:
    value = callback.data.split(":")[3]
    if value == "0":
        await state.update_data(quota=0)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await _after_task_quota(bot, callback.message, state, session)
    else:
        await state.set_state(AdminStates.task_quota)
        await replace_screen(callback, "Сколько прохождений?", back_to_admin_kb())
    await callback.answer()


@router_admin.message(AdminStates.task_quota, IsAdmin())
async def admin_task_quota(message: Message, state: FSMContext, session, bot) -> None:
    try:
        quota = int((message.text or "").strip())
        if quota < 0:
            raise ValueError
    except ValueError:
        await message.answer("Введи целое число ≥ 0.")
        return
    await state.update_data(quota=quota)
    await _after_task_quota(bot, message, state, session)


async def _after_task_quota(bot, message, state: FSMContext, session) -> None:
    data = await state.get_data()
    api_key = secrets.token_urlsafe(32) if data.get("type") == "bot" else None
    await _finish_task(bot, message, state, session, api_key)


async def _finish_task(
    bot, message, state: FSMContext, session, api_key=None
) -> None:
    data = await state.get_data()
    subtype = data.get("subtype", "public_channel")
    hours = data.get("hours", 0)
    quota = data.get("quota", 0)
    expires_at = datetime.utcnow() + timedelta(hours=hours) if hours else None

    try:
        chat_ref = parse_chat_ref(data["url"])
    except SponsorError as exc:
        await state.clear()
        await message.answer(f"❌ {exc}", reply_markup=admin_menu_kb())
        return

    url = data["url"]
    if data["type"] == "channel" and subtype == "private_request":
        try:
            chat = await bot.get_chat(chat_ref)
        except Exception:
            await state.clear()
            await message.answer(
                "❌ Не удалось получить канал. Проверьте id и что бот добавлен в канал.",
                reply_markup=admin_menu_kb(),
            )
            return
        try:
            me = await bot.get_chat_member(chat_id=chat.id, user_id=bot.id)
        except Exception:
            await state.clear()
            await message.answer(
                "❌ Бот не администратор этого канала. Добавьте бота в админы и повторите.",
                reply_markup=admin_menu_kb(),
            )
            return
        if getattr(me, "status", None) not in {"administrator", "creator"}:
            await state.clear()
            await message.answer(
                "❌ Бот не администратор этого канала. Добавьте бота в админы и повторите.",
                reply_markup=admin_menu_kb(),
            )
            return
        try:
            invite = await bot.create_chat_invite_link(
                chat.id, creates_join_request=True
            )
        except Exception:
            await state.clear()
            await message.answer(
                "❌ Не удалось создать ссылку-приглашение.",
                reply_markup=admin_menu_kb(),
            )
            return
        url = invite.invite_link

    task = TaskItem(
        type=data["type"],
        subtype=subtype,
        title=data["title"],
        url=url,
        chat_id=chat_ref if data["type"] == "channel" else None,
        reward_tenths=data["reward"],
        expires_at=expires_at,
        max_completions=quota,
        api_key=api_key,
    )
    session.add(task)
    await session.commit()
    await state.clear()
    await message.answer(
        f"✅ Задание «{html.escape(task.title)}» добавлено.",
        reply_markup=admin_menu_kb(),
    )
    if task.type == "bot":
        await _send_snippet(message, session, task.api_key, task_id=task.id)


@router_admin.callback_query(F.data.startswith("admin:task:code:"), IsAdmin())
async def admin_task_code(callback: CallbackQuery, session) -> None:
    task_id = int(callback.data.split(":")[3])
    task = await session.get(TaskItem, task_id)
    if task is None:
        await callback.answer("Задание не найдено.", show_alert=True)
        return
    await _send_snippet(callback.message, session, task.api_key, task_id=task.id)
    await callback.answer()


@router_admin.callback_query(F.data == "admin:broadcast", IsAdmin())
async def admin_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await replace_screen(callback, "Отправь текст рассылки.", back_to_admin_kb())
    await callback.answer()


@router_admin.message(AdminStates.broadcast_text, IsAdmin())
async def admin_broadcast_send(message: Message, state: FSMContext, session, bot) -> None:
    await state.clear()
    res = await session.execute(select(User.id).where(User.is_blocked.is_(False)))
    user_ids = list(res.scalars().all())
    sent = failed = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text or "")
            sent += 1
        except Exception:
            failed += 1
    session.add(Broadcast(text=message.text or "", sent_count=sent, failed_count=failed))
    await session.commit()
    await message.answer(
        f"✅ Рассылка завершена. Доставлено: {sent}, ошибок: {failed}.",
        reply_markup=admin_menu_kb(),
    )
