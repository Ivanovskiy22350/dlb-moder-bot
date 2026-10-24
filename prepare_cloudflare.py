"""Guardian Cloudflare update 2.2: all Telegram response templates.

Keep the original companion ZIP. This file overlays the updated Python sources.

Upload this file and Guardian-Telegram-Bot.zip to the repository root.
Create D1 separately and add its UUID as build variable D1_DATABASE_ID.
Optional build variables: WORKER_NAME (default dlb-moder-bot),
D1_DATABASE_NAME (default guardian-moderation).

Build command:
  python prepare_cloudflare.py && python -m venv .build-tools && .build-tools/bin/pip install uv==0.12.23 && .build-tools/bin/uv sync --directory .guardian-build --locked
Deploy command:
  .build-tools/bin/uv run --directory .guardian-build pywrangler deploy

This only prepares files. D1 schema, runtime secrets and Telegram webhook
must still be configured. No credentials belong in this file or the ZIP.
"""

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from uuid import UUID
from zipfile import ZipFile

ARCHIVE_SHA256 = "a9aec418d1fafb00b9a7904ab858e10c54d1f3c60d731b173f82912b83fa327a"
PREFIX = "guardian-bot/cloudflare/"


def prepare(root: Path) -> Path:
    database_id = os.environ.get("D1_DATABASE_ID", "").strip()
    try:
        parsed = UUID(database_id)
        if parsed.int == 0:
            raise ValueError
    except ValueError:
        raise SystemExit("Set build variable D1_DATABASE_ID to the UUID of your D1 database.")
    worker_name = os.environ.get("WORKER_NAME", "dlb-moder-bot").strip()
    database_name = os.environ.get("D1_DATABASE_NAME", "guardian-moderation").strip()
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}", worker_name):
        raise SystemExit("WORKER_NAME must use lowercase letters, digits and hyphens.")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,63}", database_name):
        raise SystemExit("Invalid D1_DATABASE_NAME.")
    archive = root / "Guardian-Telegram-Bot.zip"
    if not archive.is_file():
        raise SystemExit("Upload Guardian-Telegram-Bot.zip beside prepare_cloudflare.py.")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise SystemExit("ZIP version mismatch: use the companion archive supplied with this script.")
    output = root / ".guardian-build"
    with ZipFile(archive) as zipped:
        for item in zipped.infolist():
            if item.is_dir() or not item.filename.startswith(PREFIX):
                continue
            relative = PurePosixPath(item.filename[len(PREFIX):])
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Unsafe archive path.")
            target = output.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zipped.read(item))
    for relative, source in UPDATED_SOURCES.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
    config_path = output / "wrangler.jsonc"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["name"] = worker_name
    config["keep_vars"] = True  # Preserve runtime dashboard variables such as BOT_USERNAME.
    config["d1_databases"] = [{"binding": "DB", "database_name": database_name,
                               "database_id": str(parsed)}]
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("Python Worker prepared in .guardian-build. Runtime secrets are configured separately.")
    return output


# Embedded sources keep this update installable from a phone with one upload.
UPDATED_SOURCES = {'README_TEXTS_RU.md': '# Guardian 2.2 — все шаблоны ответов Cloudflare\n'
                       '\n'
                       '## Установка с телефона\n'
                       '\n'
                       'Замените только `prepare_cloudflare.py` в корне репозитория, сохраните '
                       'коммит в main.\n'
                       'Исходный `Guardian-Telegram-Bot.zip` оставьте на месте. Скрипт накладывает '
                       'новые модули\n'
                       'на исходный архив. Дождитесь успешной сборки и развёртывания Cloudflare.\n'
                       'Команды сборки и deploy прежние, миграция D1 не нужна.\n'
                       'Версию можно проверить по стандартной справке: «Guardian 2.2» (если help '
                       'не заменён).\n'
                       'Надёжная проверка возможностей: `/texts help` возвращает описание шаблона '
                       'help.\n'
                       '\n'
                       'Сборка сохраняет существующие переменные Cloudflare (`keep_vars: true`),\n'
                       'в том числе BOT_USERNAME. Уже удалённое значение этот флаг не '
                       'восстанавливает:\n'
                       'BOT_USERNAME должен быть задан в runtime-настройках, без @. Токены в код '
                       'не добавляйте.\n'
                       '\n'
                       '## Команды в группе\n'
                       '\n'
                       'Все изменения доступны только текущим администраторам супергруппы, от '
                       'личного\n'
                       'аккаунта. Они хранятся отдельно для каждой группы и переживают '
                       'перезапуск/деплой.\n'
                       'В личных сообщениях остаётся стандартная справка: администратор одной '
                       'группы\n'
                       'не может менять глобальные ответы бота для других людей.\n'
                       '\n'
                       '- `/texts` — первая страница каталога; `/texts 2`, `/texts 3` — '
                       'остальные.\n'
                       '- `/texts help` — допустимые подстановки и команды для выбранного '
                       'шаблона.\n'
                       '- `/settext help Моя новая справка` — заменить справку этой группы.\n'
                       '- `/settext start Привет! Команды: /help` — заменить ответ на /start в '
                       'группе.\n'
                       '- `/previewtext help` — показать сохранённый шаблон с примерами значений.\n'
                       '- `/resettext help` — вернуть стандартную справку.\n'
                       '\n'
                       'Для многострочного текста, жирного начертания, ссылок или пользовательских '
                       'эмодзи\n'
                       'отправьте образец отдельным сообщением. Ответьте на него `/settext help`.\n'
                       'Можно использовать подпись к медиа как образец. Максимум 4000 единиц '
                       'UTF-16\n'
                       '(обычный смайлик часто занимает две), 100 элементов оформления.\n'
                       '`/edit Новый текст` ответом на собственное текстовое сообщение бота меняет '
                       'только\n'
                       'это сообщение. `/settext` влияет на будущие ответы. `/emoji` ответом на '
                       'образец\n'
                       'показывает ID пользовательских эмодзи.\n'
                       '\n'
                       'Для help/start фигурные скобки сохраняются буквально: можно писать '
                       'примеры\n'
                       '`/settext mute ID {uid}`. У остальных шаблонов принимаются только '
                       'подстановки\n'
                       'из `/texts ИМЯ`. Текст не исполняется как Python или HTML. Подстановки не\n'
                       'разбираются повторно. Неизвестная подстановка не перезаписывает старый '
                       'шаблон.\n'
                       '\n'
                       'Настраиваются тексты сообщений, результаты команд, ошибки, уведомления '
                       'кнопок\n'
                       'и их подписи. Права пользователей, действия модерации и callback-команды '
                       'от\n'
                       'смены текста не меняются. validation_error задаёт общий текст ошибок '
                       'формата;\n'
                       'его {detail} содержит исходное объяснение, например неправильный срок '
                       'мута.\n'
                       '\n'
                       'В сообщениях поддерживаются оформление и пользовательские эмодзи. '
                       'Telegram\n'
                       'может запретить отправку таких эмодзи конкретному боту; в этом случае '
                       'повторяется\n'
                       'только отправка текста без custom_emoji, не наказание. В коротких '
                       'всплывающих\n'
                       'уведомлениях и подписях кнопок выводится простой текст, с ограничениями '
                       '200 и\n'
                       '64 единицы UTF-16 соответственно. /previewtext показывает образец '
                       'сообщения,\n'
                       'а фактическая кнопка/уведомление использует эти ограничения.\n'
                       '\n'
                       'Если подстановки раздули шаблон больше 4096 единиц, используется '
                       'стандартный\n'
                       'шаблон; длинные списки журналов разбиваются на сообщения с сохранением '
                       'оформления.\n'
                       'Сохранение слишком длинного текста отклоняется. Старые шаблоны 2.1 '
                       'сохраняются.\n'
                       'Технические HTTP-ответы webhook и внутренние записи аудита не являются '
                       'текстами\n'
                       'Telegram и не редактируются командами. group_only и callback_group_only '
                       'относятся\n'
                       'к неподдерживаемым контекстам; в личке действуют их стандартные значения.\n'
                       '\n'
                       '## Каталог\n'
                       '\n'
                       '| Имя | Подстановки |\n'
                       '|---|---|\n'
                       '| `mute` | `{minutes}`, `{reason}`, `{uid}` |\n'
                       '| `ban` | `{reason}`, `{uid}` |\n'
                       '| `unban` | `{reason}`, `{uid}` |\n'
                       '| `kick` | `{reason}`, `{uid}` |\n'
                       '| `unmute` | `{reason}`, `{uid}` |\n'
                       '| `warn` | `{count}`, `{limit}`, `{reason}`, `{uid}` |\n'
                       '| `automute` | `{minutes}`, `{reason}`, `{uid}` |\n'
                       '| `welcome` | `{name}` |\n'
                       '| `rules` | — |\n'
                       '| `ping` | — |\n'
                       '| `help` | — |\n'
                       '| `start` | — |\n'
                       '| `id` | `{chat}`, `{uid}` |\n'
                       '| `filters` | `{items}` |\n'
                       '| `filter_row` | `{name}`, `{state}` |\n'
                       '| `state_on` | — |\n'
                       '| `state_off` | — |\n'
                       '| `report` | `{actor}`, `{reason}` |\n'
                       '| `warnings_self` | `{count}` |\n'
                       '| `warnings` | `{count}`, `{uid}` |\n'
                       '| `unwarn` | `{count}`, `{uid}` |\n'
                       '| `resetwarns` | `{count}`, `{uid}` |\n'
                       '| `check` | `{delete}`, `{restrict}` |\n'
                       '| `settings` | `{flood_limit}`, `{flood_window}`, `{mute_minutes}`, '
                       '`{warn_limit}`, `{word_count}` |\n'
                       '| `setting_saved` | `{setting}` |\n'
                       '| `words` | `{items}` |\n'
                       '| `words_empty` | — |\n'
                       '| `words_saved` | — |\n'
                       '| `logs` | `{items}` |\n'
                       '| `stats` | `{items}` |\n'
                       '| `logs_empty` | — |\n'
                       '| `stats_empty` | — |\n'
                       '| `log_row` | `{action}`, `{actor}`, `{date}`, `{reason}`, `{uid}` |\n'
                       '| `stat_row` | `{action}`, `{count}` |\n'
                       '| `delete` | — |\n'
                       '| `edit_saved` | — |\n'
                       '| `emoji` | `{items}` |\n'
                       '| `emoji_empty` | — |\n'
                       '| `api_error` | — |\n'
                       '| `validation_error` | `{detail}` |\n'
                       '| `group_only` | — |\n'
                       '| `callback_group_only` | — |\n'
                       '| `callback_saved` | — |\n'
                       '| `callback_retry` | — |\n'
                       '| `warn_automute_failed` | — |\n'
                       '| `warn_automute_success` | `{minutes}` |\n'
                       '| `texts` | `{items}`, `{page}`, `{pages}` |\n'
                       '| `texts_detail` | `{fields}`, `{key}` |\n'
                       '| `texts_no_fields` | — |\n'
                       '| `text_saved` | `{hint}`, `{key}` |\n'
                       '| `welcome_hint` | — |\n'
                       '| `error_edit_reply` | — |\n'
                       '| `error_edit_text` | — |\n'
                       '| `error_edit_rejected` | — |\n'
                       '| `error_template_key` | — |\n'
                       '| `error_template_text` | — |\n'
                       '| `error_reset_usage` | — |\n'
                       '| `error_preview_long` | — |\n'
                       '| `error_admin_only` | — |\n'
                       '| `error_target_channel` | — |\n'
                       '| `error_target_required` | — |\n'
                       '| `error_protected` | — |\n'
                       '| `error_protected_member` | — |\n'
                       '| `error_already_restricted` | — |\n'
                       '| `error_member_missing` | — |\n'
                       '| `error_setting_unknown` | — |\n'
                       '| `error_report_reply` | — |\n'
                       '| `error_report_cooldown` | — |\n'
                       '| `error_positive_integer` | — |\n'
                       '| `error_word_usage` | — |\n'
                       '| `error_word_length` | — |\n'
                       '| `error_word_limit` | — |\n'
                       '| `error_delete_reply` | — |\n'
                       '| `error_mute_duration` | — |\n'
                       '| `error_unknown_command` | — |\n'
                       '| `error_admin_right` | `{right}` |\n'
                       '| `error_bot_right` | `{right}` |\n'
                       '| `error_set_usage` | `{parameters}` |\n'
                       '| `error_range` | `{high}`, `{low}` |\n'
                       '| `error_texts_page` | `{pages}` |\n'
                       '| `button_antiflood` | `{state}` |\n'
                       '| `button_antilinks` | `{state}` |\n'
                       '| `button_antiforward` | `{state}` |\n'
                       '| `button_stopwords` | `{state}` |\n'
                       '| `button_welcome` | `{state}` |\n',
 'src/guardian_cf/app.py': 'import asyncio\n'
                           'import logging\n'
                           'import time\n'
                           'from contextlib import suppress\n'
                           'from datetime import datetime, timedelta, timezone\n'
                           'from weakref import WeakValueDictionary\n'
                           '\n'
                           'from .telegram import (Bot, TelegramAPIError,\n'
                           '    Message, CallbackQuery, ChatPermissions, InlineKeyboardButton, '
                           'InlineKeyboardMarkup,\n'
                           ')\n'
                           '\n'
                           'from .db import Database, PersistentFlood, PersistentCooldowns\n'
                           'from .texts import (FIELDS, PREVIEW, prepared, extract, validate, '
                           'render,\n'
                           '                    template, deliver, units, join_rich, split_rich, '
                           'plain, join_lines)\n'
                           'from .policy import (BOOL_KEYS, LIMITS, Cooldowns, FloodGuard, '
                           'contains_link,\n'
                           '                     duration, forbidden_word, parse_command, '
                           'normalize)\n'
                           '\n'
                           'log = logging.getLogger(__name__)\n'
                           'ADMINS = {"creator", "administrator"}\n'
                           'GROUPS = {"supergroup"}\n'
                           '\n'
                           '\n'
                           '\n'
                           'class UserError(Exception):\n'
                           '    def __init__(self, key, **values):\n'
                           '        self.key, self.values = key, values\n'
                           '        super().__init__(key)\n'
                           '\n'
                           '\n'
                           'class Guardian:\n'
                           '    def __init__(self, bot: Bot, db: Database, username: str):\n'
                           '        self.bot, self.db, self.username = bot, db, username\n'
                           '        self.flood, self.cooldowns = PersistentFlood(db), '
                           'PersistentCooldowns(db)\n'
                           '        self.locks = WeakValueDictionary()\n'
                           '        self.started = time.monotonic()\n'
                           '\n'
                           '    def lock(self, chat):\n'
                           '        lock = self.locks.get(chat)\n'
                           '        if lock is None:\n'
                           '            lock = self.locks[chat] = asyncio.Lock()\n'
                           '        return lock\n'
                           '\n'
                           '    async def say(self, m, template_key, suffix="", method=None, '
                           'reply_markup=None, **values):\n'
                           '        s = await self.db.settings(m.chat.id)\n'
                           '        rich = prepared(s, template_key, values)\n'
                           '        if suffix:\n'
                           '            rich = join_rich(rich, suffix if isinstance(suffix, dict) '
                           'else {"text": suffix, "entities": []})\n'
                           '        kwargs = {"reply_markup": reply_markup} if reply_markup is not '
                           'None else {}\n'
                           '        result = None\n'
                           '        for part in split_rich(rich):\n'
                           '            result = await deliver(method or m.answer, part, '
                           '**kwargs)\n'
                           '        return result\n'
                           '\n'
                           '    async def alert(self, q, key, show_alert=False, **values):\n'
                           '        s = await self.db.settings(q.message.chat.id) if q.message '
                           'else {}\n'
                           '        # Callback popups cannot contain Telegram entities and are '
                           'limited to 200 characters.\n'
                           '        text = plain(prepared(s, key, values), 200)\n'
                           '        return await q.answer(text, show_alert=show_alert)\n'
                           '\n'
                           '    async def text_command(self, m, cmd, args):\n'
                           '        chat, actor = m.chat.id, m.from_user.id\n'
                           '        if cmd == "edit":\n'
                           '            reply = m.reply_to_message\n'
                           '            if (not reply or not reply.from_user or reply.from_user.id '
                           '!= self.bot.id\n'
                           '                    or reply.sender_chat or reply.forward_origin or '
                           'not reply.text\n'
                           '                    or not reply.chat or reply.chat.id != chat):\n'
                           '                raise UserError("error_edit_reply")\n'
                           '            if not args:\n'
                           '                raise UserError("error_edit_text")\n'
                           '            rich = extract(m, args)\n'
                           '            try:\n'
                           '                await deliver(reply.edit_text, rich, '
                           'reply_markup=reply.reply_markup)\n'
                           '            except TelegramAPIError as exc:\n'
                           '                if exc.code == 400:\n'
                           '                    raise UserError("error_edit_rejected") from None\n'
                           '                raise\n'
                           '            await self.db.audit(chat, actor, None, "edit_message", '
                           'str(reply.message_id))\n'
                           '            return await self.say(m, "edit_saved")\n'
                           '        if cmd == "emoji":\n'
                           '            source = m.reply_to_message or m\n'
                           '            entities = source.entities or source.caption_entities or '
                           '[]\n'
                           '            ids = list(dict.fromkeys(e.custom_emoji_id for e in '
                           'entities if e.type == "custom_emoji"))\n'
                           '            return await self.say(m, "emoji" if ids else '
                           '"emoji_empty", items="\\n".join(ids[:50]))\n'
                           '        if cmd == "texts":\n'
                           '            s = await self.db.settings(chat)\n'
                           '            if args in FIELDS:\n'
                           '                fields = ", ".join("{"+v+"}" for v in '
                           'sorted(FIELDS[args])) or prepared(s, "texts_no_fields")["text"]\n'
                           '                return await self.say(m, "texts_detail", key=args, '
                           'fields=fields)\n'
                           '            keys = list(FIELDS)\n'
                           '            pages = (len(keys)+11)//12\n'
                           '            if args and (not args.isdigit() or not 1 <= int(args) <= '
                           'pages):\n'
                           '                raise UserError("error_texts_page", pages=pages)\n'
                           '            page = int(args) if args else 1\n'
                           '            items = "\\n".join(key + ": " + (", ".join("{"+v+"}" for v '
                           'in sorted(FIELDS[key])) or\n'
                           '                prepared(s, "texts_no_fields")["text"]) for key in '
                           'keys[(page-1)*12:page*12])\n'
                           '            return await self.say(m, "texts", items=items, page=page, '
                           'pages=pages)\n'
                           '        parts = args.split(maxsplit=1)\n'
                           '        if not parts or parts[0] not in FIELDS:\n'
                           '            raise UserError("error_template_key")\n'
                           '        key = parts[0]\n'
                           '        s = await self.db.settings(chat)\n'
                           '        s["texts"] = dict(s.get("texts", {}))\n'
                           '        if cmd == "settext":\n'
                           '            if len(parts) == 2:\n'
                           '                rich = extract(m, parts[1])\n'
                           '            elif m.reply_to_message:\n'
                           '                rich = extract(m.reply_to_message)\n'
                           '            else:\n'
                           '                raise UserError("error_template_text")\n'
                           '            validate(key, rich)\n'
                           '            s["texts"][key] = rich\n'
                           '        elif cmd == "resettext":\n'
                           '            if len(parts) != 1:\n'
                           '                raise UserError("error_reset_usage")\n'
                           '            s["texts"].pop(key, None)\n'
                           '            if key in {"rules", "welcome"}:\n'
                           '                from .policy import DEFAULTS\n'
                           '                field = "rules" if key == "rules" else "welcome_text"\n'
                           '                s[field] = DEFAULTS[field]\n'
                           '        elif cmd == "previewtext":\n'
                           '            rich = render(template(s, key), {field: PREVIEW.get(field, '
                           '"Пример") for field in FIELDS[key]})\n'
                           '            if units(rich["text"]) > 4096:\n'
                           '                raise UserError("error_preview_long")\n'
                           '            for part in split_rich(rich):\n'
                           '                await deliver(m.answer, part)\n'
                           '            return\n'
                           '        await self.db.save_settings(chat, s)\n'
                           '        await self.db.audit(chat, actor, None, cmd, key)\n'
                           '        hint = prepared(s, "welcome_hint")["text"] if key == "welcome" '
                           'else ""\n'
                           '        return await self.say(m, "text_saved", key=key, hint=hint)\n'
                           '\n'
                           '    async def is_admin(self, chat, user):\n'
                           '        member = await self.bot.get_chat_member(chat, user)\n'
                           '        return member.status in ADMINS\n'
                           '\n'
                           '    async def require_admin(self, chat, user, right=None):\n'
                           '        member = await self.bot.get_chat_member(chat, user)\n'
                           '        if member.status not in ADMINS:\n'
                           '            raise UserError("error_admin_only")\n'
                           '        if right and member.status != "creator" and not '
                           'getattr(member, right, False):\n'
                           '            raise UserError("error_admin_right", right=right)\n'
                           '\n'
                           '    async def require_bot(self, chat, right):\n'
                           '        member = await self.bot.get_chat_member(chat, self.bot.id)\n'
                           '        if member.status != "administrator" or not getattr(member, '
                           'right, False):\n'
                           '            raise UserError("error_bot_right", right=right)\n'
                           '\n'
                           '    async def target(self, m, args, protect=True):\n'
                           '        reply = m.reply_to_message\n'
                           '        if reply:\n'
                           '            if reply.sender_chat or not reply.from_user:\n'
                           '                raise UserError("error_target_channel")\n'
                           '            uid, rest = reply.from_user.id, args\n'
                           '        else:\n'
                           '            pieces = args.split(maxsplit=1)\n'
                           '            if not pieces or not pieces[0].isdigit() or not 0 < '
                           'int(pieces[0]) < 2**52:\n'
                           '                raise UserError("error_target_required")\n'
                           '            uid, rest = int(pieces[0]), pieces[1] if len(pieces) > 1 '
                           'else ""\n'
                           '        if protect:\n'
                           '            if uid in {self.bot.id, m.from_user.id} or await '
                           'self.is_admin(m.chat.id, uid):\n'
                           '                raise UserError("error_protected")\n'
                           '        return uid, rest\n'
                           '\n'
                           '    async def mute(self, chat, uid, seconds):\n'
                           '        # Do not shorten an existing restriction or discard its custom '
                           'permissions.\n'
                           '        member = await self.bot.get_chat_member(chat, uid)\n'
                           '        if member.status in ADMINS or uid == self.bot.id:\n'
                           '            raise UserError("error_protected_member")\n'
                           '        if member.status == "restricted":\n'
                           '            raise UserError("error_already_restricted")\n'
                           '        if member.status in {"left", "kicked"}:\n'
                           '            raise UserError("error_member_missing")\n'
                           '        await self.bot.restrict_chat_member(\n'
                           '            chat, uid, permissions=ChatPermissions(**{k: False for k '
                           'in ChatPermissions.model_fields}),\n'
                           '            until_date=datetime.now(timezone.utc) + '
                           'timedelta(seconds=seconds),\n'
                           '            use_independent_chat_permissions=True,\n'
                           '        )\n'
                           '\n'
                           '    async def warn(self, m, uid, reason, actor):\n'
                           '        settings = await self.db.settings(m.chat.id)\n'
                           '        count = await self.db.change_warns(m.chat.id, uid, 1)\n'
                           '        await self.db.audit(m.chat.id, actor, uid, "warn", reason)\n'
                           '        suffix = ""\n'
                           '        if count >= settings["warn_limit"]:\n'
                           '            try:\n'
                           '                await self.require_bot(m.chat.id, '
                           '"can_restrict_members")\n'
                           '                await self.mute(m.chat.id, uid, '
                           'settings["mute_minutes"] * 60)\n'
                           '            except (TelegramAPIError, UserError):\n'
                           '                suffix = prepared(settings, "warn_automute_failed")\n'
                           '            else:\n'
                           '                await self.db.audit(m.chat.id, self.bot.id, uid, '
                           '"automute", "Лимит предупреждений")\n'
                           '                await self.db.change_warns(m.chat.id, uid, '
                           'reset=True)\n'
                           '                suffix = prepared(settings, "warn_automute_success", '
                           '{"minutes": settings["mute_minutes"]})\n'
                           '        await self.say(m, "warn", suffix=suffix, uid=uid, count=count, '
                           'limit=settings["warn_limit"], reason=reason[:300])\n'
                           '\n'
                           '    def keyboard(self, settings):\n'
                           '        return InlineKeyboardMarkup(inline_keyboard=[[\n'
                           '            InlineKeyboardButton(text=plain(prepared(settings, '
                           '"button_"+key,\n'
                           '                {"state": "✅" if settings[key] else "⬜"}), 64), '
                           'callback_data=f"toggle:{key}")\n'
                           '        ] for key in ("antiflood", "antilinks", "antiforward", '
                           '"stopwords", "welcome")])\n'
                           '\n'
                           '    def settings_text(self, s):\n'
                           '        return prepared(s, "settings", {**s, "word_count": '
                           'len(s["words"])})\n'
                           '\n'
                           '    async def callback(self, q: CallbackQuery):\n'
                           '        if not isinstance(q.message, Message) or q.message.chat.type '
                           'not in GROUPS:\n'
                           '            return await self.alert(q, "callback_group_only", '
                           'show_alert=True)\n'
                           '        async with self.lock(q.message.chat.id):\n'
                           '            try:\n'
                           '                await self.require_admin(q.message.chat.id, '
                           'q.from_user.id)\n'
                           '                key = (q.data or "").removeprefix("toggle:")\n'
                           '                if key not in BOOL_KEYS:\n'
                           '                    raise UserError("error_setting_unknown")\n'
                           '                s = await self.db.settings(q.message.chat.id)\n'
                           '                s[key] = not s[key]\n'
                           '                await self.db.save_settings(q.message.chat.id, s)\n'
                           '                await self.db.audit(q.message.chat.id, q.from_user.id, '
                           'None, "setting", f"{key}={s[key]}")\n'
                           '                await self.alert(q, "callback_saved")\n'
                           '                await deliver(q.message.edit_text, '
                           'self.settings_text(s), reply_markup=self.keyboard(s))\n'
                           '            except UserError as e:\n'
                           '                await self.alert(q, e.key, show_alert=True, '
                           '**e.values)\n'
                           '            except TelegramAPIError:\n'
                           '                log.warning("Callback Telegram API failure")\n'
                           '                with suppress(TelegramAPIError):\n'
                           '                    await self.alert(q, "callback_retry", '
                           'show_alert=True)\n'
                           '\n'
                           '    async def message(self, m: Message):\n'
                           '        async with self.lock(m.chat.id):\n'
                           '            try:\n'
                           '                await self.process(m)\n'
                           '            except UserError as e:\n'
                           '                await self.say(m, e.key, **e.values)\n'
                           '            except ValueError as e:\n'
                           '                await self.say(m, "validation_error", detail=str(e))\n'
                           '            except TelegramAPIError as e:\n'
                           '                log.warning("Telegram operation failed: %s", '
                           'type(e).__name__)\n'
                           '                if await self.cooldowns.ready((m.chat.id, '
                           '"api_error"), 60):\n'
                           '                    with suppress(TelegramAPIError):\n'
                           '                        await self.say(m, "api_error")\n'
                           '\n'
                           '    async def process(self, m: Message):\n'
                           '        command = parse_command(m.text or "", self.username)\n'
                           '        edited = m.edit_date is not None\n'
                           '        if m.chat.type not in GROUPS:\n'
                           '            if command and not edited:\n'
                           '                await self.say(m, command[0] if command[0] in '
                           '{"start", "help"} else "group_only")\n'
                           '            return\n'
                           '        # Anonymous admins and channel identities cannot be reliably '
                           'authorized as people.\n'
                           '        if m.sender_chat or not m.from_user or m.from_user.is_bot:\n'
                           '            return\n'
                           '        if m.new_chat_members:\n'
                           '            s = await self.db.settings(m.chat.id)\n'
                           '            if s["welcome"]:\n'
                           '                for user in m.new_chat_members:\n'
                           '                    if not user.is_bot:\n'
                           '                        await self.say(m, "welcome", '
                           'name=user.full_name)\n'
                           '            return\n'
                           '        if m.content_type in {"left_chat_member", "pinned_message", '
                           '"new_chat_title", "new_chat_photo",\n'
                           '                              "delete_chat_photo", '
                           '"group_chat_created", "supergroup_chat_created"}:\n'
                           '            return\n'
                           '        admin = await self.is_admin(m.chat.id, m.from_user.id)\n'
                           '        if not admin and await self.filter_message(m, edited):\n'
                           '            return\n'
                           '        # Edited messages are filtered, but never execute moderation '
                           'commands again.\n'
                           '        if command and not edited:\n'
                           '            if not admin and not await '
                           'self.cooldowns.ready((m.chat.id, m.from_user.id, "cmd"), 3):\n'
                           '                return\n'
                           '            await self.command(m, *command)\n'
                           '\n'
                           '    async def filter_message(self, m, edited):\n'
                           '        s = await self.db.settings(m.chat.id)\n'
                           '        reason, flood = None, False\n'
                           '        text = m.text or m.caption or ""\n'
                           '        if not edited and s["antiflood"] and await self.flood.hit(\n'
                           '                m.chat.id, m.from_user.id, s["flood_limit"], '
                           's["flood_window"]):\n'
                           '            reason, flood = "Флуд", True\n'
                           '        elif s["antilinks"] and contains_link(text, (m.entities or []) '
                           '+ (m.caption_entities or [])):\n'
                           '            reason = "Запрещённая ссылка"\n'
                           '        elif s["antiforward"] and m.forward_origin:\n'
                           '            reason = "Пересланное сообщение"\n'
                           '        elif s["stopwords"] and forbidden_word(text, s["words"]):\n'
                           '            reason = "Стоп-слово/фраза"\n'
                           '        if not reason:\n'
                           '            return False\n'
                           '        await self.require_bot(m.chat.id, "can_delete_messages")\n'
                           '        await self.bot.delete_message(m.chat.id, m.message_id)\n'
                           '        await self.db.audit(m.chat.id, self.bot.id, m.from_user.id, '
                           '"delete", reason)\n'
                           '        if not await self.cooldowns.ready((m.chat.id, m.from_user.id, '
                           '"violation"), 10):\n'
                           '            return True\n'
                           '        if flood:\n'
                           '            await self.require_bot(m.chat.id, "can_restrict_members")\n'
                           '            await self.mute(m.chat.id, m.from_user.id, '
                           's["mute_minutes"] * 60)\n'
                           '            await self.db.audit(m.chat.id, self.bot.id, '
                           'm.from_user.id, "automute", reason)\n'
                           '            await self.say(m, "automute", uid=m.from_user.id, '
                           'minutes=s["mute_minutes"], reason="флуд")\n'
                           '        else:\n'
                           '            await self.warn(m, m.from_user.id, reason, self.bot.id)\n'
                           '        return True\n'
                           '\n'
                           '    async def command(self, m, cmd, args):\n'
                           '        chat, actor = m.chat.id, m.from_user.id\n'
                           '        if cmd in {"start", "help"}:\n'
                           '            return await self.say(m, cmd)\n'
                           '        if cmd == "ping":\n'
                           '            return await self.say(m, "ping")\n'
                           '        if cmd == "id":\n'
                           '            uid = m.reply_to_message.from_user.id if '
                           'm.reply_to_message and m.reply_to_message.from_user else actor\n'
                           '            return await self.say(m, "id", chat=chat, uid=uid)\n'
                           '        if cmd == "rules":\n'
                           '            return await self.say(m, "rules")\n'
                           '        if cmd == "filters":\n'
                           '            s = await self.db.settings(chat)\n'
                           '            items = join_lines(prepared(s, "filter_row", {"name": k,\n'
                           '                "state": prepared(s, "state_on" if s[k] else '
                           '"state_off")}) for k in sorted(BOOL_KEYS))\n'
                           '            return await self.say(m, "filters", items=items)\n'
                           '        if cmd == "report":\n'
                           '            if not m.reply_to_message:\n'
                           '                raise UserError("error_report_reply")\n'
                           '            if not await self.cooldowns.ready((chat, actor, "report"), '
                           '60):\n'
                           '                raise UserError("error_report_cooldown")\n'
                           '            uid = m.reply_to_message.from_user.id if '
                           'm.reply_to_message.from_user else None\n'
                           '            await self.db.audit(chat, actor, uid, "report", args or '
                           '"Жалоба")\n'
                           '            return await self.say(m, "report", '
                           'method=m.reply_to_message.reply, actor=actor, reason=args[:300])\n'
                           '        if cmd == "warnings" and not args and not m.reply_to_message:\n'
                           '            return await self.say(m, "warnings_self", count=await '
                           'self.db.count(chat, actor))\n'
                           '\n'
                           '        right = "can_delete_messages" if cmd == "del" else (\n'
                           '            "can_restrict_members" if cmd in {"ban", "unban", "kick", '
                           '"mute", "unmute", "warn", "unwarn", "resetwarns"} else None)\n'
                           '        await self.require_admin(chat, actor, right)\n'
                           '        if cmd in {"edit", "texts", "settext", "resettext", '
                           '"previewtext", "emoji"}:\n'
                           '            return await self.text_command(m, cmd, args)\n'
                           '        if cmd == "check":\n'
                           '            member = await self.bot.get_chat_member(chat, '
                           'self.bot.id)\n'
                           '            return await self.say(m, "check", delete="✅" if '
                           'member.can_delete_messages else "❌",\n'
                           '                                  restrict="✅" if '
                           'member.can_restrict_members else "❌")\n'
                           '        if cmd == "settings":\n'
                           '            s = await self.db.settings(chat)\n'
                           '            return await deliver(m.answer, self.settings_text(s), '
                           'reply_markup=self.keyboard(s))\n'
                           '        if cmd == "set":\n'
                           '            parts = args.split()\n'
                           '            if len(parts) != 2 or parts[0] not in LIMITS:\n'
                           '                raise UserError("error_set_usage", parameters=", '
                           '".join(LIMITS))\n'
                           '            key, raw = parts\n'
                           '            if not raw.isdigit():\n'
                           '                raise UserError("error_positive_integer")\n'
                           '            value = int(raw)\n'
                           '            low, high = LIMITS[key]\n'
                           '            if not low <= value <= high:\n'
                           '                raise UserError("error_range", low=low, high=high)\n'
                           '            s = await self.db.settings(chat)\n'
                           '            s[key] = value\n'
                           '            await self.db.save_settings(chat, s)\n'
                           '            await self.db.audit(chat, actor, None, "setting", args)\n'
                           '            return await self.say(m, "setting_saved", setting=args)\n'
                           '        if cmd in {"setrules", "setwelcome"}:\n'
                           '            key = "rules" if cmd == "setrules" else "welcome"\n'
                           '            return await self.text_command(m, "settext", key + (" " + '
                           'args if args else ""))\n'
                           '        if cmd == "word":\n'
                           '            parts = args.split(maxsplit=1)\n'
                           '            s = await self.db.settings(chat)\n'
                           '            if parts == ["list"]:\n'
                           '                return await self.say(m, "words", '
                           'items="\\n".join(s["words"]) or prepared(s, "words_empty")["text"])\n'
                           '            if len(parts) != 2 or parts[0] not in {"add", "del"}:\n'
                           '                raise UserError("error_word_usage")\n'
                           '            word = normalize(parts[1]).strip()\n'
                           '            if not 1 <= len(word) <= 30:\n'
                           '                raise UserError("error_word_length")\n'
                           '            if parts[0] == "add" and word not in s["words"]:\n'
                           '                if len(s["words"]) >= 100:\n'
                           '                    raise UserError("error_word_limit")\n'
                           '                s["words"].append(word)\n'
                           '            elif parts[0] == "del" and word in s["words"]:\n'
                           '                s["words"].remove(word)\n'
                           '            await self.db.save_settings(chat, s)\n'
                           '            await self.db.audit(chat, actor, None, "word", args)\n'
                           '            return await self.say(m, "words_saved")\n'
                           '        if cmd in {"logs", "stats"}:\n'
                           '            rows = await (self.db.logs(chat) if cmd == "logs" else '
                           'self.db.stats(chat))\n'
                           '            s = await self.db.settings(chat)\n'
                           '            rich = []\n'
                           '            for r in rows:\n'
                           '                values = ({"date": '
                           'f"{datetime.fromtimestamp(r[\'at\'], timezone.utc):%d.%m %H:%M}",\n'
                           '                    "action": r["action"], "actor": r["actor"], "uid": '
                           'r["target"], "reason": r["reason"][:100]}\n'
                           '                    if cmd == "logs" else {"action": r["action"], '
                           '"count": r["n"]})\n'
                           '                rich.append(prepared(s, "log_row" if cmd == "logs" '
                           'else "stat_row", values))\n'
                           '            return await self.say(m, cmd if rich else cmd+"_empty", '
                           'items=join_lines(rich))\n'
                           '        if cmd == "del":\n'
                           '            if not m.reply_to_message:\n'
                           '                raise UserError("error_delete_reply")\n'
                           '            await self.require_bot(chat, "can_delete_messages")\n'
                           '            await self.bot.delete_message(chat, '
                           'm.reply_to_message.message_id)\n'
                           '            await self.db.audit(chat, actor, None, "delete", '
                           '"Вручную")\n'
                           '            return await self.say(m, "delete")\n'
                           '        uid, rest = await self.target(m, args, protect=cmd != '
                           '"warnings")\n'
                           '        if cmd == "warnings":\n'
                           '            return await self.say(m, "warnings", uid=uid, count=await '
                           'self.db.count(chat, uid))\n'
                           '        if cmd in {"unwarn", "resetwarns"}:\n'
                           '            n = await self.db.change_warns(chat, uid, -1, reset=cmd == '
                           '"resetwarns")\n'
                           '            await self.db.audit(chat, actor, uid, cmd)\n'
                           '            return await self.say(m, cmd, uid=uid, count=n)\n'
                           '        if cmd == "warn":\n'
                           '            return await self.warn(m, uid, rest or "Нарушение правил", '
                           'actor)\n'
                           '        await self.require_bot(chat, "can_restrict_members")\n'
                           '        if cmd == "mute":\n'
                           '            pieces = rest.split(maxsplit=1)\n'
                           '            if not pieces:\n'
                           '                raise UserError("error_mute_duration")\n'
                           '            seconds = duration(pieces[0])\n'
                           '            await self.mute(chat, uid, seconds)\n'
                           '        elif cmd == "unmute":\n'
                           '            await self.bot.restrict_chat_member(chat, uid,\n'
                           '                permissions=ChatPermissions(**{k: True for k in '
                           'ChatPermissions.model_fields}),\n'
                           '                use_independent_chat_permissions=True)\n'
                           '        elif cmd == "ban":\n'
                           '            await self.bot.ban_chat_member(chat, uid)\n'
                           '        elif cmd == "unban":\n'
                           '            await self.bot.unban_chat_member(chat, uid, '
                           'only_if_banned=True)\n'
                           '        elif cmd == "kick":\n'
                           '            await self.bot.ban_chat_member(chat, uid)\n'
                           '            # Audit the first API action even if the second fails.\n'
                           '            await self.db.audit(chat, actor, uid, "kick_ban", rest)\n'
                           '            await self.bot.unban_chat_member(chat, uid, '
                           'only_if_banned=True)\n'
                           '        else:\n'
                           '            raise UserError("error_unknown_command")\n'
                           '        await self.db.audit(chat, actor, uid, cmd, rest)\n'
                           '        reason = (pieces[1] if len(pieces) > 1 else "") if cmd == '
                           '"mute" else rest\n'
                           '        await self.say(m, cmd, uid=uid, minutes=seconds // 60 if cmd '
                           '== "mute" else 0, reason=reason[:300])\n'
                           '\n',
 'src/guardian_cf/policy.py': 'import re\n'
                              'import time\n'
                              'import unicodedata\n'
                              'from collections import OrderedDict, deque\n'
                              '\n'
                              'ALIASES = {\n'
                              '    "бан": "ban", "разбан": "unban", "мут": "mute", "размут": '
                              '"unmute",\n'
                              '    "варн": "warn", "пред": "warn", "снятьпред": "unwarn", "преды": '
                              '"warnings",\n'
                              '    "кик": "kick", "удалить": "del", "правила": "rules", '
                              '"настройки": "settings",\n'
                              '    "помощь": "help", "пинг": "ping", "ид": "id",\n'
                              '    "изменить": "edit", "тексты": "texts", "текст": "settext", '
                              '"эмодзи": "emoji",\n'
                              '}\n'
                              'COMMANDS = set(ALIASES.values()) | {\n'
                              '    "start", "help", "check", "setrules", "setwelcome", "set", '
                              '"word",\n'
                              '    "logs", "stats", "resetwarns", "report", "filters",\n'
                              '    "edit", "texts", "settext", "resettext", "previewtext", '
                              '"emoji",\n'
                              '}\n'
                              'BOOL_KEYS = {"antiflood", "antilinks", "antiforward", "welcome", '
                              '"stopwords"}\n'
                              'DEFAULTS = {\n'
                              '    "antiflood": True, "antilinks": False, "antiforward": False,\n'
                              '    "stopwords": True, "welcome": False, "flood_limit": 7, '
                              '"flood_window": 10,\n'
                              '    "warn_limit": 3, "mute_minutes": 60, "rules": "Правила пока не '
                              'заданы.",\n'
                              '    "welcome_text": "Добро пожаловать, {name}! Правила: /rules", '
                              '"words": [],\n'
                              '}\n'
                              'LIMITS = {"flood_limit": (3, 30), "flood_window": (3, 60),\n'
                              '          "warn_limit": (2, 20), "mute_minutes": (1, 10080)}\n'
                              '\n'
                              '\n'
                              'def parse_command(text: str, username: str):\n'
                              '    if not text or text[0] not in "/!":\n'
                              '        return None\n'
                              '    parts = text[1:].split(maxsplit=1)\n'
                              '    if not parts:\n'
                              '        return None\n'
                              '    name, _, addressed = parts[0].partition("@")\n'
                              '    if addressed and addressed.casefold() != username.casefold():\n'
                              '        return None\n'
                              '    name = ALIASES.get(name.casefold(), name.casefold())\n'
                              '    if name not in COMMANDS:\n'
                              '        return None\n'
                              '    return name, parts[1].strip() if len(parts) > 1 else ""\n'
                              '\n'
                              '\n'
                              'def duration(value: str) -> int:\n'
                              '    match = re.fullmatch(r"(\\d{1,6})([mhdмчд])", '
                              'value.casefold())\n'
                              '    if not match:\n'
                              '        raise ValueError("Время: 10m, 2h, 7d (или 10м, 2ч, 7д).")\n'
                              '    seconds = int(match[1]) * {"m": 60, "м": 60, "h": 3600, "ч": '
                              '3600,\n'
                              '                               "d": 86400, "д": 86400}[match[2]]\n'
                              '    if not 60 <= seconds <= 365 * 86400:\n'
                              '        raise ValueError("Срок должен быть от 1 минуты до 365 '
                              'дней.")\n'
                              '    return seconds\n'
                              '\n'
                              '\n'
                              'def normalize(text: str) -> str:\n'
                              '    return "".join(c for c in unicodedata.normalize("NFKC", '
                              'text).casefold()\n'
                              '                   if unicodedata.category(c) != "Cf")\n'
                              '\n'
                              '\n'
                              'def forbidden_word(text: str, words: list[str]) -> bool:\n'
                              '    text = normalize(text)\n'
                              '    return any(re.search(r"(?<!\\w)" + re.escape(normalize(w)) + '
                              'r"(?!\\w)", text)\n'
                              '               for w in words)\n'
                              '\n'
                              '\n'
                              'def contains_link(text: str, entities=()) -> bool:\n'
                              '    # Telegram entities also cover concealed hyperlinks in '
                              'captions.\n'
                              '    if any(e.type in {"url", "text_link"} for e in entities):\n'
                              '        return True\n'
                              '    return '
                              'bool(re.search(r"(?i)(?:https?://|tg://|www\\.|(?:t|telegram)\\.me/)", '
                              'normalize(text)))\n'
                              '\n'
                              '\n'
                              'class FloodGuard:\n'
                              '    """Bounded, monotonic sliding window; edits do not count as new '
                              'messages."""\n'
                              '    def __init__(self, capacity=20000):\n'
                              '        self.capacity = capacity\n'
                              '        self.windows = OrderedDict()\n'
                              '\n'
                              '    def hit(self, chat, user, limit, window, now=None):\n'
                              '        now = time.monotonic() if now is None else now\n'
                              '        key = (chat, user)\n'
                              '        timestamps = self.windows.pop(key, deque(maxlen=31))\n'
                              '        while timestamps and timestamps[0] <= now - window:\n'
                              '            timestamps.popleft()\n'
                              '        timestamps.append(now)\n'
                              '        self.windows[key] = timestamps\n'
                              '        while len(self.windows) > self.capacity:\n'
                              '            self.windows.popitem(last=False)\n'
                              '        return len(timestamps) > limit\n'
                              '\n'
                              '\n'
                              'class Cooldowns:\n'
                              '    def __init__(self, capacity=20000):\n'
                              '        self.values = OrderedDict()\n'
                              '        self.capacity = capacity\n'
                              '\n'
                              '    def ready(self, key, seconds):\n'
                              '        now = time.monotonic()\n'
                              '        if now < self.values.get(key, 0):\n'
                              '            return False\n'
                              '        self.values.pop(key, None)\n'
                              '        self.values[key] = now + seconds\n'
                              '        while len(self.values) > self.capacity:\n'
                              '            self.values.popitem(last=False)\n'
                              '        return True\n',
 'src/guardian_cf/texts.py': '"""Chat-scoped message templates and Telegram UTF-16 entity '
                             'handling."""\n'
                             'import re\n'
                             '\n'
                             'from .telegram import encode, TelegramAPIError\n'
                             '\n'
                             'FIELDS = {\n'
                             '    "mute": {"uid", "minutes", "reason"},\n'
                             '    "ban": {"uid", "reason"}, "unban": {"uid", "reason"},\n'
                             '    "kick": {"uid", "reason"}, "unmute": {"uid", "reason"},\n'
                             '    "warn": {"uid", "count", "limit", "reason"},\n'
                             '    "automute": {"uid", "minutes", "reason"},\n'
                             '    "welcome": {"name"}, "rules": set(), "ping": set(),\n'
                             '}\n'
                             'DEFAULT_TEXTS = {\n'
                             '    "mute": "✅ ID {uid}. Мут на {minutes} мин.\\n{reason}",\n'
                             '    "ban": "✅ ID {uid}. Участник забанен.\\n{reason}",\n'
                             '    "unban": "✅ ID {uid}. Бан снят. Участник может вернуться по '
                             'приглашению.\\n{reason}",\n'
                             '    "kick": "✅ ID {uid}. Участник удалён и может '
                             'вернуться.\\n{reason}",\n'
                             '    "unmute": "✅ ID {uid}. Персональные ограничения сняты; действуют '
                             'общие права группы.\\n{reason}",\n'
                             '    "warn": "⚠️ ID {uid}: предупреждение '
                             '{count}/{limit}.\\n{reason}",\n'
                             '    "automute": "🔇 ID {uid}: мут на {minutes} мин. Причина: '
                             '{reason}.",\n'
                             '    "ping": "🟢 Работаю. Python · Cloudflare Workers · D1",\n'
                             '}\n'
                             'TOKEN = re.compile(r"\\{([A-Za-z_][A-Za-z_0-9]*)\\}")\n'
                             '\n'
                             "DEFAULT_TEXTS.update({'help': '🛡 Guardian 2.2 — модерация "
                             "группы\\n'\n"
                             "         '\\n'\n"
                             "         'Команды можно писать с / или !. Русские варианты: !бан, "
                             "!разбан, !мут, !размут, !варн, '\n"
                             "         '!преды, !кик, !пинг.\\n'\n"
                             "         '\\n'\n"
                             "         'Ответом на сообщение участника:\\n'\n"
                             "         '/warn причина — предупреждение\\n'\n"
                             "         '/mute 30m причина — мут (m/м, h/ч, d/д)\\n'\n"
                             "         '/ban причина — постоянный бан\\n'\n"
                             "         '/kick причина — удалить, разрешив вернуться\\n'\n"
                             "         '/unmute — снять персональные ограничения\\n'\n"
                             "         '/unban — разрешить вернуться\\n'\n"
                             "         '/unwarn — снять один варн\\n'\n"
                             "         '/resetwarns — сбросить варны\\n'\n"
                             "         '/warnings — число варнов\\n'\n"
                             "         '/del — удалить одно сообщение\\n'\n"
                             "         '/report причина — жалоба в группе\\n'\n"
                             "         '\\n'\n"
                             "         'Без ответа укажи числовой ID: /mute 123456789 30m "
                             "причина.\\n'\n"
                             "         '@username не используется для наказания: надёжнее ответ "
                             "или ID.\\n'\n"
                             "         '\\n'\n"
                             "         '/settings — кнопки настроек\\n'\n"
                             "         '/set warn_limit 3\\n'\n"
                             "         '/set mute_minutes 60\\n'\n"
                             "         '/set flood_limit 7\\n'\n"
                             "         '/set flood_window 10\\n'\n"
                             "         '/word add слово — добавить стоп-слово/фразу\\n'\n"
                             "         '/word del слово — удалить\\n'\n"
                             "         '/word list — список\\n'\n"
                             "         '/setrules текст — правила\\n'\n"
                             "         '/setwelcome текст с {name} — приветствие\\n'\n"
                             "         '/rules — правила • /filters — режимы фильтров\\n'\n"
                             "         '/logs — последние действия • /stats — статистика за 90 "
                             "дней\\n'\n"
                             "         '/check — проверить права бота • /id — ID • /ping — "
                             "статус\\n'\n"
                             "         '/edit новый текст — ответом на текстовое сообщение этого "
                             "бота\\n'\n"
                             "         '/texts — список настраиваемых текстов и подстановок\\n'\n"
                             "         '/settext mute текст — изменить будущие ответы в этой "
                             "группе\\n'\n"
                             "         '/settext mute — ответом на образец с оформлением и "
                             "премиум-эмодзи\\n'\n"
                             "         '/previewtext mute — проверить текст • /resettext mute — "
                             "сбросить\\n'\n"
                             "         '/emoji — ответом на сообщение: ID пользовательских "
                             "эмодзи\\n'\n"
                             "         '\\n'\n"
                             "         'По умолчанию: антифлуд 8-е сообщение за 10 секунд → мут на "
                             "60 минут; 3 варна → мут. '\n"
                             "         'Ссылки и пересылки разрешены. Фильтры не применяются к "
                             "администраторам.\\n'\n"
                             "         'Работаю в супергруппах. /help — эта справка.',\n"
                             " 'start': '🛡 Guardian 2.2 — модерация группы\\n'\n"
                             "          '\\n'\n"
                             "          'Команды можно писать с / или !. Русские варианты: !бан, "
                             "!разбан, !мут, !размут, !варн, '\n"
                             "          '!преды, !кик, !пинг.\\n'\n"
                             "          '\\n'\n"
                             "          'Ответом на сообщение участника:\\n'\n"
                             "          '/warn причина — предупреждение\\n'\n"
                             "          '/mute 30m причина — мут (m/м, h/ч, d/д)\\n'\n"
                             "          '/ban причина — постоянный бан\\n'\n"
                             "          '/kick причина — удалить, разрешив вернуться\\n'\n"
                             "          '/unmute — снять персональные ограничения\\n'\n"
                             "          '/unban — разрешить вернуться\\n'\n"
                             "          '/unwarn — снять один варн\\n'\n"
                             "          '/resetwarns — сбросить варны\\n'\n"
                             "          '/warnings — число варнов\\n'\n"
                             "          '/del — удалить одно сообщение\\n'\n"
                             "          '/report причина — жалоба в группе\\n'\n"
                             "          '\\n'\n"
                             "          'Без ответа укажи числовой ID: /mute 123456789 30m "
                             "причина.\\n'\n"
                             "          '@username не используется для наказания: надёжнее ответ "
                             "или ID.\\n'\n"
                             "          '\\n'\n"
                             "          '/settings — кнопки настроек\\n'\n"
                             "          '/set warn_limit 3\\n'\n"
                             "          '/set mute_minutes 60\\n'\n"
                             "          '/set flood_limit 7\\n'\n"
                             "          '/set flood_window 10\\n'\n"
                             "          '/word add слово — добавить стоп-слово/фразу\\n'\n"
                             "          '/word del слово — удалить\\n'\n"
                             "          '/word list — список\\n'\n"
                             "          '/setrules текст — правила\\n'\n"
                             "          '/setwelcome текст с {name} — приветствие\\n'\n"
                             "          '/rules — правила • /filters — режимы фильтров\\n'\n"
                             "          '/logs — последние действия • /stats — статистика за 90 "
                             "дней\\n'\n"
                             "          '/check — проверить права бота • /id — ID • /ping — "
                             "статус\\n'\n"
                             "          '/edit новый текст — ответом на текстовое сообщение этого "
                             "бота\\n'\n"
                             "          '/texts — список настраиваемых текстов и подстановок\\n'\n"
                             "          '/settext mute текст — изменить будущие ответы в этой "
                             "группе\\n'\n"
                             "          '/settext mute — ответом на образец с оформлением и "
                             "премиум-эмодзи\\n'\n"
                             "          '/previewtext mute — проверить текст • /resettext mute — "
                             "сбросить\\n'\n"
                             "          '/emoji — ответом на сообщение: ID пользовательских "
                             "эмодзи\\n'\n"
                             "          '\\n'\n"
                             "          'По умолчанию: антифлуд 8-е сообщение за 10 секунд → мут "
                             "на 60 минут; 3 варна → мут. '\n"
                             "          'Ссылки и пересылки разрешены. Фильтры не применяются к "
                             "администраторам.\\n'\n"
                             "          'Работаю в супергруппах. /help — эта справка.',\n"
                             " 'id': 'Группа: {chat}\\nПользователь: {uid}',\n"
                             " 'filters': '{items}',\n"
                             " 'filter_row': '{name}: {state}',\n"
                             " 'state_on': 'вкл',\n"
                             " 'state_off': 'выкл',\n"
                             " 'report': '🚩 Администраторы, проверьте это сообщение. Жалоба от ID "
                             "{actor}.\\n{reason}',\n"
                             " 'warnings_self': 'Твои предупреждения: {count}',\n"
                             " 'warnings': 'ID {uid}: {count} предупреждений.',\n"
                             " 'unwarn': 'ID {uid}: осталось {count} предупреждений.',\n"
                             " 'resetwarns': 'ID {uid}: осталось {count} предупреждений.',\n"
                             " 'check': 'Права бота:\\nУдаление сообщений: {delete}\\nБлокировка "
                             "участников: {restrict}',\n"
                             " 'settings': '⚙️ Настройки этой группы\\n'\n"
                             "             'Антифлуд: более {flood_limit} сообщений за "
                             "{flood_window} сек.\\n'\n"
                             "             'Лимит варнов: {warn_limit}; мут: {mute_minutes} "
                             "мин.\\n'\n"
                             "             'Стоп-фраз: {word_count}\\n'\n"
                             "             'Кнопки доступны администраторам. Числа: /set параметр "
                             "значение',\n"
                             " 'setting_saved': 'Сохранено: {setting}',\n"
                             " 'words': 'Стоп-фразы:\\n{items}',\n"
                             " 'words_empty': 'пусто',\n"
                             " 'words_saved': 'Стоп-фразы сохранены.',\n"
                             " 'logs': '{items}',\n"
                             " 'stats': '{items}',\n"
                             " 'logs_empty': 'Действий пока нет.',\n"
                             " 'stats_empty': 'Действий пока нет.',\n"
                             " 'log_row': '{date} UTC | {action} | {actor} → {uid} | {reason}',\n"
                             " 'stat_row': '{action}: {count}',\n"
                             " 'delete': 'Сообщение удалено.',\n"
                             " 'edit_saved': 'Сообщение изменено. Для будущих ответов используй "
                             "/settext.',\n"
                             " 'emoji': 'ID эмодзи:\\n{items}',\n"
                             " 'emoji_empty': 'Ответь /emoji на сообщение с пользовательскими "
                             "эмодзи Telegram.',\n"
                             " 'api_error': 'Telegram не выполнил действие. Проверь /check, ID "
                             "участника и возраст сообщения. '\n"
                             "              'Изменения могут быть выполнены частично; проверь "
                             "/logs.',\n"
                             " 'validation_error': '{detail}',\n"
                             " 'group_only': 'Добавь бота администратором в супергруппу. Справка: "
                             "/help',\n"
                             " 'callback_group_only': 'Открой /settings в супергруппе.',\n"
                             " 'callback_saved': 'Сохранено',\n"
                             " 'callback_retry': 'Открой /settings заново.',\n"
                             " 'warn_automute_failed': '\\n'\n"
                             "                         'Автомут не выполнен; варны сохранены. "
                             "Проверь /check и текущие '\n"
                             "                         'ограничения.',\n"
                             " 'warn_automute_success': '\\nМут на {minutes} мин. Счётчик "
                             "сброшен.',\n"
                             " 'texts': 'Тексты этой группы — страница {page}/{pages}:\\n'\n"
                             "          '{items}\\n'\n"
                             "          '\\n'\n"
                             "          '/texts НОМЕР — другая страница\\n'\n"
                             "          '/texts help — подстановки шаблона\\n'\n"
                             "          '/settext help текст — сохранить\\n'\n"
                             "          '/previewtext help — пример\\n'\n"
                             "          '/resettext help — сбросить\\n'\n"
                             "          'Оформление задавай средствами Telegram.',\n"
                             " 'texts_detail': '{key}: {fields}\\n/settext {key} "
                             "текст\\n/previewtext {key}\\n/resettext {key}',\n"
                             " 'texts_no_fields': 'без подстановок',\n"
                             " 'text_saved': 'Сохранено. Проверка: /previewtext {key}{hint}',\n"
                             " 'welcome_hint': '. Включи приветствие в /settings.',\n"
                             " 'error_edit_reply': 'Ответь в этой теме на текстовое сообщение "
                             "этого бота: /edit новый текст',\n"
                             " 'error_edit_text': 'После /edit напиши новый текст, можно с "
                             "оформлением и премиум-эмодзи.',\n"
                             " 'error_edit_rejected': 'Telegram не изменил сообщение: текст уже "
                             "совпадает, сообщение недоступно '\n"
                             "                        'или оформление отклонено.',\n"
                             " 'error_template_key': 'Укажи название текста из /texts, например: "
                             "/settext help Моя справка',\n"
                             " 'error_template_text': 'Добавь текст после названия или ответь "
                             "командой на образец.',\n"
                             " 'error_reset_usage': 'Пример: /resettext mute',\n"
                             " 'error_preview_long': 'После подстановки текст слишком длинный. "
                             "Сократи шаблон.',\n"
                             " 'error_admin_only': 'Эта команда доступна администраторам "
                             "группы.',\n"
                             " 'error_target_channel': 'Сообщение отправлено от имени "
                             "канала/группы. Выбери пользователя.',\n"
                             " 'error_target_required': 'Ответь на сообщение участника или укажи "
                             "его числовой ID.',\n"
                             " 'error_protected': 'Нельзя применить наказание к себе, боту или "
                             "администратору.',\n"
                             " 'error_protected_member': 'Участник защищён от модерации.',\n"
                             " 'error_already_restricted': 'Участник уже ограничен. Существующее "
                             "ограничение сохранено.',\n"
                             " 'error_member_missing': 'Участник сейчас не состоит в группе.',\n"
                             " 'error_setting_unknown': 'Неизвестная настройка.',\n"
                             " 'error_report_reply': 'Отправь /report ответом на сообщение, на "
                             "которое жалуешься.',\n"
                             " 'error_report_cooldown': 'Жалобу можно отправлять раз в минуту.',\n"
                             " 'error_positive_integer': 'Нужно целое положительное число.',\n"
                             " 'error_word_usage': '/word add фраза • /word del фраза • /word "
                             "list',\n"
                             " 'error_word_length': 'Длина стоп-фразы: 1–30 символов.',\n"
                             " 'error_word_limit': 'Лимит: 100 стоп-фраз.',\n"
                             " 'error_delete_reply': 'Ответь командой /del на удаляемое "
                             "сообщение.',\n"
                             " 'error_mute_duration': 'Укажи срок: /mute 30m причина',\n"
                             " 'error_unknown_command': 'Неизвестная команда.',\n"
                             " 'error_admin_right': 'У тебя нет необходимого права администратора: "
                             "{right}',\n"
                             " 'error_bot_right': 'Выдай боту право администратора: {right}. "
                             "Проверка: /check',\n"
                             " 'error_set_usage': 'Пример: /set warn_limit 3\\nПараметры: "
                             "{parameters}',\n"
                             " 'error_range': 'Допустимый диапазон: {low}–{high}.',\n"
                             " 'error_texts_page': 'Укажи страницу от 1 до {pages} или имя "
                             "шаблона: /texts help',\n"
                             " 'button_antiflood': '{state} Антифлуд',\n"
                             " 'button_antilinks': '{state} Запрет ссылок',\n"
                             " 'button_antiforward': '{state} Запрет пересылок',\n"
                             " 'button_stopwords': '{state} Стоп-слова',\n"
                             " 'button_welcome': '{state} Приветствие'})\n"
                             'FIELDS.update({key: set(TOKEN.findall(text)) for key, text in '
                             'DEFAULT_TEXTS.items() if key not in FIELDS})\n'
                             'FIELDS["help"] = set()\n'
                             'FIELDS["start"] = set()\n'
                             '\n'
                             'STYLES = {"bold", "italic", "underline", "strikethrough", "spoiler", '
                             '"code", "pre",\n'
                             '          "text_link", "text_mention", "custom_emoji", "blockquote", '
                             '"expandable_blockquote"}\n'
                             '\n'
                             '\n'
                             'def units(text):\n'
                             '    return len(text.encode("utf-16-le")) // 2\n'
                             '\n'
                             '\n'
                             'def extract(message, body=None):\n'
                             '    """Copy message/caption or an exact command suffix, retaining '
                             'supported entities."""\n'
                             '    text = message.text if message.text is not None else '
                             '(message.caption or "")\n'
                             '    entities = message.entities if message.text is not None else '
                             'message.caption_entities\n'
                             '    if body is None:\n'
                             '        start, end = 0, len(text)\n'
                             '    else:\n'
                             '        end = len(text.rstrip())\n'
                             '        start = end - len(body)\n'
                             '        if start < 0 or text[start:end] != body:\n'
                             '            raise ValueError("Не удалось прочитать текст команды.")\n'
                             '    value = text[start:end]\n'
                             '    if not value.strip() or units(value) > 4000:\n'
                             '        raise ValueError("Текст должен содержать от 1 до 4000 '
                             'символов UTF-16.")\n'
                             '    offset, limit = units(text[:start]), units(text[:end])\n'
                             '    result = []\n'
                             '    for obj in entities or []:\n'
                             '        e = encode(obj)\n'
                             '        if e.get("type") not in STYLES:\n'
                             '            continue\n'
                             '        a, b = e["offset"], e["offset"] + e["length"]\n'
                             '        if e["type"] in {"custom_emoji", "text_link", '
                             '"text_mention"} and (a < offset or b > limit):\n'
                             '            continue\n'
                             '        a, b = max(a, offset), min(b, limit)\n'
                             '        if a < b:\n'
                             '            result.append({**e, "offset": a-offset, "length": b-a})\n'
                             '    if len(result) > 100:\n'
                             '        raise ValueError("Слишком много элементов оформления: '
                             'максимум 100.")\n'
                             '    return {"text": value, "entities": result}\n'
                             '\n'
                             '\n'
                             'def validate(key, rich):\n'
                             '    # Help can contain literal examples of other templates, such as '
                             '{uid}.\n'
                             '    if key in {"help", "start"}:\n'
                             '        return\n'
                             '    unknown = set(TOKEN.findall(rich["text"])) - FIELDS[key]\n'
                             '    if unknown:\n'
                             '        raise ValueError("Неизвестные подстановки: " + ", '
                             '".join(sorted(unknown)))\n'
                             '\n'
                             '\n'
                             'def render(rich, values):\n'
                             '    """Substitute only known literal tokens; never parse HTML or '
                             'format expressions."""\n'
                             '    text = rich["text"]\n'
                             '    spans, chunks, cursor = [], [], 0\n'
                             '    inserted, output_offset = [], 0\n'
                             '    for match in TOKEN.finditer(text):\n'
                             '        if match[1] not in values:\n'
                             '            continue\n'
                             '        raw = values[match[1]]\n'
                             '        value = raw["text"] if isinstance(raw, dict) else str(raw)\n'
                             '        output_offset += units(text[cursor:match.start()])\n'
                             '        if isinstance(raw, dict):\n'
                             '            inserted.extend({**e, "offset": '
                             'e["offset"]+output_offset} for e in raw.get("entities", []))\n'
                             '        output_offset += units(value)\n'
                             '        a, b = units(text[:match.start()]), '
                             'units(text[:match.end()])\n'
                             '        spans.append((a, b, units(value)))\n'
                             '        chunks.extend((text[cursor:match.start()], value))\n'
                             '        cursor = match.end()\n'
                             '    chunks.append(text[cursor:])\n'
                             '    output = "".join(chunks)\n'
                             '    def boundary(pos):\n'
                             '        shift = 0\n'
                             '        for a, b, length in spans:\n'
                             '            if pos <= a:\n'
                             '                break\n'
                             '            if pos < b:\n'
                             '                return None\n'
                             '            shift += length-(b-a)\n'
                             '        return pos+shift\n'
                             '    entities = []\n'
                             '    for e in rich.get("entities", []):\n'
                             '        a, b = boundary(e["offset"]), '
                             'boundary(e["offset"]+e["length"])\n'
                             '        if a is not None and b is not None and b > a:\n'
                             '            entities.append({**e, "offset": a, "length": b-a})\n'
                             '    return {"text": output, "entities": sorted(entities+inserted, '
                             'key=lambda e: (e["offset"], -e["length"]))[:100]}\n'
                             '\n'
                             '\n'
                             'def template(settings, key):\n'
                             '    if key in settings.get("texts", {}):\n'
                             '        return settings["texts"][key]\n'
                             '    text = settings["rules"] if key == "rules" else (\n'
                             '        settings["welcome_text"] if key == "welcome" else '
                             'DEFAULT_TEXTS[key])\n'
                             '    return {"text": text, "entities": []}\n'
                             '\n'
                             '\n'
                             'async def deliver(method, rich, **kwargs):\n'
                             '    """Retry only a rejected text request, never repeat the '
                             'moderation action."""\n'
                             '    try:\n'
                             '        return await method(rich["text"], '
                             'entities=rich.get("entities", []), **kwargs)\n'
                             '    except TelegramAPIError as exc:\n'
                             '        if exc.code != 400 or not any(e["type"] == "custom_emoji" '
                             'for e in rich.get("entities", [])):\n'
                             '            raise\n'
                             '        simple = [e for e in rich["entities"] if e["type"] != '
                             '"custom_emoji"]\n'
                             '        return await method(rich["text"], entities=simple, '
                             '**kwargs)\n'
                             '\n'
                             '\n'
                             'PREVIEW = {"uid": "123456789", "chat": "-100123456789", "actor": '
                             '"123456789",\n'
                             '    "minutes": 10, "reason": "Пример причины", "count": 1, "limit": '
                             '3, "name": "Участник",\n'
                             '    "key": "help", "hint": "", "fields": "без подстановок", "items": '
                             '"Пример списка",\n'
                             '    "page": 1, "pages": 7, "delete": "✅", "restrict": "✅", '
                             '"flood_limit": 7,\n'
                             '    "flood_window": 10, "warn_limit": 3, "mute_minutes": 60, '
                             '"word_count": 0,\n'
                             '    "setting": "warn_limit 3", "state": "✅", "date": "24.10 12:00", '
                             '"action": "warn",\n'
                             '    "detail": "Пример ошибки", "right": "can_restrict_members", '
                             '"parameters": "warn_limit",\n'
                             '    "low": 1, "high": 100}\n'
                             '\n'
                             '\n'
                             'def prepared(settings, key, values=None):\n'
                             '    values = values or {}\n'
                             '    rich = render(template(settings, key), values)\n'
                             '    if not rich["text"].strip() or units(rich["text"]) > 4096:\n'
                             '        rich = render(template({**settings, "texts": {}}, key), '
                             'values)\n'
                             '    return rich\n'
                             '\n'
                             '\n'
                             'def plain(rich, limit):\n'
                             '    text = rich["text"]\n'
                             '    while units(text) > limit:\n'
                             '        text = text[:-1]\n'
                             '    return text\n'
                             '\n'
                             '\n'
                             'def join_rich(first, second):\n'
                             '    shift = units(first["text"])\n'
                             '    return {"text": first["text"]+second["text"], "entities": '
                             'first.get("entities", []) +\n'
                             '            [{**e, "offset": e["offset"]+shift} for e in '
                             'second.get("entities", [])]}\n'
                             '\n'
                             '\n'
                             'def split_rich(rich, limit=4096):\n'
                             '    """Split long generated lists at Unicode boundaries and remap '
                             'formatting."""\n'
                             '    text, start = rich["text"], 0\n'
                             '    while text:\n'
                             '        count, size = 0, 0\n'
                             '        for c in text:\n'
                             '            width = units(c)\n'
                             '            if size+width > limit:\n'
                             '                break\n'
                             '            size += width\n'
                             '            count += 1\n'
                             '        end = start+size\n'
                             '        entities = []\n'
                             '        for e in rich.get("entities", []):\n'
                             '            a, b = e["offset"], e["offset"]+e["length"]\n'
                             '            if e["type"] in {"custom_emoji", "text_link", '
                             '"text_mention"} and (a < start or b > end):\n'
                             '                continue\n'
                             '            a, b = max(a, start), min(b, end)\n'
                             '            if b > a:\n'
                             '                entities.append({**e, "offset": a-start, "length": '
                             'b-a})\n'
                             '        yield {"text": text[:count], "entities": entities}\n'
                             '        text, start = text[count:], end\n'
                             '\n'
                             '\n'
                             'def join_lines(rows):\n'
                             '    result = {"text": "", "entities": []}\n'
                             '    for row in rows:\n'
                             '        if result["text"]:\n'
                             '            result = join_rich(result, {"text": "\\n", "entities": '
                             '[]})\n'
                             '        result = join_rich(result, row)\n'
                             '    return result\n',
 'tests/test_texts.py': 'import pytest\n'
                        '\n'
                        'from test_guardian import Telegram, bot, db, update\n'
                        'from guardian_cf.db import Database\n'
                        'from guardian_cf.telegram import Message, TelegramAPIError\n'
                        'from guardian_cf.texts import extract, render, units\n'
                        'from guardian_cf.webhook import process_update\n'
                        '\n'
                        '\n'
                        'async def run(db, api, text, number=1, actor=1, reply=None, '
                        'entities=None):\n'
                        '    data = update(text, actor=actor, update_id=number)\n'
                        '    if reply is not None:\n'
                        '        data["message"]["reply_to_message"] = reply\n'
                        '    if entities is not None:\n'
                        '        data["message"]["entities"] = entities\n'
                        '    await process_update(data, db, bot(api), "guardbot")\n'
                        '    return data\n'
                        '\n'
                        '\n'
                        'def emoji(offset):\n'
                        '    return {"type": "custom_emoji", "offset": offset, "length": 2, '
                        '"custom_emoji_id": "123456789"}\n'
                        '\n'
                        '\n'
                        'def sent(api):\n'
                        '    return [p for m, p in api.calls if m == "sendMessage"]\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def '
                        'test_inline_template_persists_unicode_and_renders_after_mute(db):\n'
                        '    api = Telegram()\n'
                        '    prefix = "/settext@guardbot mute "\n'
                        '    text = "{uid} 🔇 {minutes} мин. {reason}"\n'
                        '    await run(db, api, prefix+text, entities=[emoji(units(prefix+"{uid} '
                        '"))])\n'
                        '    assert (await '
                        'Database(db.binding).settings(-100123))["texts"]["mute"]["entities"][0]["offset"] '
                        '== 6\n'
                        '    await run(db, api, "/mute 5 1m <b>🙂</b>", 2)\n'
                        '    result = sent(api)[-1]\n'
                        '    assert result["text"] == "5 🔇 1 мин. <b>🙂</b>"\n'
                        '    assert result["entities"] == [emoji(2)]\n'
                        '    assert "parse_mode" not in result\n'
                        '    assert len([1 for m, _ in api.calls if m == "restrictChatMember"]) == '
                        '1\n'
                        '    assert "texts" not in await db.settings(-100456)\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        '@pytest.mark.parametrize("command", ["/settext ping changed", "/resettext '
                        'ping", "/edit changed", "/texts", "/emoji"])\n'
                        'async def test_text_commands_require_live_admin(db, command):\n'
                        '    api = Telegram()\n'
                        '    api.demoted.add(1)\n'
                        '    await run(db, api, command)\n'
                        '    assert not any(m == "editMessageText" for m, _ in api.calls)\n'
                        '    assert "texts" not in await db.settings(-100123)\n'
                        '    assert "администраторам" in sent(api)[-1]["text"]\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_reply_sample_caption_styles_and_reset(db):\n'
                        '    api = Telegram()\n'
                        '    source = update(actor=5)["message"]\n'
                        '    source.pop("text")\n'
                        '    source.update(caption="🙂 Правила", caption_entities=[emoji(0), '
                        '{"type": "bold", "offset": 3, "length": 7}])\n'
                        '    await run(db, api, "/setrules", reply=source)\n'
                        '    await run(db, api, "/rules", 2)\n'
                        '    assert sent(api)[-1]["entities"] == source["caption_entities"]\n'
                        '    await run(db, api, "/resettext rules", 3)\n'
                        '    await run(db, api, "/rules", 4)\n'
                        '    assert sent(api)[-1]["text"] == "Правила пока не заданы."\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_edit_own_message_preserves_keyboard_and_entities(db):\n'
                        '    api = Telegram()\n'
                        '    source = update("Old", actor=999)["message"]\n'
                        '    source["reply_markup"] = {"inline_keyboard": [[{"text": "Settings", '
                        '"callback_data": "toggle:welcome"}]]}\n'
                        '    await run(db, api, "/edit 🙂 Новый текст", reply=source, '
                        'entities=[emoji(6)])\n'
                        '    edited = next(p for m, p in api.calls if m == "editMessageText")\n'
                        '    assert edited["text"] == "🙂 Новый текст"\n'
                        '    assert edited["entities"] == [emoji(0)]\n'
                        '    assert edited["message_id"] == source["message_id"]\n'
                        '    assert edited["reply_markup"] == source["reply_markup"]\n'
                        '    assert (await db.logs(-100123))[0]["action"] == "edit_message"\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        '@pytest.mark.parametrize("kind", ["human", "otherbot", "forward", '
                        '"otherchat", "channel", "media", "missing"])\n'
                        'async def test_edit_rejects_other_messages(db, kind):\n'
                        '    api = Telegram()\n'
                        '    source = update("Old", actor=999)["message"]\n'
                        '    if kind == "human": source["from"]["id"] = 5\n'
                        '    if kind == "otherbot": source["from"]["id"] = 888\n'
                        '    if kind == "forward": source["forward_origin"] = {"type": "user"}\n'
                        '    if kind == "otherchat": source["chat"]["id"] = -100456\n'
                        '    if kind == "channel": source["sender_chat"] = {"id": -100456}\n'
                        '    if kind == "media": source.pop("text")\n'
                        '    if kind == "missing": source = None\n'
                        '    await run(db, api, "/edit changed", reply=source)\n'
                        '    assert not any(m == "editMessageText" for m, _ in api.calls)\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_unknown_placeholder_does_not_replace_template(db):\n'
                        '    api = Telegram()\n'
                        '    await run(db, api, "/settext ping good")\n'
                        '    await run(db, api, "/settext ping {reason}", 2)\n'
                        '    assert (await db.settings(-100123))["texts"]["ping"]["text"] == '
                        '"good"\n'
                        '    assert "Неизвестные" in sent(api)[-1]["text"]\n'
                        '\n'
                        '\n'
                        'def test_utf16_substitution_updates_bold_and_custom_emoji():\n'
                        '    rich = {"text": "🙂 {name} 🔇", "entities": [\n'
                        '        {"type": "bold", "offset": 3, "length": 6}, emoji(10)]}\n'
                        '    result = render(rich, {"name": "A🙂Б"})\n'
                        '    assert result["text"] == "🙂 A🙂Б 🔇"\n'
                        '    assert result["entities"] == [{"type": "bold", "offset": 3, "length": '
                        '4}, emoji(8)]\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_custom_emoji_rejection_retries_text_only_never_mute(db):\n'
                        '    class RejectEmoji(Telegram):\n'
                        '        async def __call__(self, method, params):\n'
                        '            result = await super().__call__(method, params)\n'
                        '            if method == "sendMessage" and any(e["type"] == '
                        '"custom_emoji" for e in params.get("entities", [])):\n'
                        '                raise TelegramAPIError(400)\n'
                        '            return result\n'
                        '    api = RejectEmoji()\n'
                        '    prefix = "/settext mute "\n'
                        '    await run(db, api, prefix+"🔇 {uid}", '
                        'entities=[emoji(units(prefix))])\n'
                        '    await run(db, api, "/mute 5 1m", 2)\n'
                        '    assert sent(api)[-1]["text"] == "🔇 5"\n'
                        '    assert sent(api)[-1]["entities"] == []\n'
                        '    assert len([1 for m, _ in api.calls if m == "restrictChatMember"]) == '
                        '1\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_preview_does_not_moderate_and_long_render_falls_back(db):\n'
                        '    api = Telegram()\n'
                        '    await run(db, api, "/settext ban " + "{reason}"*240)\n'
                        '    await run(db, api, "/previewtext ban", 2)\n'
                        '    assert not any(m == "banChatMember" for m, _ in api.calls)\n'
                        '    await run(db, api, "/ban 5 " + "x"*300, 3)\n'
                        '    assert units(sent(api)[-1]["text"]) <= 4096\n'
                        '    assert "Участник забанен" in sent(api)[-1]["text"]\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_emoji_id_and_edited_config_ignored(db):\n'
                        '    api = Telegram()\n'
                        '    source = update("🙂", actor=5)["message"]\n'
                        '    source["entities"] = [emoji(0)]\n'
                        '    await run(db, api, "/emoji", reply=source)\n'
                        '    assert "123456789" in sent(api)[-1]["text"]\n'
                        '    await process_update(update("/settext ping bad", update_id=2, '
                        'edited=True), db, bot(api), "guardbot")\n'
                        '    assert "texts" not in await db.settings(-100123)\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def '
                        'test_help_and_start_rich_templates_are_chat_scoped_and_resettable(db):\n'
                        '    api = Telegram()\n'
                        "    prefix = '/settext help '\n"
                        "    body = '🙂 Моя справка: /settext mute ID {uid}'\n"
                        '    await run(db, api, prefix+body, entities=[emoji(units(prefix))])\n'
                        "    await run(db, api, '/help', 2)\n"
                        "    assert sent(api)[-1]['text'] == body\n"
                        "    assert sent(api)[-1]['entities'] == [emoji(0)]\n"
                        "    other = update('/help', update_id=3)\n"
                        "    other['message']['chat']['id'] = -100456\n"
                        "    await process_update(other, db, bot(api), 'guardbot')\n"
                        "    assert 'Guardian' in sent(api)[-1]['text']\n"
                        "    await run(db, api, '/settext start Welcome!', 4)\n"
                        "    await run(db, api, '/start', 5)\n"
                        "    assert sent(api)[-1]['text'] == 'Welcome!'\n"
                        "    await run(db, api, '/resettext help', 6)\n"
                        "    await run(db, api, '/help', 7)\n"
                        "    assert 'Guardian' in sent(api)[-1]['text']\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_every_template_can_be_saved_previewed_and_reset(db):\n'
                        '    from guardian_cf.texts import FIELDS, PREVIEW, template, render\n'
                        '    api = Telegram()\n'
                        '    number = 1\n'
                        '    for key, fields in FIELDS.items():\n'
                        "        body = key+' '+ ' '.join('{'+f+'}' for f in sorted(fields))\n"
                        "        await run(db, api, '/settext '+key+' '+body.strip(), number)\n"
                        "        assert (await db.settings(-100123))['texts'][key]['text'] == "
                        'body.strip(), key\n'
                        "        await run(db, api, '/previewtext '+key, number+1)\n"
                        "        expected = render({'text':body.strip()}, {f: PREVIEW.get(f, "
                        "'Пример') for f in fields})['text']\n"
                        "        assert sent(api)[-1]['text'] == expected, key\n"
                        "        await run(db, api, '/resettext '+key, number+2)\n"
                        "        assert key not in (await db.settings(-100123))['texts'], key\n"
                        '        number += 3\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_template_catalog_pages_and_detail(db):\n'
                        '    from guardian_cf.texts import FIELDS\n'
                        '    api = Telegram()\n'
                        '    pages = (len(FIELDS)+11)//12\n'
                        "    all_text = ''\n"
                        '    for page in range(1, pages+1):\n'
                        "        await run(db, api, f'/texts {page}', page)\n"
                        "        result = sent(api)[-1]['text']\n"
                        '        assert units(result) <= 4096\n'
                        "        all_text += result+'\\n'\n"
                        '    for key in FIELDS:\n'
                        "        assert '\\n'+key+':' in all_text\n"
                        "    await run(db, api, '/texts help', 100)\n"
                        "    assert 'help: без подстановок' in sent(api)[-1]['text']\n"
                        "    await run(db, api, '/texts 999', 101)\n"
                        "    assert 'Укажи страницу' in sent(api)[-1]['text']\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def '
                        'test_custom_settings_survive_callback_and_button_labels_do_not_change_actions(db):\n'
                        '    api = Telegram()\n'
                        "    await run(db, api, '/settext settings Настройки: {flood_limit}; слов "
                        "{word_count}')\n"
                        "    await run(db, api, '/settext button_antilinks {state} Ссылки', 2)\n"
                        "    await run(db, api, '/settext callback_saved Готово!', 3)\n"
                        "    await run(db, api, '/settings', 4)\n"
                        "    assert sent(api)[-1]['text'] == 'Настройки: 7; слов 0'\n"
                        "    buttons = sent(api)[-1]['reply_markup']['inline_keyboard']\n"
                        "    assert buttons[1][0] == {'text':'⬜ Ссылки', "
                        "'callback_data':'toggle:antilinks'}\n"
                        "    data = {'update_id':5, 'callback_query':{'id':'query', "
                        "'data':'toggle:antilinks',\n"
                        "        'from':{'id':1}, 'message':update()['message']}}\n"
                        "    await process_update(data, db, bot(api), 'guardbot')\n"
                        "    assert (await db.settings(-100123))['antilinks'] is True\n"
                        "    assert any(m == 'answerCallbackQuery' and p['text'] == 'Готово!' for "
                        'm,p in api.calls)\n'
                        "    result = next(p for m,p in api.calls if m == 'editMessageText')\n"
                        "    assert result['text'] == 'Настройки: 7; слов 0'\n"
                        "    assert result['reply_markup']['inline_keyboard'][1][0]['text'] == '✅ "
                        "Ссылки'\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_custom_admin_error_does_not_grant_permission(db):\n'
                        '    api = Telegram()\n'
                        "    await run(db, api, '/settext error_admin_only Доступ закрыт')\n"
                        '    api.demoted.add(1)\n'
                        "    await run(db, api, '/ban 5', 2)\n"
                        "    assert sent(api)[-1]['text'] == 'Доступ закрыт'\n"
                        "    assert not any(m == 'banChatMember' for m,p in api.calls)\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        "@pytest.mark.parametrize('key, command, body, expected', [\n"
                        "    ('id','/id','Чат {chat}, ID {uid}','Чат -100123, ID 1'),\n"
                        "    ('check','/check','Удаление {delete}; мут {restrict}','Удаление ✅; "
                        "мут ✅'),\n"
                        "    ('warnings_self','/warnings','Предов: {count}','Предов: 0'),\n"
                        "    ('warnings','/warnings 5','У {uid}: {count}','У 5: 0'),\n"
                        "    ('unwarn','/unwarn 5','Осталось {count}','Осталось 0'),\n"
                        "    ('resetwarns','/resetwarns 5','Сброшено для {uid}','Сброшено для "
                        "5'),\n"
                        "    ('words_saved','/word add test','Записал','Записал'),\n"
                        "    ('setting_saved','/set warn_limit 5','Настроено: "
                        "{setting}','Настроено: warn_limit 5'),\n"
                        "    ('emoji_empty','/emoji','Нет эмодзи','Нет эмодзи'),\n"
                        "    ('error_mute_duration','/mute 5','Укажи время','Укажи время'),\n"
                        "    ('validation_error','/mute 5 xyz','Проверь: {detail}','Проверь: "
                        "Время: 10m, 2h, 7d (или 10м, 2ч, 7д).'),\n"
                        '])\n'
                        'async def test_new_command_outputs_use_saved_templates(db, key, command, '
                        'body, expected):\n'
                        '    api = Telegram()\n'
                        "    await run(db, api, f'/settext {key} {body}')\n"
                        '    await run(db, api, command, 2)\n'
                        "    assert sent(api)[-1]['text'] == expected\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_rich_log_rows_and_long_lists(db):\n'
                        '    api = Telegram()\n'
                        "    prefix = '/settext log_row '\n"
                        "    await run(db, api, prefix+'🙂 {reason}', "
                        'entities=[emoji(units(prefix))])\n'
                        "    await run(db, api, '/settext logs Журнал:\\n{items}', 2)\n"
                        "    await run(db, api, '/logs', 3)\n"
                        "    assert sent(api)[-1]['text'].startswith('Журнал:\\n🙂')\n"
                        "    assert sent(api)[-1]['entities'][0] == emoji(units('Журнал:\\n'))\n"
                        "    await run(db, api, '/settext log_row '+ '🙂'*1900, 4)\n"
                        "    await run(db, api, '/logs', 5)\n"
                        "    assert all(units(p['text']) <= 4096 for p in sent(api))\n"
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_long_help_and_bad_placeholder_keep_previous_text(db):\n'
                        '    api = Telegram()\n'
                        "    body = 'А'*3900\n"
                        "    await run(db, api, '/settext help '+body)\n"
                        "    await run(db, api, '/help', 2)\n"
                        "    assert sent(api)[-1]['text'] == body\n"
                        "    await run(db, api, '/settext settings good', 3)\n"
                        "    await run(db, api, '/settext settings {nonsense}', 4)\n"
                        "    assert (await db.settings(-100123))['texts']['settings']['text'] == "
                        "'good'\n"
                        "    await run(db, api, '/settext help '+'А'*4001, 5)\n"
                        "    assert (await db.settings(-100123))['texts']['help']['text'] == body\n"
                        '\n'
                        '\n'
                        'def test_rich_split_keeps_unicode_and_offsets():\n'
                        '    from guardian_cf.texts import split_rich\n'
                        "    rich = {'text':'А'*4095+'🙂Б', 'entities':[emoji(4095)]}\n"
                        '    parts = list(split_rich(rich))\n'
                        "    assert ''.join(p['text'] for p in parts) == rich['text']\n"
                        "    assert parts[1]['entities'] == [emoji(0)]\n"
                        "    assert all(units(p['text']) <= 4096 for p in parts)\n"}

if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent)
