"""Guardian Cloudflare update 2.5.2: verified username targets; no wrong reply fallback.

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
    # Remove only retired generated modules from a cached 2.4 build.
    for relative in ("src/guardian_cf/ranks.py", "tests/test_ranks.py"):
        (output / relative).unlink(missing_ok=True)
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
UPDATED_SOURCES = {'README_TEXTS_RU.md': '# Guardian 2.5.2 — все шаблоны ответов Cloudflare\n'
                       '\n'
                       '## Установка с телефона\n'
                       '\n'
                       'Замените только `prepare_cloudflare.py` в корне репозитория, сохраните коммит в '
                       'main.\n'
                       'Исходный `Guardian-Telegram-Bot.zip` оставьте на месте. Скрипт накладывает новые '
                       'модули\n'
                       'на исходный архив. Дождитесь успешной сборки и развёртывания Cloudflare.\n'
                       'Команды сборки и deploy прежние. Существующие настройки, тексты и предупреждения '
                       'сохраняются.\n'
                       'Версию можно проверить по стандартной справке: «Guardian 2.5.2» (если help не '
                       'заменён).\n'
                       'Надёжная проверка возможностей: `/texts` показывает кнопки выбора шаблонов и стрелки '
                       'страниц.\n'
                       '\n'
                       'Сборка сохраняет существующие переменные Cloudflare (`keep_vars: true`),\n'
                       'в том числе BOT_USERNAME. Уже удалённое значение этот флаг не восстанавливает:\n'
                       'BOT_USERNAME должен быть задан в runtime-настройках, без @. Токены в код не '
                       'добавляйте.\n'
                       '\n'
                       '## Редактор с кнопками\n'
                       '\n'
                       '1. Отправь `/texts` или открой `/settings` → «Тексты бота».\n'
                       '2. Выбери шаблон. По 12 шаблонов на странице, стрелки переключают страницы.\n'
                       '3. «Посмотреть» отправляет пример с подставленными значениями. «Исходный текст»\n'
                       '   отправляет текст с оригинальными подстановками и оформлением для копирования.\n'
                       '4. «Редактировать» присылает персональное приглашение. Ответь именно на него новым\n'
                       '   текстом (можно с премиум-эмодзи, жирным шрифтом и ссылками) или подписью к '
                       'медиа.\n'
                       '5. Бот покажет образец. Нажми «Сохранить» или «Отмена». До сохранения шаблон '
                       'прежний.\n'
                       '6. «Сбросить» → «Да, сбросить» возвращает стандартный текст. `/cancel` отменяет '
                       'редактор.\n'
                       '\n'
                       'Редактор живёт 15 минут; черновик тоже хранится 15 минут после отправки.\n'
                       'Состояние хранится в существующей D1, переживает новый запрос/перезапуск Worker.\n'
                       'Оно привязано к администратору, группе, теме и конкретному приглашению.\n'
                       'Сообщения остальных участников, другой темы и обычные сообщения не захватываются.\n'
                       'Права администратора или доступ @ivan22350 проверяются при каждом нажатии, при вводе '
                       'и сохранении.\n'
                       'Новая сессия в той же теме заменяет старую. Изменения старых сообщений не '
                       'сохраняются.\n'
                       '\n'
                       'Премиум-эмодзи добавляются из самого Telegram: выбери их на клавиатуре при вводе\n'
                       'нового текста. Для значка кнопки отредактируй шаблон `editor_edit`, `editor_save`,\n'
                       '`editor_next`, `editor_prev`, `editor_open` или другой `editor_*`/`button_*`, '
                       'добавив\n'
                       'в текст пользовательский эмодзи. В кнопке используется первый такой эмодзи;\n'
                       'обычный символ остаётся в подписи как запасной вариант. Кнопки выбора шаблонов\n'
                       'используют обычные значки и имена, а шаблоны управляющих кнопок доступны в '
                       'каталоге.\n'
                       'Telegram разрешает пользовательские эмодзи ботам с дополнительными именами,\n'
                       'приобретёнными на Fragment, или при Premium у владельца бота в поддерживаемых '
                       'чатах.\n'
                       'Если Telegram отклоняет custom emoji, отправка повторяется без них и без значков\n'
                       'кнопок; сохранённый шаблон и действия кнопок не меняются. Реальный показ зависит\n'
                       'от разрешений Telegram и клиента. Ссылки: '
                       'https://core.telegram.org/bots/api#inlinekeyboardbutton\n'
                       'и https://core.telegram.org/bots/api#formatting-options.\n'
                       '\n'
                       '## Команды в группе\n'
                       '\n'
                       'Все изменения доступны только текущим администраторам супергруппы и участнику\n'
                       'с актуальным username @ivan22350, от личного аккаунта. Они хранятся отдельно для '
                       'каждой группы и переживают перезапуск/деплой.\n'
                       'В личных сообщениях остаётся стандартная справка: администратор одной группы\n'
                       'не может менять глобальные ответы бота для других людей.\n'
                       '\n'
                       '- `/texts` — первая страница каталога; `/texts 2`, `/texts 3` — остальные.\n'
                       '- `/texts help` — допустимые подстановки и команды для выбранного шаблона.\n'
                       '- `/settext help Моя новая справка` — заменить справку этой группы.\n'
                       '- `/settext start Привет! Команды: /help` — заменить ответ на /start в группе.\n'
                       '- `/previewtext help` — показать сохранённый шаблон с примерами значений.\n'
                       '- `/resettext help` — вернуть стандартную справку.\n'
                       '\n'
                       'Для многострочного текста, жирного начертания, ссылок или пользовательских эмодзи\n'
                       'отправьте образец отдельным сообщением. Ответьте на него `/settext help`.\n'
                       'Можно использовать подпись к медиа как образец. Максимум 4000 единиц UTF-16\n'
                       '(обычный смайлик часто занимает две), 100 элементов оформления.\n'
                       '`/edit Новый текст` ответом на собственное текстовое сообщение бота меняет только\n'
                       'это сообщение. `/settext` влияет на будущие ответы. `/emoji` ответом на образец\n'
                       'показывает ID пользовательских эмодзи.\n'
                       '\n'
                       'Для help/start фигурные скобки сохраняются буквально: можно писать примеры\n'
                       '`/settext mute ID {uid}`. У остальных шаблонов принимаются только подстановки\n'
                       'из `/texts ИМЯ`. Текст не исполняется как Python или HTML. Подстановки не\n'
                       'разбираются повторно. Неизвестная подстановка не перезаписывает старый шаблон.\n'
                       '\n'
                       'Настраиваются тексты сообщений, результаты команд, ошибки, уведомления кнопок\n'
                       'и их подписи. Права пользователей, действия модерации и callback-команды от\n'
                       'смены текста не меняются. validation_error задаёт общий текст ошибок формата;\n'
                       'его {detail} содержит исходное объяснение, например неправильный срок мута.\n'
                       '\n'
                       'В сообщениях поддерживаются оформление и пользовательские эмодзи. Telegram\n'
                       'может запретить отправку таких эмодзи конкретному боту; в этом случае повторяется\n'
                       'только отправка текста без custom_emoji, не наказание. В коротких всплывающих\n'
                       'уведомлениях выводится простой текст до 200 единиц UTF-16. Подписи кнопок\n'
                       'ограничены 64 единицами UTF-16; первый custom_emoji в их шаблоне дополнительно\n'
                       'используется как icon_custom_emoji_id. Остальное оформление кнопок Telegram не '
                       'поддерживает. /previewtext показывает образец сообщения,\n'
                       'а фактическая кнопка/уведомление использует эти ограничения.\n'
                       '\n'
                       'Если подстановки раздули шаблон больше 4096 единиц, используется стандартный\n'
                       'шаблон; длинные списки журналов разбиваются на сообщения с сохранением оформления.\n'
                       'Сохранение слишком длинного текста отклоняется. Старые шаблоны 2.1 сохраняются.\n'
                       'Технические HTTP-ответы webhook и внутренние записи аудита не являются текстами\n'
                       'Telegram и не редактируются командами. group_only и callback_group_only относятся\n'
                       'к неподдерживаемым контекстам; в личке действуют их стандартные значения.\n'
                       '\n'
                       '## Доступ в версии 2.5\n'
                       '\n'
                       'Ранги, XP, таблица лидеров, их команды и кнопки удалены. Старые кнопки рангов\n'
                       'не выполняют действий. Если версия 2.4 уже запускалась, её накопленные данные\n'
                       'остаются в базе без использования; удаление рангов не стирает другие данные.\n'
                       '\n'
                       'Бан, мут, кик, предупреждения, удаление сообщений, изменение настроек и текстов\n'
                       'доступны только администраторам этой группы и аккаунту с текущим username\n'
                       '`@ivan22350`. Проверка делается по свежему ответу Telegram `getChatMember`.\n'
                       'Отображаемое имя, текст сообщения и username из пересланного сообщения доступа\n'
                       'не дают. Регистр букв username не важен. @ivan22350 должен состоять в группе.\n'
                       'При смене username этот специальный доступ перестаёт работать; правило\n'
                       'относится к текущему владельцу username, а не к навсегда закреплённому Telegram ID.\n'
                       '\n'
                       'Исключение @ivan22350 позволяет управлять ботом без назначения этого человека\n'
                       'администратором Telegram. Самому боту всё равно нужны права удаления сообщений\n'
                       'и блокировки участников. Обычные администраторы используют прежние ограничения\n'
                       'своих прав для конкретных действий. Защита администраторов, бота и себя от\n'
                       'наказания сохранена; @ivan22350 тоже защищён и освобождён от автоматических '
                       'фильтров.\n'
                       'Справка, правила, ID, жалоба и просмотр своих предупреждений остаются '
                       'общедоступными.\n'
                       '\n'
                       'Проверка доступа работает для команд, кнопок настроек, открытия редактора,\n'
                       'ввода текста и окончательного сохранения. Старый черновик нельзя сохранить\n'
                       'после потери прав. Анонимные сообщения от имени группы не используются для '
                       'управления.\n'
                       'Сохранённые пользовательские тексты справки не заменяются: при желании обнови\n'
                       'их через `/texts` или верни стандартную справку командой `/resettext help`.\n'
                       '\n'
                       '## Исправление выбора цели 2.5.1\n'
                       '\n'
                       '`/mute 8549615756 10m` выбирает указанный ID даже при ответе на сообщение\n'
                       'другого человека или бота. `/mute 10m` ответом на участника по-прежнему выбирает\n'
                       'автора сообщения, на которое дан ответ. В командах без причины /unmute, /unban, '
                       '/unwarn, /resetwarns, /warnings числовой ID также имеет приоритет.\n'
                       'Для /ban, /kick, /warn числовой ID отправляй без ответа, чтобы отличить его от '
                       'причины, начинающейся с числа.\n'
                       '\n'
                       'Вместо общей ошибки защиты бот указывает ID цели и конкретную причину:\n'
                       'собственный аккаунт, этот бот, администратор/владелец группы или @ivan22350.\n'
                       'Права и защита администраторов не отключаются. Тексты новых ошибок доступны\n'
                       'в `/texts` под именами `error_target_self`, `error_target_bot`,\n'
                       '`error_target_admin`, `error_target_trusted`.\n'
                       '\n'
                       '## Username и выбор участника (2.5.2)\n'
                       '\n'
                       'Явный @username имеет приоритет над автором сообщения, на которое отвечает команда.\n'
                       'Это работает для /mute, /unmute, /ban, /unban, /kick, /warn, /unwarn, /resetwarns и '
                       '/warnings.\n'
                       'Например, `/unmute @abamako999,` обрабатывается как `/unmute @abamako999`:\n'
                       'знаки препинания в конце username допускаются, регистр букв не важен.\n'
                       'Если ID не удалось подтвердить, команда НЕ переключается на автора ответа.\n'
                       '\n'
                       'Bot API требует числовой user_id для getChatMember и действий с участником.\n'
                       'Поэтому бот запоминает связь username → ID из авторов сообщений, сообщений,\n'
                       'на которые отвечают, и уведомлений о новых участниках. Список отдельный для каждой\n'
                       'группы, хранится в существующей таблице ephemeral до 30 дней и обновляется из '
                       'сообщений.\n'
                       'Старую историю группы бот не загружает. Перед действием getChatMember проверяет,\n'
                       'что у найденного ID всё ещё тот самый username; при переименовании действие '
                       'отклоняется.\n'
                       'Ошибка Telegram тоже не приводит к выбору другого участника.\n'
                       '\n'
                       'Если username неизвестен, ответь на старое сообщение нужного человека `/unmute`\n'
                       'без аргументов либо используй числовой ID без ответа. Это работает и когда человек\n'
                       'уже замучен и не может написать новое сообщение. После первого наблюдения username\n'
                       'можно использовать команды с ним, пока Telegram подтверждает соответствие.\n'
                       'Отображаемое имя и простое упоминание @username в тексте не используются для\n'
                       'запоминания ID. Приватные чаты и группы не обмениваются этим списком.\n'
                       '\n'
                       'Права администраторов и @ivan22350, защита целей, редактор и премиум-эмодзи '
                       'сохранены.\n'
                       'Новый текст ошибки доступен в `/texts error_username_unknown`.\n'
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
                       '| `settings` | `{flood_limit}`, `{flood_window}`, `{mute_minutes}`, `{warn_limit}`, '
                       '`{word_count}` |\n'
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
                       '| `button_welcome` | `{state}` |\n'
                       '| `editor_open` | — |\n'
                       '| `editor_source` | — |\n'
                       '| `editor_prev` | — |\n'
                       '| `editor_next` | — |\n'
                       '| `editor_page` | `{page}`, `{pages}` |\n'
                       '| `editor_edit` | — |\n'
                       '| `editor_preview` | — |\n'
                       '| `editor_reset` | — |\n'
                       '| `editor_back` | — |\n'
                       '| `editor_save` | — |\n'
                       '| `editor_cancel` | — |\n'
                       '| `editor_confirm_reset` | — |\n'
                       '| `editor_reset_question` | `{key}` |\n'
                       '| `editor_prompt` | `{key}` |\n'
                       '| `editor_waiting` | — |\n'
                       '| `editor_draft` | `{key}` |\n'
                       '| `editor_expired` | — |\n'
                       '| `editor_cancelled` | — |\n'
                       '| `error_target_self` | `{uid}` |\n'
                       '| `error_target_bot` | `{uid}` |\n'
                       '| `error_target_admin` | `{uid}` |\n'
                       '| `error_target_trusted` | `{uid}` |\n'
                       '| `error_username_unknown` | `{username}` |\n',
 'schema.sql': 'CREATE TABLE IF NOT EXISTS settings(chat INTEGER PRIMARY KEY, value TEXT NOT NULL);\n'
               'CREATE TABLE IF NOT EXISTS warnings(chat INTEGER, user INTEGER, count INTEGER NOT NULL '
               'DEFAULT 0, PRIMARY KEY(chat,user));\n'
               'CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, chat INTEGER NOT '
               'NULL, actor INTEGER NOT NULL, target INTEGER, action TEXT NOT NULL, reason TEXT NOT NULL, at '
               'INTEGER NOT NULL);\n'
               'CREATE INDEX IF NOT EXISTS audit_chat_id ON audit(chat,id);\n'
               'CREATE INDEX IF NOT EXISTS audit_at ON audit(at);\n'
               'CREATE TABLE IF NOT EXISTS ephemeral(key TEXT PRIMARY KEY, value TEXT NOT NULL, expires '
               'INTEGER NOT NULL);\n'
               'CREATE INDEX IF NOT EXISTS ephemeral_expires ON ephemeral(expires);\n'
               'CREATE TABLE IF NOT EXISTS updates(id INTEGER PRIMARY KEY, state TEXT NOT NULL, started '
               'INTEGER NOT NULL, finished INTEGER);\n'
               'CREATE INDEX IF NOT EXISTS updates_started ON updates(started);\n'
               'CREATE TABLE IF NOT EXISTS chat_locks(chat INTEGER PRIMARY KEY, owner TEXT NOT NULL, expires '
               'INTEGER NOT NULL);\n'
               'CREATE INDEX IF NOT EXISTS chat_locks_expires ON chat_locks(expires);\n',
 'src/guardian_cf/access.py': '"""Authorization based on a fresh Telegram getChatMember response, never '
                              'display names."""\n'
                              "TRUSTED_USERNAME = 'ivan22350'\n"
                              "ADMIN_STATUSES = {'creator', 'administrator'}\n"
                              '\n'
                              '\n'
                              'def trusted_member(member, user_id):\n'
                              '    user = member.user\n'
                              '    return bool(\n'
                              '        user and user.id == user_id and user.is_bot is False\n'
                              "        and (user.username or '').casefold() == TRUSTED_USERNAME\n"
                              "        and (member.status in {'creator', 'administrator', 'member'}\n"
                              "             or (member.status == 'restricted' and member.is_member is "
                              'True))\n'
                              '    )\n'
                              '\n'
                              '\n'
                              'def allowed_member(member, user_id):\n'
                              '    return member.status in ADMIN_STATUSES or trusted_member(member, '
                              'user_id)\n',
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
                           'from .usernames import Usernames, parse_username\n'
                           'from .editor import TextEditor\n'
                           'from .access import allowed_member, trusted_member\n'
                           'from .db import Database, PersistentFlood, PersistentCooldowns\n'
                           'from .texts import (FIELDS, PREVIEW, prepared, extract, validate, render,\n'
                           '                    template, deliver, units, join_rich, split_rich, plain, '
                           'join_lines, template_button)\n'
                           'from .policy import (BOOL_KEYS, LIMITS, Cooldowns, FloodGuard, contains_link,\n'
                           '                     duration, forbidden_word, parse_command, normalize)\n'
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
                           '            rich = join_rich(rich, suffix if isinstance(suffix, dict) else '
                           '{"text": suffix, "entities": []})\n'
                           '        kwargs = {"reply_markup": reply_markup} if reply_markup is not None else '
                           '{}\n'
                           '        result = None\n'
                           '        for part in split_rich(rich):\n'
                           '            result = await deliver(method or m.answer, part, **kwargs)\n'
                           '        return result\n'
                           '\n'
                           '    async def alert(self, q, key, show_alert=False, **values):\n'
                           '        s = await self.db.settings(q.message.chat.id) if q.message else {}\n'
                           '        # Callback popups cannot contain Telegram entities and are limited to '
                           '200 characters.\n'
                           '        text = plain(prepared(s, key, values), 200)\n'
                           '        return await q.answer(text, show_alert=show_alert)\n'
                           '\n'
                           '    async def text_command(self, m, cmd, args):\n'
                           '        chat, actor = m.chat.id, m.from_user.id\n'
                           '        if cmd == "edit":\n'
                           '            reply = m.reply_to_message\n'
                           '            if (not reply or not reply.from_user or reply.from_user.id != '
                           'self.bot.id\n'
                           '                    or reply.sender_chat or reply.forward_origin or not '
                           'reply.text\n'
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
                           '            entities = source.entities or source.caption_entities or []\n'
                           '            ids = list(dict.fromkeys(e.custom_emoji_id for e in entities if '
                           'e.type == "custom_emoji"))\n'
                           '            return await self.say(m, "emoji" if ids else "emoji_empty", '
                           'items="\\n".join(ids[:50]))\n'
                           '        if cmd == "texts":\n'
                           '            editor = TextEditor(self)\n'
                           '            if args in FIELDS:\n'
                           '                return await editor.detail(m, args)\n'
                           '            pages = (len(FIELDS)+11)//12\n'
                           '            if args and (not args.isdigit() or not 1 <= int(args) <= pages):\n'
                           '                raise UserError("error_texts_page", pages=pages)\n'
                           '            return await editor.page(m, int(args) if args else 1)\n'
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
                           '            rich = render(template(s, key), {field: PREVIEW.get(field, "Пример") '
                           'for field in FIELDS[key]})\n'
                           '            if units(rich["text"]) > 4096:\n'
                           '                raise UserError("error_preview_long")\n'
                           '            for part in split_rich(rich):\n'
                           '                await deliver(m.answer, part)\n'
                           '            return\n'
                           '        await self.db.save_settings(chat, s)\n'
                           '        await self.db.audit(chat, actor, None, cmd, key)\n'
                           '        hint = prepared(s, "welcome_hint")["text"] if key == "welcome" else ""\n'
                           '        return await self.say(m, "text_saved", key=key, hint=hint)\n'
                           '\n'
                           '    async def is_admin(self, chat, user):\n'
                           '        member = await self.bot.get_chat_member(chat, user)\n'
                           '        return allowed_member(member, user)\n'
                           '\n'
                           '    async def require_admin(self, chat, user, right=None):\n'
                           '        member = await self.bot.get_chat_member(chat, user)\n'
                           '        if trusted_member(member, user):\n'
                           '            return\n'
                           '        if member.status not in ADMINS:\n'
                           '            raise UserError("error_admin_only")\n'
                           '        if right and member.status != "creator" and not getattr(member, right, '
                           'False):\n'
                           '            raise UserError("error_admin_right", right=right)\n'
                           '\n'
                           '    async def require_bot(self, chat, right):\n'
                           '        member = await self.bot.get_chat_member(chat, self.bot.id)\n'
                           '        if member.status != "administrator" or not getattr(member, right, '
                           'False):\n'
                           '            raise UserError("error_bot_right", right=right)\n'
                           '\n'
                           '    async def target(self, m, args, protect=True, explicit_id=False):\n'
                           '        reply = m.reply_to_message\n'
                           '        pieces = args.split(maxsplit=1)\n'
                           '        # /mute <ID> <duration> is unambiguous because reply-style durations\n'
                           '        # always carry m/h/d. A quoted message must not override that explicit '
                           'ID.\n'
                           '        use_id = explicit_id and pieces and pieces[0].isascii() and '
                           'pieces[0].isdigit()\n'
                           "        if pieces and pieces[0].startswith('@'):\n"
                           '            username = parse_username(pieces[0])\n'
                           '            uid = await Usernames(self.db, self.bot).resolve(m.chat.id, '
                           'username)\n'
                           '            if uid is None:\n'
                           '                raise UserError("error_username_unknown", username=username)\n'
                           '            rest = pieces[1] if len(pieces) > 1 else ""\n'
                           '        elif reply and not use_id:\n'
                           '            if reply.sender_chat or not reply.from_user:\n'
                           '                raise UserError("error_target_channel")\n'
                           '            uid, rest = reply.from_user.id, args\n'
                           '        else:\n'
                           '            if (not pieces or not pieces[0].isascii() or not '
                           'pieces[0].isdigit()\n'
                           '                    or len(pieces[0]) > 16 or not 0 < int(pieces[0]) < 2**52):\n'
                           '                raise UserError("error_target_required")\n'
                           '            uid, rest = int(pieces[0]), pieces[1] if len(pieces) > 1 else ""\n'
                           '        if protect:\n'
                           '            if uid == m.from_user.id:\n'
                           '                raise UserError("error_target_self", uid=uid)\n'
                           '            if uid == self.bot.id:\n'
                           '                raise UserError("error_target_bot", uid=uid)\n'
                           '            member = await self.bot.get_chat_member(m.chat.id, uid)\n'
                           '            if member.status in ADMINS:\n'
                           '                raise UserError("error_target_admin", uid=uid)\n'
                           '            if trusted_member(member, uid):\n'
                           '                raise UserError("error_target_trusted", uid=uid)\n'
                           '        return uid, rest\n'
                           '\n'
                           '    async def mute(self, chat, uid, seconds):\n'
                           '        # Do not shorten an existing restriction or discard its custom '
                           'permissions.\n'
                           '        member = await self.bot.get_chat_member(chat, uid)\n'
                           '        if uid == self.bot.id:\n'
                           '            raise UserError("error_target_bot", uid=uid)\n'
                           '        if member.status in ADMINS:\n'
                           '            raise UserError("error_target_admin", uid=uid)\n'
                           '        if trusted_member(member, uid):\n'
                           '            raise UserError("error_target_trusted", uid=uid)\n'
                           '        if member.status == "restricted":\n'
                           '            raise UserError("error_already_restricted")\n'
                           '        if member.status in {"left", "kicked"}:\n'
                           '            raise UserError("error_member_missing")\n'
                           '        await self.bot.restrict_chat_member(\n'
                           '            chat, uid, permissions=ChatPermissions(**{k: False for k in '
                           'ChatPermissions.model_fields}),\n'
                           '            until_date=datetime.now(timezone.utc) + timedelta(seconds=seconds),\n'
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
                           '                await self.require_bot(m.chat.id, "can_restrict_members")\n'
                           '                await self.mute(m.chat.id, uid, settings["mute_minutes"] * 60)\n'
                           '            except (TelegramAPIError, UserError):\n'
                           '                suffix = prepared(settings, "warn_automute_failed")\n'
                           '            else:\n'
                           '                await self.db.audit(m.chat.id, self.bot.id, uid, "automute", '
                           '"Лимит предупреждений")\n'
                           '                await self.db.change_warns(m.chat.id, uid, reset=True)\n'
                           '                suffix = prepared(settings, "warn_automute_success", {"minutes": '
                           'settings["mute_minutes"]})\n'
                           '        await self.say(m, "warn", suffix=suffix, uid=uid, count=count, '
                           'limit=settings["warn_limit"], reason=reason[:300])\n'
                           '\n'
                           '    def keyboard(self, settings):\n'
                           '        return InlineKeyboardMarkup(inline_keyboard=[[\n'
                           '            template_button(settings, "button_"+key, f"toggle:{key}",\n'
                           '                {"state": "✅" if settings[key] else "⬜"})\n'
                           '        ] for key in ("antiflood", "antilinks", "antiforward", "stopwords", '
                           '"welcome")] +\n'
                           '            [[template_button(settings, "editor_open", "tm:page:1")]])\n'
                           '\n'
                           '    def settings_text(self, s):\n'
                           '        return prepared(s, "settings", {**s, "word_count": len(s["words"])})\n'
                           '\n'
                           '    async def callback(self, q: CallbackQuery):\n'
                           '        if not isinstance(q.message, Message) or q.message.chat.type not in '
                           'GROUPS:\n'
                           '            return await self.alert(q, "callback_group_only", show_alert=True)\n'
                           '        async with self.lock(q.message.chat.id):\n'
                           '            try:\n'
                           '                await self.require_admin(q.message.chat.id, q.from_user.id)\n'
                           '                if (q.data or "").startswith("tm:"):\n'
                           '                    return await TextEditor(self).callback(q)\n'
                           '                key = (q.data or "").removeprefix("toggle:")\n'
                           '                if key not in BOOL_KEYS:\n'
                           '                    raise UserError("error_setting_unknown")\n'
                           '                s = await self.db.settings(q.message.chat.id)\n'
                           '                s[key] = not s[key]\n'
                           '                await self.db.save_settings(q.message.chat.id, s)\n'
                           '                await self.db.audit(q.message.chat.id, q.from_user.id, None, '
                           '"setting", f"{key}={s[key]}")\n'
                           '                await self.alert(q, "callback_saved")\n'
                           '                await deliver(q.message.edit_text, self.settings_text(s), '
                           'reply_markup=self.keyboard(s))\n'
                           '            except UserError as e:\n'
                           '                await self.alert(q, e.key, show_alert=True, **e.values)\n'
                           '            except ValueError as e:\n'
                           '                await self.alert(q, "validation_error", show_alert=True, '
                           'detail=str(e))\n'
                           '            except TelegramAPIError:\n'
                           '                log.warning("Callback Telegram API failure")\n'
                           '                with suppress(TelegramAPIError):\n'
                           '                    await self.alert(q, "callback_retry", show_alert=True)\n'
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
                           '                log.warning("Telegram operation failed: %s", type(e).__name__)\n'
                           '                if await self.cooldowns.ready((m.chat.id, "api_error"), 60):\n'
                           '                    with suppress(TelegramAPIError):\n'
                           '                        await self.say(m, "api_error")\n'
                           '\n'
                           '    async def process(self, m: Message):\n'
                           '        command = parse_command(m.text or "", self.username)\n'
                           '        edited = m.edit_date is not None\n'
                           '        if m.chat.type not in GROUPS:\n'
                           '            if command and not edited:\n'
                           '                await self.say(m, command[0] if command[0] in {"start", "help"} '
                           'else "group_only")\n'
                           '            return\n'
                           '        # Anonymous admins and channel identities cannot be reliably authorized '
                           'as people.\n'
                           '        if m.sender_chat or not m.from_user or m.from_user.is_bot:\n'
                           '            return\n'
                           '        await Usernames(self.db, self.bot).observe(m)\n'
                           '        if m.new_chat_members:\n'
                           '            s = await self.db.settings(m.chat.id)\n'
                           '            if s["welcome"]:\n'
                           '                for user in m.new_chat_members:\n'
                           '                    if not user.is_bot:\n'
                           '                        await self.say(m, "welcome", name=user.full_name)\n'
                           '            return\n'
                           '        if m.content_type in {"left_chat_member", "pinned_message", '
                           '"new_chat_title", "new_chat_photo",\n'
                           '                              "delete_chat_photo", "group_chat_created", '
                           '"supergroup_chat_created"}:\n'
                           '            return\n'
                           '        if not edited and await TextEditor(self).consume(m):\n'
                           '            return\n'
                           '        admin = await self.is_admin(m.chat.id, m.from_user.id)\n'
                           '        if not admin and await self.filter_message(m, edited):\n'
                           '            return\n'
                           '        # Edited messages are filtered, but never execute moderation commands '
                           'again.\n'
                           '        if command and not edited:\n'
                           '            if not admin and not await self.cooldowns.ready((m.chat.id, '
                           'm.from_user.id, "cmd"), 3):\n'
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
                           '        elif s["antilinks"] and contains_link(text, (m.entities or []) + '
                           '(m.caption_entities or [])):\n'
                           '            reason = "Запрещённая ссылка"\n'
                           '        elif s["antiforward"] and m.forward_origin:\n'
                           '            reason = "Пересланное сообщение"\n'
                           '        elif s["stopwords"] and forbidden_word(text, s["words"]):\n'
                           '            reason = "Стоп-слово/фраза"\n'
                           '        if not reason:\n'
                           '            return False\n'
                           '        await self.require_bot(m.chat.id, "can_delete_messages")\n'
                           '        await self.bot.delete_message(m.chat.id, m.message_id)\n'
                           '        await self.db.audit(m.chat.id, self.bot.id, m.from_user.id, "delete", '
                           'reason)\n'
                           '        if not await self.cooldowns.ready((m.chat.id, m.from_user.id, '
                           '"violation"), 10):\n'
                           '            return True\n'
                           '        if flood:\n'
                           '            await self.require_bot(m.chat.id, "can_restrict_members")\n'
                           '            await self.mute(m.chat.id, m.from_user.id, s["mute_minutes"] * 60)\n'
                           '            await self.db.audit(m.chat.id, self.bot.id, m.from_user.id, '
                           '"automute", reason)\n'
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
                           '            uid = m.reply_to_message.from_user.id if m.reply_to_message and '
                           'm.reply_to_message.from_user else actor\n'
                           '            return await self.say(m, "id", chat=chat, uid=uid)\n'
                           '        if cmd == "rules":\n'
                           '            return await self.say(m, "rules")\n'
                           '        if cmd == "filters":\n'
                           '            s = await self.db.settings(chat)\n'
                           '            items = join_lines(prepared(s, "filter_row", {"name": k,\n'
                           '                "state": prepared(s, "state_on" if s[k] else "state_off")}) for '
                           'k in sorted(BOOL_KEYS))\n'
                           '            return await self.say(m, "filters", items=items)\n'
                           '        if cmd == "report":\n'
                           '            if not m.reply_to_message:\n'
                           '                raise UserError("error_report_reply")\n'
                           '            if not await self.cooldowns.ready((chat, actor, "report"), 60):\n'
                           '                raise UserError("error_report_cooldown")\n'
                           '            uid = m.reply_to_message.from_user.id if '
                           'm.reply_to_message.from_user else None\n'
                           '            await self.db.audit(chat, actor, uid, "report", args or "Жалоба")\n'
                           '            return await self.say(m, "report", method=m.reply_to_message.reply, '
                           'actor=actor, reason=args[:300])\n'
                           '        if cmd == "warnings" and not args and not m.reply_to_message:\n'
                           '            return await self.say(m, "warnings_self", count=await '
                           'self.db.count(chat, actor))\n'
                           '\n'
                           '        right = "can_delete_messages" if cmd == "del" else (\n'
                           '            "can_restrict_members" if cmd in {"ban", "unban", "kick", "mute", '
                           '"unmute", "warn", "unwarn", "resetwarns"} else None)\n'
                           '        await self.require_admin(chat, actor, right)\n'
                           '        if cmd == "cancel":\n'
                           '            return await TextEditor(self).cancel(m)\n'
                           '        if cmd in {"edit", "texts", "settext", "resettext", "previewtext", '
                           '"emoji"}:\n'
                           '            return await self.text_command(m, cmd, args)\n'
                           '        if cmd == "check":\n'
                           '            member = await self.bot.get_chat_member(chat, self.bot.id)\n'
                           '            return await self.say(m, "check", delete="✅" if '
                           'member.can_delete_messages else "❌",\n'
                           '                                  restrict="✅" if member.can_restrict_members '
                           'else "❌")\n'
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
                           '            return await self.text_command(m, "settext", key + (" " + args if '
                           'args else ""))\n'
                           '        if cmd == "word":\n'
                           '            parts = args.split(maxsplit=1)\n'
                           '            s = await self.db.settings(chat)\n'
                           '            if parts == ["list"]:\n'
                           '                return await self.say(m, "words", items="\\n".join(s["words"]) '
                           'or prepared(s, "words_empty")["text"])\n'
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
                           '                values = ({"date": f"{datetime.fromtimestamp(r[\'at\'], '
                           'timezone.utc):%d.%m %H:%M}",\n'
                           '                    "action": r["action"], "actor": r["actor"], "uid": '
                           'r["target"], "reason": r["reason"][:100]}\n'
                           '                    if cmd == "logs" else {"action": r["action"], "count": '
                           'r["n"]})\n'
                           '                rich.append(prepared(s, "log_row" if cmd == "logs" else '
                           '"stat_row", values))\n'
                           '            return await self.say(m, cmd if rich else cmd+"_empty", '
                           'items=join_lines(rich))\n'
                           '        if cmd == "del":\n'
                           '            if not m.reply_to_message:\n'
                           '                raise UserError("error_delete_reply")\n'
                           '            await self.require_bot(chat, "can_delete_messages")\n'
                           '            await self.bot.delete_message(chat, m.reply_to_message.message_id)\n'
                           '            await self.db.audit(chat, actor, None, "delete", "Вручную")\n'
                           '            return await self.say(m, "delete")\n'
                           '        uid, rest = await self.target(m, args, protect=cmd != "warnings", '
                           'explicit_id=cmd in {"mute", "unmute", "unban", "unwarn", "resetwarns", '
                           '"warnings"})\n'
                           '        if cmd == "warnings":\n'
                           '            return await self.say(m, "warnings", uid=uid, count=await '
                           'self.db.count(chat, uid))\n'
                           '        if cmd in {"unwarn", "resetwarns"}:\n'
                           '            n = await self.db.change_warns(chat, uid, -1, reset=cmd == '
                           '"resetwarns")\n'
                           '            await self.db.audit(chat, actor, uid, cmd)\n'
                           '            return await self.say(m, cmd, uid=uid, count=n)\n'
                           '        if cmd == "warn":\n'
                           '            return await self.warn(m, uid, rest or "Нарушение правил", actor)\n'
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
                           '            await self.bot.unban_chat_member(chat, uid, only_if_banned=True)\n'
                           '        elif cmd == "kick":\n'
                           '            await self.bot.ban_chat_member(chat, uid)\n'
                           '            # Audit the first API action even if the second fails.\n'
                           '            await self.db.audit(chat, actor, uid, "kick_ban", rest)\n'
                           '            await self.bot.unban_chat_member(chat, uid, only_if_banned=True)\n'
                           '        else:\n'
                           '            raise UserError("error_unknown_command")\n'
                           '        await self.db.audit(chat, actor, uid, cmd, rest)\n'
                           '        reason = (pieces[1] if len(pieces) > 1 else "") if cmd == "mute" else '
                           'rest\n'
                           '        await self.say(m, cmd, uid=uid, minutes=seconds // 60 if cmd == "mute" '
                           'else 0, reason=reason[:300])\n'
                           '\n',
 'src/guardian_cf/editor.py': '"""Persistent, per-admin template editor. No state is kept in Worker '
                              'memory."""\n'
                              'import json\n'
                              'import secrets\n'
                              'import time\n'
                              '\n'
                              'from .policy import parse_command\n'
                              'from .telegram import InlineKeyboardButton, InlineKeyboardMarkup, '
                              'TelegramAPIError\n'
                              'from .texts import (FIELDS, PREVIEW, prepared, template, render, extract, '
                              'validate,\n'
                              '                    deliver, split_rich, join_rich, plain, template_button)\n'
                              '\n'
                              'PAGE_SIZE = 12\n'
                              'TTL = 15 * 60\n'
                              'LABELS = {\n'
                              "    'help': '📖 Помощь', 'start': '👋 Старт', 'welcome': '🎉 Приветствие',\n"
                              "    'rules': '📜 Правила', 'mute': '🔇 Мут', 'unmute': '🔊 Снятие мута',\n"
                              "    'ban': '⛔ Бан', 'unban': '✅ Разбан', 'kick': '🚪 Исключение',\n"
                              "    'warn': '⚠️ Предупреждение', 'automute': '🔇 Автомут', 'ping': '🟢 "
                              "Статус',\n"
                              "    'settings': '⚙️ Настройки', 'check': '🛡 Права бота', 'logs': '📋 Журнал',\n"
                              "    'stats': '📊 Статистика', 'report': '🚩 Жалоба', 'id': '🪪 ID',\n"
                              '}\n'
                              '\n'
                              '\n'
                              'def keys():\n'
                              '    # Existing names remain the callback identifiers even if the order '
                              'changes.\n'
                              '    return list(LABELS) + [k for k in FIELDS if k not in LABELS]\n'
                              '\n'
                              '\n'
                              'def state_key(chat, user, thread):\n'
                              "    return f'text_editor:{chat}:{user}:{thread or 0}'\n"
                              '\n'
                              '\n'
                              'class TextEditor:\n'
                              '    def __init__(self, guardian):\n'
                              '        self.app, self.db = guardian, guardian.db\n'
                              '\n'
                              '    async def load(self, chat, user, thread):\n'
                              '        key = state_key(chat, user, thread)\n'
                              "        row = await self.db.first('SELECT value FROM ephemeral WHERE key=? "
                              "AND expires>?', key, int(time.time()))\n"
                              "        return json.loads(row['value']) if row else None\n"
                              '\n'
                              '    async def store(self, chat, user, thread, state):\n'
                              "        await self.db.run('INSERT OR REPLACE INTO ephemeral VALUES(?,?,?)',\n"
                              '                          state_key(chat, user, thread), json.dumps(state, '
                              'ensure_ascii=False), int(time.time())+TTL)\n'
                              '\n'
                              '    async def clear(self, chat, user, thread):\n'
                              "        await self.db.run('DELETE FROM ephemeral WHERE key=?', "
                              'state_key(chat, user, thread))\n'
                              '\n'
                              '    def button(self, settings, key, data, **values):\n'
                              '        return template_button(settings, key, data, values)\n'
                              '\n'
                              '    async def show(self, m, rich, keyboard, edit=False):\n'
                              '        # Menu text is short by default, but custom text must not break '
                              'navigation.\n'
                              '        parts = list(split_rich(rich))\n'
                              '        part = parts[0]\n'
                              '        try:\n'
                              '            return await deliver(m.edit_text if edit else m.answer, part, '
                              'reply_markup=keyboard)\n'
                              '        except TelegramAPIError as exc:\n'
                              '            if not edit or exc.code != 400:\n'
                              '                raise\n'
                              '            # A repeated click can produce "message is not modified"; a new '
                              'menu\n'
                              '            # also recovers deleted/inaccessible old menu messages. No state '
                              'mutation.\n'
                              '            return await deliver(m.answer, part, reply_markup=keyboard)\n'
                              '\n'
                              '    async def page(self, m, page=1, edit=False):\n'
                              '        s = await self.db.settings(m.chat.id)\n'
                              '        names = keys()\n'
                              '        pages = (len(names)+PAGE_SIZE-1)//PAGE_SIZE\n'
                              '        if not 1 <= page <= pages:\n'
                              "            raise ValueError(f'Укажи страницу от 1 до {pages}.')\n"
                              '        chosen = names[(page-1)*PAGE_SIZE:page*PAGE_SIZE]\n'
                              '        buttons = [InlineKeyboardButton(text=LABELS.get(k, k), '
                              "callback_data='tm:view:'+k) for k in chosen]\n"
                              '        rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]\n'
                              '        nav = []\n'
                              '        if page > 1:\n'
                              "            nav.append(self.button(s, 'editor_prev', f'tm:page:{page-1}'))\n"
                              "        nav.append(self.button(s, 'editor_page', f'tm:page:{page}', "
                              'page=page, pages=pages))\n'
                              '        if page < pages:\n'
                              "            nav.append(self.button(s, 'editor_next', f'tm:page:{page+1}'))\n"
                              '        rows.append(nav)\n'
                              "        items = '\\n'.join(k+': '+(', '.join('{'+f+'}' for f in "
                              'sorted(FIELDS[k])) or\n'
                              "                          prepared(s, 'texts_no_fields')['text']) for k in "
                              'chosen)\n'
                              "        rich = prepared(s, 'texts', {'page':page, 'pages':pages, "
                              "'items':items})\n"
                              '        return await self.show(m, rich, '
                              'InlineKeyboardMarkup(inline_keyboard=rows), edit)\n'
                              '\n'
                              '    async def detail(self, m, key, edit=False):\n'
                              '        s = await self.db.settings(m.chat.id)\n'
                              "        fields = ', '.join('{'+f+'}' for f in sorted(FIELDS[key])) or "
                              "prepared(s, 'texts_no_fields')['text']\n"
                              "        rich = prepared(s, 'texts_detail', {'key':key, 'fields':fields})\n"
                              "        rows = [[self.button(s, 'editor_edit', 'tm:edit:'+key),\n"
                              "                 self.button(s, 'editor_preview', 'tm:preview:'+key)],\n"
                              "                [self.button(s, 'editor_source', 'tm:source:'+key),\n"
                              "                 self.button(s, 'editor_reset', 'tm:reset:'+key)],\n"
                              "                [self.button(s, 'editor_back', "
                              "f'tm:page:{keys().index(key)//PAGE_SIZE+1}')]]\n"
                              '        return await self.show(m, rich, '
                              'InlineKeyboardMarkup(inline_keyboard=rows), edit)\n'
                              '\n'
                              '    async def preview(self, m, key, rich=None):\n'
                              '        s = await self.db.settings(m.chat.id)\n'
                              "        value = render(rich or template(s, key), {f:PREVIEW.get(f, 'Пример') "
                              'for f in FIELDS[key]})\n'
                              '        for part in split_rich(value):\n'
                              '            await deliver(m.answer, part)\n'
                              '\n'
                              '    async def callback(self, q):\n'
                              '        # Caller verifies current admin rights before every click.\n'
                              '        m, user = q.message, q.from_user.id\n'
                              "        parts = (q.data or '').split(':', 2)\n"
                              '        if len(parts) != 3:\n'
                              "            raise ValueError('Открой /texts заново.')\n"
                              '        _, action, key = parts\n'
                              '        s = await self.db.settings(m.chat.id)\n'
                              "        if action == 'page':\n"
                              '            if not key.isdigit() or len(key)>3:\n'
                              "                raise ValueError('Открой /texts заново.')\n"
                              "            await q.answer('')\n"
                              '            return await self.page(m, int(key), edit=True)\n'
                              "        if action in {'save', 'cancel'}:\n"
                              '            state = await self.load(m.chat.id, user, m.message_thread_id)\n'
                              "            if not state or state['nonce'] != key:\n"
                              "                return await self.app.alert(q, 'editor_expired', "
                              'show_alert=True)\n'
                              "            if action == 'cancel':\n"
                              '                await self.clear(m.chat.id, user, m.message_thread_id)\n'
                              "                await self.app.alert(q, 'editor_cancelled')\n"
                              "                return await self.detail(m, state['key'], edit=True)\n"
                              "            if state.get('draft') is None:\n"
                              "                return await self.app.alert(q, 'editor_waiting', "
                              'show_alert=True)\n'
                              "            validate(state['key'], state['draft'])\n"
                              "            s['texts'] = dict(s.get('texts', {}))\n"
                              "            s['texts'][state['key']] = state['draft']\n"
                              '            await self.db.save_settings(m.chat.id, s)\n'
                              '            await self.clear(m.chat.id, user, m.message_thread_id)\n'
                              "            await self.db.audit(m.chat.id, user, None, 'settext', "
                              "state['key'])\n"
                              "            await self.app.alert(q, 'callback_saved')\n"
                              "            return await self.detail(m, state['key'], edit=True)\n"
                              '        if key not in FIELDS or action not in '
                              "{'view','preview','source','edit','reset','confirmreset'}:\n"
                              "            raise ValueError('Открой /texts заново.')\n"
                              "        await q.answer('')\n"
                              "        if action == 'view':\n"
                              '            return await self.detail(m, key, edit=True)\n'
                              "        if action == 'preview':\n"
                              '            return await self.preview(m, key)\n'
                              "        if action == 'source':\n"
                              '            for part in split_rich(template(s, key)):\n'
                              '                await deliver(m.answer, part)\n'
                              '            return\n'
                              "        if action == 'edit':\n"
                              '            nonce = secrets.token_hex(6)\n'
                              '            # ForceReply and an explicit prompt ID prevent unrelated group '
                              'messages\n'
                              '            # from becoming configuration, including messages from other '
                              'admins.\n'
                              "            name = q.from_user.full_name or 'Администратор'\n"
                              "            mention = {'text':name+', ', 'entities':[{'type':'text_mention', "
                              "'offset':0,\n"
                              "                'length':len(name.encode('utf-16-le'))//2, "
                              "'user':{'id':user,'is_bot':False,'first_name':name}}]}\n"
                              "            prompt = join_rich(mention, prepared(s, 'editor_prompt', "
                              "{'key':key}))\n"
                              '            result = await deliver(m.answer, list(split_rich(prompt))[0],\n'
                              '                '
                              "reply_markup={'force_reply':True,'selective':True,'input_field_placeholder':'Новый "
                              "текст с эмодзи'})\n"
                              "            if not isinstance(result, dict) or not result.get('message_id'):\n"
                              "                raise ValueError('Не удалось открыть редактор. Нажми "
                              "«Редактировать» ещё раз.')\n"
                              '            await self.store(m.chat.id, user, m.message_thread_id,\n'
                              "                {'key':key,'nonce':nonce,'prompt_id':result['message_id']})\n"
                              '            kb = InlineKeyboardMarkup(inline_keyboard=[[self.button(s, '
                              "'editor_cancel', 'tm:cancel:'+nonce)]])\n"
                              "            return await self.show(m, prepared(s, 'editor_waiting'), kb)\n"
                              "        if action == 'reset':\n"
                              '            kb = InlineKeyboardMarkup(inline_keyboard=[[\n'
                              "                self.button(s, 'editor_confirm_reset', "
                              "'tm:confirmreset:'+key),\n"
                              "                self.button(s, 'editor_back', 'tm:view:'+key)]])\n"
                              "            return await self.show(m, prepared(s, 'editor_reset_question', "
                              "{'key':key}), kb, edit=True)\n"
                              "        s['texts'] = dict(s.get('texts', {}))\n"
                              "        s['texts'].pop(key, None)\n"
                              "        if key in {'rules','welcome'}:\n"
                              '            from .policy import DEFAULTS\n'
                              "            field = 'rules' if key == 'rules' else 'welcome_text'\n"
                              '            s[field] = DEFAULTS[field]\n'
                              '        await self.db.save_settings(m.chat.id, s)\n'
                              "        await self.db.audit(m.chat.id, user, None, 'resettext', key)\n"
                              '        return await self.detail(m, key, edit=True)\n'
                              '\n'
                              '    async def consume(self, m):\n'
                              '        reply = m.reply_to_message\n'
                              '        if not reply or not reply.from_user or reply.from_user.id != '
                              'self.app.bot.id:\n'
                              '            return False\n'
                              '        state = await self.load(m.chat.id, m.from_user.id, '
                              'm.message_thread_id)\n'
                              "        if not state or state['prompt_id'] != reply.message_id or "
                              "state.get('draft') is not None:\n"
                              '            return False\n'
                              '        await self.app.require_admin(m.chat.id, m.from_user.id)\n'
                              "        if parse_command(m.text or '', self.app.username) == ('cancel', ''):\n"
                              '            await self.cancel(m)\n'
                              '            return True\n'
                              '        rich = extract(m)\n'
                              "        validate(state['key'], rich)\n"
                              '        # Preview first; invalid or Telegram-rejected content is never '
                              'persisted as a template.\n'
                              "        await self.preview(m, state['key'], rich)\n"
                              "        state['draft'] = rich\n"
                              '        await self.store(m.chat.id, m.from_user.id, m.message_thread_id, '
                              'state)\n'
                              '        s = await self.db.settings(m.chat.id)\n'
                              '        kb = InlineKeyboardMarkup(inline_keyboard=[[\n'
                              "            self.button(s, 'editor_save', 'tm:save:'+state['nonce']),\n"
                              "            self.button(s, 'editor_cancel', 'tm:cancel:'+state['nonce'])]])\n"
                              "        await self.show(m, prepared(s, 'editor_draft', {'key':state['key']}), "
                              'kb)\n'
                              '        return True\n'
                              '\n'
                              '    async def cancel(self, m):\n'
                              '        await self.clear(m.chat.id, m.from_user.id, m.message_thread_id)\n'
                              "        return await self.app.say(m, 'editor_cancelled')\n",
 'src/guardian_cf/policy.py': 'import re\n'
                              'import time\n'
                              'import unicodedata\n'
                              'from collections import OrderedDict, deque\n'
                              '\n'
                              'ALIASES = {\n'
                              '    "бан": "ban", "разбан": "unban", "мут": "mute", "размут": "unmute",\n'
                              '    "варн": "warn", "пред": "warn", "снятьпред": "unwarn", "преды": '
                              '"warnings",\n'
                              '    "кик": "kick", "удалить": "del", "правила": "rules", "настройки": '
                              '"settings",\n'
                              '    "помощь": "help", "пинг": "ping", "ид": "id",\n'
                              '    "изменить": "edit", "тексты": "texts", "текст": "settext", "эмодзи": '
                              '"emoji", "отмена": "cancel",\n'
                              '}\n'
                              'COMMANDS = set(ALIASES.values()) | {\n'
                              '    "cancel", "start", "help", "check", "setrules", "setwelcome", "set", '
                              '"word",\n'
                              '    "logs", "stats", "resetwarns", "report", "filters",\n'
                              '    "edit", "texts", "settext", "resettext", "previewtext", "emoji",\n'
                              '}\n'
                              'BOOL_KEYS = {"antiflood", "antilinks", "antiforward", "welcome", '
                              '"stopwords"}\n'
                              'DEFAULTS = {\n'
                              '    "antiflood": True, "antilinks": False, "antiforward": False,\n'
                              '    "stopwords": True, "welcome": False, "flood_limit": 7, "flood_window": '
                              '10,\n'
                              '    "warn_limit": 3, "mute_minutes": 60, "rules": "Правила пока не заданы.",\n'
                              '    "welcome_text": "Добро пожаловать, {name}! Правила: /rules", "words": '
                              '[],\n'
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
                              '    match = re.fullmatch(r"(\\d{1,6})([mhdмчд])", value.casefold())\n'
                              '    if not match:\n'
                              '        raise ValueError("Время: 10m, 2h, 7d (или 10м, 2ч, 7д).")\n'
                              '    seconds = int(match[1]) * {"m": 60, "м": 60, "h": 3600, "ч": 3600,\n'
                              '                               "d": 86400, "д": 86400}[match[2]]\n'
                              '    if not 60 <= seconds <= 365 * 86400:\n'
                              '        raise ValueError("Срок должен быть от 1 минуты до 365 дней.")\n'
                              '    return seconds\n'
                              '\n'
                              '\n'
                              'def normalize(text: str) -> str:\n'
                              '    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold()\n'
                              '                   if unicodedata.category(c) != "Cf")\n'
                              '\n'
                              '\n'
                              'def forbidden_word(text: str, words: list[str]) -> bool:\n'
                              '    text = normalize(text)\n'
                              '    return any(re.search(r"(?<!\\w)" + re.escape(normalize(w)) + r"(?!\\w)", '
                              'text)\n'
                              '               for w in words)\n'
                              '\n'
                              '\n'
                              'def contains_link(text: str, entities=()) -> bool:\n'
                              '    # Telegram entities also cover concealed hyperlinks in captions.\n'
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
 'src/guardian_cf/texts.py': '"""Chat-scoped message templates and Telegram UTF-16 entity handling."""\n'
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
                             '    "kick": "✅ ID {uid}. Участник удалён и может вернуться.\\n{reason}",\n'
                             '    "unmute": "✅ ID {uid}. Персональные ограничения сняты; действуют общие '
                             'права группы.\\n{reason}",\n'
                             '    "warn": "⚠️ ID {uid}: предупреждение {count}/{limit}.\\n{reason}",\n'
                             '    "automute": "🔇 ID {uid}: мут на {minutes} мин. Причина: {reason}.",\n'
                             '    "ping": "🟢 Работаю. Python · Cloudflare Workers · D1",\n'
                             '}\n'
                             'TOKEN = re.compile(r"\\{([A-Za-z_][A-Za-z_0-9]*)\\}")\n'
                             '\n'
                             "DEFAULT_TEXTS.update({'help': '🛡 Guardian 2.5.2 — модерация группы\\n'\n"
                             "         '\\n'\n"
                             "         'Команды можно писать с / или !. Русские варианты: !бан, !разбан, "
                             "!мут, !размут, !варн, '\n"
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
                             "         'Без ответа укажи числовой ID: /mute 123456789 30m причина.\\n'\n"
                             "         '@username работает для знакомых боту участников; если он неизвестен, "
                             "ответь на сообщение человека.\\n'\n"
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
                             "         '/logs — последние действия • /stats — статистика за 90 дней\\n'\n"
                             "         '/check — проверить права бота • /id — ID • /ping — статус\\n'\n"
                             "         '/edit новый текст — ответом на текстовое сообщение этого бота\\n'\n"
                             "         '/texts — редактор текстов с кнопками; /cancel — отмена\\n'\n"
                             "         '/settext mute текст — изменить будущие ответы в этой группе\\n'\n"
                             "         '/settext mute — ответом на образец с оформлением и "
                             "премиум-эмодзи\\n'\n"
                             "         '/previewtext mute — проверить текст • /resettext mute — "
                             "сбросить\\n'\n"
                             "         '/emoji — ответом на сообщение: ID пользовательских эмодзи\\n'\n"
                             "         '\\n'\n"
                             "         'По умолчанию: антифлуд 8-е сообщение за 10 секунд → мут на 60 минут; "
                             "3 варна → мут. '\n"
                             "         'Ссылки и пересылки разрешены. Фильтры не применяются к "
                             "администраторам и @ivan22350.\\n'\n"
                             "         'Работаю в супергруппах. /help — эта справка.',\n"
                             " 'start': '🛡 Guardian 2.5.2 — модерация группы\\n'\n"
                             "          '\\n'\n"
                             "          'Команды можно писать с / или !. Русские варианты: !бан, !разбан, "
                             "!мут, !размут, !варн, '\n"
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
                             "          'Без ответа укажи числовой ID: /mute 123456789 30m причина.\\n'\n"
                             "          '@username работает для знакомых боту участников; если он "
                             "неизвестен, ответь на сообщение человека.\\n'\n"
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
                             "          '/logs — последние действия • /stats — статистика за 90 дней\\n'\n"
                             "          '/check — проверить права бота • /id — ID • /ping — статус\\n'\n"
                             "          '/edit новый текст — ответом на текстовое сообщение этого бота\\n'\n"
                             "          '/texts — редактор текстов с кнопками; /cancel — отмена\\n'\n"
                             "          '/settext mute текст — изменить будущие ответы в этой группе\\n'\n"
                             "          '/settext mute — ответом на образец с оформлением и "
                             "премиум-эмодзи\\n'\n"
                             "          '/previewtext mute — проверить текст • /resettext mute — "
                             "сбросить\\n'\n"
                             "          '/emoji — ответом на сообщение: ID пользовательских эмодзи\\n'\n"
                             "          '\\n'\n"
                             "          'По умолчанию: антифлуд 8-е сообщение за 10 секунд → мут на 60 "
                             "минут; 3 варна → мут. '\n"
                             "          'Ссылки и пересылки разрешены. Фильтры не применяются к "
                             "администраторам и @ivan22350.\\n'\n"
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
                             " 'check': 'Права бота:\\nУдаление сообщений: {delete}\\nБлокировка участников: "
                             "{restrict}',\n"
                             " 'settings': '⚙️ Настройки этой группы\\n'\n"
                             "             'Антифлуд: более {flood_limit} сообщений за {flood_window} "
                             "сек.\\n'\n"
                             "             'Лимит варнов: {warn_limit}; мут: {mute_minutes} мин.\\n'\n"
                             "             'Стоп-фраз: {word_count}\\n'\n"
                             "             'Кнопки доступны администраторам и @ivan22350. Числа: /set "
                             "параметр значение',\n"
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
                             " 'edit_saved': 'Сообщение изменено. Для будущих ответов используй /settext.',\n"
                             " 'emoji': 'ID эмодзи:\\n{items}',\n"
                             " 'emoji_empty': 'Ответь /emoji на сообщение с пользовательскими эмодзи "
                             "Telegram.',\n"
                             " 'api_error': 'Telegram не выполнил действие. Проверь /check, ID участника и "
                             "возраст сообщения. '\n"
                             "              'Изменения могут быть выполнены частично; проверь /logs.',\n"
                             " 'validation_error': '{detail}',\n"
                             " 'group_only': 'Добавь бота администратором в супергруппу. Справка: /help',\n"
                             " 'callback_group_only': 'Открой /settings в супергруппе.',\n"
                             " 'callback_saved': 'Сохранено',\n"
                             " 'callback_retry': 'Открой /settings заново.',\n"
                             " 'warn_automute_failed': '\\n'\n"
                             "                         'Автомут не выполнен; варны сохранены. Проверь /check "
                             "и текущие '\n"
                             "                         'ограничения.',\n"
                             " 'warn_automute_success': '\\nМут на {minutes} мин. Счётчик сброшен.',\n"
                             " 'texts': 'Тексты этой группы — страница {page}/{pages}:\\n'\n"
                             "          '{items}\\n'\n"
                             "          '\\n'\n"
                             "          '/texts НОМЕР — другая страница\\n'\n"
                             "          '/texts help — подстановки шаблона\\n'\n"
                             "          '/settext help текст — сохранить\\n'\n"
                             "          '/previewtext help — пример\\n'\n"
                             "          '/resettext help — сбросить\\n'\n"
                             "          'Выбери шаблон кнопкой ниже. Страницы переключаются стрелками.',\n"
                             " 'texts_detail': '{key}: {fields}\\n/settext {key} текст\\n/previewtext "
                             "{key}\\n/resettext {key}',\n"
                             " 'texts_no_fields': 'без подстановок',\n"
                             " 'text_saved': 'Сохранено. Проверка: /previewtext {key}{hint}',\n"
                             " 'welcome_hint': '. Включи приветствие в /settings.',\n"
                             " 'error_edit_reply': 'Ответь в этой теме на текстовое сообщение этого бота: "
                             "/edit новый текст',\n"
                             " 'error_edit_text': 'После /edit напиши новый текст, можно с оформлением и "
                             "премиум-эмодзи.',\n"
                             " 'error_edit_rejected': 'Telegram не изменил сообщение: текст уже совпадает, "
                             "сообщение недоступно '\n"
                             "                        'или оформление отклонено.',\n"
                             " 'error_template_key': 'Укажи название текста из /texts, например: /settext "
                             "help Моя справка',\n"
                             " 'error_template_text': 'Добавь текст после названия или ответь командой на "
                             "образец.',\n"
                             " 'error_reset_usage': 'Пример: /resettext mute',\n"
                             " 'error_preview_long': 'После подстановки текст слишком длинный. Сократи "
                             "шаблон.',\n"
                             " 'error_admin_only': 'Эта команда доступна только администраторам группы и "
                             "@ivan22350.',\n"
                             " 'error_target_channel': 'Сообщение отправлено от имени канала/группы. Выбери "
                             "пользователя.',\n"
                             " 'error_target_required': 'Ответь на сообщение участника или укажи его "
                             "числовой ID.',\n"
                             " 'error_protected': 'Нельзя применить наказание к себе, боту, администратору "
                             "или @ivan22350.',\n"
                             " 'error_protected_member': 'Участник защищён от модерации.',\n"
                             " 'error_already_restricted': 'Участник уже ограничен. Существующее ограничение "
                             "сохранено.',\n"
                             " 'error_member_missing': 'Участник сейчас не состоит в группе.',\n"
                             " 'error_setting_unknown': 'Неизвестная настройка.',\n"
                             " 'error_report_reply': 'Отправь /report ответом на сообщение, на которое "
                             "жалуешься.',\n"
                             " 'error_report_cooldown': 'Жалобу можно отправлять раз в минуту.',\n"
                             " 'error_positive_integer': 'Нужно целое положительное число.',\n"
                             " 'error_word_usage': '/word add фраза • /word del фраза • /word list',\n"
                             " 'error_word_length': 'Длина стоп-фразы: 1–30 символов.',\n"
                             " 'error_word_limit': 'Лимит: 100 стоп-фраз.',\n"
                             " 'error_delete_reply': 'Ответь командой /del на удаляемое сообщение.',\n"
                             " 'error_mute_duration': 'Укажи срок: /mute 30m причина',\n"
                             " 'error_unknown_command': 'Неизвестная команда.',\n"
                             " 'error_admin_right': 'У тебя нет необходимого права администратора: "
                             "{right}',\n"
                             " 'error_bot_right': 'Выдай боту право администратора: {right}. Проверка: "
                             "/check',\n"
                             " 'error_set_usage': 'Пример: /set warn_limit 3\\nПараметры: {parameters}',\n"
                             " 'error_range': 'Допустимый диапазон: {low}–{high}.',\n"
                             " 'error_texts_page': 'Укажи страницу от 1 до {pages} или имя шаблона: /texts "
                             "help',\n"
                             " 'button_antiflood': '{state} Антифлуд',\n"
                             " 'button_antilinks': '{state} Запрет ссылок',\n"
                             " 'button_antiforward': '{state} Запрет пересылок',\n"
                             " 'button_stopwords': '{state} Стоп-слова',\n"
                             " 'button_welcome': '{state} Приветствие'})\n"
                             "DEFAULT_TEXTS.update({'editor_open':'📝 Тексты бота', 'editor_source':'📄 "
                             "Исходный текст', 'editor_prev': '⬅️ Назад',\n"
                             " 'editor_next': 'Вперёд ➡️',\n"
                             " 'editor_page': '{page}/{pages}',\n"
                             " 'editor_edit': '✏️ Редактировать',\n"
                             " 'editor_preview': '👁 Посмотреть',\n"
                             " 'editor_reset': '↩️ Сбросить',\n"
                             " 'editor_back': '📋 К списку',\n"
                             " 'editor_save': '✅ Сохранить',\n"
                             " 'editor_cancel': '❌ Отмена',\n"
                             " 'editor_confirm_reset': 'Да, сбросить',\n"
                             " 'editor_reset_question': 'Вернуть стандартный текст «{key}»?',\n"
                             " 'editor_prompt': 'Редактируем «{key}». Ответь на это сообщение новым текстом "
                             "или подписью к '\n"
                             "                  'медиа. Можно с жирным шрифтом и премиум-эмодзи. До 4000 "
                             "символов UTF-16. '\n"
                             "                  '/cancel — отмена. Время: 15 минут.',\n"
                             " 'editor_waiting': 'Жду ответ на сообщение редактора. Обычные сообщения группы "
                             "не сохраняются.',\n"
                             " 'editor_draft': 'Выше — пример текста «{key}». Сохранить его? Изменения "
                             "увидит только эта группа.',\n"
                             " 'editor_expired': 'Этот редактор закрыт, устарел или открыт другим "
                             "администратором. Открой /texts '\n"
                             "                   'заново.',\n"
                             " 'editor_cancelled': 'Редактирование отменено. Шаблон не изменён.'})\n"
                             '\n'
                             "for _key in ('help', 'start'):\n"
                             "    DEFAULT_TEXTS[_key] += '\\n\\nУправление ботом: только администраторы "
                             "группы и @ivan22350. Ранги отключены.'\n"
                             '\n'
                             'DEFAULT_TEXTS.update({\n'
                             "    'error_target_self': 'Не применяю наказание: выбран ID {uid} — это "
                             'аккаунт, отправивший команду. Ответь на сообщение нужного участника или укажи '
                             "его ID.',\n"
                             "    'error_target_bot': 'Не применяю наказание: выбран ID {uid} — это я, бот. "
                             "Ответь на сообщение участника или укажи его ID.',\n"
                             "    'error_target_admin': 'Не применяю наказание к ID {uid}: Telegram "
                             "сообщает, что этот участник — администратор или владелец данной группы.',\n"
                             "    'error_target_trusted': 'Не применяю наказание к ID {uid}: Telegram "
                             'сообщает, что у этого участника username @ivan22350. Он защищён настройками '
                             "бота.',\n"
                             '})\n'
                             'DEFAULT_TEXTS.update({\n'
                             "    'error_username_unknown': 'Не удалось подтвердить ID пользователя "
                             '@{username}. Я никого не выбрал. Ответь на сообщение этого человека командой '
                             'без @username, например /unmute, либо укажи его числовой ID. Username '
                             'запоминается из сообщений, но перед действием всегда проверяется через '
                             "Telegram.',\n"
                             '})\n'
                             'FIELDS.update({key: set(TOKEN.findall(text)) for key, text in '
                             'DEFAULT_TEXTS.items() if key not in FIELDS})\n'
                             'FIELDS["help"] = set()\n'
                             'FIELDS["start"] = set()\n'
                             '\n'
                             'STYLES = {"bold", "italic", "underline", "strikethrough", "spoiler", "code", '
                             '"pre",\n'
                             '          "text_link", "text_mention", "custom_emoji", "blockquote", '
                             '"expandable_blockquote"}\n'
                             '\n'
                             '\n'
                             'def units(text):\n'
                             '    return len(text.encode("utf-16-le")) // 2\n'
                             '\n'
                             '\n'
                             'def extract(message, body=None):\n'
                             '    """Copy message/caption or an exact command suffix, retaining supported '
                             'entities."""\n'
                             '    text = message.text if message.text is not None else (message.caption or '
                             '"")\n'
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
                             '        raise ValueError("Текст должен содержать от 1 до 4000 символов '
                             'UTF-16.")\n'
                             '    offset, limit = units(text[:start]), units(text[:end])\n'
                             '    result = []\n'
                             '    for obj in entities or []:\n'
                             '        e = encode(obj)\n'
                             '        if e.get("type") not in STYLES:\n'
                             '            continue\n'
                             '        a, b = e["offset"], e["offset"] + e["length"]\n'
                             '        if e["type"] in {"custom_emoji", "text_link", "text_mention"} and (a < '
                             'offset or b > limit):\n'
                             '            continue\n'
                             '        a, b = max(a, offset), min(b, limit)\n'
                             '        if a < b:\n'
                             '            result.append({**e, "offset": a-offset, "length": b-a})\n'
                             '    if len(result) > 100:\n'
                             '        raise ValueError("Слишком много элементов оформления: максимум 100.")\n'
                             '    return {"text": value, "entities": result}\n'
                             '\n'
                             '\n'
                             'def validate(key, rich):\n'
                             '    # Help can contain literal examples of other templates, such as {uid}.\n'
                             '    if key in {"help", "start"}:\n'
                             '        return\n'
                             '    unknown = set(TOKEN.findall(rich["text"])) - FIELDS[key]\n'
                             '    if unknown:\n'
                             '        raise ValueError("Неизвестные подстановки: " + ", '
                             '".join(sorted(unknown)))\n'
                             '\n'
                             '\n'
                             'def render(rich, values):\n'
                             '    """Substitute only known literal tokens; never parse HTML or format '
                             'expressions."""\n'
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
                             '            inserted.extend({**e, "offset": e["offset"]+output_offset} for e '
                             'in raw.get("entities", []))\n'
                             '        output_offset += units(value)\n'
                             '        a, b = units(text[:match.start()]), units(text[:match.end()])\n'
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
                             '        a, b = boundary(e["offset"]), boundary(e["offset"]+e["length"])\n'
                             '        if a is not None and b is not None and b > a:\n'
                             '            entities.append({**e, "offset": a, "length": b-a})\n'
                             '    return {"text": output, "entities": sorted(entities+inserted, key=lambda '
                             'e: (e["offset"], -e["length"]))[:100]}\n'
                             '\n'
                             '\n'
                             'def template(settings, key):\n'
                             '    if key in settings.get("texts", {}):\n'
                             '        return settings["texts"][key]\n'
                             '    text = settings["rules"] if key == "rules" else (\n'
                             '        settings["welcome_text"] if key == "welcome" else DEFAULT_TEXTS[key])\n'
                             '    return {"text": text, "entities": []}\n'
                             '\n'
                             '\n'
                             'async def deliver(method, rich, **kwargs):\n'
                             '    """Retry rejected presentation only; never repeat a moderation action."""\n'
                             '    try:\n'
                             '        return await method(rich["text"], entities=rich.get("entities", []), '
                             '**kwargs)\n'
                             '    except TelegramAPIError as exc:\n'
                             '        markup = encode(kwargs.get("reply_markup"))\n'
                             '        icons = isinstance(markup, dict) and '
                             'any(b.get("icon_custom_emoji_id")\n'
                             '            for row in markup.get("inline_keyboard", []) for b in row)\n'
                             '        if exc.code != 400 or not (icons or any(e["type"] == "custom_emoji" '
                             'for e in rich.get("entities", []))):\n'
                             '            raise\n'
                             '        if icons:\n'
                             '            kwargs = {**kwargs, "reply_markup": {**markup, "inline_keyboard": '
                             '[\n'
                             '                [{k:v for k,v in b.items() if k != "icon_custom_emoji_id"} for '
                             'b in row]\n'
                             '                for row in markup["inline_keyboard"]]}}\n'
                             '        simple = [e for e in rich.get("entities", []) if e["type"] != '
                             '"custom_emoji"]\n'
                             '        return await method(rich["text"], entities=simple, **kwargs)\n'
                             '\n'
                             '\n'
                             'PREVIEW = {"uid": "123456789", "chat": "-100123456789", "actor": "123456789",\n'
                             '    "minutes": 10, "reason": "Пример причины", "count": 1, "limit": 3, "name": '
                             '"Участник",\n'
                             '    "key": "help", "hint": "", "fields": "без подстановок", "items": "Пример '
                             'списка",\n'
                             '    "page": 1, "pages": 7, "delete": "✅", "restrict": "✅", "flood_limit": 7,\n'
                             '    "flood_window": 10, "warn_limit": 3, "mute_minutes": 60, "word_count": 0,\n'
                             '    "setting": "warn_limit 3", "state": "✅", "date": "24.10 12:00", "action": '
                             '"warn",\n'
                             '    "detail": "Пример ошибки", "right": "can_restrict_members", "parameters": '
                             '"warn_limit",\n'
                             '    "low": 1, "high": 100}\n'
                             '\n'
                             '\n'
                             'def prepared(settings, key, values=None):\n'
                             '    values = values or {}\n'
                             '    rich = render(template(settings, key), values)\n'
                             '    if not rich["text"].strip() or units(rich["text"]) > 4096:\n'
                             '        rich = render(template({**settings, "texts": {}}, key), values)\n'
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
                             '            if e["type"] in {"custom_emoji", "text_link", "text_mention"} and '
                             '(a < start or b > end):\n'
                             '                continue\n'
                             '            a, b = max(a, start), min(b, end)\n'
                             '            if b > a:\n'
                             '                entities.append({**e, "offset": a-start, "length": b-a})\n'
                             '        yield {"text": text[:count], "entities": entities}\n'
                             '        text, start = text[count:], end\n'
                             '\n'
                             '\n'
                             'def join_lines(rows):\n'
                             '    result = {"text": "", "entities": []}\n'
                             '    for row in rows:\n'
                             '        if result["text"]:\n'
                             '            result = join_rich(result, {"text": "\\n", "entities": []})\n'
                             '        result = join_rich(result, row)\n'
                             '    return result\n'
                             '\n'
                             '\n'
                             'def template_button(settings, key, data, values=None):\n'
                             '    from .telegram import InlineKeyboardButton\n'
                             '    rich = prepared(settings, key, values)\n'
                             '    icon = next((e.get("custom_emoji_id") for e in rich.get("entities", [])\n'
                             '                 if e["type"] == "custom_emoji"), None)\n'
                             '    # Keep the ordinary emoji in the label as a fallback on unsupported '
                             'clients.\n'
                             '    return InlineKeyboardButton(text=plain(rich, 64), callback_data=data, '
                             'icon_custom_emoji_id=icon)\n',
 'src/guardian_cf/usernames.py': '"""Observed usernames are hints only; Telegram must verify them before '
                                 'targeting."""\n'
                                 'import re\n'
                                 'import time\n'
                                 '\n'
                                 'from .telegram import TelegramAPIError\n'
                                 '\n'
                                 'TTL = 30 * 86400\n'
                                 "PATTERN = re.compile(r'[A-Za-z0-9_]{1,64}\\Z')\n"
                                 '\n'
                                 '\n'
                                 'def parse_username(token):\n'
                                 "    value = token[1:].rstrip(',.;:!?') if token.startswith('@') else ''\n"
                                 '    if not PATTERN.fullmatch(value):\n'
                                 "        raise ValueError('Укажи @username без пробелов или числовой ID "
                                 "участника.')\n"
                                 '    return value.casefold()\n'
                                 '\n'
                                 '\n'
                                 'def key(chat, username):\n'
                                 "    return f'username:{chat}:{username}'\n"
                                 '\n'
                                 '\n'
                                 'class Usernames:\n'
                                 '    def __init__(self, db, bot):\n'
                                 '        self.db, self.bot = db, bot\n'
                                 '\n'
                                 '    async def remember(self, chat, user):\n'
                                 "        username = (user.username or '').casefold() if user else ''\n"
                                 '        if not user or user.is_bot or not PATTERN.fullmatch(username):\n'
                                 '            return\n'
                                 '        now = int(time.time())\n'
                                 "        await self.db.run('''INSERT INTO ephemeral VALUES(?,?,?) ON "
                                 'CONFLICT(key)\n'
                                 '            DO UPDATE SET value=excluded.value,expires=excluded.expires\n'
                                 '            WHERE ephemeral.value<>excluded.value OR '
                                 "ephemeral.expires<?''',\n"
                                 '            key(chat,username), str(user.id), now+TTL, now+TTL-86400)\n'
                                 '\n'
                                 '    async def observe(self, m):\n'
                                 '        await self.remember(m.chat.id, m.from_user)\n'
                                 '        reply = m.reply_to_message\n'
                                 '        if reply and not reply.sender_chat and reply.chat and '
                                 'reply.chat.id == m.chat.id:\n'
                                 '            await self.remember(m.chat.id, reply.from_user)\n'
                                 '        for user in (m.new_chat_members or []):\n'
                                 '            await self.remember(m.chat.id, user)\n'
                                 '\n'
                                 '    async def resolve(self, chat, username):\n'
                                 "        row = await self.db.first('SELECT value FROM ephemeral WHERE key=? "
                                 "AND expires>?',\n"
                                 '                                  key(chat,username), int(time.time()))\n'
                                 '        if not row:\n'
                                 '            return None\n'
                                 "        uid = int(row['value'])\n"
                                 '        try:\n'
                                 '            member = await self.bot.get_chat_member(chat, uid)\n'
                                 '        except TelegramAPIError as exc:\n'
                                 '            if exc.code != 400:\n'
                                 '                raise\n'
                                 '            return None\n'
                                 '        user = member.user\n'
                                 '        if (not user or user.id != uid or user.is_bot or\n'
                                 "                (user.username or '').casefold() != username):\n"
                                 "            await self.db.run('DELETE FROM ephemeral WHERE key=? AND "
                                 "value=?',key(chat,username),str(uid))\n"
                                 '            return None\n'
                                 '        return uid\n',
 'tests/test_access.py': 'import pytest\n'
                         'from test_guardian import db, bot, update\n'
                         'from test_editor import API as EditorAPI, click\n'
                         'from test_texts import run, sent\n'
                         'from guardian_cf.app import Guardian\n'
                         'from guardian_cf.editor import TextEditor\n'
                         'from guardian_cf.policy import COMMANDS, DEFAULTS, LIMITS, parse_command\n'
                         'from guardian_cf.texts import FIELDS, DEFAULT_TEXTS\n'
                         'from guardian_cf.webhook import process_update\n'
                         '\n'
                         'CHAT=-100123\n'
                         '\n'
                         '\n'
                         'class API(EditorAPI):\n'
                         '    def __init__(self):\n'
                         '        super().__init__()\n'
                         "        self.username='ivan22350'\n"
                         "        self.status='member'\n"
                         '        self.member_user_id=5\n'
                         '        self.member_bot=False\n'
                         '        self.active=True\n'
                         '        self.bot_rights=True\n'
                         '\n'
                         '    async def __call__(self, method, params):\n'
                         '        result=await super().__call__(method,params)\n'
                         "        if method=='getChatMember' and params['user_id']==5:\n"
                         "            return {'status':self.status,'is_member':self.active,\n"
                         "                    'user':{'id':self.member_user_id,'is_bot':self.member_bot,\n"
                         "                            'first_name':'Ivan','username':self.username},\n"
                         "                    'can_delete_messages':False,'can_restrict_members':False}\n"
                         "        if method=='getChatMember' and params['user_id']==999 and not "
                         'self.bot_rights:\n'
                         '            return '
                         "{'status':'administrator','can_restrict_members':False,'can_delete_messages':False}\n"
                         '        return result\n'
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         "@pytest.mark.parametrize('command,method',[\n"
                         "    ('/ban 6 причина','banChatMember'),('/mute 6 10m','restrictChatMember'),\n"
                         "    ('/unmute 6','restrictChatMember'),('/unban 6','unbanChatMember'),\n"
                         "    ('/kick 6','banChatMember'),('/warn 6 причина',None),\n"
                         "    ('/set warn_limit 5',None),('/settext help New help',None),\n"
                         "    ('/word add spam',None),('/texts',None),('/settings',None),\n"
                         '])\n'
                         'async def test_trusted_username_can_manage_as_nonadmin(db,command,method):\n'
                         '    api=API()\n'
                         '    await run(db,api,command,actor=5)\n'
                         "    assert not any('доступна только' in p['text'] for p in sent(api))\n"
                         '    if method:\n'
                         '        assert any(m==method for m,_ in api.calls)\n'
                         "    elif command.startswith('/warn'):\n"
                         '        assert await db.count(CHAT,6)==1\n'
                         "    elif command.startswith('/set '):\n"
                         "        assert (await db.settings(CHAT))['warn_limit']==5\n"
                         "    elif command.startswith('/settext'):\n"
                         "        assert (await db.settings(CHAT))['texts']['help']['text']=='New help'\n"
                         "    elif command.startswith('/word'):\n"
                         "        assert 'spam' in (await db.settings(CHAT))['words']\n"
                         '    else:\n'
                         "        assert sent(api)[-1]['reply_markup']['inline_keyboard']\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         "@pytest.mark.parametrize('command',[\n"
                         "    '/ban 7','/mute 7 10m','/unmute 7','/unban 7','/kick 7','/warn 7',\n"
                         "    '/unwarn 7','/resetwarns 7','/set warn_limit 5','/settext help hacked',\n"
                         "    '/resettext help','/setrules hacked','/setwelcome hacked','/word add hacked',\n"
                         "    '/texts','/settings','/edit hacked','/del',\n"
                         '])\n'
                         'async def test_regular_member_cannot_mutate(db,command):\n'
                         '    api=API()\n'
                         '    await run(db,api,command,actor=6)\n'
                         "    assert 'доступна только администраторам' in sent(api)[-1]['text']\n"
                         '    assert not any(m in '
                         "{'banChatMember','restrictChatMember','unbanChatMember','deleteMessage','editMessageText'}\n"
                         '                   for m,_ in api.calls)\n'
                         "    assert (await db.settings(CHAT))['warn_limit']==3\n"
                         "    assert 'texts' not in await db.settings(CHAT)\n"
                         '    assert not await db.logs(CHAT)\n'
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         "@pytest.mark.parametrize('field,value',[\n"
                         "    ('username','ivan223500'),('username',None),('username','@ivan22350'),\n"
                         "    ('username','changed_name'),('member_user_id',42),('member_bot',True),\n"
                         "    ('status','left'),('status','kicked'),('active',False),\n"
                         '])\n'
                         'async def '
                         'test_only_current_exact_active_human_username_authorizes(db,field,value):\n'
                         '    api=API()\n'
                         "    if field=='active': api.status='restricted'\n"
                         '    setattr(api,field,value)\n'
                         "    data=update('/ban 6',actor=5)\n"
                         '    # Incoming username/display name is not a trusted source for authorization.\n'
                         "    data['message']['from'].update(username='ivan22350',first_name='@ivan22350')\n"
                         "    await process_update(data,db,bot(api),'guardbot')\n"
                         "    assert not any(m=='banChatMember' for m,_ in api.calls)\n"
                         "    assert 'доступна только' in sent(api)[-1]['text']\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_username_case_insensitive_and_bot_rights_still_required(db):\n'
                         "    api=API(); api.username='IVAN22350'\n"
                         "    await run(db,api,'/ban 6',actor=5)\n"
                         "    assert sum(m=='banChatMember' for m,_ in api.calls)==1\n"
                         '    api.bot_rights=False\n'
                         "    await run(db,api,'/mute 6 10m',number=2,actor=5)\n"
                         "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                         "    assert 'Выдай боту право' in sent(api)[-1]['text']\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_editor_callbacks_input_and_save_recheck_username(db):\n'
                         "    api=API(); editor=TextEditor(Guardian(bot(api),db,'guardbot'))\n"
                         "    await click(db,api,'tm:edit:help',user=5)\n"
                         '    state=await editor.load(CHAT,5,None)\n'
                         '    assert state is not None\n'
                         "    reply=update('prompt',actor=999)['message']; "
                         "reply['message_id']=state['prompt_id']\n"
                         "    await run(db,api,'New help',number=2,actor=5,reply=reply)\n"
                         '    state=await editor.load(CHAT,5,None)\n'
                         "    assert state['draft']['text']=='New help'\n"
                         "    api.username='renamed'\n"
                         "    await click(db,api,'tm:save:'+state['nonce'],number=3,user=5)\n"
                         "    assert 'texts' not in await db.settings(CHAT)\n"
                         "    api.username='ivan22350'\n"
                         "    await click(db,api,'tm:save:'+state['nonce'],number=4,user=5)\n"
                         "    assert (await db.settings(CHAT))['texts']['help']['text']=='New help'\n"
                         "    await click(db,api,'tm:edit:rules',number=5,user=5)\n"
                         "    state=await editor.load(CHAT,5,None); reply['message_id']=state['prompt_id']\n"
                         "    api.username='renamed'\n"
                         "    await run(db,api,'Should not save',number=6,actor=5,reply=reply)\n"
                         "    assert 'draft' not in await editor.load(CHAT,5,None)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_toggle_rechecks_rights_and_stale_rank_buttons_do_nothing(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'toggle:antilinks',user=5)\n"
                         "    assert (await db.settings(CHAT))['antilinks'] is True\n"
                         "    api.username='renamed'\n"
                         "    await click(db,api,'toggle:antilinks',number=2,user=5)\n"
                         "    assert (await db.settings(CHAT))['antilinks'] is True\n"
                         "    await click(db,api,'tm:edit:help',number=3,user=6)\n"
                         "    assert await TextEditor(Guardian(bot(api),db,'guardbot')).load(CHAT,6,None) is "
                         'None\n'
                         "    await click(db,api,'rk:toggle:ranks_enabled',number=4,user=1)\n"
                         "    assert 'ranks_enabled' not in await db.settings(CHAT)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_edit_and_delete_delegate_and_protected_admin_targets(db):\n'
                         '    api=API()\n'
                         "    own=update('Bot text',actor=999)['message']\n"
                         "    await run(db,api,'/edit Updated',actor=5,reply=own)\n"
                         "    assert any(m=='editMessageText' and p['text']=='Updated' for m,p in "
                         'api.calls)\n'
                         '    await '
                         "run(db,api,'/del',number=2,actor=5,reply=update('Other',actor=6)['message'])\n"
                         "    assert any(m=='deleteMessage' for m,_ in api.calls)\n"
                         "    await run(db,api,'/ban 1',number=3,actor=5)\n"
                         "    await run(db,api,'/ban 5',number=4,actor=1)\n"
                         "    assert not any(m=='banChatMember' for m,_ in api.calls)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_rank_system_removed_and_old_data_left_untouched(db):\n'
                         '    api=API()\n'
                         '    # Simulate a database that has already run 2.4.\n'
                         "    await db.run('CREATE TABLE rank_users(chat INTEGER,user INTEGER,xp INTEGER)')\n"
                         "    await db.run('INSERT INTO rank_users VALUES(?,?,?)',CHAT,6,100)\n"
                         '    s=await db.settings(CHAT); s.update(ranks_enabled=True,xp_per_message=10)\n'
                         "    s['texts']={'help':{'text':'Custom "
                         "help','entities':[]},'rank_profile':{'text':'Old rank','entities':[]}}\n"
                         '    await db.save_settings(CHAT,s)\n'
                         "    for i,text in enumerate(['/rank','/top','/ranks','/ranksettings','/addxp 6 "
                         "50','Обычное сообщение'],1):\n"
                         '        await run(db,api,text,number=i,actor=6)\n'
                         '    assert not sent(api)\n'
                         "    assert (await db.first('SELECT xp FROM rank_users WHERE user=6'))['xp']==100\n"
                         "    assert (await db.settings(CHAT))['texts']['help']['text']=='Custom help'\n"
                         '    assert all(k not in COMMANDS for k in '
                         "['rank','top','ranks','ranksettings','addxp','setxp','setlevel','rankname'])\n"
                         "    assert not any(k.startswith('rank_') for k in FIELDS)\n"
                         "    assert 'xp_per_message' not in LIMITS and 'ranks_enabled' not in DEFAULTS\n"
                         "    assert not any('rk:' in str(p.get('reply_markup')) for _,p in api.calls)\n",
 'tests/test_editor.py': 'import pytest\n'
                         '\n'
                         'from test_guardian import Telegram, bot, db, update\n'
                         'from test_texts import run, sent, emoji\n'
                         'from guardian_cf.editor import TextEditor, state_key, keys, PAGE_SIZE\n'
                         'from guardian_cf.app import Guardian\n'
                         'from guardian_cf.telegram import TelegramAPIError\n'
                         'from guardian_cf.texts import FIELDS, units, deliver, template_button\n'
                         'from guardian_cf.webhook import process_update\n'
                         '\n'
                         '\n'
                         'class API(Telegram):\n'
                         '    def __init__(self):\n'
                         '        super().__init__()\n'
                         '        self.message_id = 100\n'
                         '\n'
                         '    async def __call__(self, method, params):\n'
                         '        result = await super().__call__(method, params)\n'
                         "        if method == 'getChatMember' and params['user_id'] == 2:\n"
                         '            return '
                         "{'status':'administrator','can_delete_messages':True,'can_restrict_members':True}\n"
                         "        if method == 'sendMessage':\n"
                         '            self.message_id += 1\n'
                         "            return {'message_id':self.message_id}\n"
                         '        return result\n'
                         '\n'
                         '\n'
                         'async def click(db, api, data, number=1, user=1, chat=-100123, thread=None):\n'
                         "    message = update('menu', actor=999)['message']\n"
                         "    message['chat']['id'] = chat\n"
                         '    if thread:\n'
                         "        message['message_thread_id'] = thread\n"
                         "    event = {'update_id':number, 'callback_query':{'id':str(number),'data':data,\n"
                         "             'from':{'id':user,'first_name':'Admin'},'message':message}}\n"
                         "    return await process_update(event, db, bot(api), 'guardbot')\n"
                         '\n'
                         '\n'
                         'def editor(db, api):\n'
                         "    return TextEditor(Guardian(bot(api), db, 'guardbot'))\n"
                         '\n'
                         '\n'
                         "async def draft(db, api, text='🙂 Новая помощь', number=2, user=1, chat=-100123,\n"
                         '                thread=None, caption=False, reply_id=None):\n'
                         '    state = await editor(db, api).load(-100123,1,None)\n'
                         '    data = update(text,actor=user,update_id=number)\n'
                         "    message = data['message']\n"
                         "    message['chat']['id'] = chat\n"
                         '    if thread:\n'
                         "        message['message_thread_id'] = thread\n"
                         "    reply = update('prompt',actor=999)['message']\n"
                         "    reply['message_id'] = reply_id if reply_id is not None else "
                         "state['prompt_id']\n"
                         "    message['reply_to_message'] = reply\n"
                         '    if caption:\n'
                         "        message.pop('text')\n"
                         "        message['caption'],message['caption_entities'] = text,[emoji(0)]\n"
                         '    else:\n'
                         "        message['entities'] = [emoji(0)] if text.startswith('🙂') else []\n"
                         "    return await process_update(data, db, bot(api), 'guardbot')\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_catalog_buttons_navigation_all_keys_and_callback_lengths(db):\n'
                         '    api = API()\n'
                         "    await run(db, api, '/texts')\n"
                         '    first = sent(api)[-1]\n'
                         "    kb = first['reply_markup']['inline_keyboard']\n"
                         "    assert kb[0][0]['callback_data'] == 'tm:view:help'\n"
                         "    assert any(b['callback_data']=='tm:page:2' for row in kb for b in row)\n"
                         '    seen = set()\n'
                         '    pages = (len(FIELDS)+PAGE_SIZE-1)//PAGE_SIZE\n'
                         '    for page in range(1,pages+1):\n'
                         "        assert (await click(db,api,f'tm:page:{page}',page+1))[1] == 'OK'\n"
                         "        p = [p for m,p in api.calls if m=='editMessageText'][-1]\n"
                         "        assert units(p['text']) <= 4096\n"
                         "        for row in p['reply_markup']['inline_keyboard']:\n"
                         '            for b in row:\n'
                         "                assert len(b['callback_data'].encode()) <= 64\n"
                         "                if b['callback_data'].startswith('tm:view:'):\n"
                         "                    seen.add(b['callback_data'].split(':')[2])\n"
                         '    assert seen == set(FIELDS)\n'
                         "    assert not any(b['callback_data']==f'tm:page:{pages+1}' for row in "
                         "p['reply_markup']['inline_keyboard'] for b in row)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_detail_buttons_and_preview_no_mutation(db):\n'
                         '    api=API()\n'
                         "    await run(db,api,'/texts help')\n"
                         "    assert 'tm:edit:help' in str(sent(api)[-1]['reply_markup'])\n"
                         "    await click(db,api,'tm:preview:help',2)\n"
                         "    assert 'Guardian 2.5.2' in sent(api)[-1]['text']\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         "@pytest.mark.parametrize('caption',[False,True])\n"
                         'async def test_edit_draft_confirm_preserves_emoji_and_persistence(db,caption):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         '    prompt=next(p for p in sent(api) if '
                         "p.get('reply_markup',{}).get('force_reply'))\n"
                         "    assert prompt['reply_markup']['selective'] is True\n"
                         "    assert prompt['entities'][0]['type']=='text_mention'\n"
                         '    await draft(db,api,caption=caption)\n'
                         '    state=await editor(db,api).load(-100123,1,None)\n'
                         "    assert state['draft']['entities']==[emoji(0)]\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         "    assert 'tm:save:' in str(sent(api)[-1]['reply_markup'])\n"
                         "    await click(db,api,'tm:save:'+state['nonce'],3)\n"
                         "    await run(db,api,'/help',4)\n"
                         "    assert sent(api)[-1]['text']=='🙂 Новая помощь'\n"
                         "    assert sent(api)[-1]['entities']==[emoji(0)]\n"
                         '    assert await editor(db,api).load(-100123,1,None) is None\n'
                         "    assert (await db.logs(-100123))[0]['action']=='settext'\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         "@pytest.mark.parametrize('variation',['other_user','other_chat','other_thread','wrong_reply','no_reply','edited'])\n"
                         'async def test_unrelated_messages_never_captured(db,variation):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         "    if variation=='no_reply':\n"
                         "        await run(db,api,'Unrelated',2)\n"
                         "    elif variation=='edited':\n"
                         '        state=await editor(db,api).load(-100123,1,None)\n'
                         "        event=update('Draft',update_id=2,edited=True)\n"
                         "        reply=update(actor=999)['message'];reply['message_id']=state['prompt_id']\n"
                         "        event['edited_message']['reply_to_message']=reply\n"
                         "        await process_update(event,db,bot(api),'guardbot')\n"
                         '    else:\n'
                         "        kwargs={'other_user':{'user':2},'other_chat':{'chat':-100456},\n"
                         '                '
                         "'other_thread':{'thread':42},'wrong_reply':{'reply_id':9999}}[variation]\n"
                         '        await draft(db,api,**kwargs)\n'
                         "    assert 'draft' not in await editor(db,api).load(-100123,1,None)\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_live_permission_checks_for_edit_input_and_save(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         '    api.demoted.add(1)\n'
                         '    await draft(db,api)\n'
                         "    assert 'draft' not in await editor(db,api).load(-100123,1,None)\n"
                         '    api.demoted.clear()\n'
                         '    await draft(db,api,number=3)\n'
                         '    state=await editor(db,api).load(-100123,1,None)\n'
                         '    api.demoted.add(1)\n'
                         "    await click(db,api,'tm:save:'+state['nonce'],4)\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_other_admin_cannot_save_or_cancel_session(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         '    await draft(db,api)\n'
                         '    state=await editor(db,api).load(-100123,1,None)\n'
                         "    await click(db,api,'tm:save:'+state['nonce'],3,user=2)\n"
                         "    await click(db,api,'tm:cancel:'+state['nonce'],4,user=2)\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         '    assert await editor(db,api).load(-100123,1,None) is not None\n'
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_invalid_draft_leaves_editor_open(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:mute')\n"
                         "    await draft(db,api,'{wrong}')\n"
                         "    assert 'Неизвестные' in sent(api)[-1]['text']\n"
                         "    assert 'draft' not in await editor(db,api).load(-100123,1,None)\n"
                         "    await draft(db,api,'🙂 {uid}',number=3)\n"
                         "    assert (await editor(db,api).load(-100123,1,None))['draft']['text']=='🙂 "
                         "{uid}'\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_expired_and_superseded_sessions(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         '    old=await editor(db,api).load(-100123,1,None)\n'
                         "    await click(db,api,'tm:edit:start',2)\n"
                         "    await draft(db,api,number=3,reply_id=old['prompt_id'])\n"
                         "    assert 'draft' not in await editor(db,api).load(-100123,1,None)\n"
                         "    await click(db,api,'tm:cancel:'+old['nonce'],4)\n"
                         '    assert await editor(db,api).load(-100123,1,None) is not None\n'
                         "    await db.run('UPDATE ephemeral SET expires=0 WHERE "
                         "key=?',state_key(-100123,1,None))\n"
                         "    await click(db,api,'tm:save:'+old['nonce'],5)\n"
                         "    assert 'texts' not in await db.settings(-100123)\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_reset_requires_second_click_and_cancel_preserves_template(db):\n'
                         '    api=API()\n'
                         "    await run(db,api,'/settext help Original')\n"
                         "    await click(db,api,'tm:reset:help',2)\n"
                         "    assert (await db.settings(-100123))['texts']['help']['text']=='Original'\n"
                         "    await click(db,api,'tm:confirmreset:help',3)\n"
                         "    assert 'help' not in (await db.settings(-100123))['texts']\n"
                         "    await click(db,api,'tm:edit:help',4)\n"
                         '    await draft(db,api,number=5)\n'
                         '    state=await editor(db,api).load(-100123,1,None)\n'
                         "    await click(db,api,'tm:cancel:'+state['nonce'],6)\n"
                         "    await click(db,api,'tm:save:'+state['nonce'],7)\n"
                         "    assert 'help' not in (await db.settings(-100123))['texts']\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_cancel_command_and_slash_prefixed_sample(db):\n'
                         '    api=API()\n'
                         "    await click(db,api,'tm:edit:help')\n"
                         "    await draft(db,api,'/ban 5 sample',number=2)\n"
                         "    assert not any(m=='banChatMember' for m,p in api.calls)\n"
                         "    await run(db,api,'/cancel',3)\n"
                         '    assert await editor(db,api).load(-100123,1,None) is None\n'
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_custom_button_icon_and_text_emoji_fallback():\n'
                         "    s={'texts':{'editor_edit':{'text':'🙂 Изменить','entities':[emoji(0)]}}}\n"
                         "    button=template_button(s,'editor_edit','tm:edit:help')\n"
                         "    assert button.icon_custom_emoji_id=='123456789'\n"
                         '    calls=[]\n'
                         '    async def method(text,**params):\n'
                         '        from guardian_cf.telegram import encode\n'
                         '        params=encode(params);calls.append(params)\n'
                         '        if len(calls)==1: raise TelegramAPIError(400)\n'
                         '    await '
                         "deliver(method,{'text':'🙂','entities':[emoji(0)]},reply_markup={'inline_keyboard':[[button]]})\n"
                         '    assert len(calls)==2\n'
                         "    assert calls[1]['entities']==[]\n"
                         "    assert 'icon_custom_emoji_id' not in "
                         "calls[1]['reply_markup']['inline_keyboard'][0][0]\n"
                         '    assert '
                         "calls[1]['reply_markup']['inline_keyboard'][0][0]['callback_data']=='tm:edit:help'\n"
                         '\n'
                         '\n'
                         '@pytest.mark.asyncio\n'
                         'async def test_cancel_reply_and_source_preserve_placeholders(db):\n'
                         '    api=API()\n'
                         "    await run(db,api,'/settext mute Test {uid}')\n"
                         "    await click(db,api,'tm:source:mute',2)\n"
                         "    assert sent(api)[-1]['text']=='Test {uid}'\n"
                         "    await click(db,api,'tm:edit:help',3)\n"
                         "    await draft(db,api,'/cancel',number=4)\n"
                         '    assert await editor(db,api).load(-100123,1,None) is None\n'
                         "    await run(db,api,'/settings',5)\n"
                         "    assert 'tm:page:1' in str(sent(api)[-1]['reply_markup'])\n",
 'tests/test_mute_target.py': 'import pytest\n'
                              'from test_guardian import db, update\n'
                              'from test_access import API\n'
                              'from test_texts import run, sent\n'
                              '\n'
                              'TARGET=8549615756\n'
                              '\n'
                              '\n'
                              '@pytest.mark.asyncio\n'
                              "@pytest.mark.parametrize('reply_actor',[None,1,999,5,42])\n"
                              'async def test_explicit_mute_id_wins_over_quoted_sender(db,reply_actor):\n'
                              '    api=API()\n'
                              "    reply=update('Quoted message',actor=reply_actor)['message'] if "
                              'reply_actor else None\n'
                              "    await run(db,api,f'/mute {TARGET} 10m',actor=1,reply=reply)\n"
                              "    calls=[p for m,p in api.calls if m=='restrictChatMember']\n"
                              "    assert len(calls)==1 and calls[0]['user_id']==TARGET\n"
                              "    assert f'ID {TARGET}' in sent(api)[-1]['text']\n"
                              '\n'
                              '\n'
                              '@pytest.mark.asyncio\n'
                              'async def '
                              'test_reply_style_mute_still_works_and_numeric_ban_reason_not_a_target(db):\n'
                              '    api=API()\n'
                              "    reply=update('Person',actor=TARGET)['message']\n"
                              "    await run(db,api,'/mute 10m нарушение',actor=5,reply=reply)\n"
                              '    assert [p for m,p in api.calls if '
                              "m=='restrictChatMember'][-1]['user_id']==TARGET\n"
                              "    await run(db,api,'/ban 3 нарушения',number=2,actor=5,reply=reply)\n"
                              '    assert [p for m,p in api.calls if '
                              "m=='banChatMember'][-1]['user_id']==TARGET\n"
                              "    assert '3 нарушения' in sent(api)[-1]['text']\n"
                              '\n'
                              '\n'
                              '@pytest.mark.asyncio\n'
                              "@pytest.mark.parametrize('uid,reason',[(1,'аккаунт, отправивший'),(999,'я, "
                              "бот'),(2,'администратор'),(5,'username @ivan22350')])\n"
                              'async def test_precise_denial_identifies_selected_target(db,uid,reason):\n'
                              '    api=API()\n'
                              '    s=await db.settings(-100123)\n'
                              "    s['texts']={'error_protected':{'text':'Old ambiguous "
                              "error','entities':[]}}\n"
                              '    await db.save_settings(-100123,s)\n'
                              "    await run(db,api,f'/mute {uid} 10m',actor=1)\n"
                              "    assert str(uid) in sent(api)[-1]['text']\n"
                              "    assert reason in sent(api)[-1]['text']\n"
                              "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                              '\n'
                              '\n'
                              '@pytest.mark.asyncio\n'
                              "@pytest.mark.parametrize('target',['0','99999999999999999999999999999'])\n"
                              'async def test_invalid_explicit_id_never_falls_back_to_reply(db,target):\n'
                              '    api=API()\n'
                              "    await run(db,api,f'/mute {target} "
                              "10m',actor=1,reply=update(actor=TARGET)['message'])\n"
                              "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n",
 'tests/test_texts.py': 'import pytest\n'
                        '\n'
                        'from test_guardian import Telegram, bot, db, update\n'
                        'from guardian_cf.db import Database\n'
                        'from guardian_cf.telegram import Message, TelegramAPIError\n'
                        'from guardian_cf.texts import extract, render, units\n'
                        'from guardian_cf.webhook import process_update\n'
                        '\n'
                        '\n'
                        'async def run(db, api, text, number=1, actor=1, reply=None, entities=None):\n'
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
                        'async def test_inline_template_persists_unicode_and_renders_after_mute(db):\n'
                        '    api = Telegram()\n'
                        '    prefix = "/settext@guardbot mute "\n'
                        '    text = "{uid} 🔇 {minutes} мин. {reason}"\n'
                        '    await run(db, api, prefix+text, entities=[emoji(units(prefix+"{uid} "))])\n'
                        '    assert (await '
                        'Database(db.binding).settings(-100123))["texts"]["mute"]["entities"][0]["offset"] '
                        '== 6\n'
                        '    await run(db, api, "/mute 5 1m <b>🙂</b>", 2)\n'
                        '    result = sent(api)[-1]\n'
                        '    assert result["text"] == "5 🔇 1 мин. <b>🙂</b>"\n'
                        '    assert result["entities"] == [emoji(2)]\n'
                        '    assert "parse_mode" not in result\n'
                        '    assert len([1 for m, _ in api.calls if m == "restrictChatMember"]) == 1\n'
                        '    assert "texts" not in await db.settings(-100456)\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        '@pytest.mark.parametrize("command", ["/settext ping changed", "/resettext ping", '
                        '"/edit changed", "/texts", "/emoji"])\n'
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
                        '    source.update(caption="🙂 Правила", caption_entities=[emoji(0), {"type": "bold", '
                        '"offset": 3, "length": 7}])\n'
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
                        '    await run(db, api, "/edit 🙂 Новый текст", reply=source, entities=[emoji(6)])\n'
                        '    edited = next(p for m, p in api.calls if m == "editMessageText")\n'
                        '    assert edited["text"] == "🙂 Новый текст"\n'
                        '    assert edited["entities"] == [emoji(0)]\n'
                        '    assert edited["message_id"] == source["message_id"]\n'
                        '    assert edited["reply_markup"] == source["reply_markup"]\n'
                        '    assert (await db.logs(-100123))[0]["action"] == "edit_message"\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        '@pytest.mark.parametrize("kind", ["human", "otherbot", "forward", "otherchat", '
                        '"channel", "media", "missing"])\n'
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
                        '    assert (await db.settings(-100123))["texts"]["ping"]["text"] == "good"\n'
                        '    assert "Неизвестные" in sent(api)[-1]["text"]\n'
                        '\n'
                        '\n'
                        'def test_utf16_substitution_updates_bold_and_custom_emoji():\n'
                        '    rich = {"text": "🙂 {name} 🔇", "entities": [\n'
                        '        {"type": "bold", "offset": 3, "length": 6}, emoji(10)]}\n'
                        '    result = render(rich, {"name": "A🙂Б"})\n'
                        '    assert result["text"] == "🙂 A🙂Б 🔇"\n'
                        '    assert result["entities"] == [{"type": "bold", "offset": 3, "length": 4}, '
                        'emoji(8)]\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_custom_emoji_rejection_retries_text_only_never_mute(db):\n'
                        '    class RejectEmoji(Telegram):\n'
                        '        async def __call__(self, method, params):\n'
                        '            result = await super().__call__(method, params)\n'
                        '            if method == "sendMessage" and any(e["type"] == "custom_emoji" for e in '
                        'params.get("entities", [])):\n'
                        '                raise TelegramAPIError(400)\n'
                        '            return result\n'
                        '    api = RejectEmoji()\n'
                        '    prefix = "/settext mute "\n'
                        '    await run(db, api, prefix+"🔇 {uid}", entities=[emoji(units(prefix))])\n'
                        '    await run(db, api, "/mute 5 1m", 2)\n'
                        '    assert sent(api)[-1]["text"] == "🔇 5"\n'
                        '    assert sent(api)[-1]["entities"] == []\n'
                        '    assert len([1 for m, _ in api.calls if m == "restrictChatMember"]) == 1\n'
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
                        '    await process_update(update("/settext ping bad", update_id=2, edited=True), db, '
                        'bot(api), "guardbot")\n'
                        '    assert "texts" not in await db.settings(-100123)\n'
                        '\n'
                        '\n'
                        '@pytest.mark.asyncio\n'
                        'async def test_help_and_start_rich_templates_are_chat_scoped_and_resettable(db):\n'
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
                        "        assert (await db.settings(-100123))['texts'][key]['text'] == body.strip(), "
                        'key\n'
                        "        await run(db, api, '/previewtext '+key, number+1)\n"
                        "        expected = render({'text':body.strip()}, {f: PREVIEW.get(f, 'Пример') for f "
                        "in fields})['text']\n"
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
                        "    assert any(m == 'answerCallbackQuery' and p['text'] == 'Готово!' for m,p in "
                        'api.calls)\n'
                        "    result = next(p for m,p in api.calls if m == 'editMessageText')\n"
                        "    assert result['text'] == 'Настройки: 7; слов 0'\n"
                        "    assert result['reply_markup']['inline_keyboard'][1][0]['text'] == '✅ Ссылки'\n"
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
                        "    ('check','/check','Удаление {delete}; мут {restrict}','Удаление ✅; мут ✅'),\n"
                        "    ('warnings_self','/warnings','Предов: {count}','Предов: 0'),\n"
                        "    ('warnings','/warnings 5','У {uid}: {count}','У 5: 0'),\n"
                        "    ('unwarn','/unwarn 5','Осталось {count}','Осталось 0'),\n"
                        "    ('resetwarns','/resetwarns 5','Сброшено для {uid}','Сброшено для 5'),\n"
                        "    ('words_saved','/word add test','Записал','Записал'),\n"
                        "    ('setting_saved','/set warn_limit 5','Настроено: {setting}','Настроено: "
                        "warn_limit 5'),\n"
                        "    ('emoji_empty','/emoji','Нет эмодзи','Нет эмодзи'),\n"
                        "    ('error_mute_duration','/mute 5','Укажи время','Укажи время'),\n"
                        "    ('validation_error','/mute 5 xyz','Проверь: {detail}','Проверь: Время: 10m, 2h, "
                        "7d (или 10м, 2ч, 7д).'),\n"
                        '])\n'
                        'async def test_new_command_outputs_use_saved_templates(db, key, command, body, '
                        'expected):\n'
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
                        "    await run(db, api, prefix+'🙂 {reason}', entities=[emoji(units(prefix))])\n"
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
                        "    assert (await db.settings(-100123))['texts']['settings']['text'] == 'good'\n"
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
                        "    assert all(units(p['text']) <= 4096 for p in parts)\n",
 'tests/test_usernames.py': 'import pytest\n'
                            'from test_guardian import db, update\n'
                            'from test_access import API as BaseAPI\n'
                            'from test_texts import run, sent\n'
                            'from guardian_cf.usernames import Usernames, key\n'
                            'from guardian_cf.db import Database\n'
                            'from guardian_cf.telegram import wrap, TelegramAPIError\n'
                            'from guardian_cf.webhook import process_update\n'
                            'from test_guardian import bot\n'
                            '\n'
                            'CHAT=-100123\n'
                            'TARGET=8549615756\n'
                            'OTHER=1311500781\n'
                            '\n'
                            '\n'
                            'class API(BaseAPI):\n'
                            '    def __init__(self):\n'
                            '        super().__init__()\n'
                            "        self.target_name='abamako999'\n"
                            "        self.target_status='restricted'\n"
                            '        self.target_error=None\n'
                            '\n'
                            '    async def __call__(self,method,params):\n'
                            '        result=await super().__call__(method,params)\n'
                            "        if method=='getChatMember' and params['user_id']==TARGET:\n"
                            '            if self.target_error: raise TelegramAPIError(self.target_error)\n'
                            "            return {'status':self.target_status,'is_member':True,\n"
                            '                    '
                            "'user':{'id':TARGET,'is_bot':False,'first_name':'Target','username':self.target_name}}\n"
                            "        if method=='getChatMember' and params['user_id']==OTHER:\n"
                            '            return '
                            "{'status':'administrator','user':{'id':OTHER,'is_bot':False,'first_name':'Other','username':'otheradmin'}}\n"
                            '        return result\n'
                            '\n'
                            '\n'
                            "def person(uid=TARGET,username='abamako999',chat=CHAT):\n"
                            "    msg=update('Old message',actor=uid)['message']\n"
                            "    msg['from']['username']=username\n"
                            "    msg['chat']['id']=chat\n"
                            '    return msg\n'
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            'async def test_unknown_username_never_uses_reply_author(db):\n'
                            '    api=API()\n'
                            "    await run(db,api,'/unmute @abamako999,',reply=person(OTHER,'otheradmin'))\n"
                            "    assert 'Не удалось подтвердить ID пользователя @abamako999' in "
                            "sent(api)[-1]['text']\n"
                            "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                            "    assert not any(m=='getChatMember' and p['user_id']==OTHER for m,p in "
                            'api.calls)\n'
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            'async def '
                            'test_known_username_wins_over_unrelated_reply_and_survives_restart(db):\n'
                            '    api=API()\n'
                            "    await Usernames(db,bot(api)).remember(CHAT,wrap(person()['from']))\n"
                            "    await run(Database(db.binding),api,'/unmute "
                            "@ABAMAKO999,',reply=person(OTHER,'otheradmin'))\n"
                            "    calls=[p for m,p in api.calls if m=='restrictChatMember']\n"
                            "    assert len(calls)==1 and calls[0]['user_id']==TARGET\n"
                            "    assert all(calls[0]['permissions'].values())\n"
                            "    assert not any(m=='getChatMember' and p['user_id']==OTHER for m,p in "
                            'api.calls)\n'
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            'async def test_reply_learns_username_and_no_username_reply_unmute_works(db):\n'
                            '    api=API()\n'
                            "    await run(db,api,'/unmute @abamako999,',reply=person())\n"
                            '    assert [p for m,p in api.calls if '
                            "m=='restrictChatMember'][-1]['user_id']==TARGET\n"
                            "    await run(db,api,'/unmute',number=2,reply=person())\n"
                            '    assert [p for m,p in api.calls if '
                            "m=='restrictChatMember'][-1]['user_id']==TARGET\n"
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            "@pytest.mark.parametrize('command,method',[\n"
                            "    ('/mute @abamako999, 10m','restrictChatMember'),('/ban @abamako999 "
                            "нарушение','banChatMember'),\n"
                            "    ('/unban @abamako999,','unbanChatMember'),('/kick "
                            "@abamako999','banChatMember'),\n"
                            "    ('/warn @abamako999 причина',None),\n"
                            '])\n'
                            'async def test_username_moderation_commands(db,command,method):\n'
                            "    api=API(); api.target_status='member'\n"
                            "    await Usernames(db,bot(api)).remember(CHAT,wrap(person()['from']))\n"
                            "    await run(db,api,command,actor=5,reply=person(OTHER,'otheradmin'))\n"
                            '    if method:\n'
                            "        assert [p for m,p in api.calls if m==method][-1]['user_id']==TARGET\n"
                            '    else:\n'
                            '        assert await db.count(CHAT,TARGET)==1\n'
                            '        assert await db.count(CHAT,OTHER)==0\n'
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            "@pytest.mark.parametrize('variation',['renamed','expired','otherchat','api400','api403','api429'])\n"
                            'async def '
                            'test_unverified_cached_username_never_executes_or_falls_back(db,variation):\n'
                            '    api=API(); names=Usernames(db,bot(api))\n'
                            "    await names.remember(CHAT if variation!='otherchat' else "
                            "-100456,wrap(person()['from']))\n"
                            "    if variation=='renamed': api.target_name='newname'\n"
                            "    if variation=='expired': await db.run('UPDATE ephemeral SET expires=0 WHERE "
                            "key=?',key(CHAT,'abamako999'))\n"
                            "    if variation.startswith('api'): api.target_error=int(variation[3:])\n"
                            "    await run(db,api,'/unmute @abamako999,',reply=person(6,'unrelated'))\n"
                            "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            'async def test_speaker_username_learned_and_privileges_not_bypassed(db):\n'
                            '    api=API()\n'
                            "    message=update('Hello',actor=TARGET)\n"
                            "    message['message']['from']['username']='abamako999'\n"
                            "    await process_update(message,db,bot(api),'guardbot')\n"
                            "    assert (await db.first('SELECT value FROM ephemeral WHERE "
                            "key=?',key(CHAT,'abamako999')))['value']==str(TARGET)\n"
                            "    await run(db,api,'/unmute @abamako999,',number=2,actor=6)\n"
                            "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                            "    assert 'доступна только' in sent(api)[-1]['text']\n"
                            "    api.target_status='administrator'\n"
                            "    await run(db,api,'/unmute @abamako999,',number=3,actor=1)\n"
                            "    assert 'администратор' in sent(api)[-1]['text'] and str(TARGET) in "
                            "sent(api)[-1]['text']\n"
                            "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            'async def test_explicit_unmute_id_wins_over_reply(db):\n'
                            '    api=API()\n'
                            "    await run(db,api,f'/unmute {TARGET}',reply=person(OTHER,'otheradmin'))\n"
                            '    assert [p for m,p in api.calls if '
                            "m=='restrictChatMember'][-1]['user_id']==TARGET\n"
                            '\n'
                            '\n'
                            '@pytest.mark.asyncio\n'
                            "@pytest.mark.parametrize('token',['@','@@abamako999','@abamako999/other'])\n"
                            'async def test_invalid_username_never_uses_reply(db,token):\n'
                            '    api=API()\n'
                            "    await run(db,api,'/unmute '+token,reply=person(6,'unrelated'))\n"
                            "    assert not any(m=='restrictChatMember' for m,_ in api.calls)\n"}

if __name__ == '__main__':
    prepare(Path(__file__).resolve().parent)
